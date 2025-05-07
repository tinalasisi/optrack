#!/bin/bash
# push_to_updates_branch.sh
# 
# This script handles pushing commits to a separate "auto-updates" branch
# for review before merging to main branch.
#
# It checks if there are uncommitted changes or new commits that need to be pushed,
# creates the branch if it doesn't exist, and pushes changes while keeping the
# original branch intact.

set -e  # Exit on error

# Configuration
UPDATES_BRANCH="auto-updates"
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
REPO_ROOT=$(git rev-parse --show-toplevel)
LOG_DIR="$REPO_ROOT/logs/scheduled_runs"
LOG_FILE="$LOG_DIR/run_$(date +"%Y%m%d_%H%M%S").log"

# Print with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Go to repository root
cd "$REPO_ROOT"

log "🔍 Checking for new commits to push..."

# First check if there are any local logs that need to be moved
LOGS_EXIST=false
if [ -f "$LOG_FILE" ]; then
    LOGS_EXIST=true
fi

# Check if there are commits that haven't been pushed
COMMITS_TO_PUSH=$(git log --branches --not --remotes --oneline | wc -l | tr -d '[:space:]')

# Check if there are differences between current branch and auto-updates branch
# This ensures we also capture changes even if they've been pushed to origin
if git rev-parse --verify --quiet "$UPDATES_BRANCH" >/dev/null; then
    DIFF_WITH_UPDATES=$(git rev-list --count "$ORIGINAL_BRANCH..$UPDATES_BRANCH" "$UPDATES_BRANCH..$ORIGINAL_BRANCH" 2>/dev/null || echo "0")
else
    # If updates branch doesn't exist yet, we need to create it
    DIFF_WITH_UPDATES=1
fi

if [ "$COMMITS_TO_PUSH" -eq 0 ] && [ "$DIFF_WITH_UPDATES" -eq 0 ] && [ "$LOGS_EXIST" = false ]; then
    log "✅ No new commits to push and no logs to move. Exiting."
    exit 0
fi

log "📦 Processing updates: $COMMITS_TO_PUSH unpushed commits, $DIFF_WITH_UPDATES differences with updates branch"

# Check if updates branch exists locally
if ! git rev-parse --verify --quiet "$UPDATES_BRANCH" >/dev/null; then
    log "🌱 Creating new '$UPDATES_BRANCH' branch"
    # Create branch based on current branch
    git branch "$UPDATES_BRANCH"
else
    log "✓ '$UPDATES_BRANCH' branch already exists"
fi

# Save a copy of any existing log file to move to the updates branch
if [ -f "$LOG_FILE" ]; then
    TEMP_LOG_FILE="/tmp/optrack_run_log_temp.txt"
    cp "$LOG_FILE" "$TEMP_LOG_FILE"
    
    # Remove the log file from the original branch since we'll move it to updates branch
    rm "$LOG_FILE"
    # Remove from git tracking if it was added
    git reset HEAD "$LOG_FILE" 2>/dev/null || true
fi

# Save current branch to return to it later
log "💾 Saving current state on '$ORIGINAL_BRANCH'"

# Switch to updates branch
log "🔄 Switching to '$UPDATES_BRANCH' branch"
git checkout "$UPDATES_BRANCH"

# Update updates branch with changes from original branch
log "🔄 Updating '$UPDATES_BRANCH' with changes from '$ORIGINAL_BRANCH'"
git merge "$ORIGINAL_BRANCH" --no-edit

# Move the log file to the updates branch if we saved it
if [ -f "$TEMP_LOG_FILE" ]; then
    # Make sure the log directory exists
    mkdir -p "$LOG_DIR"
    
    # Copy the log file
    cp "$TEMP_LOG_FILE" "$LOG_FILE"
    
    # Add to git
    git add "$LOG_FILE"
    
    # Amend the last commit to include the log
    git commit --amend --no-edit
    
    # Clean up
    rm "$TEMP_LOG_FILE"
fi

# Push changes to remote
log "⬆️ Pushing changes to remote '$UPDATES_BRANCH' branch"
git push -u origin "$UPDATES_BRANCH"

# Return to original branch
log "🔙 Returning to '$ORIGINAL_BRANCH' branch"
git checkout "$ORIGINAL_BRANCH"

log "✅ Successfully pushed changes to '$UPDATES_BRANCH' branch"
log "📝 Please review changes on the '$UPDATES_BRANCH' branch before merging to main"

exit 0