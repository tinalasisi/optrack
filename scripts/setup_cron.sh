#!/bin/bash
# Helper script to set up cron jobs for optrack

# Get the current directory (the base directory of the repo)
REPO_PATH=$(dirname "$(dirname "$(realpath "$0")")")
echo "Repository path: $REPO_PATH"

# Display instructions
echo "===== Opportunity Tracker Cron Setup ====="
echo ""
echo "This script will help you set up automated grant scanning."
echo "Choose a schedule option below:"
echo ""
echo "1: Daily at 9 AM (0 9 * * *)"
echo "2: Twice weekly - Monday and Thursday at 9 AM (0 9 * * 1,4)"
echo "3: Weekly - Monday at 9 AM (0 9 * * 1)"
echo "4: Custom schedule (you'll enter the cron expression)"
echo ""
read -p "Enter your choice (1-4): " choice

# Set up cron expression based on choice
case $choice in
  1)
    CRON_EXPR="0 9 * * *"
    DESCRIPTION="daily at 9 AM"
    ;;
  2)
    CRON_EXPR="0 9 * * 1,4"
    DESCRIPTION="twice weekly on Monday and Thursday at 9 AM"
    ;;
  3)
    CRON_EXPR="0 9 * * 1"
    DESCRIPTION="weekly on Monday at 9 AM"
    ;;
  4)
    read -p "Enter your custom cron expression: " CRON_EXPR
    DESCRIPTION="using custom schedule"
    ;;
  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

# Create temporary crontab file
TEMP_CRONTAB=$(mktemp)
crontab -l > "$TEMP_CRONTAB" 2>/dev/null

# Add the new cron job
echo "# optrack - Opportunity Tracker" >> "$TEMP_CRONTAB"
echo "$CRON_EXPR $REPO_PATH/scripts/run_on_autoupdates.sh" >> "$TEMP_CRONTAB"

# Show preview
echo ""
echo "===== Preview of crontab entry ====="
echo "$CRON_EXPR $REPO_PATH/scripts/run_on_autoupdates.sh"
echo ""

# Confirm installation
read -p "Install this cron job? (y/n): " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
  crontab "$TEMP_CRONTAB"
  echo "Cron job installed! Optrack will run $DESCRIPTION"
else
  echo "Cancelled. No changes were made to your crontab."
fi

# Clean up
rm "$TEMP_CRONTAB"