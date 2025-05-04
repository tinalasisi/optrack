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
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, List, Dict, Any
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
COOKIE_PATH = Path("data/cookies.pkl")
DEFAULT_BASE = "https://umich.infoready4.com"
HEADERS = {"User-Agent": "UMich Grant Scraper (contact: tlasisi@umich.edu)"}
LISTING_PATH = "#homePage"   # known hash‑route for UM InfoReady listings

# Setup logging
logger = logging.getLogger("scrape_grants")
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Add console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console)

# History file for tracking seen IDs (used in incremental mode)
HISTORY_FILE = Path("output") / "seen_competitions.json"

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
# History management for incremental scraping
# ------------------------------------------------------------------
def load_seen_ids() -> Set[str]:
    """Load previously seen competition IDs for incremental mode."""
    # Create history directory if it doesn't exist
    HISTORY_FILE.parent.mkdir(exist_ok=True, parents=True)
    
    if not HISTORY_FILE.exists():
        logger.info(f"No history file found at {HISTORY_FILE}")
        return set()
    
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("seen_ids", []))
    except Exception as e:
        logger.warning(f"Error loading history file: {e}")
        return set()

def save_seen_ids(seen_ids: Set[str]) -> None:
    """Save seen competition IDs to history file."""
    # Ensure output directory exists
    HISTORY_FILE.parent.mkdir(exist_ok=True, parents=True)
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "seen_ids": list(seen_ids), 
            "last_updated": datetime.now().isoformat(),
            "count": len(seen_ids)
        }, f, indent=2)

# ------------------------------------------------------------------
# Core scraping
# ------------------------------------------------------------------
def scan_for_new_ids(
    sess: requests.Session,
    base_url: str,
    seen_ids: Set[str]
) -> Set[str]:
    """
    Quickly scan the main listing page for new competition IDs.
    
    Returns a set of new competition IDs not previously seen.
    """
    driver = webdriver.Chrome()
    new_ids = set()
    
    try:
        # Navigate to main listing
        url = f"{base_url}/{LISTING_PATH}"
        logger.info(f"Fast-scanning listings at {url}")
        driver.get(url)
        
        # Wait for the page to load
        try:
            WebDriverWait(driver, 8).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[competitionid]"))
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for listing anchors on {url}")
        
        # Dismiss any modal popups
        dismiss_any_modal(driver, timeout=3)
        
        # Get all competition IDs from the page
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        anchors = soup.select("a[competitionid]")
        
        # Extract IDs and titles
        all_ids = {}
        for a in anchors:
            comp_id = a.get("competitionid", "")
            title = a.get_text(strip=True)
            if comp_id and comp_id not in seen_ids:
                new_ids.add(comp_id)
                all_ids[comp_id] = title
        
        logger.info(f"Found {len(anchors)} listings total")
        logger.info(f"Found {len(new_ids)} NEW listings")
        
        if new_ids:
            logger.info("New listings found:")
            for comp_id in new_ids:
                logger.info(f"  - {comp_id}: {all_ids.get(comp_id, 'Unknown')}")
    
    finally:
        driver.quit()
    
    return new_ids

def scrape_all(
    sess: requests.Session,
    base_url: str,
    max_items: Optional[int] = None,
    incremental: bool = False,
    fast_scan: bool = False,
    seen_ids: Optional[Set[str]] = None,
) -> list[dict]:
    api = f"{base_url}/Search/GetFundingOpportunities"
    page = 1
    records: list[dict] = []
    use_json = True
    driver: webdriver.Chrome | None = None
    
    # Handle incremental mode
    ids_seen_this_run = set()
    if incremental and seen_ids is None:
        seen_ids = load_seen_ids()
        logger.info(f"Incremental mode: loaded {len(seen_ids)} previously seen competition IDs")
    
    try:
        while True:
            if use_json:
                params = {"pageNumber": page, "pageSize": 25, "sort": "CloseDate"}
                r = sess.get(api, params=params, headers={"Accept": "application/json"}, timeout=20)
                if r.status_code in (403, 404):
                    logger.info("🙈  JSON endpoint unavailable, switching to Selenium …")
                    use_json = False
                    driver = webdriver.Chrome()
                    continue
                r.raise_for_status()
                data = r.json()
                if not data:
                    break
                # Process items with incremental filtering if needed
                batch = []
                for i in data:
                    comp_id = str(i.get('Id', ''))
                    
                    # Skip if we've seen this ID before in incremental mode
                    if incremental and seen_ids and comp_id in seen_ids:
                        continue
                    
                    # Record this ID as seen in this run
                    if incremental:
                        ids_seen_this_run.add(comp_id)
                    
                    # Add to batch
                    batch.append(dict(
                        title=i.get("Title", "").strip(),
                        deadline=i.get("CloseDateDisplay", "").strip(),
                        synopsis=i.get("Description", "").strip(),
                        link=f"{base_url}/FundingOppDetails?Id={i['Id']}",
                        competition_id=comp_id,
                    ))
            else:
                # -----------------------------------------------------------
                # Rendered listing page → find every anchor on the page
                # -----------------------------------------------------------
                url = f"{base_url}/{LISTING_PATH}"   # homePage shows all current opportunities
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
                    # Extract competition ID early for filtering
                    comp_id = a.get("competitionid", "")
                    
                    # Skip if we've seen this ID before in incremental mode
                    if incremental and seen_ids and comp_id in seen_ids:
                        continue
                    
                    # Record this ID as seen in this run
                    if incremental:
                        ids_seen_this_run.add(comp_id)
                    
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
            logger.info(f"Found {len(batch)} items")
            break  # Only one page to process
    finally:
        if driver:
            with contextlib.suppress(Exception):
                driver.quit()
    
    # Update seen IDs if we're in incremental mode
    if incremental and seen_ids is not None and ids_seen_this_run:
        seen_ids.update(ids_seen_this_run)
        save_seen_ids(seen_ids)
        logger.info(f"Saved {len(ids_seen_this_run)} new competition IDs to history file")
        logger.info(f"Total unique IDs tracked: {len(seen_ids)}")

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
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Enable incremental mode - only scrape new grants not seen before",
    )
    parser.add_argument(
        "--fast-scan",
        action="store_true",
        help="Only scan for new IDs without fetching details (much faster)",
    )
    parser.add_argument(
        "--append",
        default=None,
        help="Append new grants to this existing JSON file instead of creating a new one",
    )
    args = parser.parse_args()

    bases = args.base if args.base else [DEFAULT_BASE]
    bases = list({clean_base(b) for b in bases})

    sess = load_session()
    
    # Handle incremental mode and existing data
    seen_ids = None
    existing_data = []
    
    if args.incremental or args.fast_scan:
        # Load seen IDs for incremental or fast scan mode
        seen_ids = load_seen_ids()
        
    if args.append:
        # Load existing data for append mode
        append_path = Path(args.append)
        if append_path.exists():
            try:
                with open(append_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                logger.info(f"Loaded {len(existing_data)} existing records from {append_path}")
                
                # Extract IDs from existing data for deduplication
                if (args.incremental or args.fast_scan) and seen_ids is not None:
                    for r in existing_data:
                        if "competition_id" in r:
                            seen_ids.add(str(r["competition_id"]))
                    logger.info(f"Updated seen IDs with {len(existing_data)} IDs from existing data")
            except Exception as e:
                logger.warning(f"Error loading existing data: {e}")
    
    # Collect new rows
    all_rows = list(existing_data)  # Start with existing data if any
    new_count = 0
    
    for b in bases:
        logger.info(f"\n🔗  Processing {b}")
        
        if args.fast_scan:
            # Just scan for new IDs without fetching details
            if seen_ids is not None:
                new_ids = scan_for_new_ids(sess, b, seen_ids)
                
                # Update history
                if new_ids:
                    seen_ids.update(new_ids)
                    save_seen_ids(seen_ids)
                    logger.info(f"Added {len(new_ids)} new IDs to tracking history")
                    logger.info(f"Run without --fast-scan flag to fetch their details")
                    
                # No rows to add since we're just scanning
                continue
        
        # Regular scraping mode
        rows = scrape_all(
            sess, b, args.max_items, 
            incremental=args.incremental, 
            fast_scan=args.fast_scan,
            seen_ids=seen_ids
        )
        
        for r in rows:
            r["site"] = b
        
        new_count += len(rows)
        all_rows.extend(rows)

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Determine output file path
    if args.append:
        # Use the specified file for append mode
        out_json = Path(args.append)
    else:
        # Generate timestamped filename
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts = ["scraped_data", ts]
        if args.suffix:
            parts.append(args.suffix.replace(" ", "_"))
        filename = "_".join(parts)
        out_json = output_dir / f"{filename}.json"
    
    # Only save if we have data
    if all_rows:
        # Save JSON file
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, ensure_ascii=False, indent=2)
        
        # Auto-convert to CSV (unless --no-csv flag was used)
        if not args.no_csv:
            out_csv = out_json.with_suffix(".csv")
            df = pd.json_normalize(all_rows)
            df.to_csv(out_csv, index=False)
            logger.info(f"Additionally saved CSV → {out_csv}")
        
        if args.append and new_count > 0:
            logger.info(f"\nAppended {new_count} new records to {out_json}")
        else:
            logger.info(f"\nSaved {len(all_rows)} records ({new_count} new) → {out_json}")
        
        # Suggestion for the improved CSV
        if not args.no_csv:
            logger.info(f"To create an improved CSV file, run:")
            logger.info(f"python improved_json_to_csv.py {out_json}")
    else:
        logger.info("No data to save. Output file not created.")
        
    # Summary for cron jobs
    if args.incremental:
        logger.info(f"\n=== Incremental Scrape Summary ===")
        logger.info(f"Existing records: {len(existing_data)}")
        logger.info(f"New records: {new_count}")
        logger.info(f"Total records: {len(all_rows)}")
        logger.info(f"Unique IDs tracked: {len(seen_ids) if seen_ids else 0}")


if __name__ == "__main__":
    main()