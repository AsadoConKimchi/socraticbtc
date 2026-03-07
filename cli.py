"""SocraticBTC CLI — scrape and translate Bitcoin technical content."""

import click
from rich.console import Console

from scrapers import scrape_reviews, scrape_optech
from pipeline import translate_content

console = Console()


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
def scrape(source: str, limit: int):
    """Scrape content from the specified source."""
    console.print(f"[bold]Scraping: {source}[/]")
    if source == "reviews":
        scrape_reviews(limit=limit)
    elif source == "optech":
        scrape_optech(limit=limit)


@cli.command()
@click.option(
    "--source",
    type=click.Choice(["reviews", "optech"]),
    required=True,
    help="Source to translate.",
)
def translate(source: str):
    """Translate scraped content to Korean."""
    console.print(f"[bold]Translating: {source}[/]")
    translate_content(source)


@cli.command()
@click.option("--limit", default=5, help="Number of items to scrape per source.")
def all(limit: int):
    """Run full pipeline: scrape all sources, then translate."""
    console.print("[bold]Running full pipeline...[/]")
    scrape_reviews(limit=limit)
    scrape_optech(limit=limit)
    translate_content("reviews")
    translate_content("optech")
    console.print("[bold green]Full pipeline complete.[/]")


if __name__ == "__main__":
    cli()
