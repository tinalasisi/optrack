#!/usr/bin/env python
"""
Convert grant data JSON to CSV with minimal processing.
Preserves detailed information in JSON format for flexibility.
"""
import argparse
import json
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Convert grant JSON to CSV with minimal processing")
    parser.add_argument("json_file", help="Input JSON file")
    parser.add_argument("-o", "--output", help="Output CSV filename")
    parser.add_argument("--output-dir", 
                       default="output",
                       help="Directory to save output files (default: 'output')")
    args = parser.parse_args()
    
    # Handle paths
    input_path = Path(args.json_file)
    
    # Create output directory if needed
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
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
    
    print(f"Loaded {len(data)} records from {input_path}")
    
    # Extract consistent fields, keep details as JSON
    records = []
    for item in data:
        record = {
            'title': item.get('title', ''),
            'link': item.get('link', ''),
            'competition_id': item.get('competition_id', ''),
            'site': item.get('site', ''),
            'description': item.get('description_full', '').strip(),
            'details_json': json.dumps(item.get('details', {}))
        }
        records.append(record)
    
    # Create DataFrame and save
    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"✅ CSV written to {output_path}")
    print(f"  Columns: {', '.join(df.columns)}")
    print(f"  Records: {len(df)}")

if __name__ == "__main__":
    main()