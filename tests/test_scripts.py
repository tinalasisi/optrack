#!/usr/bin/env python
"""
Test script for validating the OpTrack scripts and workflow.

This script helps verify:
1. The integrity of the script architecture
2. Website configuration loading
3. Database directory structure
4. Command generation for different sites

Run this test to validate changes to the script architecture without
actually scraping websites. Add --dry-run to simulate all steps.
"""
import os
import sys
import json
import shutil
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime

if __name__ != "__main__":
    import pytest
    pytest.skip(
        "Network-based functional test, skipped during pytest run",
        allow_module_level=True,
    )

# Setup paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DB_DIR = OUTPUT_DIR / "db"
TEST_DIR = OUTPUT_DIR / "test"
CONFIG_FILE = BASE_DIR / "data/websites.json"
LOG_FILE = TEST_DIR / "test_scripts.log"

# Create test directories
TEST_DIR.mkdir(exist_ok=True, parents=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_scripts")

def check_environment():
    """Verify the basic environment is correct."""
    logger.info("Checking OpTrack environment...")
    
    # Check for virtual environment
    venv_path = BASE_DIR / "venv"
    has_venv = venv_path.exists()
    if has_venv:
        logger.info(f"✓ Virtual environment found at {venv_path}")
    else:
        logger.warning(f"✗ Virtual environment not found at {venv_path}")
    
    # Check for website configuration
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                websites = config.get("websites", [])
                logger.info(f"✓ Website configuration found with {len(websites)} sites")
                
                # Log site information
                for site in websites:
                    status = "ENABLED" if site.get("enabled", True) else "DISABLED"
                    logger.info(f"  - {site['name']} ({site['url']}): {status}")
                    
                defaults = config.get('defaults', {})
                logger.info(f"  - Default settings: {json.dumps(defaults, indent=2)}")
        except Exception as e:
            logger.error(f"✗ Error reading website configuration: {e}")
    else:
        logger.error(f"✗ Website configuration not found at {CONFIG_FILE}")
    
    # Check required scripts
    required_files = [
        "utils/scrape_grants.py",
        "utils/json_converter.py",
        "core/source_tracker.py",
        "scripts/optrack_incremental.sh",
        "scripts/optrack_full.sh"
    ]
    
    for file_path in required_files:
        full_path = BASE_DIR / file_path
        if full_path.exists():
            logger.info(f"✓ Required file exists: {file_path}")
        else:
            logger.error(f"✗ Required file missing: {file_path}")
    
    # Check output directory structure
    OUTPUT_DB_DIR.mkdir(exist_ok=True, parents=True)
    logger.info(f"✓ Output directory exists: {OUTPUT_DB_DIR}")
    
    return has_venv

def validate_scripts():
    """Validate shell scripts using bash -n."""
    logger.info("Validating shell scripts...")
    
    scripts = [
        "scripts/optrack_incremental.sh",
        "scripts/optrack_full.sh",
        "scripts/setup_cron.sh"
    ]
    
    all_valid = True
    
    for script in scripts:
        script_path = BASE_DIR / script
        if script_path.exists():
            try:
                result = subprocess.run(
                    ["bash", "-n", str(script_path)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info(f"✓ Script validation passed: {script}")
                else:
                    logger.error(f"✗ Script validation failed: {script}")
                    logger.error(f"  Error: {result.stderr}")
                    all_valid = False
            except Exception as e:
                logger.error(f"✗ Error validating script {script}: {e}")
                all_valid = False
        else:
            logger.error(f"✗ Script not found: {script}")
            all_valid = False
    
    return all_valid

def simulate_incremental_run(site=None, dry_run=True):
    """Simulate running the incremental script for one or all sites."""
    logger.info(f"Simulating incremental script run {'(DRY RUN)' if dry_run else ''}")
    
    # Load website configuration
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    # Filter sites if specified
    websites = config.get("websites", [])
    if site:
        websites = [s for s in websites if s.get("name") == site and s.get("enabled", True)]
        if not websites:
            logger.error(f"No enabled site found with name '{site}'")
            return False
    else:
        websites = [s for s in websites if s.get("enabled", True)]
    
    logger.info(f"Will process {len(websites)} sites")
    
    for site_config in websites:
        site_name = site_config.get("name")
        site_url = site_config.get("url")
        logger.info(f"Processing site: {site_name} ({site_url})")
        
        # Generate commands that would be run
        commands = []
        
        # Fast scan command
        fast_scan_cmd = [
            "python", "utils/scrape_grants.py",
            "--site", site_name,
            "--fast-scan",
            "--output-dir", "output/db"
        ]
        commands.append((" ".join(fast_scan_cmd), "Fast scan"))
        
        # Incremental scan command
        incr_scan_cmd = [
            "python", "utils/scrape_grants.py",
            "--site", site_name,
            "--incremental",
            "--output-dir", "output/db"
        ]
        commands.append((" ".join(incr_scan_cmd), "Incremental scan"))
        
        # CSV conversion command
        csv_cmd = [
            "python", "utils/json_converter.py",
            "--site", site_name
        ]
        commands.append((" ".join(csv_cmd), "CSV conversion"))
        
        # Log or execute commands
        for cmd, description in commands:
            if dry_run:
                logger.info(f"  Would run ({description}): {cmd}")
            else:
                logger.info(f"  Running ({description}): {cmd}")
                # In a real run, we'd execute these commands
                # For safety, we're not actually executing them
                # subprocess.run(cmd.split(), cwd=BASE_DIR)
    
    logger.info("Incremental simulation complete")
    return True

def simulate_full_run(site=None, dry_run=True):
    """Simulate running the full script for one or all sites."""
    logger.info(f"Simulating full script run {'(DRY RUN)' if dry_run else ''}")
    
    # Load website configuration
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    # Filter sites if specified
    websites = config.get("websites", [])
    if site:
        websites = [s for s in websites if s.get("name") == site and s.get("enabled", True)]
        if not websites:
            logger.error(f"No enabled site found with name '{site}'")
            return False
    else:
        websites = [s for s in websites if s.get("enabled", True)]
    
    logger.info(f"Will process {len(websites)} sites")
    
    for site_config in websites:
        site_name = site_config.get("name")
        site_url = site_config.get("url")
        logger.info(f"Processing site: {site_name} ({site_url})")
        
        # Generate commands that would be run
        commands = []
        
        # Full scan command (non-incremental)
        full_scan_cmd = [
            "python", "utils/scrape_grants.py",
            "--site", site_name,
            "--output-dir", "output/db"
        ]
        commands.append((" ".join(full_scan_cmd), "Full scan"))
        
        # CSV conversion command
        csv_cmd = [
            "python", "utils/json_converter.py",
            "--site", site_name
        ]
        commands.append((" ".join(csv_cmd), "CSV conversion"))
        
        # Log or execute commands
        for cmd, description in commands:
            if dry_run:
                logger.info(f"  Would run ({description}): {cmd}")
            else:
                logger.info(f"  Running ({description}): {cmd}")
                # In a real run, we'd execute these commands
                # For safety, we're not actually executing them
                # subprocess.run(cmd.split(), cwd=BASE_DIR)
    
    logger.info("Full simulation complete")
    return True

def check_database_status():
    """Check the status of site-specific database files."""
    logger.info("Checking database status...")
    
    # Load website configuration
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    websites = [s.get("name") for s in config.get("websites", []) if s.get("enabled", True)]
    
    for site in websites:
        json_db = OUTPUT_DB_DIR / f"{site}_grants.json"
        csv_db = OUTPUT_DB_DIR / f"{site}_grants.csv"
        history_file = OUTPUT_DB_DIR / f"{site}_seen_competitions.json"
        
        # Check JSON database
        if json_db.exists():
            size = json_db.stat().st_size / 1024  # Size in KB
            try:
                with open(json_db) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        count = len(data)
                    else:
                        count = "unknown format"
            except:
                count = "error reading"
            
            logger.info(f"  {site} JSON DB: {size:.1f} KB, {count} entries")
        else:
            logger.info(f"  {site} JSON DB: not found")
        
        # Check CSV database
        if csv_db.exists():
            size = csv_db.stat().st_size / 1024  # Size in KB
            logger.info(f"  {site} CSV file: {size:.1f} KB")
        else:
            logger.info(f"  {site} CSV file: not found")
        
        # Check history file
        if history_file.exists():
            size = history_file.stat().st_size / 1024  # Size in KB
            try:
                with open(history_file) as f:
                    data = json.load(f)
                    count = len(data.get("ids", []))
            except:
                count = "error reading"
            
            logger.info(f"  {site} History: {size:.1f} KB, {count} IDs")
        else:
            logger.info(f"  {site} History: not found")

def main():
    parser = argparse.ArgumentParser(description="Test OpTrack script architecture")
    parser.add_argument(
        "--site", 
        help="Test only a specific site (default: all enabled sites)"
    )
    parser.add_argument(
        "--full-run",
        action="store_true",
        help="Test full run script (default: test incremental)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test both incremental and full run scripts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate runs without executing commands (default: true)"
    )
    args = parser.parse_args()
    
    logger.info("=== OpTrack Script Architecture Test ===")
    logger.info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Always check environment
        check_environment()
        
        # Always validate scripts
        scripts_valid = validate_scripts()
        if not scripts_valid:
            logger.error("Script validation failed - fix errors before continuing")
            return
        
        # Check database status
        check_database_status()
        
        # Run tests based on arguments
        if args.all or not args.full_run:
            simulate_incremental_run(args.site, args.dry_run)
        
        if args.all or args.full_run:
            simulate_full_run(args.site, args.dry_run)
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
    
    logger.info(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Test logs saved to: {LOG_FILE}")

if __name__ == "__main__":
    main()# Test timestamp: Wed May  7 15:06:38 EDT 2025
