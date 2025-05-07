#!/bin/bash
# OpTrack full scraping script - rebuilds the entire database
# Use this for a complete non-incremental scan of all enabled sites

# Change to project root directory
cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Ensure output directories exist
mkdir -p output/db 

# Create timestamp for log
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "==== OpTrack full scan started at $timestamp ====" >> output/db/scan_log.txt

# Read site information from websites.json and process each enabled site
python -c "
import json
import os
import subprocess
import time

# Load websites config
with open('data/websites.json') as f:
    config = json.load(f)

# Process each enabled site
for site in config['websites']:
    if site.get('enabled', True):
        site_name = site['name']
        site_url = site['url']
        
        print(f\"Full scan of {site_name} ({site_url})...\")
        
        # Log start
        with open('output/db/scan_log.txt', 'a') as log:
            log.write(f\"Full scan of {site_name} ({site_url})...\\n\")
        
        # Do a complete non-incremental scan
        # This will overwrite the existing database
        subprocess.run([
            'python', 'utils/scrape_grants.py',
            '--site', site_name,
            '--output-dir', 'output/db'
        ])
        
        # Convert to CSV
        subprocess.run([
            'python', 'utils/json_converter.py',
            '--site', site_name
        ])
        
        print(f\"Completed processing {site_name}\")
        
        # Short pause between sites to avoid overwhelming the server
        time.sleep(2)
        
# Generate summary
with open('output/db/grant_summary.txt', 'w') as summary:
    summary.write(f\"Database Summary - {timestamp}\\n\")
    summary.write(\"-\" * 50 + \"\\n\")
    
    # Count entries in each database
    for site in config['websites']:
        if site.get('enabled', True):
            site_name = site['name']
            db_file = f\"output/db/{site_name}_grants.json\"
            
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

echo "==== OpTrack full scan completed at $(date) ====" >> output/db/scan_log.txt
echo "Scan complete. See output/db/grant_summary.txt for results."