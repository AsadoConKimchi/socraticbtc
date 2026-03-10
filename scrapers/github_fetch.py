"""GitHub repo-based fetcher for Bitcoin Core Review Club and Optech Newsletter.

git clone --depth=1 으로 전체 마크다운 아카이브를 수집 (HTTP 스크래핑 불필요).
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console

console = Console()
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

REVIEWS_REPO = "https://github.com/bitcoin-core-review-club/website"
OPTECH_REPO = "https://github.com/bitcoinops/bitcoinops.github.io"


# --- YAML front matter 파서 ---

_FM_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FM_KEY_RE = re.compile(r"^(\w[\w-]*):\s*(.*)", re.MULTILINE)


_LIQUID_TAG_RE = re.compile(r"\{%[^%]*?%\}", re.DOTALL)
_LIQUID_VAR_RE = re.compile(r"\{\{[^}]*?\}\}")
_LIQUID_ATTR_RE = re.compile(r"\{:[^}]*?\}")


def _clean_liquid(text: str) -> str:
    """Liquid 템플릿 태그/변수/속성을 제거해 순수 마크다운만 남긴다."""
    text = _LIQUID_TAG_RE.sub("", text)
    text = _LIQUID_VAR_RE.sub("", text)
    text = _LIQUID_ATTR_RE.sub("", text)
    # 빈 줄 3개 이상 → 2개로 축소
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """YAML front matter를 파싱해 (metadata_dict, body_text) 반환."""
    m = _FM_BLOCK_RE.match(text)
    if not m:
        return {}, text
    fm_block = m.group(1)
    body = text[m.end():]
    meta: dict = {}
    for key, val in _FM_KEY_RE.findall(fm_block):
        # 인용부호 제거
        val = val.strip().strip('"').strip("'")
        meta[key] = val
    return meta, body


def _clone_repo(url: str, dest: Path) -> None:
    """Git shallow clone (depth=1)."""
    console.print(f"[bold blue]Cloning {url}...[/]")
    result = subprocess.run(
        ["git", "clone", "--depth=1", "--quiet", url, str(dest)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
    console.print(f"[green]Cloned to {dest}[/]")


# --- Reviews fetcher ---

def fetch_reviews(limit: int = 200) -> list[dict]:
    """bitcoin-core-review-club/website 레포에서 마크다운 수집."""
    tmp = Path(tempfile.mkdtemp())
    try:
        repo_dir = tmp / "reviews"
        _clone_repo(REVIEWS_REPO, repo_dir)

        posts_dir = repo_dir / "_posts"
        if not posts_dir.exists():
            raise RuntimeError(f"_posts directory not found in {repo_dir}")

        md_files = sorted(posts_dir.glob("*.md"), reverse=True)  # 최신순
        console.print(f"[green]Found {len(md_files)} review posts.[/]")

        results: list[dict] = []
        for md_file in md_files[:limit]:
            try:
                text = md_file.read_text(encoding="utf-8", errors="replace")
                meta, body = _parse_front_matter(text)

                title = meta.get("title", md_file.stem)
                # PR 번호 추출: 파일명 YYYY-MM-DD-PRNUMBER.md → PRNUMBER
                # 일부 파일명에 '#' 접두사가 있으므로 제거 (e.g. #33300 → 33300)
                pr_num = md_file.stem.split("-")[-1].lstrip("#")
                url = f"https://bitcoincore.reviews/{pr_num}"

                # Liquid 태그 제거 후 길이 제한
                content = _clean_liquid(body)[:8000]

                results.append({
                    "title": title,
                    "url": url,
                    "content": content,
                })
            except Exception as e:
                console.print(f"  [red]Error parsing {md_file.name}: {e}[/]")

        DATA_DIR.mkdir(exist_ok=True)
        out_path = DATA_DIR / "reviews.json"
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[bold green]Saved {len(results)} reviews to {out_path}[/]")
        return results

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- Optech fetcher ---

def fetch_optech(limit: int = 300) -> list[dict]:
    """bitcoinops/bitcoinops.github.io 레포에서 뉴스레터 수집."""
    tmp = Path(tempfile.mkdtemp())
    try:
        repo_dir = tmp / "optech"
        _clone_repo(OPTECH_REPO, repo_dir)

        posts_dir = repo_dir / "_posts" / "en" / "newsletters"
        if not posts_dir.exists():
            raise RuntimeError(f"newsletters directory not found in {repo_dir}")

        md_files = sorted(posts_dir.glob("*.md"), reverse=True)  # 최신순
        console.print(f"[green]Found {len(md_files)} newsletter posts.[/]")

        results: list[dict] = []
        for md_file in md_files[:limit]:
            try:
                text = md_file.read_text(encoding="utf-8", errors="replace")
                meta, body = _parse_front_matter(text)

                title = meta.get("title", md_file.stem)
                # permalink 예: /en/newsletters/2024-01-03-newsletter-282/
                permalink = meta.get("permalink", "")
                if permalink:
                    url = f"https://bitcoinops.org{permalink}"
                else:
                    # permalink 없는 경우 파일명에서 재구성
                    slug = md_file.stem  # YYYY-MM-DD-newsletter-NNN
                    url = f"https://bitcoinops.org/en/newsletters/{slug}/"

                # Liquid 태그 제거 후 길이 제한
                content = _clean_liquid(body)[:8000]

                results.append({
                    "title": title,
                    "url": url,
                    "content": content,
                })
            except Exception as e:
                console.print(f"  [red]Error parsing {md_file.name}: {e}[/]")

        DATA_DIR.mkdir(exist_ok=True)
        out_path = DATA_DIR / "optech.json"
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[bold green]Saved {len(results)} newsletters to {out_path}[/]")
        return results

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
