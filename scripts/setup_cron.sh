#!/bin/bash
# setup_cron.sh
# Helper script to set up cron jobs for optrack
# Runs on the current branch without any branch switching

# Get the current directory (the base directory of the repo)
REPO_PATH=$(dirname "$(dirname "$(realpath "$0")")")
echo "Repository path: $REPO_PATH"

# Display instructions
echo "===== Opportunity Tracker Cron Setup ====="
echo ""
echo "This script will set up automated grant scanning that runs on your current branch."
echo "Current branch: $(cd "$REPO_PATH" && git rev-parse --abbrev-ref HEAD)"
echo ""
echo "Choose a schedule option below:"
echo ""
echo "1: Daily at 7 AM (0 7 * * *)"
echo "2: Daily at 9 AM (0 9 * * *)"
echo "3: Twice weekly - Monday and Thursday at 7 AM (0 7 * * 1,4)"
echo "4: Weekly - Monday at 7 AM (0 7 * * 1)"
echo "5: Custom schedule (you'll enter the cron expression)"
echo ""
read -p "Enter your choice (1-5): " choice

# Set up cron expression based on choice
case $choice in
  1)
    CRON_EXPR="0 7 * * *"
    DESCRIPTION="daily at 7 AM"
    ;;
  2)
    CRON_EXPR="0 9 * * *"
    DESCRIPTION="daily at 9 AM"
    ;;
  3)
    CRON_EXPR="0 7 * * 1,4"
    DESCRIPTION="twice weekly on Monday and Thursday at 7 AM"
    ;;
  4)
    CRON_EXPR="0 7 * * 1"
    DESCRIPTION="weekly on Monday at 7 AM"
    ;;
  5)
    read -p "Enter your custom cron expression: " CRON_EXPR
    DESCRIPTION="using custom schedule"
    ;;
  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

# Ask about auto-push
echo ""
read -p "Do you want to automatically push changes to GitHub? (y/n): " autopush
PUSH_FLAG=""
if [[ "$autopush" == "y" || "$autopush" == "Y" ]]; then
  PUSH_FLAG="--push"
fi

# Create temporary crontab file
TEMP_CRONTAB=$(mktemp)
crontab -l > "$TEMP_CRONTAB" 2>/dev/null || true

# Check if optrack entry already exists
if grep -q "optrack" "$TEMP_CRONTAB"; then
  echo ""
  echo "An OpTrack cron job already exists:"
  grep "optrack" "$TEMP_CRONTAB"
  echo ""
  read -p "Replace it with the new schedule? (y/n): " replace
  if [[ "$replace" != "y" && "$replace" != "Y" ]]; then
    echo "Keeping existing cron job. Exiting."
    rm "$TEMP_CRONTAB"
    exit 0
  fi
  # Remove existing optrack entries
  grep -v "optrack" "$TEMP_CRONTAB" > "${TEMP_CRONTAB}.new" || true
  mv "${TEMP_CRONTAB}.new" "$TEMP_CRONTAB"
fi

# Ensure log directory exists
mkdir -p "$REPO_PATH/output/logs"

# Add the new cron job
echo "# optrack - Opportunity Tracker" >> "$TEMP_CRONTAB"
echo "$CRON_EXPR cd $REPO_PATH && $REPO_PATH/scripts/run_optrack_update.sh $PUSH_FLAG >> $REPO_PATH/output/logs/cron.log 2>&1" >> "$TEMP_CRONTAB"

# Show preview
echo ""
echo "===== Preview of crontab entry ====="
echo "$CRON_EXPR cd $REPO_PATH && $REPO_PATH/scripts/run_optrack_update.sh $PUSH_FLAG >> $REPO_PATH/output/logs/cron.log 2>&1"
echo ""
echo "This will run OpTrack $DESCRIPTION"
if [ -n "$PUSH_FLAG" ]; then
  echo "Changes will be automatically pushed to GitHub"
else
  echo "Changes will be saved locally (not pushed to GitHub)"
fi
echo ""

# Confirm installation
read -p "Install this cron job? (y/n): " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
  crontab "$TEMP_CRONTAB"
  echo "Cron job installed! OpTrack will run $DESCRIPTION"
  echo ""
  echo "Logs will be saved to: $REPO_PATH/output/logs/cron.log"
  echo ""
  echo "To check your cron jobs: crontab -l"
  echo "To remove the cron job: crontab -e (and delete the optrack line)"
else
  echo "Cancelled. No changes were made to your crontab."
fi

# Clean up
rm "$TEMP_CRONTAB"
