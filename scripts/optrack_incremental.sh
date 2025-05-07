#!/bin/bash
# OpTrack incremental scraping script - designed for cron jobs
# Performs an efficient, incremental update of grant databases for all enabled sites

# Default values
MAX_ITEMS=""
OUTPUT_DIR="output/db"
TEST_MODE=false
SITE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --test)
      TEST_MODE=true
      OUTPUT_DIR="output/test"
      shift
      ;;
    --max-items)
      MAX_ITEMS="--max-items $2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --site)
      SITE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--test] [--max-items N] [--output-dir DIR] [--site SITE]"
      exit 1
      ;;
  esac
done

# Change to project root directory
cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Ensure output directories exist
mkdir -p $OUTPUT_DIR

# Create timestamp for log
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "==== OpTrack incremental scan started at $timestamp ====" >> $OUTPUT_DIR/scan_log.txt

# Show execution mode
if [ "$TEST_MODE" = true ]; then
  echo "Running in TEST MODE"
  echo "- Output directory: $OUTPUT_DIR"
  echo "- Max items: ${MAX_ITEMS:-'unlimited'}"
  [ -n "$SITE" ] && echo "- Site: $SITE"
fi

# Read site information from websites.json and process each enabled site
python -c "
import json
import os
import subprocess
import sys

# Pass command-line arguments from shell to this Python script
output_dir = '$OUTPUT_DIR'
max_items_arg = '$MAX_ITEMS'
site_filter = '$SITE'
timestamp = '$timestamp'

# Load websites config
with open('data/websites.json') as f:
    config = json.load(f)

# Filter sites if specified
websites = config['websites']
if site_filter:
    websites = [site for site in websites if site.get('name') == site_filter and site.get('enabled', True)]
    if not websites:
        print(f\"No enabled site found with name '{site_filter}'\")
        sys.exit(1)
else:
    websites = [site for site in websites if site.get('enabled', True)]

# Process each site
for site in websites:
    site_name = site['name']
    site_url = site['url']
    
    print(f\"Processing {site_name} ({site_url})...\")
    
    # Log start
    with open(f'{output_dir}/scan_log.txt', 'a') as log:
        log.write(f\"Processing {site_name} ({site_url})...\\n\")
    
    # Step 1: Fast scan to identify new grants (with max items limit if specified)
    fast_scan_cmd = [
        'python', 'utils/scrape_grants.py',
        '--site', site_name,
        '--fast-scan',
        '--output-dir', output_dir
    ]
    
    # Add max items if specified
    if max_items_arg:
        fast_scan_cmd.extend(max_items_arg.split())
        
    subprocess.run(fast_scan_cmd)
    
    # Step 2: Get details for new grants incremental mode
    incremental_cmd = [
        'python', 'utils/scrape_grants.py',
        '--site', site_name,
        '--incremental',
        '--output-dir', output_dir
    ]
    
    # Add max items if specified
    if max_items_arg:
        incremental_cmd.extend(max_items_arg.split())
        
    subprocess.run(incremental_cmd)
    
    # Step 3: Convert to CSV
    csv_cmd = [
        'python', 'utils/json_converter.py',
        '--site', site_name,
        '--output-dir', output_dir
    ]
    
    subprocess.run(csv_cmd)
    
    print(f\"Completed processing {site_name}\")
    
# Generate summary
with open(f'{output_dir}/grant_summary.txt', 'w') as summary:
    summary.write(f\"Database Summary - {timestamp}\\n\")
    summary.write(\"-\" * 50 + \"\\n\")
    
    # Count entries in each database
    for site in config['websites']:
        if (not site_filter or site.get('name') == site_filter) and site.get('enabled', True):
            site_name = site['name']
            db_file = f\"{output_dir}/{site_name}_grants.json\"
            
            if os.path.exists(db_file):
                # Count entries by counting competition_id occurrences
                try:
                    with open(db_file, 'r') as f:
                        content = f.read()
                        count = content.count('\"competition_id\"')
                    summary.write(f\"{site_name}: {count} grants\\n\")
                except Exception as e:
                    summary.write(f\"{site_name}: Error reading database - {e}\\n\")
            else:
                summary.write(f\"{site_name}: No database file found\\n\")
    
    summary.write(\"-\" * 50 + \"\\n\")
"

echo "==== OpTrack incremental scan completed at $(date) ====" >> $OUTPUT_DIR/scan_log.txt
echo "Scan complete. See $OUTPUT_DIR/grant_summary.txt for results."