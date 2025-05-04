#!/bin/bash
# Wrapper script for cron job to scan for grants from multiple sources

# Change to the directory containing the script
cd "$(dirname "$(dirname "$0")")"

# Activate virtual environment
source venv/bin/activate

# Create timestamp for logs
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "==== Grant scan started at $timestamp ====" >> output/scan_log.txt

# Run the grant tracker for all sources
echo "Scanning Michigan InfoReady portal (umich)..." >> output/scan_log.txt
python core/grant_tracker.py --fetch-details --source umich --base "https://umich.infoready4.com"
echo "Scan completed for umich at $(date)" >> output/scan_log.txt

echo "Scanning Medical School InfoReady portal (umms)..." >> output/scan_log.txt
python core/grant_tracker.py --fetch-details --source umms --base "https://umms.infoready4.com"
echo "Scan completed for umms at $(date)" >> output/scan_log.txt

# Generate a database summary report
echo "Generating database summary..." >> output/scan_log.txt
python core/grant_tracker.py --summary >> output/grant_summary.txt
echo "Summary generated at $(date)" >> output/scan_log.txt

# When you need to add more sources, duplicate the pattern above
# For example, to add a new source like NSF:
# echo "Scanning [new source]..." >> output/scan_log.txt
# python core/grant_tracker.py --fetch-details --source [source_id] --base "https://[source_url]"
# echo "Scan completed for [source_id] at $(date)" >> output/scan_log.txt

echo "==== Grant scan completed at $(date) ====" >> output/scan_log.txt