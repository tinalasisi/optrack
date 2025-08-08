#!/bin/bash
# run_optrack_update.sh
# 
# This script runs the OpTrack incremental scan on the current branch.
# It's designed to be simple and run everything in place without branch switching.
#
# Usage: ./run_optrack_update.sh [--full]
#   --full: Run a full scan instead of incremental
#
# This script:
# 1. Runs the incremental (or full) scan
# 2. Updates website data files
# 3. Commits and pushes changes (optional)

set -e  # Exit on error

# Parse command line arguments
SCAN_MODE="incremental"
PUSH_CHANGES=false
HELP=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --full)
      SCAN_MODE="full"
      shift
      ;;
    --push)
      PUSH_CHANGES=true
      shift
      ;;
    --help)
      HELP=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      HELP=true
      shift
      ;;
  esac
done

if [ "$HELP" = true ]; then
  echo "Usage: $0 [--full] [--push]"
  echo ""
  echo "Options:"
  echo "  --full    Run a full scan instead of incremental"
  echo "  --push    Automatically commit and push changes"
  echo "  --help    Show this help message"
  echo ""
  exit 0
fi

# Configuration
REPO_ROOT=$(git rev-parse --show-toplevel)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Change to repository root
cd "$REPO_ROOT"

echo "✅ Running OpTrack on current branch: '$CURRENT_BRANCH'"

# Create log directories
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="$REPO_ROOT/output"
LOG_BASE_DIR="$OUTPUT_DIR/logs"
RUNS_DIR="$LOG_BASE_DIR/runs/$TIMESTAMP"
mkdir -p "$RUNS_DIR"

# Create a log entry at the beginning of the run
LOG_FILE="$RUNS_DIR/run_summary.log"
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")

# Prepare the log content with start time
{
  echo "==== OpTrack Scheduled Run ===="
  echo "Start Time: $START_TIME"
  echo "Branch: $CURRENT_BRANCH"
  echo "Mode: $(echo $SCAN_MODE | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
  echo ""
  echo "=== Run in Progress ==="
  echo "Scan started at $START_TIME - please wait for completion..."
  echo ""
} > "$LOG_FILE"

# Run the appropriate script
echo "🔍 Running OpTrack $SCAN_MODE scan"
export OPTRACK_LOG_FILE="$LOG_FILE"
export OPTRACK_RUN_TIMESTAMP="$TIMESTAMP"

if [ "$SCAN_MODE" = "full" ]; then
  "$REPO_ROOT/scripts/optrack_full.sh"
else
  "$REPO_ROOT/scripts/optrack_incremental.sh"
fi

# Update the log with end time
END_TIME=$(date +"%Y-%m-%d %H:%M:%S")
{
  echo ""
  echo "=== Run Completed ==="
  echo "End Time: $END_TIME"
  
  # Get database statistics for the log
  if [ -f "$REPO_ROOT/output/db/grant_summary.txt" ]; then
    echo ""
    echo "=== Database Summary ==="
    cat "$REPO_ROOT/output/db/grant_summary.txt"
  fi
  
  echo ""
  # Calculate duration in a macOS-compatible way
  START_SECONDS=$(date -jf "%Y-%m-%d %H:%M:%S" "$START_TIME" +%s 2>/dev/null || date -d "$START_TIME" +%s)
  END_SECONDS=$(date -jf "%Y-%m-%d %H:%M:%S" "$END_TIME" +%s 2>/dev/null || date -d "$END_TIME" +%s)
  DURATION_SECONDS=$((END_SECONDS - START_SECONDS))
  HOURS=$((DURATION_SECONDS / 3600))
  MINUTES=$(((DURATION_SECONDS % 3600) / 60))
  SECONDS=$((DURATION_SECONDS % 60))
  
  echo "Total Duration: $(printf "%02d:%02d:%02d" $HOURS $MINUTES $SECONDS) (HH:MM:SS)"
} >> "$LOG_FILE"

# Update website data files with current stats
echo "📊 Updating website data files"
python core/stats.py --json > website/public/grants-data.json
python core/stats.py --json > docs/grants-data.json

# Keep sample-data.json for backward compatibility 
cp website/public/grants-data.json website/public/sample-data.json
cp docs/grants-data.json docs/sample-data.json

# If push flag is set, commit and push changes
if [ "$PUSH_CHANGES" = true ]; then
  echo "📝 Committing changes"
  
  # Add all relevant files
  git add -A output/db/
  git add website/public/grants-data.json docs/grants-data.json
  git add website/public/sample-data.json docs/sample-data.json
  git add "$LOG_FILE"
  
  # Create commit message
  COMMIT_MSG="Update grant database - $(date +"%Y-%m-%d %H:%M")"
  
  # Check if there's anything to commit
  if git diff --cached --quiet; then
    echo "📝 No changes to commit"
  else
    git commit -m "$COMMIT_MSG"
    
    # Push to remote
    echo "⬆️ Pushing changes to remote"
    git push origin "$CURRENT_BRANCH"
  fi
else
  echo "ℹ️  Changes not committed. Use --push flag to automatically commit and push."
fi

echo "✅ OpTrack scan completed!"
echo "📝 Log saved to: $LOG_FILE"

# Show summary of changes
if [ -f "$REPO_ROOT/output/db/grant_summary.txt" ]; then
  echo ""
  echo "📊 Summary:"
  tail -n 5 "$REPO_ROOT/output/db/grant_summary.txt"
fi

exit 0
