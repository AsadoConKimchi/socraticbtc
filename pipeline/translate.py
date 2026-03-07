"""LLM-based translation pipeline using OpenAI API."""

import json
import os
from pathlib import Path

from openai import OpenAI
from rich.console import Console

console = Console()
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SYSTEM_PROMPT = (
    "You are a professional translator specializing in Bitcoin and cryptocurrency "
    "technical content. Translate the following English text into Korean. "
    "Preserve technical terms (e.g., UTXO, mempool, SegWit) in English where appropriate. "
    "Use natural, fluent Korean suitable for developers and technically-minded readers."
)


def translate_content(source: str) -> list[dict]:
    """Translate scraped content to Korean using OpenAI API.

    Args:
        source: Either 'reviews' or 'optech'.

    Returns:
        List of translated items.
    """
    input_path = DATA_DIR / f"{source}.json"
    if not input_path.exists():
        console.print(f"[red]No data found at {input_path}. Run scrape first.[/]")
        return []

    items = json.loads(input_path.read_text(encoding="utf-8"))
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        console.print("[yellow]OPENAI_API_KEY not set. Saving stub translations.[/]")
        results = []
        for item in items:
            results.append({
                "title": item["title"],
                "url": item["url"],
                "translated_title": f"[STUB] {item['title']}",
                "translated_content": "[STUB] Translation requires OPENAI_API_KEY.",
            })
        _save(source, results)
        return results

    client = OpenAI(api_key=api_key)
    results = []

    for item in items:
        console.print(f"  Translating: {item['title'][:60]}...")
        try:
            # Translate title
            title_resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Translate this title:\n{item['title']}"},
                ],
                max_tokens=200,
            )
            translated_title = title_resp.choices[0].message.content.strip()

            # Translate content (chunked if needed)
            content = item.get("content", "")
            if content:
                content_resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Translate:\n{content[:4000]}"},
                    ],
                    max_tokens=4000,
                )
                translated_content = content_resp.choices[0].message.content.strip()
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
