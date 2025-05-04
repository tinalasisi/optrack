"""
scrape_grants.py
-----------------
Scrapes one or more InfoReady4 portals using cookies saved by
`login_and_save_cookies.py`.

Flow:
1. Try the fast JSON endpoint:  /Search/GetFundingOpportunities
2. If that returns 404/403, fall back to Selenium, open
   #/FundingOpportunities?page=N, wait for React to render, parse HTML.

Output: scraped_data_YYYYMMDD_HHMMSS[_suffix].json
"""

from __future__ import annotations

import argparse
import contextlib
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

import json
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup
from bs4 import NavigableString
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver

POPUP_DISMISSED = False  # cache so we do not repeatedly search once handled

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
COOKIE_PATH = Path("cookies.pkl")
DEFAULT_BASE = "https://umich.infoready4.com"
HEADERS = {"User-Agent": "UMich Grant Scraper (contact: tlasisi@umich.edu)"}
LISTING_PATH = "#homePage"   # known hash‑route for UM InfoReady listings

# --- modal + key filtering config ---------------------------
BLOCKED_KEY_PREFIXES = (
    "notice",                       # maintenance or other alerts
    "√ó infoready review",          # any stray banner headers
)
MAIN_DETAIL_SELECTORS = [
    "#competitionDetail",
    ".freeformCompetitionDetail",
    "div[id*='competitiondetail']",
]

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def clean_base(url: str) -> str:
    """Strip fragments / query-strings and trailing slashes."""
    p = urlparse(url)
    return urlunparse(p._replace(fragment="", query="")).rstrip("/")


def load_session() -> requests.Session:
    """
    Load cookies from file or create a new session with default headers.
    
    Falls back to a fresh session if cookies are inaccessible.
    """
    sess = requests.Session()
    sess.headers.update(HEADERS)
    
    if not COOKIE_PATH.exists():
        print("⚠️  No cookies.pkl found - using a session without cookies")
        return sess
    
    try:
        cookies = pickle.load(COOKIE_PATH.open("rb"))
        if not cookies:
            print("⚠️  Cookie file is empty - using a session without cookies")
            return sess
            
        for c in cookies:
            sess.cookies.set(c["name"], c["value"], domain=c["domain"])
        print(f"✅ Loaded {len(cookies)} cookies successfully")
    except (pickle.UnpicklingError, EOFError, ValueError, AttributeError, TypeError) as e:
        print(f"⚠️ Problem loading cookies ({type(e).__name__}). Using a session without cookies.")
        
    return sess


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def fetch_html_via_selenium(driver: webdriver.Chrome, url: str) -> str:
    """Navigate to *url* and return fully rendered HTML after the JS table appears."""

    driver.get(url)
    dismiss_any_modal(driver, timeout=3)

    # wait until the document is fully loaded, then for at least one listing anchor.
    try:
        WebDriverWait(driver, 8).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[competitionid]"))
        )
    except TimeoutException:
        # Listing anchors did not appear in time. Keep whatever HTML we have.
        print(f"⚠️  Timeout waiting for listing anchors on {url}")

    time.sleep(0.15)  # small extra pause for layout
    return driver.page_source

# ------------------------------------------------------------------
# Modal helper
# ------------------------------------------------------------------
def dismiss_any_modal(driver: webdriver.Chrome, timeout: int = 3) -> None:
    """
    Close *any* visible InfoReady modal dialog:
    1. Tick a 'do not show' checkbox/label if present.
    2. Click Close/×/OK.
    Caches POPUP_DISMISSED so we do this only once per session.
    """
    global POPUP_DISMISSED
    if POPUP_DISMISSED:
        return

    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.modal.in, div.modal[style*='display: block']")
            )
        )
    except TimeoutException:
        return  # no modal present

    # iterate through *all* visible modal overlays
    for modal in driver.find_elements(By.CSS_SELECTOR, "div.modal.in, div.modal[style*='display: block']"):
        if not modal.is_displayed():
            continue

        # 1) tick the 'do not show' checkbox if available
        try:
            cb = modal.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
            if cb.is_enabled() and not cb.is_selected():
                cb.click()
        except Exception:
            # fallback: click label containing the phrase
            labels = modal.find_elements(
                By.XPATH,
                ".//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'do not show')]"
            )
            for lab in labels:
                if lab.is_displayed() and lab.is_enabled():
                    lab.click()
                    break

        # 2) click a close / ok / × button
        for sel in ("button.close", "button[data-dismiss='modal']", "button", "a.close"):
            try:
                btn = modal.find_element(By.CSS_SELECTOR, sel)
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    break
            except Exception:
                continue

    # wait until all modals disappear
    try:
        WebDriverWait(driver, 5).until_not(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.modal.in, div.modal[style*='display: block']")
            )
        )
        POPUP_DISMISSED = True
    except TimeoutException:
        pass


# ------------------------------------------------------------------
# Long description extraction helper
# ------------------------------------------------------------------
def extract_long_description(dsoup: BeautifulSoup) -> str:
    """
    Best‑effort extraction of the long description block on a competition
    detail page.

    Strategy:
    1. Try direct selectors whose id/class contains the word 'description'
       (case‑insensitive) or the typical Knockout data‑bind attribute.
    2. If not found, locate an element whose *text* is exactly 'Description'
       and concatenate text from its next few siblings until we seem to hit
       another section heading.
    3. Fallback: return an empty string.
    """
    # --- 1) common direct selectors ---------------------------------------
    for sel in ("[id*='description' i]",
                "[class*='description' i]",
                "[data-bind*='Description']"):
        elem = dsoup.select_one(sel)
        if elem and elem.get_text(strip=True):
            return elem.get_text(" ", strip=True)

    # --- 2) heading + following siblings ----------------------------------
    heading = dsoup.find(string=re.compile(r"^\s*Description\s*$", re.I))
    if heading:
        container = heading.parent
        pieces = []
        for sib in container.next_siblings:
            if isinstance(sib, NavigableString):
                continue
            txt = sib.get_text(" ", strip=True)
            if not txt:
                continue
            # stop when another *short* heading/label is encountered
            if len(txt) < 50 and txt.endswith(":"):
                break
            pieces.append(txt)
            if len(pieces) >= 8:          # safety guard
                break
        if pieces:
            return " ".join(pieces)

    # --- 3) give up --------------------------------------------------------
    return ""


# ------------------------------------------------------------------
# Core scraping
# ------------------------------------------------------------------
def scrape_all(
    sess: requests.Session,
    base_url: str,
    max_pages: Optional[int] = None,
    max_items: Optional[int] = None,
) -> list[dict]:
    api = f"{base_url}/Search/GetFundingOpportunities"
    page = 1
    records: list[dict] = []
    use_json = True
    driver: webdriver.Chrome | None = None

    try:
        while True:
            if use_json:
                params = {"pageNumber": page, "pageSize": 25, "sort": "CloseDate"}
                r = sess.get(api, params=params, headers={"Accept": "application/json"}, timeout=20)
                if r.status_code in (403, 404):
                    print("🙈  JSON endpoint unavailable, switching to Selenium …")
                    use_json = False
                    driver = webdriver.Chrome()
                    continue
                r.raise_for_status()
                data = r.json()
                if not data:
                    break
                batch = [
                    dict(
                        title=i.get("Title", "").strip(),
                        deadline=i.get("CloseDateDisplay", "").strip(),
                        synopsis=i.get("Description", "").strip(),
                        link=f"{base_url}/FundingOppDetails?Id={i['Id']}",
                    )
                    for i in data
                ]
            else:
                # -----------------------------------------------------------
                # Rendered listing page → find every anchor for this page
                # -----------------------------------------------------------
                url = f"{base_url}/{LISTING_PATH}"   # homePage shows all current opportunities
                if page > 1:                         # UM instance has no paging on this view
                    break
                html = fetch_html_via_selenium(driver, url)
                soup = BeautifulSoup(html, "html.parser")

                anchors = soup.select("a[competitionid]")
                # honour --max-items before we start clicking links
                if max_items:
                    remaining = max_items - len(records)
                    if remaining <= 0:
                        break
                    anchors = anchors[: remaining]

                batch = []
                combined_sel = ",".join(MAIN_DETAIL_SELECTORS)
                for a in anchors:
                    # Extract row-level metadata from the listing table
                    row = a.find_parent("tr")
                    cells = row.find_all("td") if row else []
                    row_data: dict[str, str] = {}
                    if len(cells) >= 5:
                        row_data = {
                            "Due Date": cells[1].get_text(strip=True),
                            "Organizer": cells[2].get_text(strip=True),
                            "Category": cells[3].get_text(strip=True),
                            "Cycle": cells[4].get_text(strip=True),
                        }

                    # 1) quick info from the row
                    title_text = a.get_text(strip=True)
                    detail_url = urljoin(base_url, a["href"])
                    comp_id    = a.get("competitionid", "")

                    # 2) navigate to detail page
                    driver.get(detail_url)
                    dismiss_any_modal(driver, timeout=3)

                    # wait for the detail page to finish loading, then look for any selector
                    try:
                        WebDriverWait(driver, 10).until(
                            lambda d: d.execute_script("return document.readyState") == "complete"
                        )
                        WebDriverWait(driver, 8).until(
                            lambda d: d.find_elements(By.CSS_SELECTOR, combined_sel)
                        )
                    except TimeoutException:
                        print(f"⚠️  Timeout waiting for detail selectors on {detail_url}")

                    # after the container exists, make sure no modal HTML pollutes the page
                    driver.execute_script("document.querySelectorAll('div.modal').forEach(el => el.remove());")

                    dhtml = driver.page_source
                    dsoup = BeautifulSoup(dhtml, "html.parser")

                    # ---- generic key/value scrape inside main container ----
                    details = {}
                    container = None
                    for sel in MAIN_DETAIL_SELECTORS:
                        container = dsoup.select_one(sel)
                        if container:
                            break
                    container = container or dsoup  # fallback whole doc

                    for elem in container.select("div, span, td, li"):
                        txt = elem.get_text(" ", strip=True)
                        if ":" not in txt:
                            continue
                        key, val = map(str.strip, txt.split(":", 1))
                        if not key or not val:
                            continue
                        if key.lower().startswith(BLOCKED_KEY_PREFIXES):
                            continue
                        details[key] = val

                    # Explicit grab of long description block, if present
                    long_desc = extract_long_description(dsoup)

                    # 3) assemble record
                    # Merge listing metadata with detail-page key/value pairs
                    merged_details = { **row_data, **details }
                    record = {
                        "title": title_text,
                        "link": detail_url,
                        "competition_id": comp_id,
                        "description_full": long_desc,
                        "details": merged_details,  # Keep the original key name for backward compatibility
                    }

                    # skip pages that produced no real content
                    if not long_desc and not details:
                        driver.back()
                        time.sleep(0.5)
                        continue

                    batch.append(record)

                    if max_items and len(records) >= max_items:
                        break

                    # 4) back to the listing
                    driver.back()
                    time.sleep(0.8)

                if max_items and len(records) >= max_items:
                    break

            records.extend(batch)
            if max_items and len(records) >= max_items:
                # trim to exact number requested
                records = records[: max_items]
                break
            print(f"Page {page}: {len(batch)} items")
            page += 1
            if max_pages and page > max_pages:
                break
            if max_items and len(records) >= max_items:
                break
            time.sleep(1)
    finally:
        if driver:
            with contextlib.suppress(Exception):
                driver.quit()

    return records


# ------------------------------------------------------------------
# CLI entry-point
# ------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape InfoReady portals and write a timestamped JSON *and* CSV."
    )
    parser.add_argument(
        "--base",
        action="append",
        help="Base URL of a portal (repeatable). Default is the UM instance.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit pages per portal while testing.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Stop after scraping this many opportunities per portal.",
    )
    parser.add_argument(
        "--suffix",
        default="",
        help="Optional suffix for the output filename (e.g. 'daily').",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save output files (default: 'output')",
    )
    parser.add_argument(
        "--no-csv", 
        action="store_true",
        help="Skip auto-generating CSV (use improved_json_to_csv.py instead)",
    )
    args = parser.parse_args()

    bases = args.base if args.base else [DEFAULT_BASE]
    bases = list({clean_base(b) for b in bases})

    sess = load_session()
    all_rows: list[dict] = []

    for b in bases:
        print(f"\n🔗  Scraping {b}")
        rows = scrape_all(sess, b, args.max_pages, args.max_items)
        for r in rows:
            r["site"] = b
        all_rows.extend(rows)

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Generate timestamped filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = ["scraped_data", ts]
    if args.suffix:
        parts.append(args.suffix.replace(" ", "_"))
    filename = "_".join(parts)
    
    # Save JSON file
    out_json = output_dir / f"{filename}.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)
    
    # Auto-convert to CSV (unless --no-csv flag was used)
    if not args.no_csv:
        out_csv = output_dir / f"{filename}.csv"
        df = pd.json_normalize(all_rows)
        df.to_csv(out_csv, index=False)
        print(f"Additionally saved CSV → {out_csv}")

    print(f"\nSaved {len(all_rows)} records → {out_json}")
    
    # Suggestion for the improved CSV
    if not args.no_csv:
        print(f"To create an improved CSV file, run:")
        print(f"python improved_json_to_csv.py {out_json}")


if __name__ == "__main__":
    main()