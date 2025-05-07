#!/usr/bin/env python
"""
json_converter.py
----------------
Converts grant database JSON files to properly formatted CSV.
Handles special characters, newlines, and proper quoting to ensure
CSV files are correctly formatted for analysis and import.

Usage:
    python json_converter.py input.json [--output output.csv] [--site-db] [--output-dir DIR]
    python json_converter.py --site umich [--output-dir DIR]

The --site-db flag indicates the input is a site-specific database file,
which has a different structure than the export files.
The --site parameter allows converting a specific site's database directly.
"""
import argparse
import json
import csv
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd

# Setup logging
logger = logging.getLogger("json_converter")
logger.setLevel(logging.INFO)
if not logger.handlers:
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console)

# Define standard directories
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DB_DIR = BASE_DIR / "output/db"
OUTPUT_TEST_DIR = BASE_DIR / "output/test"

# Database file patterns
DATABASE_PATTERN = "{site}_grants.json"
CSV_PATTERN = "{site}_grants.csv"

def clean_text_for_csv(text: str) -> str:
    """
    Clean text for CSV export, handling newlines and other special characters.
    
    Args:
        text: The text to clean
        
    Returns:
        Cleaned text safe for CSV export
    """
    if not text:
        return ""
        
    # Replace newlines with spaces
    cleaned = text.replace('\n', ' ').replace('\r', ' ')
    
    # Replace problematic characters for CSV
    cleaned = cleaned.replace('"', '""')  # Double escape quotes for CSV
    
    # Handle other troublesome characters that might cause row breaks
    cleaned = cleaned.replace('\u2028', ' ')  # Line separator
    cleaned = cleaned.replace('\u2029', ' ')  # Paragraph separator
    cleaned = cleaned.replace('\f', ' ')      # Form feed
    cleaned = cleaned.replace('\v', ' ')      # Vertical tab
    
    # Replace multiple spaces with a single space
    cleaned = ' '.join(cleaned.split())
    
    return cleaned

def process_item(item: Dict[str, Any]) -> Dict[str, str]:
    """
    Process a single grant item for CSV export.
    
    Args:
        item: The grant item to process
        
    Returns:
        A dictionary with cleaned fields ready for CSV export
    """
    # Collect all extra fields into a details object
    details = {}
    for k, v in item.items():
        if k not in ['title', 'url', 'link', 'id', 'competition_id', 'site', 'description_full']:
            details[k] = v
    
    # Standardize field names
    url = item.get('url', item.get('link', ''))
    comp_id = item.get('id', item.get('competition_id', ''))
    description = item.get('description_full', item.get('description', '')).strip()
    
    # Create a clean record with proper encoding to prevent CSV issues
    record = {
        'title': clean_text_for_csv(item.get('title', '')),
        'url': url,
        'id': comp_id,
        'site': item.get('site', ''),
        'description': clean_text_for_csv(description),
        # JSON-encode with ensure_ascii and escape characters that might break CSV
        'details_json': clean_text_for_csv(json.dumps(details, ensure_ascii=True))
    }
    
    return record

def convert_to_csv(
    input_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    output_path: Path,
    is_site_db: bool = False
) -> None:
    """
    Convert input data to a properly formatted CSV file.
    
    Args:
        input_data: The data to convert (list or site DB structure)
        output_path: Path to write the CSV file
        is_site_db: Whether the input is a site-specific database
    """
    # Extract records from site DB if needed
    if is_site_db and isinstance(input_data, dict) and 'grants' in input_data:
        grants_dict = input_data.get('grants', {})
        # Convert from dict of grants to list
        records_list = list(grants_dict.values())
        logger.info(f"Extracted {len(records_list)} grants from site-specific database")
    elif isinstance(input_data, list):
        # Already a list of records
        records_list = input_data
    else:
        # Unknown format
        logger.error("Unknown input format - expected list or site database")
        return
    
    # Process each item
    records = [process_item(item) for item in records_list]
    
    # Create DataFrame
    df = pd.DataFrame(records)
    
    # Save with proper quoting to handle embedded newlines and commas
    df.to_csv(
        output_path, 
        index=False, 
        quoting=csv.QUOTE_ALL,  # Quote all fields
        quotechar='"',          # Use double quotes
        doublequote=True,       # Escape quotes by doubling them
        escapechar='\\',        # Use backslash as escape character
        lineterminator='\n'     # Explicit line terminator
    )
    
    logger.info(f"✅ CSV written to {output_path}")
    logger.info(f"  Columns: {', '.join(df.columns)}")
    logger.info(f"  Records: {len(df)}")

def convert_site_database(site: str, output_dir: Path) -> None:
    """
    Convert a site-specific database to CSV format.
    
    Args:
        site: The site name
        output_dir: Directory to write the CSV file
    """
    # Construct paths
    db_path = output_dir / DATABASE_PATTERN.format(site=site)
    csv_path = output_dir / CSV_PATTERN.format(site=site)
    
    if not db_path.exists():
        logger.error(f"Site database not found: {db_path}")
        return
    
    # Load JSON database
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded site database from {db_path}")
        convert_to_csv(data, csv_path, is_site_db=True)
        
    except Exception as e:
        logger.error(f"Error converting site database: {e}")

def main():
    parser = argparse.ArgumentParser(description="Convert grant JSON to CSV with proper formatting")
    parser.add_argument("json_file", nargs='?', help="Input JSON file")
    parser.add_argument("-o", "--output", help="Output CSV filename")
    parser.add_argument("--output-dir", 
                       default="output",
                       help="Directory to save output files (default: 'output')")
    parser.add_argument("--site-db", 
                       action="store_true",
                       help="Treat input as site-specific database format")
    parser.add_argument("--site", 
                       help="Site name to convert directly from database")
    args = parser.parse_args()
    
    # Determine which output directory to use
    if "test" in args.output_dir:
        output_dir = OUTPUT_TEST_DIR
    else:
        output_dir = OUTPUT_DB_DIR
    
    # Create output directory if needed
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Handle site-specific conversion
    if args.site:
        logger.info(f"Converting site database for '{args.site}'")
        convert_site_database(args.site, output_dir)
        return
    
    # Regular JSON file conversion
    if not args.json_file:
        parser.print_help()
        return
    
    # Handle paths
    input_path = Path(args.json_file)
    
    if args.output:
        # Use specified output path
        output_path = Path(args.output)
    else:
        # Generate output path in the output directory
        stem = input_path.stem
        output_path = output_dir / f"{stem}_clean.csv"
    
    # Load JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"Loaded {len(data) if isinstance(data, list) else 'site database'} from {input_path}")
    
    # Convert to CSV
    convert_to_csv(data, output_path, is_site_db=args.site_db)

if __name__ == "__main__":
    main()