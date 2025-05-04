#!/usr/bin/env python
"""
Utility to purge test files created by test_scraper.py.

This script removes the test-output directory and all its contents.
"""
import shutil
import os
from pathlib import Path
import argparse

# Directory setup
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
TEST_DIR = OUTPUT_DIR / "test-output"

def purge_test_files(args):
    """Remove test files and directory."""
    if not TEST_DIR.exists():
        print(f"✅ No test directory found at {TEST_DIR}")
        return
    
    if args.list_only:
        # Just list the files without deleting them
        print(f"Test files that would be deleted:")
        for item in TEST_DIR.glob("**/*"):
            if item.is_file():
                print(f"  - {item.relative_to(BASE_DIR)}")
        return
    
    # Count files
    file_count = sum(1 for _ in TEST_DIR.glob("**/*") if _.is_file())
    
    # Confirm deletion
    if not args.force:
        response = input(f"This will delete {file_count} test files in {TEST_DIR}. Proceed? (y/n): ")
        if response.lower() not in ["y", "yes"]:
            print("Operation cancelled.")
            return
    
    # Remove the directory and its contents
    try:
        shutil.rmtree(TEST_DIR)
        print(f"✅ Successfully removed {file_count} test files and directory {TEST_DIR}")
    except Exception as e:
        print(f"❌ Error removing test directory: {e}")

def main():
    parser = argparse.ArgumentParser(description="Purge test files created by test_scraper.py")
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Force deletion without confirmation"
    )
    parser.add_argument(
        "--list-only", 
        action="store_true",
        help="List files that would be deleted without actually deleting them"
    )
    args = parser.parse_args()
    
    purge_test_files(args)

if __name__ == "__main__":
    main()