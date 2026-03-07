"""Scraper for Bitcoin Optech Newsletter (https://bitcoinops.org/en/newsletters/)."""

import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()
BASE_URL = "https://bitcoinops.org/en/newsletters/"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def scrape_optech(limit: int = 5) -> list[dict]:
    """Scrape recent Optech newsletters."""
    console.print(f"[bold blue]Fetching newsletter index from {BASE_URL}...[/]")
    resp = httpx.get(BASE_URL, follow_redirects=True, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Newsletter index lists links to individual issues
    newsletters: list[dict] = []
    seen = set()

    for link in soup.select("a[href]"):
        href = link.get("href", "")
        if "/en/newsletters/" not in href or href == "/en/newsletters/":
            continue
        title = link.get_text(strip=True)
        if not title or href in seen:
            continue
        seen.add(href)

        url = href if href.startswith("http") else f"https://bitcoinops.org{href}"
        newsletters.append({"title": title, "url": url})

        if len(newsletters) >= limit:
            break

    console.print(f"[green]Found {len(newsletters)} newsletters on index page.[/]")

    # Fetch each newsletter page
    results = []
    for nl in newsletters:
        console.print(f"  Fetching: {nl['title'][:60]}...")
        try:
            page = httpx.get(nl["url"], follow_redirects=True, timeout=30)
            page.raise_for_status()
            page_soup = BeautifulSoup(page.text, "html.parser")

            content_el = (
                page_soup.select_one("article")
                or page_soup.select_one(".post-content")
                or page_soup.select_one("main")
            )
            content = content_el.get_text(separator="\n", strip=True) if content_el else ""

            results.append({
                "title": nl["title"],
                "url": nl["url"],
                "content": content[:8000],  # Newsletters are longer
            })
        except httpx.HTTPError as e:
            console.print(f"  [red]Error fetching {nl['url']}: {e}[/]")

    # Save to data/
    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / "optech.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[bold green]Saved {len(results)} newsletters to {out_path}[/]")

    return results
