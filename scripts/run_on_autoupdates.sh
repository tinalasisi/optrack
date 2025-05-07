#!/bin/bash
# run_on_autoupdates.sh
# 
# This script runs the OpTrack incremental scan directly on the auto-updates branch.
# It handles all branch management in a single script for simplicity:
# 1. Switches to auto-updates branch
# 2. Runs the incremental scan there
# 3. Pushes changes to remote if available
# 4. Returns to the original branch
#
# This ensures all operations and logs remain only on the auto-updates branch.

set -e  # Exit on error

# Configuration
UPDATES_BRANCH="auto-updates"
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
REPO_ROOT=$(git rev-parse --show-toplevel)

# Change to repository root
cd "$REPO_ROOT"

echo "✅ Running OpTrack on '$UPDATES_BRANCH' branch"

# Check if auto-updates branch exists
if ! git rev-parse --verify --quiet "$UPDATES_BRANCH" >/dev/null; then
  echo "🌱 Creating new '$UPDATES_BRANCH' branch"
  # Create branch based on current branch
  git branch "$UPDATES_BRANCH"
else
  echo "✓ '$UPDATES_BRANCH' branch already exists"
fi

# Check for uncommitted changes
STASHED=false
if [[ -n $(git status --porcelain) ]]; then
  echo "🔄 Stashing uncommitted changes"
  git stash save "Automatic stash before switching to $UPDATES_BRANCH branch"
  STASHED=true
fi

# Switch to auto-updates branch
echo "🔄 Switching to '$UPDATES_BRANCH' branch"
git checkout "$UPDATES_BRANCH"

# Make sure auto-updates is up to date with origin if remote exists
if git remote -v | grep -q origin; then
  echo "📥 Updating auto-updates branch from remote"
  git pull origin "$UPDATES_BRANCH" 2>/dev/null || true
fi

# Create a log entry at the beginning of the run
LOG_DIR="$REPO_ROOT/logs/scheduled_runs"
LOG_FILE="$LOG_DIR/run_$(date +"%Y%m%d_%H%M%S").log"
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")

mkdir -p "$LOG_DIR"

# Prepare the log content with start time
{
  echo "==== OpTrack Scheduled Run ===="
  echo "Start Time: $START_TIME"
  echo "Branch: $UPDATES_BRANCH"
  echo "Mode: Incremental"
  echo ""
  echo "=== Run in Progress ==="
  echo "Scan started at $START_TIME - please wait for completion..."
  echo ""
} > "$LOG_FILE"

# Add the log file to git
git add "$LOG_FILE"
git commit -m "Start OpTrack scan on $(date +"%Y-%m-%d")"

# Run the incremental script directly on auto-updates branch
echo "🔍 Running OpTrack incremental scan on '$UPDATES_BRANCH' branch"
# Pass OPTRACK_LOG_FILE env variable to prevent duplicate log creation
export OPTRACK_LOG_FILE="$LOG_FILE"
"$REPO_ROOT/scripts/optrack_incremental.sh"

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
    cat "$REPO_ROOT/output/db/grant_summary.txt" >> "$LOG_FILE"
  fi
  
  echo ""
  # Calculate duration in a macOS-compatible way
  START_SECONDS=$(date -jf "%Y-%m-%d %H:%M:%S" "$START_TIME" +%s)
  END_SECONDS=$(date -jf "%Y-%m-%d %H:%M:%S" "$END_TIME" +%s)
  DURATION_SECONDS=$((END_SECONDS - START_SECONDS))
  HOURS=$((DURATION_SECONDS / 3600))
  MINUTES=$(((DURATION_SECONDS % 3600) / 60))
  SECONDS=$((DURATION_SECONDS % 60))
  
  echo "Total Duration: $(printf "%02d:%02d:%02d" $HOURS $MINUTES $SECONDS) (HH:MM:SS)"
} >> "$LOG_FILE"

# Commit the updated log
git add "$LOG_FILE"
git commit -m "Complete OpTrack scan on $(date +"%Y-%m-%d")"

# Push changes if remote exists and there are unpushed commits
if git remote -v | grep -q origin; then
  # Check if there are any unpushed commits
  UNPUSHED_COMMITS=$(git log --branches --not --remotes --oneline | wc -l | tr -d '[:space:]')
  
  if [ "$UNPUSHED_COMMITS" -gt 0 ]; then
    echo "⬆️ Pushing changes to remote '$UPDATES_BRANCH' branch"
    git push -u origin "$UPDATES_BRANCH"
  else
    echo "📝 No new commits to push"
  fi
fi

# Ensure log files are committed before switching branch
if [[ -n $(git status --porcelain -- "$LOG_DIR") ]]; then
  echo "📝 Committing any outstanding log files"
  git add "$LOG_DIR"
  git commit -m "Complete logs for OpTrack scan on $(date +"%Y-%m-%d")"
fi

# Return to original branch
echo "🔙 Returning to '$ORIGINAL_BRANCH' branch"
git checkout "$ORIGINAL_BRANCH"

# Apply stashed changes if we stashed them
if [ "$STASHED" = true ]; then
  echo "🔄 Applying stashed changes"
  git stash pop || echo "⚠️ Warning: Could not apply stashed changes, they remain in the stash"
fi

echo "✅ OpTrack scan completed on '$UPDATES_BRANCH' branch"
echo "📝 Check the '$UPDATES_BRANCH' branch for updates"

exit 0