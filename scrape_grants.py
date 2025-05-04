"""
scrape_grants.py
Uses saved cookies to pull all grant listings into um_grants.csv.
Adjust BASE and CSS selectors for other portals.
"""

import pickle
import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.parse import urlparse, urlunparse
import argparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

COOKIE_PATH = Path("cookies.pkl")
DEFAULT_BASE = "https://umich.infoready4.com"

HEADERS = {"User-Agent": "UMich Grant Scraper (contact: tlasisi@umich.edu)"}

def clean_base(url: str) -> str:
    """
    Strip URL fragments or query strings and trailing slashes so that
    '?page=N' can be appended safely.
    """
    parsed = urlparse(url)
    cleaned = parsed._replace(fragment="", query="")
    return urlunparse(cleaned).rstrip("/")

def load_session() -> requests.Session:
    if not COOKIE_PATH.exists():
        raise RuntimeError("cookies.pkl not found. Run login_and_save_cookies.py first.")
    with COOKIE_PATH.open("rb") as fh:
        cookie_jar = pickle.load(fh)
    sess = requests.Session()
    sess.headers.update(HEADERS)
    for c in cookie_jar:
        sess.cookies.set(c["name"], c["value"], domain=c["domain"])
    return sess

def parse_page(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("div.opportunity-row")  # tweak selector if needed
    results = []
    for row in rows:
        title_el = row.select_one("h3 a")
        results.append(
            dict(
                title=title_el.get_text(strip=True),
                link=urljoin(base_url, title_el["href"]),
                deadline=row.select_one("span.deadline").get_text(strip=True),
                synopsis=row.select_one("p.synopsis").get_text(strip=True),
            )
        )
    return results

def scrape_all(sess: requests.Session, base_url: str) -> list[dict]:
    records, page = [], 1
    while True:
        url = f"{base_url}?page={page}"
        r = sess.get(url, timeout=20)
        if r.status_code != 200:
            break
        batch = parse_page(r.text, base_url)
        if not batch:
            break
        records.extend(batch)
        print(f"Page {page}: {len(batch)} items")
        page += 1
        time.sleep(1)
    return records

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape one or more InfoReady-like portals into a CSV."
    )
    parser.add_argument(
        "--base",
        action="append",
        help="Base listings URL (repeatable). Defaults to the UM InfoReady host.",
    )
    args = parser.parse_args()

    # Clean and deduplicate base URLs
    base_urls = args.base if args.base else [DEFAULT_BASE]
    base_urls = list({clean_base(b) for b in base_urls})

    sess = load_session()
    all_rows = []
    for b in base_urls:
        print(f"\n🔗  Scraping {b}")
        rows = scrape_all(sess, b)
        for row in rows:
            row["site"] = b
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    df.to_csv("um_grants.csv", index=False)
    print(f"\nSaved {len(df)} total rows → um_grants.csv")

if __name__ == '__main__':
    main()