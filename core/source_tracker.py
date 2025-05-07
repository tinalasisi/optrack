#!/usr/bin/env python3
"""
source_tracker.py
----------------
Manages source-specific tracking of seen competition IDs.
This allows incremental scraping by keeping track of which
competition IDs have already been processed for each source.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Optional

# Setup logging
logger = logging.getLogger("source_tracker")
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Add console handler
    import sys
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console)

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Output directories
OUTPUT_DB_DIR = BASE_DIR / "output/db"
OUTPUT_TEST_DIR = BASE_DIR / "output/test"

# History file patterns for tracking seen IDs (used in incremental mode)
HISTORY_PATTERN = "{site}_seen_competitions.json"

# History file paths
DB_HISTORY_DIR = OUTPUT_DB_DIR
TEST_HISTORY_DIR = OUTPUT_TEST_DIR


class SeenIDsTracker:
    """Tracks seen competition IDs for each source separately."""
    
    def __init__(self, is_test: bool = False):
        self.base_dir = TEST_HISTORY_DIR if is_test else DB_HISTORY_DIR
        self.is_test = is_test
        self.seen_ids: Dict[str, Set[str]] = {}
        
        # Legacy file path for backward compatibility
        self.legacy_file = self.base_dir / "seen_competitions.json"
        
        # Load any existing IDs
        self.load_all_sources()
    
    def _get_history_path(self, source: str) -> Path:
        """Get the file path for a specific source's history file."""
        # Sanitize source name to ensure valid filename
        safe_source = source.replace("/", "_").replace("\\", "_")
        return self.base_dir / HISTORY_PATTERN.format(site=safe_source)
    
    def load_all_sources(self) -> None:
        """Load seen IDs from all source-specific history files."""
        # First check legacy file for backward compatibility
        if self.legacy_file.exists():
            self._load_legacy_file()
        
        # Then look for source-specific files
        self._load_source_files()
        
        # Log summary
        total_sources = len(self.seen_ids)
        total_ids = sum(len(ids) for ids in self.seen_ids.values())
        logger.info(f"Loaded {total_ids} seen IDs across {total_sources} sources")
    
    def _load_legacy_file(self) -> None:
        """Load the legacy single history file."""
        try:
            with open(self.legacy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Handle different file formats
                if "seen_ids" in data and isinstance(data["seen_ids"], dict):
                    # Already source-segmented format
                    for source, ids in data["seen_ids"].items():
                        self.seen_ids[source] = set(ids)
                elif "seen_ids" in data and isinstance(data["seen_ids"], list):
                    # Old format with single list - migrate to default source
                    self.seen_ids["default"] = set(data["seen_ids"])
                
            logger.info(f"Loaded legacy seen IDs file: {self.legacy_file}")
            
            # Migrate legacy data to source-specific files
            self._migrate_legacy_data()
        except Exception as e:
            logger.error(f"Error loading legacy history file: {e}")
    
    def _load_source_files(self) -> None:
        """Load all source-specific history files."""
        # Look for all history files matching the pattern
        history_files = list(self.base_dir.glob("*_seen_competitions.json"))
        
        for file_path in history_files:
            # Skip legacy file if it exists
            if file_path == self.legacy_file:
                continue
                
            # Extract source name from filename
            filename = file_path.name
            source = filename.replace("_seen_competitions.json", "")
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    if "ids" in data and isinstance(data["ids"], list):
                        self.seen_ids[source] = set(data["ids"])
                        logger.info(f"Loaded {len(self.seen_ids[source])} seen IDs for source '{source}'")
            except Exception as e:
                logger.error(f"Error loading history for source '{source}': {e}")
    
    def _migrate_legacy_data(self) -> None:
        """Migrate data from legacy file to source-specific files."""
        for source, ids in self.seen_ids.items():
            source_file = self._get_history_path(source)
            
            # Skip if source file already exists
            if source_file.exists():
                continue
                
            # Save to source-specific file
            self._save_source(source)
            logger.info(f"Migrated {len(ids)} IDs for source '{source}' to {source_file}")
    
    def save(self) -> None:
        """Save all seen IDs to their respective source files."""
        # Ensure directory exists
        self.base_dir.mkdir(exist_ok=True, parents=True)
        
        # Save each source to its own file
        for source in self.seen_ids:
            self._save_source(source)
        
        # Log summary
        total_ids = sum(len(ids) for ids in self.seen_ids.values())
        logger.info(f"Saved {total_ids} seen IDs across {len(self.seen_ids)} sources")
    
    def _save_source(self, source: str) -> None:
        """Save seen IDs for a specific source."""
        # Get source-specific file path
        file_path = self._get_history_path(source)
        
        # Ensure directory exists
        file_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Prepare data for file
        data = {
            "source": source,
            "ids": list(self.seen_ids.get(source, set())),
            "count": len(self.seen_ids.get(source, set())),
            "last_updated": datetime.now().isoformat()
        }
        
        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def get_seen_ids(self, source: str) -> Set[str]:
        """Get seen IDs for a specific source."""
        return self.seen_ids.get(source, set())
    
    def add_ids(self, source: str, ids: Set[str]) -> None:
        """Add new IDs for a source."""
        if source not in self.seen_ids:
            self.seen_ids[source] = set()
        
        # Track how many new IDs are added
        new_count = len(ids - self.seen_ids[source])
        self.seen_ids[source].update(ids)
        
        if new_count > 0:
            logger.info(f"Added {new_count} new IDs for source '{source}'")
            # Save this source's file immediately
            self._save_source(source)
    
    def check_id(self, source: str, comp_id: str) -> bool:
        """Check if an ID has been seen for a specific source.
        
        Args:
            source: The source to check
            comp_id: The competition ID to check
            
        Returns:
            True if the ID has been seen, False otherwise
        """
        return comp_id in self.get_seen_ids(source)
    
    def add_id(self, source: str, comp_id: str) -> None:
        """Add a single ID for a source.
        
        Args:
            source: The source to add the ID to
            comp_id: The competition ID to add
        """
        self.add_ids(source, {comp_id})


# Legacy compatibility functions

def load_seen_ids(is_test: bool = False, source: str = "default") -> Set[str]:
    """
    Legacy function for backward compatibility.
    Loads seen IDs for the specified source (defaults to "default").
    
    Returns:
        Set of seen competition IDs for the specified source.
    """
    tracker = SeenIDsTracker(is_test=is_test)
    return tracker.get_seen_ids(source)

def save_seen_ids(seen_ids: Set[str], is_test: bool = False, source: str = "default") -> None:
    """
    Legacy function for backward compatibility.
    Saves seen IDs for the specified source (defaults to "default").
    
    Args:
        seen_ids: Set of competition IDs to save
        is_test: Whether this is a test run
        source: Source name to save the IDs for (defaults to "default")
    """
    tracker = SeenIDsTracker(is_test=is_test)
    tracker.add_ids(source, seen_ids)
    tracker.save()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage source-specific competition ID tracking")
    parser.add_argument("--list", action="store_true", help="List all sources and their ID counts")
    parser.add_argument("--source", type=str, help="Specific source to operate on")
    parser.add_argument("--list-ids", action="store_true", help="List all IDs for a specific source (requires --source)")
    parser.add_argument("--test", action="store_true", help="Use test directory instead of database directory")
    
    args = parser.parse_args()
    
    # Create tracker
    tracker = SeenIDsTracker(is_test=args.test)
    
    if args.list:
        # List all sources and their ID counts
        print(f"Sources tracked ({len(tracker.seen_ids)}):")
        for source, ids in tracker.seen_ids.items():
            print(f"  - {source}: {len(ids)} IDs")
    
    if args.source and args.list_ids:
        # List all IDs for a specific source
        ids = tracker.get_seen_ids(args.source)
        print(f"IDs for source '{args.source}' ({len(ids)}):")
        for comp_id in sorted(ids):
            print(f"  - {comp_id}")