#!/bin/bash
# run_on_autoupdates.sh
# 
# This script runs the OpTrack incremental scan directly on the auto-updates branch.
# It handles all branch management in a single script for simplicity:
# 1. Switches to auto-updates branch (creating it from main or specified branch if needed)
# 2. Runs the incremental scan there
# 3. Pushes changes to remote if available
# 4. Returns to the original branch
#
# Usage: ./run_on_autoupdates.sh [--from BRANCH_NAME]
#   --from BRANCH_NAME: Create auto-updates from specified branch instead of main
#                      Use "current" to create from current branch
#
# This ensures all operations and logs remain only on the auto-updates branch.

set -e  # Exit on error

# Parse command line arguments
SOURCE_BRANCH="main"  # Default source branch is main
HELP=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --from)
      SOURCE_BRANCH="$2"
      shift 2
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
  echo "Usage: $0 [--from BRANCH_NAME]"
  echo ""
  echo "Options:"
  echo "  --from BRANCH_NAME    Create auto-updates from specified branch instead of main"
  echo "                        (useful for testing branch-specific changes)"
  echo "  --help                Show this help message"
  echo ""
  exit 0
fi

# Configuration
UPDATES_BRANCH="auto-updates"
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
REPO_ROOT=$(git rev-parse --show-toplevel)

# Change to repository root
cd "$REPO_ROOT"

echo "✅ Running OpTrack on '$UPDATES_BRANCH' branch"

# Check if auto-updates branch exists
if ! git rev-parse --verify --quiet "$UPDATES_BRANCH" >/dev/null; then
  # If SOURCE_BRANCH is "current", use the current branch
  if [ "$SOURCE_BRANCH" = "current" ]; then
    echo "🌱 Creating new '$UPDATES_BRANCH' branch from current branch ($ORIGINAL_BRANCH)"
    git branch "$UPDATES_BRANCH"
  else
    echo "🌱 Creating new '$UPDATES_BRANCH' branch from '$SOURCE_BRANCH'"
    # Make sure we have the latest source branch
    git fetch origin "$SOURCE_BRANCH"
    # Create branch based on the specified source branch
    git branch "$UPDATES_BRANCH" "origin/$SOURCE_BRANCH"
  fi
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

# Create branch-specific log directories to prevent merge conflicts
LOG_BASE_DIR="$REPO_ROOT/logs"
RUNS_DIR="$LOG_BASE_DIR/scheduled_runs/$UPDATES_BRANCH"
MERGE_DIR="$LOG_BASE_DIR/merge_logs/$UPDATES_BRANCH"
mkdir -p "$RUNS_DIR" "$MERGE_DIR"

# Timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MERGE_LOG_FILE="$MERGE_DIR/merge_${TIMESTAMP}.log"

# Make sure auto-updates is up to date with origin and main
if git remote -v | grep -q origin; then
  echo "📥 Updating auto-updates branch from remote"
  git pull origin "$UPDATES_BRANCH" 2>/dev/null || true
  
  echo "🔄 Syncing with main branch"
  # First update main branch
  git fetch origin main
  
  # Check if we need to merge (if auto-updates is behind main)
  BEHIND_COMMITS=$(git rev-list --count "$UPDATES_BRANCH..origin/main")
  
  if [ "$BEHIND_COMMITS" -gt 0 ]; then
    echo "ℹ️ Found $BEHIND_COMMITS new commit(s) in main to merge"
    
    # Create a temporary file to store merge status
    MERGE_STATUS_FILE=$(mktemp)
    
    # Start a merge log
    {
      echo "==== OpTrack Main Branch Merge ===="
      echo "Date: $(date +"%Y-%m-%d %H:%M:%S")"
      echo "From: origin/main"
      echo "To: $UPDATES_BRANCH"
      echo "Number of commits to merge: $BEHIND_COMMITS"
      echo ""
    } > "$MERGE_LOG_FILE"
    
    # Try to merge - redirect output to both console and file
    if git merge origin/main --no-edit > >(tee -a "$MERGE_LOG_FILE") 2>&1; then
      echo "✅ Successfully merged changes from main"
      
      # Get summary of merged changes and add to log
      {
        echo "Merge succeeded"
        echo ""
        echo "=== Merged Changes Summary ==="
        git log --oneline --graph --decorate=short --pretty=format:'%h %s (%ar)' HEAD~$BEHIND_COMMITS..HEAD
        echo ""
        echo "=== Files Changed ==="
        git show --name-status --oneline HEAD~$BEHIND_COMMITS..HEAD
      } >> "$MERGE_LOG_FILE"
      
      # Commit the merge success log
      git add -f "$MERGE_LOG_FILE"
      git commit -m "Record successful merge from main on $(date +"%Y-%m-%d")"
    else
      echo "⚠️ Merge conflict detected. Aborting merge."
      git merge --abort
      
      # Log the merge failure details
      echo "❌ Could not automatically merge changes from main. Manual intervention required."
      echo "Details of conflicting files:"
      cat "$MERGE_STATUS_FILE" | grep -E "CONFLICT|ERROR" || echo "No detailed conflict information available"
      
      # Add failure to log
      {
        echo ""
        echo "=== ⚠️ Merge Failure ==="
        echo "Failed to merge latest changes from main branch"
        echo "Reason: Merge conflicts detected"
        echo "Action: Manual resolution required"
        
        # Add details of conflicts
        echo ""
        echo "Conflict details:"
        cat "$MERGE_STATUS_FILE" | grep -E "CONFLICT|ERROR" || echo "No detailed conflict information available"
      } >> "$MERGE_LOG_FILE"
      
      # Commit the merge failure log
      git add -f "$MERGE_LOG_FILE"
      git commit -m "Record merge failure from main on $(date +"%Y-%m-%d")"
    fi
    
    # Clean up temp file
    rm -f "$MERGE_STATUS_FILE"
  else
    echo "✅ Auto-updates branch is already up-to-date with main"
  fi
fi

# Create a log entry at the beginning of the run - use branch-specific log directory to prevent merge conflicts
LOG_FILE="$RUNS_DIR/run_${TIMESTAMP}.log"
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")

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

# Add the log file to git (force add since it might be in .gitignore)
git add -f "$LOG_FILE"
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

# Commit the updated log (force add since it might be in .gitignore)
git add -f "$LOG_FILE"
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
if [[ -n $(git status --porcelain -- "$RUNS_DIR") ]]; then
  echo "📝 Committing any outstanding log files"
  git add -f "$RUNS_DIR"
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