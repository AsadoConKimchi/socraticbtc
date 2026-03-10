# SocraticBTC

**Live site:** https://site-rouge-theta-41.vercel.app

A Python-based scraper and Korean translation pipeline for Bitcoin technical content.

## What It Does

- **Bitcoin Core PR Review Club**: Scrapes meeting notes from [bitcoincore.reviews](https://bitcoincore.reviews) — a weekly study group where developers review Bitcoin Core pull requests.
- **Bitcoin Optech Newsletter**: Scrapes newsletters from [bitcoinops.org](https://bitcoinops.org/en/newsletters/) — a weekly summary of Bitcoin protocol development, Lightning Network updates, and technical proposals.
- **Korean Translation**: Translates scraped content into Korean using LLM (OpenAI API), making Bitcoin technical resources accessible to Korean-speaking developers and enthusiasts.

## Setup

```bash
pip install -e .
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

## Usage

```bash
# Scrape Bitcoin Core PR review meetings
python cli.py scrape --source reviews

# Scrape Optech newsletters
python cli.py scrape --source optech

# Translate scraped content
python cli.py translate --source reviews
python cli.py translate --source optech

# Run full pipeline (scrape + translate all)
python cli.py all
```

## Project Structure

```
socraticbtc/
  cli.py                  # Click CLI entry point
  scrapers/
    bitcoincore_reviews.py  # PR Review Club scraper
    optech.py               # Optech Newsletter scraper
  pipeline/
    translate.py            # LLM translation (OpenAI)
  data/                     # Scraped and translated output
```

## License

MIT
