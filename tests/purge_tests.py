#!/usr/bin/env python
"""
This script removes all contents within the output/test directory while preserving the parent directory itself.
"""
import shutil
import os
from pathlib import Path
import argparse

if __name__ != "__main__":
    import pytest
    pytest.skip(
        "Utility script, skipped during pytest run",
        allow_module_level=True,
    )

# Directory setup
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DB_DIR = OUTPUT_DIR / "db"
TEST_DIR = OUTPUT_DIR / "test"

def purge_test_files(args):
    """Remove all test files and subdirectories while preserving the parent test directory."""
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
    
    # Remove all contents but preserve the parent directory
    try:
        # Remove all contents but keep the parent directory
        for item in TEST_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        print(f"✅ Successfully removed test files and subdirectories from {TEST_DIR}")
    except Exception as e:
        print(f"❌ Error removing test directory contents: {e}")

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