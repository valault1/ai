#!/usr/bin/env python3
"""SEC EDGAR 10-K section fetcher.

Usage:
    python3 scripts/sec_fetcher.py AAPL --section 1 --section 1A --section 7
    python3 scripts/sec_fetcher.py AAPL --section 7 --output-dir reports/AAPL/

SEC EDGAR User-Agent requirement: all requests include 'StockAnalysis valault1@gmail.com'
"""

import argparse
import re
import sys
import time
from html import unescape
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SEC_HEADERS = {
    "User-Agent": "StockAnalysis valault1@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}


def get_cik(ticker: str) -> str:
    """Look up CIK from ticker via SEC company tickers JSON."""
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"].upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"CIK not found for ticker: {ticker}")


def get_latest_10k_url(cik: str) -> str:
    """Get the URL of the most recent 10-K primary document."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accession_numbers = filings.get("accessionNumber", [])
    primary_documents = filings.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form == "10-K":
            accession = accession_numbers[i].replace("-", "")
            doc = primary_documents[i]
            cik_int = int(cik)
            return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{doc}"

    raise ValueError(f"No 10-K filing found for CIK {cik}")


def fetch_filing_html(url: str) -> str:
    """Download the 10-K filing HTML."""
    time.sleep(0.5)  # Be polite to SEC servers
    resp = requests.get(url, headers=SEC_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def extract_section(html: str, section: str) -> str:
    """Extract text for a given Item section from 10-K HTML.

    Strips HTML tags, finds the Item N header, extracts until the next Item.
    Truncates to ~15,000 chars to keep agent context manageable.
    Uses a multi-match approach to avoid catching Table of Contents entries.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    text = unescape(text)

    # Normalize whitespace
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    section_pattern = re.compile(
        rf"(?:^|\n)\s*ITEM\s+{re.escape(section.upper())}[\s\.:\-]+",
        re.IGNORECASE | re.MULTILINE,
    )
    next_item_pattern = re.compile(
        r"(?:^|\n)\s*ITEM\s+\d+[A-Z]?[\s\.:\-]+",
        re.IGNORECASE | re.MULTILINE,
    )

    matches = list(section_pattern.finditer(text))
    if not matches:
        return f"Section Item {section} not found in filing. The filing may use a different format."

    # Pick the match that results in the longest extracted text (to avoid TOC)
    best_extracted = ""
    max_len = -1
    for match in matches:
        start = match.start()
        next_match = next_item_pattern.search(text, match.end())
        end = next_match.start() if next_match else len(text)
        extracted = text[start:end].strip()
        if len(extracted) > max_len:
            max_len = len(extracted)
            best_extracted = extracted

    if len(best_extracted) > 15000:
        best_extracted = best_extracted[:15000] + "\n\n[... truncated at 15,000 chars ...]"

    return best_extracted


def main():
    parser = argparse.ArgumentParser(description="Fetch SEC EDGAR 10-K sections")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument(
        "--section",
        action="append",
        default=[],
        metavar="N",
        help="10-K section to extract (e.g. 1, 1A, 7). Repeatable.",
    )
    parser.add_argument("--output-dir", help="Directory to save extracted section text files")
    args = parser.parse_args()

    sections = args.section if args.section else ["1"]
    ticker = args.ticker.upper()

    try:
        cik = get_cik(ticker)
        print(f"CIK: {cik}", file=sys.stderr)
        filing_url = get_latest_10k_url(cik)
        print(f"Filing URL: {filing_url}", file=sys.stderr)
        html = fetch_filing_html(filing_url)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    for section in sections:
        text = extract_section(html, section)
        print(f"\n{'='*60}")
        print(f"ITEM {section.upper()}")
        print(f"{'='*60}\n")
        print(text)

        if args.output_dir:
            out = Path(args.output_dir)
            out.mkdir(parents=True, exist_ok=True)
            fname = out / f"{ticker}_10k_section{section}.txt"
            fname.write_text(text)
            print(f"\nSaved: {fname}", file=sys.stderr)


if __name__ == "__main__":
    main()
