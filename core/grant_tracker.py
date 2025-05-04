#!/usr/bin/env python
"""
Grant Tracker - Database management for grant listings.

This script maintains a database of all seen grants and provides:
1. Quick scanning for new grants
2. Fetching details for only new grants
3. Updating the database with new findings
"""
import sys
import time
import json
import pickle
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

# Constants
DEFAULT_BASE = "https://umich.infoready4.com"
COOKIE_PATH = Path("data/cookies.pkl")
LISTING_PATH = "#homePage"
DATABASE_PATH = Path("output/tracked_grants.json")
OUTPUT_DIR = Path("output")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("grant_tracker")

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

class GrantsDatabase:
    """Manages the database of tracked grants."""
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self.grants: Dict[str, Dict[str, Any]] = {}
        self.load()
    
    def load(self) -> None:
        """Load the database from disk."""
        if not self.db_path.exists():
            logger.info(f"No existing database found at {self.db_path}")
            self.grants = {}
            return
        
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.grants = data.get("grants", {})
            logger.info(f"Loaded {len(self.grants)} grants from database")
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            self.grants = {}
    
    def save(self) -> None:
        """Save the database to disk."""
        data = {
            "grants": self.grants,
            "last_updated": datetime.now().isoformat(),
            "count": len(self.grants)
        }
        
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self.grants)} grants to database")
    
    def get_known_ids(self) -> Set[str]:
        """Get all known competition IDs."""
        return set(self.grants.keys())
    
    def add_grant(self, competition_id: str, title: str, url: str, source: str = "umich") -> None:
        """Add a new grant to the database."""
        # Create a unique ID that includes the source
        unique_id = f"{source}:{competition_id}"
        
        if unique_id not in self.grants:
            self.grants[unique_id] = {
                "title": title,
                "url": url,
                "first_seen": datetime.now().isoformat(),
                "id": competition_id,
                "source": source,
                "unique_id": unique_id
            }
    
    def add_details(self, competition_id: str, details: Dict[str, Any], source: str = "umich") -> None:
        """Add detailed information to a grant's record."""
        unique_id = f"{source}:{competition_id}"
        if unique_id in self.grants:
            self.grants[unique_id].update(details)
    
    def get_grant(self, competition_id: str, source: str = "umich") -> Optional[Dict[str, Any]]:
        """Get a specific grant by ID and source."""
        unique_id = f"{source}:{competition_id}"
        return self.grants.get(unique_id)
        
    def get_grants_by_source(self, source: str) -> Dict[str, Dict[str, Any]]:
        """Get all grants from a specific source."""
        return {k: v for k, v in self.grants.items() if v.get("source") == source}
        
    def get_sources(self) -> List[str]:
        """Get all unique sources in the database."""
        return list(set(grant.get("source", "unknown") for grant in self.grants.values()))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the database."""
        # Find oldest and newest grants
        if not self.grants:
            return {"count": 0, "sources": []}
        
        # Sort by first_seen date
        sorted_grants = sorted(
            [g for g in self.grants.values() if "first_seen" in g],
            key=lambda x: x["first_seen"]
        )
        
        # Find newest and oldest by date
        oldest = sorted_grants[0] if sorted_grants else None
        newest = sorted_grants[-1] if sorted_grants else None
        
        # Get sources
        sources = self.get_sources()
        source_counts = {}
        for source in sources:
            source_counts[source] = len(self.get_grants_by_source(source))
        
        # Find highest and lowest actual IDs (not unique_ids)
        id_grants = []
        for v in self.grants.values():
            if "id" in v and isinstance(v["id"], str) and v["id"].isdigit():
                id_grants.append((int(v["id"]), v))
        
        lowest_id = min(id_grants, key=lambda x: x[0])[1] if id_grants else None
        highest_id = max(id_grants, key=lambda x: x[0])[1] if id_grants else None
        
        return {
            "count": len(self.grants),
            "oldest": oldest,
            "newest": newest,
            "lowest_id": lowest_id,
            "highest_id": highest_id,
            "sources": sources,
            "by_source": source_counts
        }


def load_cookies():
    """Load cookies from the standard location."""
    if not COOKIE_PATH.exists():
        logger.warning(f"No cookie file found at {COOKIE_PATH}")
        return []
    
    try:
        with open(COOKIE_PATH, "rb") as f:
            cookies = pickle.load(f)
        return cookies
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return []


def scan_for_grants(base_url: str = DEFAULT_BASE) -> Dict[str, Dict]:
    """
    Quickly scan the main listing page for all grants.
    
    Returns a dictionary of competition IDs to basic metadata.
    """
    logger.info(f"Scanning for grants at {base_url}")
    
    driver = webdriver.Chrome()
    grants = {}
    
    try:
        # Load domain
        driver.get(base_url)
        
        # Add cookies if available
        cookies = load_cookies()
        if cookies:
            for cookie in cookies:
                if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                    cookie['expiry'] = int(cookie['expiry'])
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
        
        # Navigate to listing page
        url = f"{base_url}/{LISTING_PATH}"
        logger.info(f"Loading listings page: {url}")
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
            logger.warning(f"Timeout waiting for listings at {url}")
        
        # Dismiss any modal popups
        try:
            from scrape_grants import dismiss_any_modal
            dismiss_any_modal(driver, timeout=3)
        except ImportError:
            # If we can't import, just wait a bit for modals to appear
            time.sleep(2)
            # Try clicking a close button
            try:
                close_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    "button.close, [data-dismiss='modal'], .modal .btn-primary")
                for btn in close_buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
            except:
                pass
        
        # Get the HTML
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # Find all competition links
        anchors = soup.select("a[competitionid]")
        logger.info(f"Found {len(anchors)} grant listings")
        
        # Extract metadata
        for a in anchors:
            comp_id = a.get("competitionid", "")
            if not comp_id:
                continue
                
            title = a.get_text(strip=True)
            href = a.get("href", "")
            
            # Make sure href is absolute
            if href and not href.startswith(("http://", "https://")):
                href = f"{base_url}{href if href.startswith('/') else '/' + href}"
            
            # If no href, construct one from competition ID
            if not href:
                href = f"{base_url}#competitionDetail/{comp_id}"
            
            # Get deadline if available
            deadline = ""
            row = a.find_parent("tr")
            if row:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    deadline = cells[1].get_text(strip=True)
            
            grants[comp_id] = {
                "id": comp_id,
                "title": title,
                "url": href,
                "deadline": deadline,
                "scanned_date": datetime.now().isoformat()
            }
    
    finally:
        driver.quit()
    
    return grants


def fetch_grant_details(competition_id: str, base_url: str = DEFAULT_BASE) -> Dict[str, Any]:
    """Fetch detailed information for a specific grant."""
    logger.info(f"Fetching details for grant {competition_id}")
    
    driver = webdriver.Chrome()
    details = {}
    
    try:
        # Load domain
        driver.get(base_url)
        
        # Add cookies if available
        cookies = load_cookies()
        if cookies:
            for cookie in cookies:
                if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                    cookie['expiry'] = int(cookie['expiry'])
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
        
        # Navigate to detail page
        url = f"{base_url}#competitionDetail/{competition_id}"
        logger.info(f"Loading detail page: {url}")
        driver.get(url)
        
        # Wait for the page to load
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for detail page to load: {url}")
        
        # Additional wait for content
        time.sleep(2)
        
        # Dismiss any modal popups
        try:
            from scrape_grants import dismiss_any_modal
            dismiss_any_modal(driver, timeout=3)
        except ImportError:
            # If we can't import, try clicking common modal buttons
            try:
                close_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    "button.close, [data-dismiss='modal'], .modal .btn-primary")
                for btn in close_buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
            except:
                pass
        
        # Get the HTML
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract general details from competition div
        competition_divs = soup.select("#competitionDetail, .freeformCompetitionDetail, div[id*='competitiondetail']")
        competition_div = competition_divs[0] if competition_divs else soup
        
        # Get key-value details
        detailed_info = {}
        for elem in competition_div.select("div, span, td, li"):
            text = elem.get_text(" ", strip=True)
            if ":" not in text:
                continue
            
            try:
                key, value = map(str.strip, text.split(":", 1))
                if key and value:
                    detailed_info[key] = value
            except:
                pass
        
        # Try to find description
        description = ""
        
        # Look for any element with description in the id/class
        desc_elements = soup.select("[id*='description' i], [class*='description' i]")
        if desc_elements:
            description = desc_elements[0].get_text(" ", strip=True)
        
        # If no description found, try looking for a Description heading
        if not description:
            import re
            heading = soup.find(string=re.compile(r"^\s*Description\s*$", re.I))
            if heading:
                container = heading.parent
                pieces = []
                for sib in container.next_siblings:
                    if isinstance(sib, str):
                        continue
                    txt = sib.get_text(" ", strip=True)
                    if not txt:
                        continue
                    if len(txt) < 50 and txt.endswith(":"):
                        break
                    pieces.append(txt)
                    if len(pieces) >= 8:
                        break
                if pieces:
                    description = " ".join(pieces)
        
        # Assemble details
        details = {
            "id": competition_id,
            "details": detailed_info,
            "description_full": description,
            "fetched_date": datetime.now().isoformat()
        }
        
    finally:
        driver.quit()
    
    return details


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Track and manage grants from InfoReady portals."
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only scan for grants, don't fetch details"
    )
    parser.add_argument(
        "--fetch-details",
        action="store_true",
        help="Fetch details for new grants"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all known grants in the database"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show a summary of the grants database"
    )
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help=f"Base URL (default: {DEFAULT_BASE})"
    )
    parser.add_argument(
        "--source",
        default="umich",
        help="Source identifier for the grants (default: umich)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help=f"Output directory (default: output)"
    )
    args = parser.parse_args()
    
    # Set output directory
    OUTPUT_DIR = Path(args.output_dir)
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    DATABASE_PATH = OUTPUT_DIR / "tracked_grants.json"
    
    # Initialize database
    db = GrantsDatabase()
    
    if args.list:
        # List all grants in database
        if not db.grants:
            print("No grants in database yet.")
            return
        
        # Get sources for grouping
        sources = db.get_sources()
        
        print(f"Found {len(db.grants)} grants in database across {len(sources)} sources:")
        
        # Group by source
        for source in sorted(sources):
            source_grants = db.get_grants_by_source(source)
            print(f"\nSource: {source} ({len(source_grants)} grants)")
            
            # List grants for this source
            for grant in sorted(source_grants.values(), key=lambda g: g.get("id", "")):
                print(f"  [{grant.get('id', 'Unknown')}] {grant.get('title', 'Unknown')} "
                      f"(first seen: {grant.get('first_seen', 'Unknown')})")
        
        return
    
    if args.summary:
        # Show database summary
        summary = db.get_summary()
        print(f"Grants Database Summary:")
        print(f"  Total grants: {summary['count']}")
        
        # Show source breakdown
        sources = summary.get('sources', [])
        if sources:
            print(f"  Sources: {len(sources)}")
            for source, count in summary.get('by_source', {}).items():
                print(f"    - {source}: {count} grants")
        
        if summary['count'] > 0:
            oldest = summary.get('oldest', {})
            newest = summary.get('newest', {})
            lowest = summary.get('lowest_id', {})
            highest = summary.get('highest_id', {})
            
            if oldest:
                print(f"  Oldest grant: [{oldest.get('id')}] {oldest.get('title')} "
                      f"(source: {oldest.get('source', 'unknown')}, first seen: {oldest.get('first_seen')})")
            
            if newest:
                print(f"  Newest grant: [{newest.get('id')}] {newest.get('title')} "
                      f"(source: {newest.get('source', 'unknown')}, first seen: {newest.get('first_seen')})")
            
            if lowest:
                print(f"  Lowest ID: [{lowest.get('id')}] {lowest.get('title')} "
                      f"(source: {lowest.get('source', 'unknown')})")
            
            if highest:
                print(f"  Highest ID: [{highest.get('id')}] {highest.get('title')} "
                      f"(source: {highest.get('source', 'unknown')})")
        
        return
    
    # Scan for all current grants
    scanned_grants = scan_for_grants(args.base)
    logger.info(f"Found {len(scanned_grants)} grants on the site")
    
    # Create unique IDs with source prefix for checking
    source = args.source
    current_ids = {f"{source}:{id}" for id in scanned_grants.keys()}
    
    # Check which ones are new
    known_ids = db.get_known_ids()
    new_ids = current_ids - known_ids
    
    # Extract the actual IDs from the unique IDs
    new_actual_ids = [id.split(":", 1)[1] for id in new_ids]
    
    if new_actual_ids:
        logger.info(f"Found {len(new_actual_ids)} NEW grants from source '{source}' not in database")
        
        # Add basic info to database
        for grant_id in new_actual_ids:
            grant = scanned_grants[grant_id]
            db.add_grant(grant_id, grant['title'], grant['url'], source=source)
        
        # Save updated database
        db.save()
        
        # Show new grants
        print(f"\nNew grants found from source '{source}':")
        for grant_id in sorted(new_actual_ids):
            grant = scanned_grants[grant_id]
            print(f"  [{grant_id}] {grant['title']}")
        
        # Fetch details if requested
        if args.fetch_details and not args.scan_only:
            logger.info(f"Fetching details for {len(new_actual_ids)} new grants from source '{source}'")
            
            # Prepare timestamped output file for new grants
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_file = OUTPUT_DIR / f"new_grants_{source}_{ts}.json"
            
            new_grants_with_details = []
            
            # Fetch details for each new grant
            for grant_id in new_actual_ids:
                grant_details = fetch_grant_details(grant_id, args.base)
                
                # Add the basic info
                basic_info = scanned_grants[grant_id]
                grant_details.update(basic_info)
                
                # Add source information
                grant_details["source"] = source
                
                # Update database
                db.add_details(grant_id, grant_details, source=source)
                
                # Add to output list
                new_grants_with_details.append(grant_details)
                
                # Small pause to be polite
                time.sleep(1)
            
            # Save updated database
            db.save()
            
            # Save new grants data to file
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(new_grants_with_details, f, indent=2)
            logger.info(f"Saved details for {len(new_grants_with_details)} new grants from source '{source}' to {out_file}")
            
            # Generate CSV
            try:
                import pandas as pd
                csv_file = out_file.with_suffix('.csv')
                df = pd.json_normalize(new_grants_with_details)
                df.to_csv(csv_file, index=False)
                logger.info(f"Also saved CSV version to {csv_file}")
            except ImportError:
                logger.warning("Pandas not available, skipping CSV generation")
    else:
        logger.info("No new grants found! Database is up to date.")
    
    # Output a summary
    summary = db.get_summary()
    logger.info(f"Database now contains {summary['count']} grants")


if __name__ == "__main__":
    main()