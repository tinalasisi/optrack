#!/bin/bash
# Update the website's JSON data file with the latest stats

# Ensure we're in the project root directory
cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Run stats.py to generate fresh JSON data and save it to the website directory
python core/stats.py --json > website/public/sample-data.json

echo "Updated website/public/sample-data.json with the latest statistics"

# If npm is installed, also build the website
if command -v npm &> /dev/null; then
  cd website
  echo "Building website..."
  npm run build
  echo "Website built successfully. Files are in the 'build' directory."
else
  echo "npm not found. Skipping website build step."
  echo "To build the website manually, run: cd website && npm install && npm run build"
fi