#!/usr/bin/env python3
"""
Bitcoin 기술 콘텐츠 한국어 번역 스크립트.
claude CLI를 사용하여 reviews.json / optech.json → reviews_ko.json / optech_ko.json 번역.

사용법:
  python3 translate_batch.py daily [count] [model]
  # 미번역 항목 중 count건을 번역 (기본 20건, 모델 기본 sonnet)
"""

import json
import re
import subprocess
import sys
import os
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

TRANSLATE_PROMPT = """You are a Bitcoin technical content translator (English → Korean).

The source is a raw Markdown file that may contain Jekyll/Liquid template tags and HTML. Your job is to produce clean, readable Korean Markdown.

## PREPROCESSING (do before translating)
- **Strip** all Jekyll/Liquid tags: `{% ... %}`, `{%- ... -%}`, `{{ ... }}` — remove them entirely, keep only their visible text content if any.
- **Strip** raw HTML tags (`<div>`, `<a href=...>`, `<br>`, `<p>`, etc.) — keep the inner text only.
- **Unescape** `\\n`, `\\t` etc. into real newlines/tabs.
- Remove YAML front matter (`---` blocks at the top) if present.

## TRANSLATION RULES

**1. Keep in English (do NOT translate):**
- Bitcoin/crypto terms: UTXO, mempool, SegWit, taproot, P2WSH, CPFP, RBF, IBD, BIP, scriptPubKey, nonce, hash, block, node, wallet, peer, fee, relay, orphan, coinbase, PSBT, descriptor, signet, mainnet, testnet
- Code identifiers: function/variable/class names like `CBlockIndex`, `CTxDestination`, `GetBlockHash`
- GitHub references: PR #1234, issue #567, commit hashes
- URLs, numbers, version numbers (v26.0 etc.)

**2. Natural Korean (경어체):**
Translate fluidly — not word-for-word. Use natural Korean technical writing. Avoid awkward literal translations.

**3. Markdown formatting (CRITICAL — this is the most important rule):**

Structure the output with rich Markdown:
- `## 섹션 제목` for major sections (Notes→노트, Questions→질문, Meeting Log→회의 로그, Summary→요약)
- `### 소제목` for subsections
- **Bold** key concepts and important terms on first mention: e.g. **cluster linearization**, **eviction 전략**
- Blank line between every paragraph — never run paragraphs together
- Bullet lists with `-` for enumerations; numbered lists `1.` for steps
- Inline code backticks for all code, function names, RPC names, file paths: e.g. `getblocktemplate`, `src/net.cpp`
- Code blocks (` ``` `) for multi-line code or command examples
- Blockquotes `>` for quoted text or important callouts
- IRC meeting logs: each line as `**nickname**: 번역된 발언` — one per line, blank line between speakers

**4. Completeness:**
Translate EVERY paragraph, bullet, and question. Do not skip or summarize anything.

**5. Output:**
Reply with ONLY the translated Markdown. No preamble, no "Here is the translation", no explanation.

---
CONTENT TO TRANSLATE:
"""

# 분할 번역 시 사용할 헤더 패턴
SECTION_HEADER_RE = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)

# 최소 번역 길이 비율 (원문 대비)
MIN_TRANSLATION_RATIO = 0.4


def translate_text(text, model="sonnet", max_retries=3, timeout=300):
    """claude CLI를 사용하여 텍스트 번역"""
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    prompt = TRANSLATE_PROMPT + text

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["claude", "-p", "--model", model, prompt],
                capture_output=True, text=True, timeout=timeout, env=env
            )
            if result.returncode == 0 and result.stdout.strip():
                translated = result.stdout.strip()
                return translated
            else:
                print(f"  ERROR (attempt {attempt+1}): {result.stderr[:200]}", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT (attempt {attempt+1})", file=sys.stderr)
        except Exception as e:
            print(f"  EXCEPTION (attempt {attempt+1}): {e}", file=sys.stderr)

        wait = min(5 * (2 ** attempt), 30)
        print(f"  Waiting {wait}s before retry...")
        time.sleep(wait)

    return None


def split_by_sections(text, max_chunk_size=6000):
    """헤더 기준으로 텍스트를 분할. 각 청크가 max_chunk_size 이하가 되도록."""
    headers = list(SECTION_HEADER_RE.finditer(text))

    if not headers:
        # 헤더가 없으면 줄바꿈 기준으로 분할
        lines = text.split("\n")
        chunks = []
        current = []
        current_len = 0
        for line in lines:
            if current_len + len(line) > max_chunk_size and current:
                chunks.append("\n".join(current))
                current = [line]
                current_len = len(line)
            else:
                current.append(line)
                current_len += len(line) + 1
        if current:
            chunks.append("\n".join(current))
        return chunks

    # 헤더 기준 분할
    chunks = []
    # 첫 헤더 이전 내용
    if headers[0].start() > 0:
        preamble = text[:headers[0].start()].strip()
        if preamble:
            chunks.append(preamble)

    for i, header in enumerate(headers):
        start = header.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        section = text[start:end].strip()
        if section:
            # 섹션이 너무 크면 추가 분할
            if len(section) > max_chunk_size:
                sub_chunks = _split_large_section(section, max_chunk_size)
                chunks.extend(sub_chunks)
            else:
                chunks.append(section)

    # 인접한 작은 청크들을 합침
    merged = []
    current = ""
    for chunk in chunks:
        if len(current) + len(chunk) + 2 <= max_chunk_size:
            current = current + "\n\n" + chunk if current else chunk
        else:
            if current:
                merged.append(current)
            current = chunk
    if current:
        merged.append(current)

    return merged


def _split_large_section(text, max_size):
    """큰 섹션을 줄바꿈 기준으로 분할"""
    lines = text.split("\n")
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        if current_len + len(line) > max_size and current:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def translate_long_content(text, model="sonnet"):
    """긴 콘텐츠를 분할 번역 후 합침"""
    if len(text) <= 6000:
        return translate_text(text, model)

    chunks = split_by_sections(text, max_chunk_size=6000)
    print(f"    Content split into {len(chunks)} chunks ({len(text)} chars total)")

    translated_parts = []
    for i, chunk in enumerate(chunks):
        print(f"    Translating chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
        translated = translate_text(chunk, model)
        if translated is None:
            print(f"    FAILED to translate chunk {i+1}", file=sys.stderr)
            return None
        translated_parts.append(translated)
        # API rate limit 대비
        if i < len(chunks) - 1:
            time.sleep(2)

    return "\n\n".join(translated_parts)


def validate_translation(original, translated):
    """번역 결과 검증: 길이 비율 체크"""
    if not translated:
        return False, "empty translation"
    ratio = len(translated) / len(original)
    if ratio < MIN_TRANSLATION_RATIO:
        return False, f"too short (ratio={ratio:.2f}, min={MIN_TRANSLATION_RATIO})"
    return True, f"ok (ratio={ratio:.2f})"


def load_json(path):
    """JSON 파일 로드"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    """JSON 파일 저장"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def translate_daily(count=20, model="sonnet"):
    """미번역 항목 중 count건을 번역 (reviews + optech 합산)"""
    sources = [
        ("reviews", os.path.join(DATA_DIR, "reviews.json"), os.path.join(DATA_DIR, "reviews_ko.json")),
        ("optech", os.path.join(DATA_DIR, "optech.json"), os.path.join(DATA_DIR, "optech_ko.json")),
    ]

    total_done = 0
    half = count // 2  # 각 소스별 절반씩

    for source_name, src_path, ko_path in sources:
        items = load_json(src_path)
        translated = load_json(ko_path)
        translated_urls = {r["url"] for r in translated}

        # 미번역 항목 필터
        pending = [item for item in items if item["url"] not in translated_urls]
        to_translate = pending[:half]

        if not to_translate:
            print(f"\n[{source_name}] All {len(items)} items already translated!")
            continue

        print(f"\n{'='*60}")
        print(f"[{source_name}] {len(translated)}/{len(items)} done, translating {len(to_translate)} more...")
        print(f"{'='*60}")

        for i, item in enumerate(to_translate):
            print(f"\n  [{i+1}/{len(to_translate)}] {item['title'][:70]}...")

            # 제목 번역
            translated_title = translate_text(item["title"], model)
            if not translated_title:
                print(f"  SKIP: title translation failed", file=sys.stderr)
                continue

            # 본문 번역 (긴 콘텐츠는 분할)
            translated_content = translate_long_content(item["content"], model)

            # 검증
            valid, msg = validate_translation(item["content"], translated_content)
            if not valid:
                print(f"  WARNING: {msg} — retrying with full content...")
                # 재시도: 전체를 한 번에 번역 시도 (더 긴 타임아웃)
                translated_content = translate_text(item["content"], model, timeout=600)
                valid2, msg2 = validate_translation(item["content"], translated_content)
                if not valid2:
                    print(f"  SKIP: validation failed after retry ({msg2})", file=sys.stderr)
                    continue

            print(f"  OK: {len(item['content'])} → {len(translated_content)} chars ({msg})")

            translated.append({
                "title": item["title"],
                "url": item["url"],
                "translated_title": translated_title,
                "translated_content": translated_content,
            })

            # 매 항목마다 저장 (중단 대비)
            save_json(ko_path, translated)
            total_done += 1

            # API rate limit 대비
            time.sleep(1)

        print(f"\n[{source_name}] Now {len(translated)}/{len(items)} items translated")

    print(f"\n{'='*60}")
    print(f"Daily batch complete: {total_done} items translated")
    print(f"{'='*60}")
    return total_done


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 translate_batch.py daily [count] [model]")
        print("  count: 번역할 항목 수 (기본 20)")
        print("  model: 사용할 모델 (기본 sonnet)")
        print()
        print("Example:")
        print("  python3 translate_batch.py daily 20 sonnet")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "daily":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        model = sys.argv[3] if len(sys.argv) > 3 else "sonnet"
        translate_daily(count, model)
    else:
        print(f"Unknown command: {cmd}")
        print("Available: daily")
        sys.exit(1)


if __name__ == "__main__":
    main()
