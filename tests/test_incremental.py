#!/usr/bin/env python
"""
Test script for incremental scraping and sorting behavior.

This script helps verify:
1. How grant listings are sorted on the page
2. If the incremental scraping correctly finds only new items
3. How duplicates are handled

Use in development mode to test these behaviors.
"""
import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import pickle
import re

if __name__ != "__main__":
    import pytest
    pytest.skip(
        "Network-based functional test, skipped during pytest run",
        allow_module_level=True,
    )

import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Setup paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DB_DIR = OUTPUT_DIR / "db"  
TEST_DIR = OUTPUT_DIR / "test"
COOKIES_PATH = BASE_DIR / "data/cookies.pkl"
LOG_FILE = TEST_DIR / "test_incremental.log"

# Source-specific history files
DEFAULT_SITE = "umich"
HISTORY_PATTERN = "{site}_seen_competitions.json"

# Create test directories
TEST_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DB_DIR.mkdir(exist_ok=True, parents=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_incremental")

# Common constants from scrape_grants.py
DEFAULT_BASE = "https://umich.infoready4.com"
LISTING_PATH = "#homePage"

def setup_test_env(site=DEFAULT_SITE):
    """Create test directory and clean any old data."""
    # Create test directory
    TEST_DIR.mkdir(exist_ok=True, parents=True)
    
    # Clear history file if exists
    history_file = TEST_DIR / HISTORY_PATTERN.format(site=site)
    if history_file.exists():
        history_file.unlink()
    
    logger.info(f"Test environment set up in {TEST_DIR} for site '{site}'")
    
def load_cookies():
    """Load cookies from the standard location."""
    if not COOKIES_PATH.exists():
        logger.warning(f"No cookie file found at {COOKIES_PATH}")
        return None
    
    try:
        with open(COOKIES_PATH, "rb") as f:
            cookies = pickle.load(f)
            logger.info(f"Loaded {len(cookies)} cookies")
            return cookies
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return None

def check_sorting_behavior(url):
    """Check how grants are sorted on the listing page."""
    driver = webdriver.Chrome()
    
    try:
        # Add cookies if available
        cookies = load_cookies()
        
        # First load the domain 
        driver.get(url)
        
        if cookies:
            for cookie in cookies:
                if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                    cookie['expiry'] = int(cookie['expiry'])
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
            
            # Refresh to apply cookies
            driver.get(url)
        
        # Navigate to main listing
        list_url = f"{url}/{LISTING_PATH}"
        driver.get(list_url)
        
        # Wait for page to load
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[competitionid]"))
            )
        except TimeoutException:
            logger.warning("Timeout waiting for listings to load")
        
        # Get page source
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # Find all competition anchors
        anchors = soup.select("a[competitionid]")
        logger.info(f"Found {len(anchors)} listing entries")
        
        if not anchors:
            logger.error("No competitions found on the page.")
            return
        
        # Extract data to check sorting
        competitions = []
        row_pattern = {
            "title": "",
            "id": "",
            "date": "",
            "organizer": "",
            "category": "",
            "raw_html": ""
        }
        
        for i, a in enumerate(anchors[:10]):  # Look at first 10 to see patterns
            comp = row_pattern.copy()
            comp["title"] = a.get_text(strip=True)
            comp["id"] = a.get("competitionid", "")
            comp["raw_html"] = str(a)
            
            # Try to extract date and other metadata
            row = a.find_parent("tr")
            if row:
                cells = row.find_all("td")
                if len(cells) >= 5:
                    comp["date"] = cells[1].get_text(strip=True)
                    comp["organizer"] = cells[2].get_text(strip=True)
                    comp["category"] = cells[3].get_text(strip=True)
            
            competitions.append(comp)
            
        # Save the data
        out_file = TEST_DIR / "sort_check.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(competitions, f, indent=2)
        
        # Analyze sorting
        logger.info("=== Sorting Analysis ===")
        
        # Check if sorted by date
        has_dates = all("date" in c and c["date"] for c in competitions)
        if has_dates:
            logger.info("Dates found in listings. Checking if sorted by date...")
            
            # Try to extract and parse dates
            dates = []
            for comp in competitions:
                date_str = comp["date"]
                # Look for common date formats
                for pattern in [r'\b(\w+\s+\d{1,2},\s+\d{4})', r'(\d{1,2}/\d{1,2}/\d{4})']:
                    match = re.search(pattern, date_str)
                    if match:
                        dates.append((comp["id"], match.group(1)))
                        break
            
            if dates:
                logger.info("Date sequence:")
                for comp_id, date in dates:
                    logger.info(f"  ID: {comp_id}, Date: {date}")
                
                # Try to determine if it's ascending or descending
                if len(dates) >= 2:
                    logger.info("It appears listings may be ordered by date.")
            else:
                logger.info("Could not extract dates for sorting analysis.")
        
        # Check if sorted alphabetically
        titles = [c["title"] for c in competitions]
        sorted_titles = sorted(titles)
        if titles == sorted_titles:
            logger.info("Listings appear to be sorted alphabetically by title (A-Z).")
        elif titles == sorted_titles[::-1]:
            logger.info("Listings appear to be sorted alphabetically by title (Z-A).")
        else:
            logger.info("Listings do not appear to be sorted alphabetically by title.")
        
        # Report IDs in sequence for future reference
        logger.info("Sequence of competition IDs:")
        for i, comp in enumerate(competitions):
            logger.info(f"  {i+1}. {comp['id']} - {comp['title'][:30]}...")
        
        return competitions
    
    finally:
        driver.quit()

def test_incremental_scraping(url, run_count=2, site=DEFAULT_SITE):
    """Test incremental scraping by running the script multiple times."""
    # Get the history file for this site
    history_file = TEST_DIR / HISTORY_PATTERN.format(site=site)
    
    for run in range(1, run_count + 1):
        logger.info(f"\n=== Incremental Test Run {run}/{run_count} for site '{site}' ===")
        
        # Create a suffix for this run
        suffix = f"incr-test-{run}"
        
        # Run the scraper with incremental mode and site-specific settings
        cmd = [
            sys.executable, 
            str(BASE_DIR / "utils/scrape_grants.py"),
            "--incremental",
            "--max-items=5",
            "--site", site,  # Add site parameter
            "--output-dir", str(TEST_DIR)
        ]
        
        # Add base URL if specified
        if url != DEFAULT_BASE:
            cmd.extend(["--base", url])
        
        logger.info(f"Running: {' '.join(cmd)}")
        output_file = None
        
        # Execute the command
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Log output
        logger.info("STDOUT:")
        for line in result.stdout.splitlines():
            logger.info(f"  {line}")
            
            # Try to extract output file from the log
            if "Saved" in line and "records" in line and "→" in line:
                parts = line.split("→")
                if len(parts) >= 2:
                    output_file = parts[1].strip()
        
        if result.stderr:
            logger.info("STDERR:")
            for line in result.stderr.splitlines():
                logger.info(f"  {line}")
        
        # Analyze result
        if run == 1:
            logger.info("First run should have found some items")
            # Check if history file was created
            if history_file.exists():
                with open(history_file, "r") as f:
                    history = json.load(f)
                    logger.info(f"History file created with {len(history.get('ids', []))} IDs for site '{site}'")
            else:
                logger.warning(f"No history file was created for site '{site}'!")
        else:
            logger.info(f"Run {run} should find fewer or no new items")
            # Check if history file was updated
            if history_file.exists():
                with open(history_file, "r") as f:
                    history = json.load(f)
                    logger.info(f"History file now has {len(history.get('ids', []))} IDs for site '{site}'")
            
        # Wait between runs to avoid rate limiting
        if run < run_count:
            time.sleep(2)
    
    # Final Summary
    logger.info(f"\n=== Incremental Testing Summary for site '{site}' ===")
    if history_file.exists():
        with open(history_file, "r") as f:
            history = json.load(f)
            logger.info(f"Final history contains {len(history.get('ids', []))} unique competition IDs")
            logger.info(f"IDs tracked: {', '.join(map(str, history.get('ids', [])))}")
    
    # List output files - look for site-specific database files
    db_files = list(TEST_DIR.glob(f"{site}_grants.*"))
    logger.info(f"Site database files generated: {len(db_files)}")
    for f in db_files:
        logger.info(f"  - {f.name}")

def main():
    parser = argparse.ArgumentParser(description="Test incremental scraping mode")
    parser.add_argument(
        "--url", 
        default=DEFAULT_BASE,
        help=f"Base URL to test (default: {DEFAULT_BASE})"
    )
    parser.add_argument(
        "--site",
        default=DEFAULT_SITE,
        help=f"Site name to test (default: {DEFAULT_SITE})"
    )
    parser.add_argument(
        "--sort-only",
        action="store_true",
        help="Only check sorting behavior, skip incremental test"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="Number of incremental test runs (default: 2)"
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep test files (don't clean up after testing)"
    )
    args = parser.parse_args()
    
    # Setup test environment for the specified site
    setup_test_env(site=args.site)
    
    try:
        # Always check sorting behavior
        logger.info(f"Checking sorting behavior at {args.url}")
        competitions = check_sorting_behavior(args.url)
        
        if not args.sort_only:
            # Test incremental scraping for the specified site
            logger.info(f"Testing incremental scraping with {args.runs} runs for site '{args.site}'")
            test_incremental_scraping(args.url, args.runs, site=args.site)
    
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
    
    # Cleanup unless --keep was specified
    if not args.keep:
        logger.info(f"Tests complete. To keep test files, run with --keep flag.")
        logger.info(f"Test logs saved to: {LOG_FILE}")
    else:
        logger.info(f"Tests complete. Test files kept in: {TEST_DIR}")
        logger.info(f"Test logs saved to: {LOG_FILE}")

if __name__ == "__main__":
    main()