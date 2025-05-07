#!/usr/bin/env python
"""
Test script for InfoReady scraper.

Creates a dedicated output/test directory
and runs a small test scrape to verify functionality.
"""
import os
import sys
import argparse
import subprocess
import datetime
from pathlib import Path
import json
import shutil

# Test directory setup
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DB_DIR = OUTPUT_DIR / "db"
TEST_DIR = OUTPUT_DIR / "test"

def ensure_directory(path: Path):
    """Create directory if it doesn't exist."""
    path.mkdir(exist_ok=True, parents=True)

def run_command(cmd: list, desc: str = None):
    """Run a command and print output."""
    if desc:
        print(f"\n=== {desc} ===")
    
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error output: {e.stderr}")
        return None

def test_scraper(args):
    """Run a test scrape with minimal parameters."""
    # Set up timestamp for filenames
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create test directories
    ensure_directory(TEST_DIR)
    
    # Base URL and test parameters
    base_url = args.base_url
    site_name = args.site
    items = args.items
    
    # Run the scraper with site-specific settings
    scrape_cmd = [
        sys.executable, 
        str(BASE_DIR / "utils/scrape_grants.py"),
        "--base", base_url,
        "--site", site_name,
        "--max-items", str(items),
        "--output-dir", str(TEST_DIR),
        # Default is now non-incremental, so no need for a flag
    ]
    
    print(f"\n🧪 Running test scrape for site '{site_name}'...")
    run_command(scrape_cmd, "Scraper Output")
    
    # Check for site-specific database file
    db_pattern = f"{site_name}_grants.json"
    db_file = TEST_DIR / db_pattern
    
    if not db_file.exists():
        print(f"❌ Test failed! No site database file was created: {db_pattern}")
        return False
    
    print(f"✅ Found site database file: {db_file.name}")
    
    # Convert JSON to CSV using our enhanced converter
    converter_cmd = [
        sys.executable,
        str(BASE_DIR / "utils/json_converter.py"),
        "--site", site_name,
        "--output-dir", str(TEST_DIR)
    ]
    
    print("\n🧮 Converting JSON to CSV...")
    run_command(converter_cmd, "Converter Output")
    
    # Check for CSV file
    csv_pattern = f"{site_name}_grants.csv"
    csv_file = TEST_DIR / csv_pattern
    
    if not csv_file.exists():
        print(f"❌ Test failed! No CSV file was created: {csv_pattern}")
        return False
    
    print(f"✅ Found CSV file: {csv_file.name}")
    
    # Print test summary
    print("\n📊 Test Summary:")
    print(f"  - Test time: {timestamp}")
    print(f"  - Site: {site_name}")
    print(f"  - Records requested: {items}")
    
    # Check database file content
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            grants = data.get('grants', {})
            print(f"  - Records in database: {len(grants)}")
    except Exception as e:
        print(f"  - Error reading database: {e}")
    
    print(f"\nTest files are located in: {TEST_DIR}")
    print("Run 'python tests/purge_tests.py' to clean up test files when done.")
    
    return True

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run a test scrape")
    parser.add_argument(
        "--base-url", 
        default="https://umich.infoready4.com",
        help="Base URL to scrape (default: https://umich.infoready4.com)"
    )
    parser.add_argument(
        "--site", 
        default="umich",
        help="Site name to use for the test (default: umich)"
    )
    parser.add_argument(
        "--items", 
        type=int, 
        default=5,
        help="Number of items to scrape (default: 5)"
    )
    args = parser.parse_args()
    
    # Run test
    test_scraper(args)

if __name__ == "__main__":
    main()