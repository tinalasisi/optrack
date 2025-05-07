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

# Print with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Go to repository root
cd "$REPO_ROOT"

log "🔍 Checking for new commits to push..."

# Check if there are commits that haven't been pushed
COMMITS_TO_PUSH=$(git log --branches --not --remotes --oneline | wc -l | tr -d '[:space:]')

if [ "$COMMITS_TO_PUSH" -eq 0 ]; then
    log "✅ No new commits to push. Exiting."
    exit 0
fi

log "📦 Found $COMMITS_TO_PUSH new commit(s) to push"

# Check if updates branch exists locally
if ! git rev-parse --verify --quiet "$UPDATES_BRANCH" >/dev/null; then
    log "🌱 Creating new '$UPDATES_BRANCH' branch"
    # Create branch based on current branch
    git branch "$UPDATES_BRANCH"
else
    log "✓ '$UPDATES_BRANCH' branch already exists"
fi

# Save current branch to return to it later
log "💾 Saving current state on '$ORIGINAL_BRANCH'"

# Switch to updates branch
log "🔄 Switching to '$UPDATES_BRANCH' branch"
git checkout "$UPDATES_BRANCH"

# Update updates branch with changes from original branch
log "🔄 Updating '$UPDATES_BRANCH' with changes from '$ORIGINAL_BRANCH'"
git merge "$ORIGINAL_BRANCH" --no-edit

# Push changes to remote
log "⬆️ Pushing changes to remote '$UPDATES_BRANCH' branch"
git push -u origin "$UPDATES_BRANCH"

# Return to original branch
log "🔙 Returning to '$ORIGINAL_BRANCH' branch"
git checkout "$ORIGINAL_BRANCH"

log "✅ Successfully pushed changes to '$UPDATES_BRANCH' branch"
log "📝 Please review changes on the '$UPDATES_BRANCH' branch before merging to main"

exit 0