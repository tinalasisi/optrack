#!/usr/bin/env python
"""
stats.py - Database statistics and reporting for OpTrack.

This script provides detailed statistics about the OpTrack databases,
including counts of grants per source, seen IDs, and database health metrics.

Usage:
    python core/stats.py [--site SITE] [--output FORMAT] [--json]

Where:
    --site SITE: Optional site name to filter statistics
    --output FORMAT: Output format (text, csv, json)
    --json: Shorthand for --output json
"""

import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime
import logging
import sys
from typing import Dict, Any, List, Optional, Set

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("optrack_stats")

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Output directories
OUTPUT_DB_DIR = BASE_DIR / "output/db"
OUTPUT_TEST_DIR = BASE_DIR / "output/test"

# Database file patterns
DATABASE_PATTERN = "{site}_grants.json"
JSONL_PATTERN = "{site}_grants_data.jsonl"
INDEX_PATTERN = "{site}_grants_index.json"
SEEN_IDS_PATTERN = "{site}_seen_competitions.json"
CSV_PATTERN = "{site}_grants.csv"

def get_datetime_str(dt_str: str) -> str:
    """Convert ISO format datetime string to a more readable format."""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return dt_str

def get_site_names(is_test: bool = False) -> List[str]:
    """Get all site names from the database directory."""
    db_dir = OUTPUT_TEST_DIR if is_test else OUTPUT_DB_DIR
    site_names = set()
    
    # Check for JSON files
    for path in db_dir.glob("*_grants.json"):
        site_name = path.stem.replace("_grants", "")
        site_names.add(site_name)
        
    # Check for JSONL files
    for path in db_dir.glob("*_grants_data.jsonl"):
        site_name = path.stem.replace("_grants_data", "")
        site_names.add(site_name)
        
    # Check for seen IDs files
    for path in db_dir.glob("*_seen_competitions.json"):
        site_name = path.stem.replace("_seen_competitions", "")
        site_names.add(site_name)
        
    return sorted(list(site_names))

def get_site_stats(site_name: str, is_test: bool = False) -> Dict[str, Any]:
    """Get statistics for a specific site."""
    db_dir = OUTPUT_TEST_DIR if is_test else OUTPUT_DB_DIR

    stats = {
        "site": site_name,
        "database_exists": False,
        "seen_ids_exists": False,
        "grant_count": 0,
        "seen_ids_count": 0,
        "grants_without_details": 0,  # IDs seen but not in database
        "last_updated": None,
        "latest_pull": {
            "timestamp": None,
            "total_found": 0,
            "new_grants": 0
        },
        "storage_stats": {
            "legacy_json_size": 0,
            "jsonl_size": 0,
            "index_size": 0,
            "csv_size": 0,
            "total_size": 0
        },
        "storage_format": "unknown",
        "pending_grants": [],  # List of grants with IDs seen but no details
        "new_grants": []       # List of recently added grants
    }
    
    # Check legacy JSON database
    json_path = db_dir / DATABASE_PATTERN.format(site=site_name)
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                stats["grant_count"] = data.get("count", 0)
                stats["last_updated"] = get_datetime_str(data.get("last_updated", ""))
                stats["database_exists"] = True
                stats["storage_stats"]["legacy_json_size"] = json_path.stat().st_size
                stats["storage_format"] = "legacy_json"

                # Set latest pull timestamp to match last_updated
                stats["latest_pull"]["timestamp"] = stats["last_updated"]
                stats["latest_pull"]["total_found"] = stats["grant_count"]
        except Exception as e:
            logger.warning(f"Error reading database for {site_name}: {e}")

    # Try to find latest run log
    log_dir = BASE_DIR / "output/logs/runs"
    if log_dir.exists():
        # Find the most recent log directory
        log_dirs = sorted([d for d in log_dir.glob("*") if d.is_dir()],
                         key=lambda x: x.name, reverse=True)

        for recent_log_dir in log_dirs[:5]:  # Check the 5 most recent logs
            # Check for comparison summary file
            comparison_file = recent_log_dir / "comparison_summary.json"
            if comparison_file.exists():
                try:
                    with open(comparison_file, "r", encoding="utf-8") as f:
                        comparison_data = json.load(f)
                        if "sites" in comparison_data and site_name in comparison_data["sites"]:
                            site_data = comparison_data["sites"][site_name]
                            # Extract new grants info
                            if "new_count" in site_data and site_data["new_count"] > 0:
                                stats["latest_pull"]["new_grants"] = site_data["new_count"]
                                stats["latest_pull"]["timestamp"] = get_datetime_str(
                                    comparison_data.get("completed_at", ""))
                                # Estimate total found
                                if "before_count" in site_data and "after_count" in site_data:
                                    stats["latest_pull"]["total_found"] = site_data["after_count"]
                                
                                # Get new_ids if available and find their titles
                                if "new_ids" in site_data and site_data["new_ids"]:
                                    for new_id in site_data["new_ids"]:
                                        # Try to get the title from the database
                                        title = f"New Grant {new_id}"
                                        if json_path.exists():
                                            try:
                                                with open(json_path, "r", encoding="utf-8") as db_file:
                                                    db_data = json.load(db_file)
                                                    if "grants" in db_data and new_id in db_data["grants"]:
                                                        title = db_data["grants"][new_id].get("title", title)
                                            except Exception as e:
                                                logger.warning(f"Error getting new grant title from DB: {e}")
                                        
                                        # If not in database, try logs
                                        if title.startswith("New Grant"):
                                            log_file = db_dir / "launchd_output.log"
                                            if log_file.exists():
                                                try:
                                                    with open(log_file, "r", encoding="utf-8") as f:
                                                        log_content = f.read()
                                                        pattern = rf"- {new_id}: (.+?)(?:\n|$)"
                                                        match = re.search(pattern, log_content)
                                                        if match:
                                                            title = match.group(1).strip()
                                                except Exception as e:
                                                    logger.warning(f"Error searching logs for new grant title: {e}")
                                        
                                        stats["new_grants"].append({
                                            "id": new_id,
                                            "title": title,
                                            "source": site_name,
                                            "url": f"https://{site_name}.infoready4.com#competitionDetail/{new_id}"
                                        })
                                        
                                break
                except Exception as e:
                    logger.warning(f"Error reading comparison data for {site_name}: {e}")
    
    # Check append-only JSONL database
    jsonl_path = db_dir / JSONL_PATTERN.format(site=site_name)
    index_path = db_dir / INDEX_PATTERN.format(site=site_name)
    
    if jsonl_path.exists() and index_path.exists():
        try:
            # Get stats from index file
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
                if stats["grant_count"] == 0:  # Only set if not already set from legacy JSON
                    stats["grant_count"] = index_data.get("count", 0)
                if not stats["last_updated"]:  # Only set if not already set from legacy JSON
                    stats["last_updated"] = get_datetime_str(index_data.get("last_updated", ""))
            
            stats["storage_stats"]["jsonl_size"] = jsonl_path.stat().st_size
            stats["storage_stats"]["index_size"] = index_path.stat().st_size
            stats["storage_format"] = "append_only"
            stats["database_exists"] = True
        except Exception as e:
            logger.warning(f"Error reading append-only database for {site_name}: {e}")
    
    # Check seen IDs file
    seen_ids_path = db_dir / SEEN_IDS_PATTERN.format(site=site_name)
    if seen_ids_path.exists():
        try:
            with open(seen_ids_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                stats["seen_ids_count"] = data.get("count", 0)
                stats["seen_ids_exists"] = True
                
                # Calculate IDs seen but not in database
                if stats["database_exists"]:
                    grants_without_details = max(0, stats["seen_ids_count"] - stats["grant_count"])
                    stats["grants_without_details"] = grants_without_details
                    
                    # Get details for pending grants if there are any without details
                    if grants_without_details > 0:
                        # First, get the set of IDs with details
                        db_ids = set()
                        if json_path.exists():
                            try:
                                with open(json_path, "r", encoding="utf-8") as f:
                                    json_data = json.load(f)
                                    if "grants" in json_data and isinstance(json_data["grants"], dict):
                                        db_ids = set(json_data["grants"].keys())
                            except Exception as e:
                                logger.warning(f"Error extracting IDs from {json_path}: {e}")
                        
                        # Get seen IDs that aren't in the database
                        seen_ids = set(data.get("ids", []))
                        pending_ids = seen_ids - db_ids
                        
                        # Get information about pending grants from the launchd logs
                        for pending_id in pending_ids:
                            # Try to get title from logs
                            title = f"Unknown Grant {pending_id}"
                            log_file = db_dir / "launchd_output.log"
                            
                            if log_file.exists():
                                try:
                                    with open(log_file, "r", encoding="utf-8") as f:
                                        log_content = f.read()
                                        # Look for pattern: - {id}: {title}
                                        pattern = rf"- {pending_id}: (.+?)(?:\n|$)"
                                        match = re.search(pattern, log_content)
                                        if match:
                                            title = match.group(1).strip()
                                except Exception as e:
                                    logger.warning(f"Error searching logs for pending grant title: {e}")
                            
                            stats["pending_grants"].append({
                                "id": pending_id,
                                "title": title,
                                "source": site_name,
                                "url": f"https://{site_name}.infoready4.com#competitionDetail/{pending_id}"
                            })
        except Exception as e:
            logger.warning(f"Error reading seen IDs for {site_name}: {e}")
    
    # Check CSV file
    csv_path = db_dir / CSV_PATTERN.format(site=site_name)
    if csv_path.exists():
        stats["storage_stats"]["csv_size"] = csv_path.stat().st_size
    
    # Calculate total size
    stats["storage_stats"]["total_size"] = (
        stats["storage_stats"]["legacy_json_size"] +
        stats["storage_stats"]["jsonl_size"] +
        stats["storage_stats"]["index_size"] +
        stats["storage_stats"]["csv_size"]
    )
    
    # Convert bytes to KB for better readability
    for key in stats["storage_stats"]:
        stats["storage_stats"][key] = round(stats["storage_stats"][key] / 1024, 2)  # KB
    
    return stats

def get_all_stats(site_name: Optional[str] = None, is_test: bool = False) -> Dict[str, Any]:
    """Get statistics for all sites or a specific site."""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "environment": "test" if is_test else "production",
        "total_grants": 0,
        "total_seen_ids": 0,
        "sites": [],
        "summary": {}
    }
    
    site_names = [site_name] if site_name else get_site_names(is_test)
    
    for name in site_names:
        site_stats = get_site_stats(name, is_test)
        stats["sites"].append(site_stats)
        stats["total_grants"] += site_stats["grant_count"]
        stats["total_seen_ids"] += site_stats["seen_ids_count"]
    
    # Add summary
    stats["summary"] = {
        "total_sites": len(stats["sites"]),
        "total_grants": stats["total_grants"],
        "total_seen_ids": stats["total_seen_ids"],
        "pending_details": sum(s["grants_without_details"] for s in stats["sites"]),
        "new_grants_last_pull": sum(s["latest_pull"]["new_grants"] for s in stats["sites"]),
        "last_updated": max([s["last_updated"] for s in stats["sites"] if s["last_updated"]], default="N/A"),
        "pending_grants": [],  # Will be populated with all pending grants
        "new_grants": []       # Will be populated with all new grants
    }
    
    # Collect all pending grants and new grants in the summary
    for site in stats["sites"]:
        if site["pending_grants"]:
            stats["summary"]["pending_grants"].extend(site["pending_grants"])
        if site["new_grants"]:
            stats["summary"]["new_grants"].extend(site["new_grants"])
    
    return stats

def print_text_report(stats: Dict[str, Any]) -> None:
    """Print a text report of the statistics."""
    print(f"=== OpTrack Database Statistics ===")
    print(f"Time: {get_datetime_str(stats['timestamp'])}")
    print(f"Environment: {stats['environment']}")
    print("")
    print(f"=== Summary ===")
    print(f"Total Sites: {stats['summary']['total_sites']}")
    print(f"Total Grants: {stats['summary']['total_grants']}")
    print(f"Total Seen IDs: {stats['summary']['total_seen_ids']}")
    print(f"New Grants (Last Pull): {stats['summary']['new_grants_last_pull']}")
    print(f"Pending Details: {stats['summary']['pending_details']} (IDs seen but not in database)")
    print(f"Last Updated: {stats['summary']['last_updated']}")
    print("")

    print(f"=== Site Details ===")
    for site in stats["sites"]:
        print(f"Site: {site['site']}")
        print(f"  Database Format: {site['storage_format']}")
        print(f"  Grants in Database: {site['grant_count']}")
        print(f"  Seen IDs: {site['seen_ids_count']}")
        if site["grants_without_details"] > 0:
            print(f"  Pending Details: {site['grants_without_details']} (IDs seen but not in database)")
        print(f"  Latest Pull:")
        print(f"    Total Found: {site['latest_pull']['total_found']}")
        print(f"    New Grants: {site['latest_pull']['new_grants']}")
        print(f"    Timestamp: {site['latest_pull']['timestamp']}")
        print(f"  Last Updated: {site['last_updated']}")
        print(f"  Storage (KB):")
        print(f"    Legacy JSON: {site['storage_stats']['legacy_json_size']}")
        print(f"    JSONL Data: {site['storage_stats']['jsonl_size']}")
        print(f"    Index: {site['storage_stats']['index_size']}")
        print(f"    CSV: {site['storage_stats']['csv_size']}")
        print(f"    Total: {site['storage_stats']['total_size']}")
        print("")

def print_csv_report(stats: Dict[str, Any]) -> None:
    """Print a CSV report of the statistics."""
    # Header
    headers = [
        "site", "database_format", "grants_in_database", "seen_ids",
        "pending_details", "latest_pull_total", "latest_pull_new",
        "latest_pull_time", "last_updated", "total_kb"
    ]
    print(",".join(headers))

    # Site rows
    for site in stats["sites"]:
        row = [
            site["site"],
            site["storage_format"],
            str(site["grant_count"]),
            str(site["seen_ids_count"]),
            str(site["grants_without_details"]),
            str(site["latest_pull"]["total_found"]),
            str(site["latest_pull"]["new_grants"]),
            site["latest_pull"]["timestamp"] or "N/A",
            site["last_updated"] or "N/A",
            str(site["storage_stats"]["total_size"])
        ]
        print(",".join(row))

    # Summary row
    summary_row = [
        "TOTAL",
        "",
        str(stats["summary"]["total_grants"]),
        str(stats["summary"]["total_seen_ids"]),
        str(stats["summary"]["pending_details"]),
        "",
        str(stats["summary"]["new_grants_last_pull"]),
        "",
        stats["summary"]["last_updated"],
        ""
    ]
    print(",".join(summary_row))

def main() -> None:
    parser = argparse.ArgumentParser(description="Get statistics about OpTrack databases")
    parser.add_argument("--site", help="Site name to get statistics for")
    parser.add_argument("--test", action="store_true", help="Get statistics for test environment")
    parser.add_argument("--output", choices=["text", "json", "csv"], default="text", help="Output format")
    parser.add_argument("--json", action="store_true", help="Output in JSON format (shorthand for --output json)")
    
    args = parser.parse_args()
    
    # Handle --json flag
    if args.json:
        args.output = "json"
    
    # Get statistics
    stats = get_all_stats(args.site, args.test)
    
    # Output in the requested format
    if args.output == "json":
        print(json.dumps(stats, indent=2))
    elif args.output == "csv":
        print_csv_report(stats)
    else:
        print_text_report(stats)

if __name__ == "__main__":
    main()