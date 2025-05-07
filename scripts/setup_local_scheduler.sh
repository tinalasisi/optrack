#!/bin/bash
# Helper script to set up a local scheduler for OpTrack
# This script creates a launchd plist for macOS users

# Get the absolute path to the repository
REPO_PATH=$(cd "$(dirname "$0")/.." && pwd)
echo "Repository path: $REPO_PATH"

# Detect operating system
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "This setup script is currently for macOS only."
    echo "For other systems, please use cron or your system's scheduler."
    exit 1
fi

# Display options
echo "===== OpTrack Local Scheduler Setup ====="
echo ""
echo "This script will set up a local scheduler that runs when your computer is awake."
echo "Choose how often you want OpTrack to check for updates:"
echo ""
echo "1: Daily at 9 AM (or when computer wakes up after 9 AM)"
echo "2: Twice daily - 9 AM and 5 PM (or on wake)"
echo "3: Morning check only - 7 AM (or on wake)"
echo "4: Evening check only - 7 PM (or on wake)"
echo ""
read -p "Enter your choice (1-4): " choice

# Create launchd plist directory if it doesn't exist
mkdir -p ~/Library/LaunchAgents

# Define the plist file path
PLIST_FILE=~/Library/LaunchAgents/com.user.optrack.plist

# Generate appropriate launchd configuration
case $choice in
  1)
    # Daily at 9 AM
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.optrack</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${REPO_PATH}/scripts/optrack_incremental.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>${REPO_PATH}/output/db/launchd_error.log</string>
    <key>StandardOutPath</key>
    <string>${REPO_PATH}/output/db/launchd_output.log</string>
    <key>WorkingDirectory</key>
    <string>${REPO_PATH}</string>
</dict>
</plist>
EOF
    DESCRIPTION="daily at 9 AM"
    ;;
    
  2)
    # Twice daily - 9 AM and 5 PM
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.optrack</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${REPO_PATH}/scripts/optrack_incremental.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>9</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>17</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>${REPO_PATH}/output/db/launchd_error.log</string>
    <key>StandardOutPath</key>
    <string>${REPO_PATH}/output/db/launchd_output.log</string>
    <key>WorkingDirectory</key>
    <string>${REPO_PATH}</string>
</dict>
</plist>
EOF
    DESCRIPTION="twice daily at 9 AM and 5 PM"
    ;;
    
  3)
    # Morning check - 7 AM
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.optrack</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${REPO_PATH}/scripts/optrack_incremental.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>${REPO_PATH}/output/db/launchd_error.log</string>
    <key>StandardOutPath</key>
    <string>${REPO_PATH}/output/db/launchd_output.log</string>
    <key>WorkingDirectory</key>
    <string>${REPO_PATH}</string>
</dict>
</plist>
EOF
    DESCRIPTION="every morning at 7 AM"
    ;;
    
  4)
    # Evening check - 7 PM
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.optrack</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${REPO_PATH}/scripts/optrack_incremental.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>19</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>${REPO_PATH}/output/db/launchd_error.log</string>
    <key>StandardOutPath</key>
    <string>${REPO_PATH}/output/db/launchd_output.log</string>
    <key>WorkingDirectory</key>
    <string>${REPO_PATH}</string>
</dict>
</plist>
EOF
    DESCRIPTION="every evening at 7 PM"
    ;;
    
  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

# Show preview
echo ""
echo "===== Scheduler Configuration ====="
echo "Created launchd configuration to run OpTrack $DESCRIPTION"
echo "Configuration file: $PLIST_FILE"
echo ""

# Ask to load the job
read -p "Load this job now? (y/n): " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
  # Unload any existing job first
  launchctl unload "$PLIST_FILE" 2>/dev/null
  
  # Load the new job
  launchctl load "$PLIST_FILE"
  echo "✅ Scheduler job loaded successfully!"
  echo "OpTrack will run $DESCRIPTION (or when your Mac wakes up after the scheduled time)"
  echo ""
  echo "To manually unload this job later, run:"
  echo "launchctl unload $PLIST_FILE"
else
  echo "Job created but not loaded. To load it manually, run:"
  echo "launchctl load $PLIST_FILE"
fi

# Make the file executable
chmod +x "$PLIST_FILE"

# Note about logs
echo ""
echo "Logs will be written to:"
echo "${REPO_PATH}/output/db/launchd_output.log"
echo "${REPO_PATH}/output/db/launchd_error.log"