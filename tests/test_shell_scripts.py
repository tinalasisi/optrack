#!/usr/bin/env python
"""
Test script for safely testing the OpTrack shell scripts.

This script:
1. Tests both optrack_incremental.sh and optrack_full.sh scripts
2. Processes all websites defined in data/websites.json
3. Uses emoji-based logging for clear progress visualization
4. Provides a summary of all created test files
5. Never deletes test files unless explicitly requested
"""
import os
import sys
import json
import argparse
import subprocess
import datetime
from pathlib import Path

# Set up paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
TEST_DIR = OUTPUT_DIR / "test"
CONFIG_FILE = BASE_DIR / "data/websites.json"

# Emoji constants for better display
SUCCESS = "✅"
FAIL = "❌"
WORKING = "⏳"
INFO = "ℹ️"
WARNING = "⚠️"
TEST = "🧪"
DATABASE = "🗃️"
FILE = "📄"
ROCKET = "🚀"

if __name__ != "__main__":
    import pytest
    pytest.skip(
        "Network-based functional test, skipped during pytest run",
        allow_module_level=True,
    )

def ensure_directory(path: Path):
    """Create directory if it doesn't exist."""
    path.mkdir(exist_ok=True, parents=True)
    return path

def print_header(message):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {message}")
    print("=" * 70)

def run_command(cmd: list, desc: str = None, verbose: bool = True):
    """Run a command and return the results."""
    if desc and verbose:
        print(f"\n{WORKING} {desc}")
    
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        if verbose:
            print(result.stdout)
        return True, result.stdout, ""
    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"{FAIL} Error: {e}")
            print(f"Output: {e.stdout}")
            print(f"Error output: {e.stderr}")
        return False, e.stdout, e.stderr

def load_websites():
    """Load website configuration from JSON file."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        websites = [site for site in config.get("websites", []) if site.get("enabled", True)]
        return websites
    except Exception as e:
        print(f"{FAIL} Failed to load websites from {CONFIG_FILE}: {e}")
        return []

def list_test_files():
    """List all files created in the test directory."""
    if not TEST_DIR.exists():
        return []
    
    files = []
    for file_path in TEST_DIR.glob("**/*"):
        if file_path.is_file():
            size_kb = file_path.stat().st_size / 1024
            mod_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            
            files.append({
                "path": file_path,
                "name": file_path.name,
                "size_kb": size_kb,
                "modified": mod_time
            })
    
    # Sort files by name for consistent display
    files.sort(key=lambda x: x["name"])
    return files

def print_file_summary(files):
    """Print a summary of the test files."""
    if not files:
        print(f"{INFO} No test files found in {TEST_DIR}")
        return
    
    # Group files by type
    json_files = [f for f in files if f["name"].endswith(".json")]
    csv_files = [f for f in files if f["name"].endswith(".csv")]
    log_files = [f for f in files if f["name"].endswith(".log") or f["name"].endswith(".txt")]
    other_files = [f for f in files if not (f["name"].endswith(".json") or 
                                          f["name"].endswith(".csv") or
                                          f["name"].endswith(".log") or 
                                          f["name"].endswith(".txt"))]
    
    print(f"\n{INFO} Found {len(files)} test files in {TEST_DIR}")
    
    if json_files:
        print(f"\n{DATABASE} JSON Databases ({len(json_files)}):")
        for f in json_files:
            print(f"  - {f['name']} ({f['size_kb']:.1f} KB)")
    
    if csv_files:
        print(f"\n{FILE} CSV Files ({len(csv_files)}):")
        for f in csv_files:
            print(f"  - {f['name']} ({f['size_kb']:.1f} KB)")
    
    if log_files:
        print(f"\n{INFO} Log Files ({len(log_files)}):")
        for f in log_files:
            print(f"  - {f['name']} ({f['size_kb']:.1f} KB)")
    
    if other_files:
        print(f"\n{INFO} Other Files ({len(other_files)}):")
        for f in other_files:
            print(f"  - {f['name']} ({f['size_kb']:.1f} KB)")

def test_incremental_script(sites, args):
    """Test the incremental shell script with all websites."""
    print_header(f"{ROCKET} Testing optrack_incremental.sh")
    
    ensure_directory(TEST_DIR)
    
    site_results = {}
    for site in sites:
        site_name = site.get("name")
        site_url = site.get("url")
        
        print(f"\n{WORKING} Testing incremental script on {site_name} ({site_url})")
        
        # Build command with test parameters
        cmd = [
            "bash", 
            str(BASE_DIR / "scripts/optrack_incremental.sh"),
            "--test",                       # Use test mode
            "--site", site_name,            # Specific site
            "--max-items", "1"              # Process just 1 item
        ]
        
        # Run the command
        success, stdout, stderr = run_command(
            cmd, 
            f"Running incremental script for {site_name}",
            args.verbose
        )
        
        # Store the result
        site_results[site_name] = {
            "success": success,
            "stdout": stdout,
            "stderr": stderr
        }
        
        # Show result
        if success:
            print(f"{SUCCESS} Incremental script succeeded for {site_name}")
        else:
            print(f"{FAIL} Incremental script failed for {site_name}")
    
    return site_results

def test_full_script(sites, args):
    """Test the full shell script with all websites."""
    print_header(f"{ROCKET} Testing optrack_full.sh")
    
    ensure_directory(TEST_DIR)
    
    site_results = {}
    for site in sites:
        site_name = site.get("name")
        site_url = site.get("url")
        
        print(f"\n{WORKING} Testing full script on {site_name} ({site_url})")
        
        # Build command with test parameters
        cmd = [
            "bash", 
            str(BASE_DIR / "scripts/optrack_full.sh"),
            "--test",                       # Use test mode
            "--site", site_name,            # Specific site
            "--max-items", "1"              # Process just 1 item
        ]
        
        # Run the command
        success, stdout, stderr = run_command(
            cmd, 
            f"Running full script for {site_name}",
            args.verbose
        )
        
        # Store the result
        site_results[site_name] = {
            "success": success,
            "stdout": stdout,
            "stderr": stderr
        }
        
        # Show result
        if success:
            print(f"{SUCCESS} Full script succeeded for {site_name}")
        else:
            print(f"{FAIL} Full script failed for {site_name}")
    
    return site_results

def main():
    parser = argparse.ArgumentParser(description="Test OpTrack shell scripts safely")
    parser.add_argument("--all", action="store_true", help="Test all scripts")
    parser.add_argument("--incremental", action="store_true", help="Test the incremental script")
    parser.add_argument("--full", action="store_true", help="Test the full script")
    parser.add_argument("--site", help="Only test with a specific site (default: all enabled sites)")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--list-files", action="store_true", help="Only list test files without running tests")
    args = parser.parse_args()
    
    # Load websites from configuration
    all_websites = load_websites()
    if not all_websites:
        print(f"{FAIL} No enabled websites found in configuration file")
        return
    
    # Filter to specific site if requested
    websites = all_websites
    if args.site:
        websites = [site for site in all_websites if site.get("name") == args.site]
        if not websites:
            print(f"{FAIL} No enabled website found with name '{args.site}'")
            return
    
    # If only listing files, do that and exit
    if args.list_files:
        files = list_test_files()
        print_file_summary(files)
        return
    
    # Print test configuration
    print_header(f"{TEST} OpTrack Test Configuration")
    print(f"{INFO} Testing with {len(websites)} websites:")
    for site in websites:
        print(f"  - {site.get('name')} ({site.get('url')})")
    
    # Default to testing all if no specific test is selected
    run_both = not (args.incremental or args.full or args.all)
    incremental_results = {}
    full_results = {}
    
    # Run requested tests
    if args.incremental or run_both or args.all:
        incremental_results = test_incremental_script(websites, args)
    
    if args.full or run_both or args.all:
        full_results = test_full_script(websites, args)
    
    # Print test results summary
    print_header(f"{INFO} Test Results Summary")
    
    if incremental_results:
        inc_success = sum(1 for r in incremental_results.values() if r["success"])
        print(f"{SUCCESS if inc_success == len(incremental_results) else WARNING} " 
              f"Incremental Script: {inc_success}/{len(incremental_results)} sites succeeded")
        
        # Show per-site results
        for site_name, result in incremental_results.items():
            print(f"  {SUCCESS if result['success'] else FAIL} {site_name}")
    
    if full_results:
        full_success = sum(1 for r in full_results.values() if r["success"])
        print(f"{SUCCESS if full_success == len(full_results) else WARNING} " 
              f"Full Script: {full_success}/{len(full_results)} sites succeeded")
        
        # Show per-site results
        for site_name, result in full_results.items():
            print(f"  {SUCCESS if result['success'] else FAIL} {site_name}")
    
    # Print file summary
    files = list_test_files()
    print_file_summary(files)
    
    # Show how to clean up
    print(f"\n{INFO} Clean up test files:")
    print(f"    • Inside venv: python tests/purge_tests.py --force")
    print(f"    • Outside venv: source venv/bin/activate && python tests/purge_tests.py --force")

if __name__ == "__main__":
    main()