#!/bin/bash
# Script to manage automated Git updates on a separate branch
# Run this after optrack_incremental.sh or optrack_full.sh

# Get the project root directory
REPO_PATH=$(cd "$(dirname "$0")/.." && pwd)
cd "$REPO_PATH"

# Parameters
OUTPUT_DIR="${1:-output/db}"
UPDATE_BRANCH="auto-updates"
PUSH_UPDATES="${2:-false}"  # Whether to auto-push changes

# Create a log file for this run
LOG_DIR="$REPO_PATH/logs/scheduled_runs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/git_update_${TIMESTAMP}.log"

# Log header
{
  echo "==== OpTrack Git Update ===="
  echo "Date: $(date +"%Y-%m-%d %H:%M:%S")"
  echo "Output Directory: $OUTPUT_DIR"
} > "$LOG_FILE"

# Check if there are any changes to commit
if git status --porcelain | grep -q "$OUTPUT_DIR"; then
  # Determine which files changed
  CHANGED_FILES=$(git status --porcelain | grep "$OUTPUT_DIR" | awk '{print $2}')
  echo "Changed files:" >> "$LOG_FILE"
  echo "$CHANGED_FILES" >> "$LOG_FILE"
  
  # Count grants from the summary file
  GRANTS_COUNT=0
  if [ -f "$OUTPUT_DIR/grant_summary.txt" ]; then
    GRANTS_COUNT=$(grep -o "[0-9]* grants" "$OUTPUT_DIR/grant_summary.txt" | awk '{s+=$1} END {print s}')
  fi
  
  # Remember the current branch
  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
  echo "Current branch: $CURRENT_BRANCH" >> "$LOG_FILE"
  
  # Check if auto-updates branch exists, create if not
  if ! git show-ref --verify --quiet refs/heads/$UPDATE_BRANCH; then
    git checkout -b $UPDATE_BRANCH
    echo "Created new branch: $UPDATE_BRANCH" >> "$LOG_FILE"
    echo "Created new branch: $UPDATE_BRANCH"
  else
    # Switch to auto-updates branch
    git checkout $UPDATE_BRANCH
    echo "Switched to branch: $UPDATE_BRANCH" >> "$LOG_FILE"
    echo "Switched to branch: $UPDATE_BRANCH"
    
    # Try to merge from the original branch to keep up to date
    if [ "$CURRENT_BRANCH" != "$UPDATE_BRANCH" ]; then
      git merge $CURRENT_BRANCH --no-edit
      echo "Merged changes from $CURRENT_BRANCH" >> "$LOG_FILE"
    fi
  fi
  
  # Add all changed files from the output directory and logs
  git add "$OUTPUT_DIR"
  git add "$LOG_DIR"
  
  # Create commit message
  if [[ "$OUTPUT_DIR" == *"test"* ]]; then
    COMMIT_MSG="Test update: $GRANTS_COUNT grants on $(date +"%Y-%m-%d")"
  else
    COMMIT_MSG="Auto-update: $GRANTS_COUNT grants on $(date +"%Y-%m-%d")"
  fi
  
  # Commit changes
  git commit -m "$COMMIT_MSG"
  echo "Committed changes: $COMMIT_MSG" >> "$LOG_FILE"
  echo "✅ Committed changes: $COMMIT_MSG"
  
  # Push if requested
  if [ "$PUSH_UPDATES" = "true" ]; then
    if git remote -v | grep -q "origin"; then
      git push --set-upstream origin $UPDATE_BRANCH
      PUSH_RESULT=$?
      
      if [ $PUSH_RESULT -eq 0 ]; then
        echo "Pushed changes to origin/$UPDATE_BRANCH" >> "$LOG_FILE"
        echo "✅ Pushed changes to origin/$UPDATE_BRANCH"
      else
        echo "Failed to push changes to origin/$UPDATE_BRANCH" >> "$LOG_FILE"
        echo "❌ Failed to push changes"
      fi
    else
      echo "No remote named 'origin' found - skipping push" >> "$LOG_FILE"
      echo "ℹ️ No remote found - skipping push"
    fi
  else
    echo "Auto-push disabled - not pushing changes" >> "$LOG_FILE"
    echo "ℹ️ Auto-push disabled - changes are only committed locally"
  fi
  
  # Return to original branch
  git checkout $CURRENT_BRANCH
  echo "Returned to branch: $CURRENT_BRANCH" >> "$LOG_FILE"
  echo "Returned to branch: $CURRENT_BRANCH"
  
  # Print merge instructions
  echo "" >> "$LOG_FILE"
  echo "To get these changes in your current branch, run:" >> "$LOG_FILE"
  echo "git merge $UPDATE_BRANCH" >> "$LOG_FILE"
  
  echo ""
  echo "To get these changes in your current branch, run:"
  echo "git merge $UPDATE_BRANCH"
  
else
  echo "No changes detected in $OUTPUT_DIR" >> "$LOG_FILE"
  echo "ℹ️ No changes detected - nothing to commit"
fi

# Add summary section
{
  echo ""
  echo "=== Summary ==="
  echo "Output directory: $OUTPUT_DIR"
  echo "Update branch: $UPDATE_BRANCH"
  echo "Auto-push: $PUSH_UPDATES"
  echo "Log file: $LOG_FILE"
} >> "$LOG_FILE"

echo ""
echo "Log file: $LOG_FILE"