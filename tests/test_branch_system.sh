#!/bin/bash
# test_branch_system.sh
#
# This script tests the branch management system by creating a test file,
# committing it, and pushing to the auto-updates branch.

set -e  # Exit on error

# Configuration
REPO_ROOT=$(git rev-parse --show-toplevel)
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Go to repository root
cd "$REPO_ROOT"

# Create test directory if it doesn't exist
mkdir -p output/test

# Create a test file with timestamp
echo "This is a test file created at $(date)" > output/test/branch_test.txt

# Create a test change in one of the test scripts
echo "# Test timestamp: $(date)" >> tests/test_scripts.py

# Add the changes to git
git add tests/test_scripts.py

# Commit the change
git commit -m "Test commit for branch system testing"

echo "✅ Created test commit"

# Push to auto-updates branch
if [ -x "$REPO_ROOT/scripts/push_to_updates_branch.sh" ]; then
  echo "🔄 Testing branch system by pushing test commit..."
  "$REPO_ROOT/scripts/push_to_updates_branch.sh"
  echo "✅ Test complete! Verify changes on the auto-updates branch"
else
  echo "❌ Error: push_to_updates_branch.sh script not found or not executable"
  exit 1
fi

exit 0