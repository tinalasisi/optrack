#!/bin/bash
# OpTrack incremental scraping script - designed for cron jobs
# Performs an efficient, incremental update of grant databases for all enabled sites

# Change to project root directory
cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Ensure output directories exist
mkdir -p output/db 

# Create timestamp for log
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "==== OpTrack incremental scan started at $timestamp ====" >> output/db/scan_log.txt

# Read site information from websites.json and process each enabled site
python -c "
import json
import os
import subprocess

# Load websites config
with open('data/websites.json') as f:
    config = json.load(f)

# Process each enabled site
for site in config['websites']:
    if site.get('enabled', True):
        site_name = site['name']
        site_url = site['url']
        
        print(f\"Processing {site_name} ({site_url})...\")
        
        # Log start
        with open('output/db/scan_log.txt', 'a') as log:
            log.write(f\"Processing {site_name} ({site_url})...\\n\")
        
        # Step 1: Fast scan to identify new grants
        subprocess.run([
            'python', 'utils/scrape_grants.py',
            '--site', site_name,
            '--fast-scan',
            '--output-dir', 'output/db'
        ])
        
        # Step 2: Get details for new grants incremental mode
        subprocess.run([
            'python', 'utils/scrape_grants.py',
            '--site', site_name,
            '--incremental',
            '--output-dir', 'output/db'
        ])
        
        # Step 3: Convert to CSV
        subprocess.run([
            'python', 'utils/json_converter.py',
            '--site', site_name
        ])
        
        print(f\"Completed processing {site_name}\")
        
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

echo "==== OpTrack incremental scan completed at $(date) ====" >> output/db/scan_log.txt
echo "Scan complete. See output/db/grant_summary.txt for results."