"""LLM-based translation pipeline using Anthropic Claude API."""

import json
import os
from pathlib import Path

import anthropic
from rich.console import Console

console = Console()
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SYSTEM_PROMPT = (
    "You are a professional translator specializing in Bitcoin and cryptocurrency "
    "technical content. Translate the following English text into Korean. "
    "Preserve technical terms (e.g., UTXO, mempool, SegWit) in English where appropriate. "
    "Use natural, fluent Korean suitable for developers and technically-minded readers."
)


def translate_content(source: str, limit: int = 1) -> list[dict]:
    """Translate scraped content to Korean using Anthropic Claude API.

    Args:
        source: Either 'reviews' or 'optech'.
        limit: Maximum number of items to translate (default 1 for testing).

    Returns:
        List of translated items.
    """
    input_path = DATA_DIR / f"{source}.json"
    if not input_path.exists():
        console.print(f"[red]No data found at {input_path}. Run scrape first.[/]")
        return []

    all_items = json.loads(input_path.read_text(encoding="utf-8"))

    # 기존 번역 로드 — 이미 번역된 항목은 skip (incremental)
    out_path = DATA_DIR / f"{source}_ko.json"
    existing: list[dict] = []
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))
    translated_urls = {
        e["url"] for e in existing
        if not e.get("translated_title", "").startswith("[STUB]")
    }

    pending = [i for i in all_items if i["url"] not in translated_urls]
    items = pending[:limit]
    console.print(f"  [dim]{len(translated_urls)} already translated, {len(pending)} pending, processing {len(items)}[/]")

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        console.print("[yellow]ANTHROPIC_API_KEY not set. Saving stub translations.[/]")
        results = list(existing)
        for item in items:
            if item["url"] not in {e["url"] for e in results}:
                results.append({
                    "title": item["title"],
                    "url": item["url"],
                    "translated_title": f"[STUB] {item['title']}",
                    "translated_content": "[STUB] Translation requires ANTHROPIC_API_KEY.",
                })
        _save(source, results)
        return results

    client = anthropic.Anthropic(api_key=api_key)
    # 기존 번역을 결과에 포함
    results = list(existing)

    for item in items:
        console.print(f"  Translating: {item['title'][:60]}...")
        try:
            # Translate title
            title_resp = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=200,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": f"Translate this title:\n{item['title']}"},
                ],
            )
            translated_title = title_resp.content[0].text.strip()

            # Translate content (chunked if needed)
            content = item.get("content", "")
            if content:
                content_resp = client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=4000,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": f"Translate:\n{content[:4000]}"},
                    ],
                )
                translated_content = content_resp.content[0].text.strip()
            else:
                translated_content = ""

            results.append({
                "title": item["title"],
                "url": item["url"],
                "translated_title": translated_title,
                "translated_content": translated_content,
            })
        except Exception as e:
            console.print(f"  [red]Translation error: {e}[/]")
            results.append({
                "title": item["title"],
                "url": item["url"],
                "translated_title": item["title"],
                "translated_content": f"[ERROR] {e}",
            })

    _save(source, results)
    return results


def _save(source: str, results: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / f"{source}_ko.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[bold green]Saved {len(results)} translations to {out_path}[/]")
