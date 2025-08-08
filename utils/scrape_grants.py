"""
scrape_grants.py
-----------------
Scrapes one or more InfoReady4 portals using cookies saved by
`login_and_save_cookies.py`.

Flow:
1. Try the fast JSON endpoint:  /Search/GetFundingOpportunities
2. If that returns 404/403, fall back to Selenium, open
   #/FundingOpportunities?page=N, wait for React to render, parse HTML.

This script focuses on scraping and saving JSON data to source-specific databases.
For CSV conversion, use utils/json_converter.py separately.
For tracking seen IDs, this script uses core/source_tracker.py.
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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Import project utilities
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.source_tracker import SeenIDsTracker, load_seen_ids, save_seen_ids
from core.append_store import AppendStore  # Import the new AppendStore class

POPUP_DISMISSED = False  # cache so we do not repeatedly search once handled

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
COOKIE_PATH = Path("data/cookies.pkl")
CONFIG_PATH = Path("data/websites.json")
DEFAULT_BASE = "https://umich.infoready4.com"  # Fallback default
HEADERS = {"User-Agent": "UMich Grant Scraper (contact: tlasisi@umich.edu)"}
LISTING_PATH = "#homePage"   # known hash‑route for UM InfoReady listings

def load_website_config():
    """Load website configuration from JSON file."""
    if not CONFIG_PATH.exists():
        logger.warning(f"No configuration file found at {CONFIG_PATH}. Using default settings.")
        return {
            "websites": [{"name": "umich", "url": DEFAULT_BASE, "enabled": True}],
            "defaults": {"max_items": None, "incremental": True, "output_dir": str(OUTPUT_DB_DIR)}
        }
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Validate that required keys exist
        if "websites" not in config or not isinstance(config["websites"], list):
            logger.warning("Invalid config: 'websites' list not found in config. Using default.")
            config["websites"] = [{"name": "umich", "url": DEFAULT_BASE, "enabled": True}]
        
        if "defaults" not in config or not isinstance(config["defaults"], dict):
            logger.warning("Invalid config: 'defaults' not found in config. Using default.")
            config["defaults"] = {"max_items": None, "incremental": True, "output_dir": str(OUTPUT_DB_DIR)}
        
        # Only use enabled websites
        config["websites"] = [w for w in config["websites"] if w.get("enabled", True)]
        
        if not config["websites"]:
            logger.warning("No enabled websites found in config. Using default.")
            config["websites"] = [{"name": "umich", "url": DEFAULT_BASE, "enabled": True}]
        
        logger.info(f"Loaded {len(config['websites'])} websites from configuration")
        return config
    except Exception as e:
        logger.error(f"Error loading website configuration: {e}")
        return {
            "websites": [{"name": "umich", "url": DEFAULT_BASE, "enabled": True}],
            "defaults": {"max_items": None, "incremental": True, "output_dir": str(OUTPUT_DB_DIR)}
        }

# Setup logging
logger = logging.getLogger("scrape_grants")
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Add console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console)

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Output directories
OUTPUT_DB_DIR = BASE_DIR / "output/db"
OUTPUT_TEST_DIR = BASE_DIR / "output/test"

# Database file patterns
DATABASE_PATTERN = "{site}_grants.json"
CSV_PATTERN = "{site}_grants.csv"

# History file patterns for tracking seen IDs (used in incremental mode)
HISTORY_PATTERN = "{site}_seen_competitions.json"

# History file paths
DB_HISTORY_DIR = OUTPUT_DB_DIR
TEST_HISTORY_DIR = OUTPUT_TEST_DIR

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

    logger.info(f"Fetching URL with Selenium: {url}")
    driver.get(url)
    
    # Log current URL and title for debugging
    logger.info(f"Current URL: {driver.current_url}")
    logger.info(f"Page title: {driver.title}")
    
    dismiss_any_modal(driver, timeout=3)

    # wait until the document is fully loaded, then for at least one listing anchor.
    try:
        logger.info("Waiting for document to be ready...")
        WebDriverWait(driver, 8).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logger.info("Document ready, waiting for listing anchors...")
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[competitionid]"))
        )
        logger.info("Found listing anchors on page")
    except TimeoutException:
        # Listing anchors did not appear in time. Keep whatever HTML we have.
        logger.warning(f"⚠️  Timeout waiting for listing anchors on {url}")
        # Check what elements are available on the page
        body_text = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Page content sample: {body_text[:200]}...")

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
# Database management
# ------------------------------------------------------------------
class SiteDatabase(AppendStore):
    """
    Manages site-specific grant databases using the append-only storage.
    This version inherits from AppendStore for efficient storage.

    For backward compatibility, it also maintains the legacy JSON format.
    """

    def __init__(self, site_name: str, is_test: bool = False):
        # Initialize the underlying AppendStore
        super().__init__(site_name=site_name, is_test=is_test)

        # Set up paths for CSV
        self.output_dir = OUTPUT_TEST_DIR if is_test else OUTPUT_DB_DIR
        self.csv_path = self.output_dir / CSV_PATTERN.format(site=site_name)

        # For compatibility with existing code that expects grants dictionary
        self.grants = {}

        # Load all grants into memory only when explicitly requested
        # This is not done by default to save memory

    def load(self) -> None:
        """
        Load the database into memory.
        This is only used for backward compatibility with code that expects
        the grants dictionary to be available.
        """
        # Get all IDs from the index
        grant_ids = self.get_all_ids()

        # Load each grant
        self.grants = {}
        for grant_id in grant_ids:
            grant = self.get_grant(grant_id)
            if grant:
                self.grants[grant_id] = grant

        logger.info(f"Loaded {len(self.grants)} grants from {self.site_name} database into memory")

    def save(self) -> None:
        """
        Save the database to disk.
        In the append-only model, this exports to the legacy JSON format
        and saves the CSV.
        """
        # Export to legacy JSON format
        self.export_to_json()

        # Save CSV version with clean format
        try:
            self.save_csv()
        except Exception as e:
            logger.warning(f"Could not save CSV: {e}")

    def save_csv(self) -> None:
        """Save a clean CSV version of the database."""
        import pandas as pd

        # Get all IDs
        grant_ids = self.get_all_ids()

        # Extract consistent fields, keep details as JSON
        records = []
        for grant_id in grant_ids:
            grant = self.get_grant(grant_id)
            if not grant:
                continue

            # Collect all extra fields into a details object
            details = {}
            for k, v in grant.items():
                if k not in ['title', 'url', 'id', 'site', 'description_full']:
                    details[k] = v

            # Create a clean record with proper encoding to prevent CSV issues
            record = {
                'title': grant.get('title', '').replace('\n', ' '),
                'url': grant.get('link', grant.get('url', '')),
                'id': grant.get('competition_id', grant.get('id', '')),
                'site': self.site_name,
                'description': grant.get('description_full', '').strip().replace('\n', ' '),
                # JSON-encode with ensure_ascii to prevent encoding issues
                'details_json': json.dumps(details, ensure_ascii=True)
            }
            records.append(record)

        # Create the CSV with proper quoting to handle embedded newlines and commas
        import csv  # For CSV constants
        df = pd.DataFrame(records)
        df.to_csv(self.csv_path, index=False, quoting=csv.QUOTE_ALL, escapechar='\\', doublequote=False)
        logger.info(f"Also saved CSV version to {self.csv_path}")

    def update_from_scrape(self, scraped_records: List[Dict[str, Any]]) -> None:
        """
        Update the database with newly scraped records.
        Uses the more efficient append-only storage.
        """
        # Use the AppendStore implementation
        new_count = super().update_from_scrape(scraped_records)

        # If new grants were added, also save the CSV
        if new_count > 0:
            # Save CSV version
            try:
                self.save_csv()
            except Exception as e:
                logger.warning(f"Could not save CSV: {e}")

            # Also export to legacy format for compatibility
            self.export_to_json()

# ------------------------------------------------------------------
# History management for incremental scraping
# ------------------------------------------------------------------
# Note: SeenIDsTracker class has been moved to core/source_tracker.py
# The load_seen_ids and save_seen_ids functions are now imported from there

# ------------------------------------------------------------------
# Core scraping
# ------------------------------------------------------------------
def scan_for_new_ids(
    sess: requests.Session,
    base_url: str,
    seen_ids: Set[str],
    site_name: str = "default",
    visible: bool = False
) -> Set[str]:
    """
    Quickly scan the main listing page for new competition IDs.
    
    Args:
        sess: The requests session to use
        base_url: The base URL of the site to scan
        seen_ids: Set of already seen competition IDs for this site
        site_name: The name of the site being scanned
        visible: Whether to show the browser UI
        
    Returns:
        A set of new competition IDs not previously seen
    """
    logger.info(f"Initializing Selenium driver for scanning {site_name}")
    driver = create_selenium_driver(headless=not visible)
    if driver is None:
        logger.warning("Skipping fast scan; Chrome driver not available")
        return set()
    new_ids = set()

    try:
        # Navigate to main listing
        url = f"{base_url}/{LISTING_PATH}"
        logger.info(f"Fast-scanning listings at {url} for site '{site_name}'")
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
        
        logger.info(f"Found {len(anchors)} listings total for site '{site_name}'")
        logger.info(f"Found {len(new_ids)} NEW listings for site '{site_name}'")
        
        if new_ids:
            logger.info(f"New listings found for site '{site_name}':")
            for comp_id in new_ids:
                logger.info(f"  - {comp_id}: {all_ids.get(comp_id, 'Unknown')}")
    
    finally:
        driver.quit()
    
    return new_ids

def create_selenium_driver(headless: bool = True) -> Optional[webdriver.Chrome]:
    """
    Create a properly configured Selenium driver with options for reliability.
    
    Args:
        headless: Whether to run in headless mode (default: True for scheduled jobs)
    """
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument("--disable-gpu")  # Disable GPU acceleration
    options.add_argument("--no-sandbox")  # Disable sandbox
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    options.add_argument("--disable-extensions")  # Disable extensions
    options.add_argument("--disable-popup-blocking")  # Allow popups
    
    if headless:
        options.add_argument("--headless")  # Run in headless mode (no visible window)
        logger.info("Running Chrome in headless mode")
    else:
        options.add_argument("--start-maximized")  # Start maximized (only when visible)
        logger.info("Running Chrome in visible mode")
    
    # Create and return the driver using webdriver-manager for portability
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)  # Set page load timeout to 30 seconds
        return driver
    except Exception as e:
        logger.warning(f"Chrome driver unavailable: {e}")
        return None

def scrape_all(
    sess: requests.Session,
    base_url: str,
    max_items: Optional[int] = None,
    incremental: bool = False,
    fast_scan: bool = False,
    seen_ids: Optional[Set[str]] = None,
    site_name: str = "default",
    batch_size: Optional[int] = None,
    batch_index: int = 0,
    timeout_per_grant: int = 12,
    visible: bool = False
) -> list[dict]:
    api = f"{base_url}/Search/GetFundingOpportunities"
    page = 1
    records: list[dict] = []
    use_json = True
    driver: webdriver.Chrome | None = None
    
    # Load database to check which IDs we already have details for
    db = SiteDatabase(site_name=site_name, is_test=False)
    db_ids = db.get_all_ids()  # Use the new method that doesn't load everything into memory
    logger.info(f"Loaded {len(db_ids)} existing grants in the database for site '{site_name}'")

    # Handle incremental mode
    ids_seen_this_run = set()
    if incremental and seen_ids is None:
        seen_ids = load_seen_ids(source=site_name)
        logger.info(f"Incremental mode: loaded {len(seen_ids)} previously seen competition IDs for site '{site_name}'")

    # Identify IDs that we've seen but don't have details for
    missing_ids = set()
    if incremental and seen_ids:
        missing_ids = seen_ids - db_ids
        if missing_ids:
            logger.info(f"Found {len(missing_ids)} IDs that were seen before but are not in the database - will collect their details")
    
    try:
        while True:
            if use_json:
                params = {"pageNumber": page, "pageSize": 25, "sort": "CloseDate"}
                r = sess.get(api, params=params, headers={"Accept": "application/json"}, timeout=20)
                if r.status_code in (403, 404):
                    logger.info("🙈  JSON endpoint unavailable, switching to Selenium …")
                    use_json = False
                    driver = create_selenium_driver(headless=not visible)  # Use the visible parameter passed to the function
                    logger.info("Selenium driver initialized successfully")
                    continue
                r.raise_for_status()
                data = r.json()
                if not data:
                    break
                # Process items with incremental filtering if needed
                batch = []
                for idx, i in enumerate(data):
                    # Skip entries based on batch index when using batch mode
                    if batch_size and batch_index > 0:
                        # Skip items from previous batches
                        if idx < batch_index * batch_size:
                            continue
                    
                    comp_id = str(i.get('Id', ''))
                    logger.info(f"Processing competition ID: {comp_id}")
                    
                    # Skip if we've seen this ID before AND have its details in the database
                    if incremental and seen_ids and comp_id in seen_ids and db.has_id(comp_id):
                        logger.info(f"Skipping {comp_id} - already in database")
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
                    
                    # Stop if we've reached the batch size
                    if batch_size and len(batch) >= batch_size:
                        logger.info(f"Reached batch size limit of {batch_size}")
                        break
                        
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
                
                # Handle batching when using Selenium method
                if batch_size and batch_index > 0:
                    start_idx = batch_index * batch_size
                    end_idx = start_idx + batch_size
                    # Only process the current batch's worth of anchors
                    anchors = anchors[start_idx:end_idx]
                    logger.info(f"Processing batch {batch_index+1}: items {start_idx+1}-{end_idx}")
                
                for idx, a in enumerate(anchors):
                    # Extract competition ID early for filtering
                    comp_id = a.get("competitionid", "")
                    
                    # Skip if we've seen this ID before AND have its details in the database
                    if incremental and seen_ids and comp_id in seen_ids and db.has_id(comp_id):
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
                
                    # Stop if we've reached the batch size
                    if batch_size and len(batch) >= batch_size:
                        logger.info(f"Reached batch size limit of {batch_size}")
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
        # Use the correct output directory based on the database path
        is_test = False  # Always use the database directory unless explicitly in test mode
        save_seen_ids(seen_ids, is_test=is_test, source=site_name)
        logger.info(f"Saved {len(ids_seen_this_run)} new competition IDs to history file for site '{site_name}'")
        logger.info(f"Total unique IDs tracked for site '{site_name}': {len(seen_ids)}")
    
    # Save batch data immediately if using batch mode
    if batch_size and records:
        # Update database with this batch
        db.update_from_scrape(records)
        logger.info(f"Saved batch of {len(records)} grants to database for site '{site_name}'")
        
        # Give a batch summary
        next_batch = batch_index + 1
        logger.info(f"Completed batch {batch_index+1}. To continue, use --batch-index {next_batch}")

    return records


# ------------------------------------------------------------------
# CLI entry-point
# ------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape InfoReady portals and update source-specific databases."
    )
    parser.add_argument(
        "--base",
        action="append",
        help="Base URL of a portal (repeatable). Overrides config file if specified.",
    )
    parser.add_argument(
        "--site",
        "--source",
        dest="site",
        default=None,
        help="Site name to use for source-specific database",
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
        help="Optional suffix for the output filename (used only with --export).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save output files (default from config or 'output/db')",
    )
    parser.add_argument(
        "--no-csv", 
        action="store_true",
        help="Skip CSV generation when exporting (used only with --export)",
    )
    parser.add_argument(
        "--export", 
        action="store_true",
        help="Export results to separate JSON/CSV files (source-specific databases are always updated)",
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
        help="Append new grants to this existing JSON file instead of creating a new one (used only with --export)",
    )
    parser.add_argument(
        "--use-config",
        action="store_true",
        help="Use only websites from the configuration file",
    )
    parser.add_argument(
        "--website",
        action="append",
        help="Specific website name(s) from config to scrape (repeatable)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Process grants in batches of this size (recommended: 5-10)"
    )
    parser.add_argument(
        "--batch-index",
        type=int,
        default=0,
        help="Start with this batch index (0-based, for resuming interrupted scrapes)"
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run browser in visible mode (not headless) - useful for troubleshooting"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact the database files to optimize storage (run periodically)"
    )
    args = parser.parse_args()

    # Load config file
    config = load_website_config()
    defaults = config.get("defaults", {})
    
    # Determine which websites to scrape
    websites_to_scrape = []
    
    if args.site:
        # If site name is provided, use it as primary identifier
        site_name = args.site
        # Try to find matching website in config
        found = False
        for site in config.get("websites", []):
            if site.get("name") == site_name:
                websites_to_scrape.append(site)
                found = True
                break
                
        if not found:
            # If no matching site in config, create one with default URL
            if args.base:
                url = clean_base(args.base[0])
            else:
                url = DEFAULT_BASE
                
            websites_to_scrape.append({"name": site_name, "url": url})
            logger.info(f"Created custom site '{site_name}' with URL {url}")
                
    elif args.base:
        # If base URLs provided, use them instead of config
        bases = list({clean_base(b) for b in args.base})
        for base in bases:
            # Try to find a matching website in config for the name
            name = None
            for w in config.get("websites", []):
                if clean_base(w.get("url", "")) == base:
                    name = w.get("name")
                    break
            websites_to_scrape.append({"name": name or "custom", "url": base})
    elif args.website:
        # If specific website names provided, filter to those
        websites = config.get("websites", [])
        for site_name in args.website:
            for site in websites:
                if site.get("name") == site_name:
                    websites_to_scrape.append(site)
                    break
            else:
                logger.warning(f"Website '{site_name}' not found in configuration")
    else:
        # Use all enabled websites from config
        websites_to_scrape = config.get("websites", [])
        
    if not websites_to_scrape:
        logger.warning("No websites to scrape specified. Using default.")
        websites_to_scrape = [{"name": "umich", "url": DEFAULT_BASE}]
    
    # Log websites to be scraped
    logger.info(f"Will scrape {len(websites_to_scrape)} websites:")
    for site in websites_to_scrape:
        logger.info(f"  - {site.get('name', 'unknown')}: {site.get('url')}")
        
    # Get settings from config if not specified in args
    max_items = args.max_items if args.max_items is not None else defaults.get("max_items")
    incremental = args.incremental  # Default is now non-incremental; explicit flag to enable
    output_dir = args.output_dir or defaults.get("output_dir", "output/db")

    # Handle database compaction if requested
    if args.compact:
        logger.info("Running database compaction...")
        for site in websites_to_scrape:
            site_name = site.get("name")
            if site_name:
                logger.info(f"Compacting database for {site_name}...")
                db = SiteDatabase(site_name=site_name, is_test=False)
                if db.compact():
                    logger.info(f"Successfully compacted database for {site_name}")
                else:
                    logger.error(f"Failed to compact database for {site_name}")
        logger.info("Compaction complete!")
        return

    # Get list of base URLs
    bases = [site.get("url") for site in websites_to_scrape]

    sess = load_session()
    
    # Handle incremental mode and existing data
    seen_ids = None
    existing_data = []
    
    # Determine if this is a test run
    is_test_run = "test" in str(output_dir)
    
    # Global tracker for shared IDs from append mode
    global_seen_ids = {}
    
    # Initialize existing data for append mode
    existing_data = []
    
    if args.append:
        # Load existing data for append mode
        append_path = Path(args.append)
        if append_path.exists():
            try:
                with open(append_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                logger.info(f"Loaded {len(existing_data)} existing records from {append_path}")
                
                # Group existing data by site and extract IDs for deduplication
                if args.incremental or args.fast_scan:
                    # Group by site
                    site_grouped = {}
                    for r in existing_data:
                        site = r.get("site", "default")
                        if site not in site_grouped:
                            site_grouped[site] = []
                        site_grouped[site].append(r)
                    
                    # Extract IDs for each site
                    for site, records in site_grouped.items():
                        global_seen_ids[site] = set()
                        for r in records:
                            if "competition_id" in r:
                                global_seen_ids[site].add(str(r["competition_id"]))
                        logger.info(f"Extracted {len(global_seen_ids[site])} IDs for site '{site}' from existing data")
            except Exception as e:
                logger.warning(f"Error loading existing data: {e}")
    
    # Collect new rows
    all_rows = list(existing_data)  # Start with existing data if any
    new_count = 0
    
    for b in bases:
        logger.info(f"\n🔗  Processing {b}")
        
        # Get site name for this URL
        site_name = None
        for site in websites_to_scrape:
            if site.get("url") == b:
                site_name = site.get("name")
                break
                
        if not site_name:
            # Fall back to a safe name derived from the URL
            from urllib.parse import urlparse
            parsed = urlparse(b)
            site_name = parsed.netloc.split('.')[0]  # Just take the first part of the domain
        
        if args.fast_scan:
            # Just scan for new IDs without fetching details
            # Load site-specific seen IDs
            site_seen_ids = load_seen_ids(is_test=is_test_run, source=site_name)
            
            # Add any IDs from existing data
            if site_name in global_seen_ids:
                site_seen_ids.update(global_seen_ids[site_name])
            
            new_ids = scan_for_new_ids(sess, b, site_seen_ids, site_name, visible=args.visible if hasattr(args, 'visible') else False)
            
            # Update history
            if new_ids:
                site_seen_ids.update(new_ids)
                save_seen_ids(site_seen_ids, is_test=is_test_run, source=site_name)
                logger.info(f"Added {len(new_ids)} new IDs to tracking history for site '{site_name}'")
                logger.info(f"Run without --fast-scan flag to fetch their details")
                
            # No rows to add since we're just scanning
            continue
        
        # Load site-specific seen IDs for regular scraping mode
        site_seen_ids = None
        if incremental:
            site_seen_ids = load_seen_ids(is_test=is_test_run, source=site_name)
            
            # Add any IDs from existing data
            if site_name in global_seen_ids:
                site_seen_ids.update(global_seen_ids[site_name])
        
        # Regular scraping mode
        rows = scrape_all(
            sess, b, max_items, 
            incremental=incremental, 
            fast_scan=args.fast_scan,
            seen_ids=site_seen_ids,
            site_name=site_name,
            visible=args.visible if hasattr(args, 'visible') else False,
            batch_size=args.batch_size,
            batch_index=args.batch_index
        )
        
        # Set the site name for all rows from this source
        for r in rows:
            r["site"] = site_name
        
        new_count += len(rows)
        all_rows.extend(rows)

    # Determine if this is a test run
    is_test = "test" in str(output_dir)
    
    # Set output directory based on whether this is a test
    if is_test:
        output_path = OUTPUT_TEST_DIR  # Use the test directory constant
    else:
        output_path = OUTPUT_DB_DIR    # Use the database directory constant
    
    # Create output directory if it doesn't exist
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Initialize the seen IDs tracker
    seen_tracker = SeenIDsTracker(is_test=is_test)
    
    # Group rows by site
    site_records = {}
    for row in all_rows:
        site = row.get('site', '')
        if not site and len(websites_to_scrape) == 1:
            # Use the website name if site isn't specified
            site = websites_to_scrape[0].get('name', 'default')
            row['site'] = site
            
        if not site:
            # Skip rows without site information
            continue
            
        if site not in site_records:
            site_records[site] = []
        site_records[site].append(row)
    
    # Update site-specific databases
    for site, records in site_records.items():
        # Initialize site database
        db = SiteDatabase(site_name=site, is_test=is_test)
        
        # Update database from scraped records
        db.update_from_scrape(records)
        
        # Update seen IDs for this site
        competition_ids = {r.get('competition_id', '') for r in records if r.get('competition_id')}
        if competition_ids:
            seen_tracker.add_ids(site, competition_ids)
    
    # Save seen IDs
    seen_tracker.save()
    
    # Export to separate files if requested
    if args.export and all_rows:
        # Determine output file path
        if args.append:
            # Use the specified file for append mode
            out_json = Path(args.append)
        else:
            # Generate timestamped filename
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            parts = ["export", ts]
            
            # Add website names to the filename if multiple
            if len(websites_to_scrape) == 1:
                site_name = websites_to_scrape[0].get("name")
                if site_name:
                    parts.append(site_name)
            elif len(websites_to_scrape) > 1:
                parts.append("multi_site")
                
            if args.suffix:
                parts.append(args.suffix.replace(" ", "_"))
                
            filename = "_".join(parts)
            out_json = output_path / f"{filename}.json"
        
        # Save JSON file
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, ensure_ascii=False, indent=2)
        logger.info(f"Exported {len(all_rows)} records to {out_json}")
        
        # Auto-convert to clean CSV (unless --no-csv flag was used)
        if not args.no_csv:
            out_csv = out_json.with_suffix(".csv")
            
            # Extract consistent fields, keep details as JSON
            records = []
            for item in all_rows:
                record = {
                    'title': item.get('title', ''),
                    'link': item.get('link', item.get('url', '')),
                    'competition_id': item.get('competition_id', item.get('id', '')),
                    'site': item.get('site', ''),
                    'description': item.get('description_full', '').strip(),
                    'details_json': json.dumps(item.get('details', {}))
                }
                records.append(record)
            
            # Create the clean CSV
            df = pd.DataFrame(records)
            df.to_csv(out_csv, index=False)
            logger.info(f"Also exported CSV → {out_csv}")
    
    # Summary message
    logger.info("\n=== Scrape Summary ===")
    logger.info(f"Sites processed: {len(site_records)}")
    for site, records in site_records.items():
        logger.info(f"  - {site}: {len(records)} records")
    logger.info(f"Each site has its own database file and CSV in {output_path}")
    
    # List the database files
    for site in site_records.keys():
        db_path = output_path / DATABASE_PATTERN.format(site=site)
        csv_path = output_path / CSV_PATTERN.format(site=site)
        logger.info(f"  - {site}: {db_path} and {csv_path}")
        
    # Summary for cron jobs
    if args.incremental:
        logger.info(f"\n=== Incremental Scrape Summary ===")
        logger.info(f"Existing records: {len(existing_data)}")
        logger.info(f"New records: {new_count}")
        logger.info(f"Total records: {len(all_rows)}")
        logger.info(f"Unique IDs tracked: {len(seen_ids) if seen_ids else 0}")
    
    # Batch summary if applicable
    if args.batch_size:
        logger.info(f"\n=== Batch Processing Summary ===")
        logger.info(f"Batch size: {args.batch_size}")
        logger.info(f"Current batch index: {args.batch_index}")
        logger.info(f"Next batch index: {args.batch_index + 1}")
        
        # Display command for next batch
        next_cmd = f"python utils/scrape_grants.py"
        if args.website:
            for site in args.website:
                next_cmd += f" --website {site}"
        if args.max_items:
            next_cmd += f" --max-items {args.max_items}"
        if args.batch_size:
            next_cmd += f" --batch-size {args.batch_size}"
        next_cmd += f" --batch-index {args.batch_index + 1}"
        if args.incremental:
            next_cmd += " --incremental"
        
        logger.info(f"\nTo continue with next batch, run:")
        logger.info(f"{next_cmd}")


if __name__ == "__main__":
    main()