#!/usr/bin/env python
"""
Test script for InfoReady scraper.

Creates a dedicated test-output directory within output/ 
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
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
TEST_DIR = OUTPUT_DIR / "test-output"

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
    items = args.items
    suffix = f"test-{timestamp}"
    
    # Run the scraper
    scrape_cmd = [
        sys.executable, 
        str(BASE_DIR / "scrape_grants.py"),
        "--base", base_url,
        "--max-items", str(items),
        "--suffix", suffix,
        "--output-dir", str(TEST_DIR)
    ]
    
    print("\n🧪 Running test scrape...")
    run_command(scrape_cmd, "Scraper Output")
    
    # Check for JSON file
    json_pattern = f"scraped_data_*_{suffix}.json"
    json_files = list(TEST_DIR.glob(json_pattern))
    
    if not json_files:
        print("❌ Test failed! No JSON file was created.")
        return False
    
    json_file = json_files[0]
    print(f"✅ Found JSON file: {json_file.name}")
    
    # Run the improved converter
    convert_cmd = [
        sys.executable,
        str(BASE_DIR / "improved_json_to_csv.py"),
        str(json_file),
        "--output-dir", str(TEST_DIR)
    ]
    
    print("\n🧮 Running CSV converter...")
    run_command(convert_cmd, "Converter Output")
    
    # Check results
    csv_pattern = f"scraped_data_*_{suffix}_clean.csv"
    csv_files = list(TEST_DIR.glob(csv_pattern))
    
    if not csv_files:
        print("❌ Test failed! No clean CSV file was created.")
        return False
    
    csv_file = csv_files[0]
    print(f"✅ Found CSV file: {csv_file.name}")
    
    # Print test summary
    print("\n📊 Test Summary:")
    print(f"  - Test time: {timestamp}")
    print(f"  - Records requested: {items}")
    
    # Check JSON file content
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"  - Records scraped: {len(data)}")
    except Exception as e:
        print(f"  - Error reading JSON: {e}")
    
    print(f"\nTest files are located in: {TEST_DIR}")
    print("Run 'python purge_tests.py' to clean up test files when done.")
    
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
        "--items", 
        type=int, 
        default=2,
        help="Number of items to scrape (default: 2)"
    )
    args = parser.parse_args()
    
    # Run test
    test_scraper(args)

if __name__ == "__main__":
    main()