"""
append_store.py
-----------------
Append-only storage implementation for OpTrack.

This module provides a more efficient storage mechanism that:
1. Only appends new entries without rewriting the entire database
2. Maintains an index file for fast ID lookups
3. Reduces memory usage by not loading the entire database
4. Preserves compatibility with the existing JSON structure

Usage:
    from core.append_store import AppendStore
    
    # Initialize with a site name
    store = AppendStore(site_name="umich")
    
    # Add a new grant
    store.add_grant(grant_data)
    
    # Check if an ID exists
    if store.has_id("123456"):
        print("Grant already exists")
        
    # Get a specific grant
    grant = store.get_grant("123456")
    
    # Export to the old format (for compatibility)
    store.export_to_json()
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Set, List, Optional, Tuple
from datetime import datetime

# Setup logging
logger = logging.getLogger("append_store")
logger.setLevel(logging.INFO)

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Output directories
OUTPUT_DB_DIR = BASE_DIR / "output/db"
OUTPUT_TEST_DIR = BASE_DIR / "output/test"

# File patterns
DATA_FILE_PATTERN = "{site}_grants_data.jsonl"
INDEX_FILE_PATTERN = "{site}_grants_index.json"
LEGACY_FILE_PATTERN = "{site}_grants.json"  # For compatibility with old format


class AppendStore:
    """
    Append-only storage for grant data.
    
    Stores grants in an append-only JSONL file for efficiency:
    - Each grant is a single line in the file
    - New grants are appended to the end
    - An index file maps IDs to positions in the file
    """
    
    def __init__(self, site_name: str, is_test: bool = False):
        """
        Initialize the append store for a specific site.
        
        Args:
            site_name: The name of the site
            is_test: Whether this is a test run (uses test directory)
        """
        self.site_name = site_name
        self.output_dir = OUTPUT_TEST_DIR if is_test else OUTPUT_DB_DIR
        self.data_path = self.output_dir / DATA_FILE_PATTERN.format(site=site_name)
        self.index_path = self.output_dir / INDEX_FILE_PATTERN.format(site=site_name)
        self.legacy_path = self.output_dir / LEGACY_FILE_PATTERN.format(site=site_name)
        
        # Ensure the output directory exists
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # The index maps grant IDs to line numbers in the data file
        self.index: Dict[str, int] = {}
        
        # Metadata about the database
        self.metadata = {
            "site": site_name,
            "count": 0,
            "last_updated": datetime.now().isoformat()
        }
        
        # Load the index if it exists
        self._load_index()
        
        # If there's no index but a legacy database exists, initialize from legacy
        if not self.index and self.legacy_path.exists():
            self._initialize_from_legacy()
    
    def _load_index(self) -> None:
        """Load the index file that maps grant IDs to line numbers."""
        if not self.index_path.exists():
            self.index = {}
            return
        
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.index = data.get("index", {})
                self.metadata = {
                    "site": data.get("site", self.site_name),
                    "count": data.get("count", 0),
                    "last_updated": data.get("last_updated", datetime.now().isoformat())
                }
            logger.info(f"Loaded index with {len(self.index)} entries for {self.site_name}")
        except Exception as e:
            logger.error(f"Error loading index for {self.site_name}: {e}")
            self.index = {}
    
    def _save_index(self) -> None:
        """Save the index file that maps grant IDs to line numbers."""
        data = {
            "site": self.site_name,
            "count": len(self.index),
            "last_updated": datetime.now().isoformat(),
            "index": self.index
        }
        
        # Update metadata
        self.metadata.update({
            "count": len(self.index),
            "last_updated": datetime.now().isoformat()
        })
        
        # Save index
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def _initialize_from_legacy(self) -> None:
        """Initialize from a legacy database file if it exists."""
        if not self.legacy_path.exists():
            return
        
        try:
            with open(self.legacy_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                grants = data.get("grants", {})
            
            # If there are no grants, nothing to do
            if not grants:
                return
                
            logger.info(f"Converting legacy database with {len(grants)} grants to append format")
            
            # Create a new data file
            with open(self.data_path, "w", encoding="utf-8") as f:
                # Write each grant on its own line
                for line_num, (grant_id, grant_data) in enumerate(grants.items()):
                    # Ensure the grant has an ID
                    if "competition_id" not in grant_data:
                        grant_data["competition_id"] = grant_id
                    
                    # Write the grant as a JSON line
                    f.write(json.dumps(grant_data) + "\n")
                    
                    # Update the index
                    self.index[grant_id] = line_num
            
            # Update metadata
            self.metadata.update({
                "site": data.get("site", self.site_name),
                "count": len(grants),
                "last_updated": data.get("last_updated", datetime.now().isoformat())
            })
            
            # Save the index
            self._save_index()
            
            logger.info(f"Successfully converted {len(grants)} grants to append format")
        except Exception as e:
            logger.error(f"Error initializing from legacy database: {e}")
    
    def has_id(self, grant_id: str) -> bool:
        """Check if a grant ID exists in the database."""
        return grant_id in self.index
    
    def get_grant(self, grant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific grant by ID.
        
        Args:
            grant_id: The ID of the grant to retrieve
            
        Returns:
            The grant data or None if not found
        """
        if not self.has_id(grant_id):
            return None
        
        try:
            # Get the line number from the index
            line_num = self.index[grant_id]
            
            # Open the data file and seek to the correct line
            with open(self.data_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i == line_num:
                        # Found the line, parse the JSON
                        return json.loads(line)
            
            # If we got here, the line wasn't found
            return None
        except Exception as e:
            logger.error(f"Error retrieving grant {grant_id}: {e}")
            return None
    
    def add_grant(self, grant_data: Dict[str, Any]) -> bool:
        """
        Add a new grant to the database or update an existing one.
        
        Args:
            grant_data: The grant data to add
            
        Returns:
            True if the grant was added/updated, False on error
        """
        # Ensure the grant has an ID
        grant_id = grant_data.get("competition_id")
        if not grant_id:
            logger.error("Cannot add grant without competition_id")
            return False
        
        try:
            # Check if this is an update to an existing grant
            if self.has_id(grant_id):
                # Get the existing grant
                existing = self.get_grant(grant_id)
                if existing:
                    # Merge with existing data
                    existing.update(grant_data)
                    grant_data = existing
                
                # In an append-only store, updates are new appends with updated index
                line_num = self._append_to_file(grant_data)
                if line_num is not None:
                    self.index[grant_id] = line_num
                    self._save_index()
                    return True
                return False
            
            # This is a new grant
            line_num = self._append_to_file(grant_data)
            if line_num is not None:
                self.index[grant_id] = line_num
                self._save_index()
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding grant {grant_id}: {e}")
            return False
    
    def _append_to_file(self, grant_data: Dict[str, Any]) -> Optional[int]:
        """
        Append a grant to the data file.
        
        Args:
            grant_data: The grant data to append
            
        Returns:
            The line number where the grant was appended, or None on error
        """
        try:
            # Determine the line number for this new entry
            line_num = len(self.index)
            
            # Open the file in append mode
            with open(self.data_path, "a", encoding="utf-8") as f:
                # Write the grant as a JSON line
                f.write(json.dumps(grant_data) + "\n")
            
            return line_num
        except Exception as e:
            logger.error(f"Error appending to file: {e}")
            return None
    
    def update_from_scrape(self, scraped_records: List[Dict[str, Any]]) -> int:
        """
        Update the database with newly scraped records.
        
        Args:
            scraped_records: List of newly scraped grant records
            
        Returns:
            Number of new grants added
        """
        new_count = 0
        
        for record in scraped_records:
            competition_id = record.get("competition_id", "")
            if not competition_id:
                continue
            
            # Add the grant (this handles both new and updates)
            if self.add_grant(record):
                if not self.has_id(competition_id):
                    new_count += 1
        
        if new_count > 0:
            logger.info(f"Added {new_count} new grants to {self.site_name} database")
        else:
            logger.info(f"No new grants added to {self.site_name} database")
        
        return new_count
    
    def get_all_ids(self) -> Set[str]:
        """Get all grant IDs in the database."""
        return set(self.index.keys())
    
    def export_to_json(self) -> bool:
        """
        Export the database to a JSON file in the legacy format.
        This is for compatibility with existing code that expects the old format.
        
        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Create grants dictionary
            grants = {}
            
            # Read all grants from the data file
            with open(self.data_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    try:
                        grant = json.loads(line)
                        grant_id = grant.get("competition_id")
                        if grant_id:
                            grants[grant_id] = grant
                    except Exception as e:
                        logger.error(f"Error parsing line {line_num}: {e}")
            
            # Create the legacy format
            data = {
                "site": self.site_name,
                "grants": grants,
                "last_updated": datetime.now().isoformat(),
                "count": len(grants)
            }
            
            # Write to the legacy path
            with open(self.legacy_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported {len(grants)} grants to legacy format at {self.legacy_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return False
    
    def compact(self) -> bool:
        """
        Compact the data file by removing duplicates and outdated entries.
        This should be run periodically to prevent the data file from growing too large.
        
        Returns:
            True if compaction was successful, False otherwise
        """
        try:
            # Create a temporary file
            temp_path = self.data_path.with_suffix(".tmp")
            
            # Map of IDs to most recent data
            latest_data = {}
            
            # Read all grants from the data file
            with open(self.data_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        grant = json.loads(line)
                        grant_id = grant.get("competition_id")
                        if grant_id:
                            # Keep only the latest version of each grant
                            latest_data[grant_id] = grant
                    except Exception as e:
                        logger.error(f"Error parsing line: {e}")
            
            # Write to the temporary file
            with open(temp_path, "w", encoding="utf-8") as f:
                # Update the index with new line numbers
                new_index = {}
                for line_num, (grant_id, grant) in enumerate(latest_data.items()):
                    f.write(json.dumps(grant) + "\n")
                    new_index[grant_id] = line_num
            
            # Replace the old file with the new one
            temp_path.replace(self.data_path)
            
            # Update the index
            self.index = new_index
            self._save_index()
            
            logger.info(f"Compacted database from {len(self.index)} to {len(new_index)} entries")
            return True
        except Exception as e:
            logger.error(f"Error compacting database: {e}")
            return False