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
REPO_PATH=$(pwd)

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

# Create a log directory for this run with date and time
RUN_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$REPO_PATH/logs/runs/$RUN_TIMESTAMP"
mkdir -p "$LOG_DIR"

# IMPORTANT: Capture grant IDs BEFORE scraping
# Create a file to store the BEFORE counts for compatibility
PREVIOUS_COUNTS_FILE="$LOG_DIR/before_counts.txt"
echo "# Grant counts BEFORE scraping $(date)" > "$PREVIOUS_COUNTS_FILE"

# Also create a JSON file with all grant IDs for accurate comparison
PREVIOUS_IDS_FILE="$LOG_DIR/before_ids.json"

# Get all competition IDs from current databases
python -c "
import json
import os
import sys

# Function to extract IDs from database file
def extract_ids(file_path):
    ids = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if 'grants' in data and isinstance(data['grants'], dict):
                    # Each key in the grants dict is a competition ID
                    ids = list(data['grants'].keys())
        except Exception as e:
            print(f\"Error extracting IDs from {file_path}: {e}\", file=sys.stderr)
    return ids

# Store results in a dictionary
result = {}

# Load websites config
try:
    with open('data/websites.json') as f:
        config = json.load(f)

    # Filter sites if specified
    site_filter = '$SITE'
    websites = config['websites']
    if site_filter:
        websites = [site for site in websites if site.get('name') == site_filter and site.get('enabled', True)]
    else:
        websites = [site for site in websites if site.get('enabled', True)]

    # Process each site
    for site in websites:
        site_name = site['name']
        db_file = \"$OUTPUT_DIR/{}_grants.json\".format(site_name)

        # Create source-specific log directory
        site_log_dir = os.path.join('$LOG_DIR', site_name)
        os.makedirs(site_log_dir, exist_ok=True)

        # Extract IDs from this site's database
        ids = extract_ids(db_file)
        result[site_name] = {
            'count': len(ids),
            'ids': ids
        }

        # Also write to the counts file for backward compatibility
        print(f\"{site_name}: {len(ids)}\")

        # Save site-specific before data
        site_before_file = os.path.join(site_log_dir, 'before_ids.json')
        with open(site_before_file, 'w') as f:
            json.dump({
                'count': len(ids),
                'ids': ids,
                'site': site_name
            }, f, indent=2)

    # Save combined results to the main before file
    with open('$PREVIOUS_IDS_FILE', 'w') as f:
        json.dump(result, f, indent=2)

except Exception as e:
    print(f\"ERROR: {e}\")
    # Create an empty JSON file to avoid errors later
    with open('$PREVIOUS_IDS_FILE', 'w') as f:
        json.dump({}, f)
" >> "$PREVIOUS_COUNTS_FILE"

# Read site information from websites.json and process each enabled site
# Export LOG_DIR for use by Python script
export LOG_DIR="$LOG_DIR"

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
        
    # Always use headless mode for automated jobs
        
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
summary_file = f'{output_dir}/grant_summary.txt'
with open(summary_file, 'w') as summary:
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
COMPLETION_TIME=$(date +"%Y-%m-%d %H:%M:%S")

# Copy scan log and grant summary to the log directory
cp "$OUTPUT_DIR/scan_log.txt" "$LOG_DIR/scan_log.txt"
cp "$OUTPUT_DIR/grant_summary.txt" "$LOG_DIR/grant_summary.txt"

echo "Scan complete. See $OUTPUT_DIR/grant_summary.txt for results."
echo "Logs saved to $LOG_DIR"

# Create a log entry only if not already provided by parent script
if [ -z "$OPTRACK_LOG_FILE" ]; then
  LOG_FILE="$LOG_DIR/run.log"

  # Prepare the log content
  {
    echo "==== OpTrack Scheduled Run ===="
    echo "Date: $COMPLETION_TIME"
    echo "Mode: Incremental"
    echo "Output Directory: $OUTPUT_DIR"
    echo ""
    echo "=== Sites Processed ==="
    
    # Get database statistics for the log
    if [ -f "$OUTPUT_DIR/grant_summary.txt" ]; then
      cat "$OUTPUT_DIR/grant_summary.txt" >> "$LOG_FILE"
    fi
    
    echo ""
    echo "=== New Grants Added ==="
    # This will be populated by the git diff check below
  } > "$LOG_FILE"
else
  # Use the log file provided by the parent script
  LOG_FILE="$OPTRACK_LOG_FILE"
  echo "Using existing log file: $LOG_FILE"
fi

# Only perform Git operations if not in test mode
if [ "$TEST_MODE" = false ]; then
  # Create a file to store the AFTER database with all competition IDs
  AFTER_IDS_FILE="$LOG_DIR/after_ids.json"

  # Get all competition IDs from current databases AFTER scraping
  python -c "
import json
import os
import sys

# Function to extract IDs from database file
def extract_ids(file_path):
    ids = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if 'grants' in data and isinstance(data['grants'], dict):
                    # Each key in the grants dict is a competition ID
                    ids = list(data['grants'].keys())
        except Exception as e:
            print(f\"Error extracting IDs from {file_path}: {e}\", file=sys.stderr)
    return ids

# Store results in a dictionary
result = {}

# Load websites config
try:
    with open('data/websites.json') as f:
        config = json.load(f)

    # Filter sites if specified
    site_filter = '$SITE'
    websites = config['websites']
    if site_filter:
        websites = [site for site in websites if site.get('name') == site_filter and site.get('enabled', True)]
    else:
        websites = [site for site in websites if site.get('enabled', True)]

    # Process each site
    for site in websites:
        site_name = site['name']
        db_file = \"$OUTPUT_DIR/{}_grants.json\".format(site_name)

        # Get the site-specific log directory
        site_log_dir = os.path.join('$LOG_DIR', site_name)
        os.makedirs(site_log_dir, exist_ok=True)

        # Extract IDs from this site's database
        ids = extract_ids(db_file)
        result[site_name] = {
            'count': len(ids),
            'ids': ids
        }

        # Save site-specific after data
        site_after_file = os.path.join(site_log_dir, 'after_ids.json')
        with open(site_after_file, 'w') as f:
            json.dump({
                'count': len(ids),
                'ids': ids,
                'site': site_name
            }, f, indent=2)

        # Copy the database file for reference
        try:
            import shutil
            if os.path.exists(db_file):
                dest_db = os.path.join(site_log_dir, f\"{site_name}_grants.json\")
                shutil.copy2(db_file, dest_db)
        except Exception as e:
            print(f\"Error copying database: {e}\", file=sys.stderr)

    # Save combined results to the main after file
    with open('$AFTER_IDS_FILE', 'w') as f:
        json.dump(result, f, indent=2)

except Exception as e:
    print(f\"ERROR: {e}\", file=sys.stderr)
    # Create an empty JSON file to avoid errors later
    with open('$AFTER_IDS_FILE', 'w') as f:
        json.dump({}, f)
"

  # Now compare the before and after IDs to find changes
  # This uses JSON for accurate ID tracking rather than just counts
  echo "=== Database Changes ===" >> "$LOG_FILE"

  # Compare the before and after ID files to find new grants
  NEW_GRANTS_COUNT=0
  HAS_CHANGES=false

  # Use Python for more accurate comparison of JSON files
  python -c "
import json
import sys
import os

try:
    # Load before and after data
    with open('$PREVIOUS_IDS_FILE', 'r') as f:
        before_data = json.load(f)

    with open('$AFTER_IDS_FILE', 'r') as f:
        after_data = json.load(f)

    # Track total new grants
    new_grants_total = 0
    has_changes = False

    # Create a comparison report file
    report_file = '$LOG_DIR/comparison_report.json'
    comparison_results = {}

    # Process each site
    for site_name, after_site in after_data.items():
        after_ids = set(after_site['ids'])
        after_count = len(after_ids)

        # Get before data for this site
        before_site = before_data.get(site_name, {'ids': [], 'count': 0})
        before_ids = set(before_site['ids'])
        before_count = len(before_ids)

        # Calculate differences
        new_ids = after_ids - before_ids
        removed_ids = before_ids - after_ids
        new_count = len(new_ids)
        removed_count = len(removed_ids)

        # Update totals
        new_grants_total += new_count
        if new_count > 0:
            has_changes = True

        # Get the site-specific log directory
        site_log_dir = os.path.join('$LOG_DIR', site_name)
        os.makedirs(site_log_dir, exist_ok=True)

        # Create site-specific comparison results
        site_results = {
            'site': site_name,
            'before_count': before_count,
            'after_count': after_count,
            'new_count': new_count,
            'new_ids': list(new_ids),
            'removed_count': removed_count,
            'removed_ids': list(removed_ids),
            'has_changes': new_count > 0
        }

        # Save site-specific comparison results
        site_comparison_file = os.path.join(site_log_dir, 'comparison.json')
        with open(site_comparison_file, 'w') as f:
            json.dump(site_results, f, indent=2)

        # Also create a human-readable report
        site_report_file = os.path.join(site_log_dir, 'report.txt')
        with open(site_report_file, 'w') as f:
            f.write(f\"=== Comparison Report for {site_name} ===\\n\")
            f.write(f\"Before count: {before_count}\\n\")
            f.write(f\"After count: {after_count}\\n\")
            f.write(f\"New grants: {new_count}\\n\")
            if new_count > 0:
                f.write(f\"New IDs: {', '.join(list(new_ids)[:10])}{' and more...' if len(new_ids) > 10 else ''}\\n\")
            f.write(f\"Removed grants: {removed_count}\\n\")
            if removed_count > 0:
                f.write(f\"Removed IDs: {', '.join(list(removed_ids)[:10])}{' and more...' if len(removed_ids) > 10 else ''}\\n\")

        # Add to overall comparison results
        comparison_results[site_name] = site_results

        # Report for this site
        if new_count > 0:
            print(f\"{site_name}: {new_count} new grants (previous: {before_count}, current: {after_count})\")
            # List some of the new IDs (limited to first 3 for brevity)
            if new_ids:
                sample_ids = list(new_ids)[:3]
                print(f\"  New IDs sample: {', '.join(sample_ids)}{' and more...' if len(new_ids) > 3 else ''}\")
        else:
            print(f\"{site_name}: No new grants (count: {after_count})\")

        # Report removed grants if any
        if removed_count > 0:
            print(f\"  Note: {removed_count} grants no longer in source but remain archived in database.\")

    # Save overall comparison results
    with open(report_file, 'w') as f:
        json.dump({
            'total_new_grants': new_grants_total,
            'has_changes': has_changes,
            'sites': comparison_results
        }, f, indent=2)

    # Write results to shell variables
    print(f\"NEW_GRANTS_COUNT={new_grants_total}\")
    print(f\"HAS_CHANGES={'true' if has_changes else 'false'}\")

except Exception as e:
    print(f\"Error comparing databases: {e}\", file=sys.stderr)
    print(\"NEW_GRANTS_COUNT=0\")
    print(\"HAS_CHANGES=false\")
" | while read -r line; do
    if [[ "$line" == NEW_GRANTS_COUNT=* ]]; then
      NEW_GRANTS_COUNT="${line#NEW_GRANTS_COUNT=}"
    elif [[ "$line" == HAS_CHANGES=* ]]; then
      HAS_CHANGES="${line#HAS_CHANGES=}"
    else
      echo "$line" >> "$LOG_FILE"
    fi
  done

  # Clean up temp files
  rm -f "$PREVIOUS_IDS_FILE" "$AFTER_IDS_FILE"

  # Always report the findings based on our direct database comparison
  if [ "$HAS_CHANGES" = true ]; then
    # Check git status, but don't rely solely on it for determining if changes occurred
    CHANGED_FILES=$(git status --porcelain | grep "$OUTPUT_DIR" | awk '{print $2}')
    if [ -n "$CHANGED_FILES" ]; then
      echo "Files with Git changes:" >> "$LOG_FILE"
      echo "$CHANGED_FILES" >> "$LOG_FILE"
    else
      echo "No Git changes detected, but database counts indicate updates occurred." >> "$LOG_FILE"
      echo "This often happens when changes were already committed on the auto-updates branch." >> "$LOG_FILE"
    fi

    # Prepare commit message for the log file
    COMMIT_MSG="Auto-update: Found $NEW_GRANTS_COUNT new grants on $(date +"%Y-%m-%d")"
    echo "Commit message: $COMMIT_MSG" >> "$LOG_FILE"

    # Attempt to commit the changes
    git add $OUTPUT_DIR
    if git commit -m "$COMMIT_MSG"; then
      echo ""
      echo "✅ Changes committed to Git: $COMMIT_MSG"
      echo "Git commit successful" >> "$LOG_FILE"
    else
      echo ""
      echo "ℹ️ No Git changes to commit, but $NEW_GRANTS_COUNT new grants were found"
      echo "No Git changes to commit, but database counters indicate $NEW_GRANTS_COUNT new grants" >> "$LOG_FILE"
      echo "This usually means the grants were already added in a previous run on this branch." >> "$LOG_FILE"
    fi

    # Record for the user that changes were detected
    echo ""
    echo "✅ Database changes detected: $NEW_GRANTS_COUNT new grants found"
  else
    # No new grants found in the database comparison
    echo "No new grants found in this scan." >> "$LOG_FILE"
    echo "ℹ️  No changes detected in grant databases."
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