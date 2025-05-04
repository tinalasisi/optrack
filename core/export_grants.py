#!/usr/bin/env python
"""
Export Script - To export grant data from the database.

This script provides functionality to export the entire grants database
or specific sources to separate files.
"""
import sys
import json
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Import from the local grant_tracker module
# When running from the repository root, use:
# from core.grant_tracker import GrantsDatabase, OUTPUT_DIR
# When running from the core directory, use:
from grant_tracker import GrantsDatabase, OUTPUT_DIR

def export_all_grants(db: GrantsDatabase, output_dir: Path) -> None:
    """Export all grants to a single JSON file."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"all_grants_{ts}.json"
    
    # Export to JSON
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(list(db.grants.values()), f, indent=2)
    print(f"Exported all {len(db.grants)} grants to {out_file}")
    
    # Export to CSV if pandas is available
    try:
        csv_file = out_file.with_suffix('.csv')
        df = pd.json_normalize(list(db.grants.values()))
        df.to_csv(csv_file, index=False)
        print(f"Also saved CSV version to {csv_file}")
    except Exception as e:
        print(f"Error creating CSV: {e}")

def export_by_source(db: GrantsDatabase, sources: List[str], output_dir: Path) -> None:
    """Export grants for specific sources to separate files."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for source in sources:
        source_grants = db.get_grants_by_source(source)
        if not source_grants:
            print(f"No grants found for source: {source}")
            continue
            
        out_file = output_dir / f"{source}_grants_{ts}.json"
        
        # Export to JSON
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(list(source_grants.values()), f, indent=2)
        print(f"Exported {len(source_grants)} grants from source '{source}' to {out_file}")
        
        # Export to CSV if pandas is available
        try:
            csv_file = out_file.with_suffix('.csv')
            df = pd.json_normalize(list(source_grants.values()))
            df.to_csv(csv_file, index=False)
            print(f"Also saved CSV version to {csv_file}")
        except Exception as e:
            print(f"Error creating CSV: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Export grant data from the database."
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help=f"Output directory (default: output)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export all grants to a single file"
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        help="Export grants for specific sources (space-separated list)"
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List all available sources in the database"
    )
    args = parser.parse_args()
    
    # Set output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Initialize database
    db = GrantsDatabase()
    
    if args.list_sources:
        sources = db.get_sources()
        print(f"Available sources ({len(sources)}):")
        for source in sorted(sources):
            source_count = len(db.get_grants_by_source(source))
            print(f"  {source}: {source_count} grants")
        return
    
    if args.all:
        export_all_grants(db, output_dir)
    
    if args.sources:
        export_by_source(db, args.sources, output_dir)
    
    if not (args.all or args.sources or args.list_sources):
        print("No export action specified. Use --all or --sources to export data.")
        print("Use --list-sources to see available sources.")
        return

if __name__ == "__main__":
    main()