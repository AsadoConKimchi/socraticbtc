"""Scraper for Bitcoin Core PR Review Club (https://bitcoincore.reviews)."""

import json
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()
BASE_URL = "https://bitcoincore.reviews"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Meeting pages use PR number as path, e.g. /33300, /32489
_MEETING_PATH_RE = re.compile(r"^/\d+$")


def scrape_reviews(limit: int = 5) -> list[dict]:
    """Scrape recent PR review meeting pages from bitcoincore.reviews."""
    console.print(f"[bold blue]Fetching review index from {BASE_URL}...[/]")
    resp = httpx.get(BASE_URL, follow_redirects=True, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Meeting links are PR numbers like /33300
    meetings: list[dict] = []
    seen = set()

    for link in soup.select("a[href]"):
        href = link.get("href", "")
        if not _MEETING_PATH_RE.match(href):
            continue

        title = link.get_text(strip=True)
        if not title or href in seen:
            continue
        seen.add(href)

        url = f"{BASE_URL}{href}"
        meetings.append({"title": title, "url": url})

        if len(meetings) >= limit:
            break

    console.print(f"[green]Found {len(meetings)} meetings on index page.[/]")

    # Fetch each meeting page for details
    results = []
    for meeting in meetings:
        console.print(f"  Fetching: {meeting['title'][:60]}...")
        try:
            page = httpx.get(meeting["url"], follow_redirects=True, timeout=30)
            page.raise_for_status()
            page_soup = BeautifulSoup(page.text, "html.parser")

            # Extract main content
            content_el = (
                page_soup.select_one("article")
                or page_soup.select_one(".post-content")
                or page_soup.select_one("main")
            )
            content = content_el.get_text(separator="\n", strip=True) if content_el else ""

            results.append({
                "title": meeting["title"],
                "url": meeting["url"],
                "content": content[:5000],  # Cap content length
            })
        except httpx.HTTPError as e:
            console.print(f"  [red]Error fetching {meeting['url']}: {e}[/]")

    # Save to data/
    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / "reviews.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[bold green]Saved {len(results)} reviews to {out_path}[/]")

    return results
