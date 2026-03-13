"""SocraticBTC CLI — scrape and translate Bitcoin technical content."""

import click
from rich.console import Console

from scrapers import scrape_reviews, scrape_optech, fetch_reviews, fetch_optech
from pipeline import translate_content

console = Console()

# 소스별 fetcher 매핑
_FETCHERS = {
    "github": {"reviews": fetch_reviews, "optech": fetch_optech},
    "http": {"reviews": scrape_reviews, "optech": scrape_optech},
}


@click.group()
def cli():
    """SocraticBTC: Bitcoin Core PR Review & Optech Newsletter scraper + Korean translator."""
    pass


@cli.command()
@click.option(
    "--source",
    type=click.Choice(["reviews", "optech"]),
    required=True,
    help="Source to scrape: 'reviews' (Bitcoin Core PR Review Club) or 'optech' (Optech Newsletter).",
)
@click.option("--limit", default=5, help="Number of items to scrape.")
@click.option(
    "--mode",
    type=click.Choice(["http", "github"]),
    default="github",
    help="Fetch mode: 'github' (git clone, default) or 'http' (legacy HTTP scraping).",
)
def scrape(source: str, limit: int, mode: str):
    """Scrape content from the specified source."""
    console.print(f"[bold]Scraping: {source} (mode={mode})[/]")
    _FETCHERS[mode][source](limit=limit)


@cli.command()
@click.option(
    "--source",
    type=click.Choice(["reviews", "optech"]),
    required=True,
    help="Source to translate.",
)
@click.option("--limit", default=1, help="Number of items to translate (default 1 for testing).")
def translate(source: str, limit: int):
    """Translate scraped content to Korean."""
    console.print(f"[bold]Translating: {source} (limit={limit})[/]")
    translate_content(source, limit=limit)


@cli.command()
@click.option("--limit", default=999, help="Number of items to scrape per source (default: all).")
@click.option(
    "--mode",
    type=click.Choice(["http", "github"]),
    default="github",
    help="Fetch mode: 'github' (git clone, default) or 'http' (legacy HTTP scraping).",
)
def all(limit: int, mode: str):
    """Run full pipeline: fetch all sources, then translate."""
    console.print(f"[bold]Running full pipeline (mode={mode})...[/]")
    fetchers = _FETCHERS[mode]
    fetchers["reviews"](limit=limit)
    fetchers["optech"](limit=limit)
    translate_content("reviews", limit=limit)
    translate_content("optech", limit=limit)
    console.print("[bold green]Full pipeline complete.[/]")


if __name__ == "__main__":
    cli()
