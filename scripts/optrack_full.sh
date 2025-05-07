#!/bin/bash
# OpTrack full scraping script - rebuilds the entire database
# Use this for a complete non-incremental scan of all enabled sites

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
REPO_PATH=$(pwd)

# Activate virtual environment
source venv/bin/activate

# Ensure output directories exist
mkdir -p $OUTPUT_DIR

# Create timestamp for log
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "==== OpTrack full scan started at $timestamp ====" >> $OUTPUT_DIR/scan_log.txt

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
import time

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
    
    print(f\"Full scan of {site_name} ({site_url})...\")
    
    # Log start
    with open(f'{output_dir}/scan_log.txt', 'a') as log:
        log.write(f\"Full scan of {site_name} ({site_url})...\\n\")
    
    # Do a complete non-incremental scan (with max items limit if specified)
    # This will overwrite the existing database
    scan_cmd = [
        'python', 'utils/scrape_grants.py',
        '--site', site_name,
        '--output-dir', output_dir
    ]
    
    # Add max items if specified
    if max_items_arg:
        scan_cmd.extend(max_items_arg.split())
        
    # Always use headless mode for automated jobs
        
    subprocess.run(scan_cmd)
    
    # Convert to CSV
    csv_cmd = [
        'python', 'utils/json_converter.py',
        '--site', site_name,
        '--output-dir', output_dir
    ]
    
    subprocess.run(csv_cmd)
    
    print(f\"Completed processing {site_name}\")
    
    # Short pause between sites to avoid overwhelming the server
    if len(websites) > 1:
        time.sleep(2)
        
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

echo "==== OpTrack full scan completed at $(date) ====" >> $OUTPUT_DIR/scan_log.txt
COMPLETION_TIME=$(date +"%Y-%m-%d %H:%M:%S")
echo "Scan complete. See $OUTPUT_DIR/grant_summary.txt for results."

# Create a log entry in the dedicated logs directory
LOG_DIR="$REPO_PATH/logs/scheduled_runs"
LOG_FILE="$LOG_DIR/run_$(date +"%Y%m%d_%H%M%S").log"
mkdir -p "$LOG_DIR"

# Prepare the log content
{
  echo "==== OpTrack Scheduled Run ===="
  echo "Date: $COMPLETION_TIME"
  echo "Mode: Full"
  echo "Output Directory: $OUTPUT_DIR"
  echo ""
  echo "=== Sites Processed ==="
  
  # Get database statistics for the log
  if [ -f "$OUTPUT_DIR/grant_summary.txt" ]; then
    cat "$OUTPUT_DIR/grant_summary.txt" >> "$LOG_FILE"
  fi
  
  echo ""
  echo "=== Grants in Database ==="
  # This will be populated by the git diff check below
} > "$LOG_FILE"

# Only perform Git operations if not in test mode
if [ "$TEST_MODE" = false ]; then
  # Check if there are any changes to commit
  HAS_CHANGES=false
  if git status --porcelain | grep -q "$OUTPUT_DIR"; then
    HAS_CHANGES=true
    # Determine which files changed
    CHANGED_FILES=$(git status --porcelain | grep "$OUTPUT_DIR" | awk '{print $2}')
    echo "$CHANGED_FILES" >> "$LOG_FILE"
    
    # Count grants from the summary file
    GRANTS_COUNT=0
    if [ -f "$OUTPUT_DIR/grant_summary.txt" ]; then
      # Extract the total count
      GRANTS_COUNT=$(grep -o "[0-9]* grants" "$OUTPUT_DIR/grant_summary.txt" | awk '{s+=$1} END {print s}')
    fi
    
    # Prepare commit message for the log file
    COMMIT_MSG="Full database rebuild: $GRANTS_COUNT grants on $(date +"%Y-%m-%d")"
    echo "Commit message: $COMMIT_MSG" >> "$LOG_FILE"
    
    # Commit the changes (only database files, not log file)
    git add $OUTPUT_DIR
    git commit -m "$COMMIT_MSG"
    
    echo ""
    echo "✅ Changes committed to Git: $COMMIT_MSG"
  else
    echo "No changes detected in the database." >> "$LOG_FILE"
    echo "ℹ️  No changes detected, nothing to commit."
  fi
  
  # Always run branch management if the script exists, regardless of whether there were changes
  if [ -x "$REPO_PATH/scripts/push_to_updates_branch.sh" ]; then
    echo "🔄 Running branch management system..."
    
    # Always run the branch management script, which will handle logs appropriately
    "$REPO_PATH/scripts/push_to_updates_branch.sh"
    echo "Ran branch management system" >> "$LOG_FILE"
  fi
fi

# If in test mode, show cleanup command
if [ "$TEST_MODE" = true ]; then
  echo -e "\nℹ️  Clean up test files:"
  echo "    • Inside venv: python tests/purge_tests.py --force"
  echo "    • Outside venv: source venv/bin/activate && python tests/purge_tests.py --force"
fi