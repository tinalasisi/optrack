# OpTrack Script Documentation

This document explains how the various automation scripts in the OpTrack system work together.

## Automation Components

OpTrack uses several integrated scripts to provide a complete automation solution:

### Core Components

1. **Scheduling Scripts**
   - `setup_local_scheduler.sh`: Sets up macOS launchd scheduling (runs when computer is awake)
   - `setup_cron.sh`: Sets up traditional cron scheduling (requires system to be always on)

2. **Processing Scripts**
   - `optrack_incremental.sh`: Performs efficient incremental updates (for daily/weekly runs)
   - `optrack_full.sh`: Performs complete database rebuilds (for initial setup or resets)

3. **Utility Scripts**
   - `check_cookies.sh`: Validates cookie files and prompts for refresh when needed
   - `run_on_autoupdates.sh`: Runs the incremental script directly on the auto-updates branch
   - `test_branch_system.sh`: Tests the branch management functionality

## How Everything Works Together

The automation components form a cohesive system:

```
┌─────────────────┐     ┌───────────────────┐     ┌───────────────┐
│    Scheduler    │────▶│ Processing Script │────▶│ Cookie Check  │
│ (launchd/cron)  │     │ (inc. or full)    │     │               │
└─────────────────┘     └───────────────────┘     └───────┬───────┘
                                   │                      │
                                   ▼                      ▼
                         ┌───────────────────┐    ┌───────────────┐
                         │   Git Commits     │    │ Fallback to   │
                         │   (auto-tracked)  │    │   Selenium    │
                         └─────────┬─────────┘    └───────────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │  Branch Manager   │
                         │ (auto-updates)    │
                         └───────────────────┘
```

### Workflow Explanation

1. **Scheduler Activation**:
   - The launchd job or cron job activates at the scheduled time
   - It runs the appropriate processing script (incremental or full)

2. **Processing Script Execution**:
   - The processing script runs the appropriate Python tools for each source
   - It checks cookies before making web requests
   - It collects and processes grant data
   - It generates summary files and logs

3. **Git Integration**:
   - When changes are detected, they are automatically committed
   - The commit includes all database changes and logs
   - If branch management is enabled, changes are pushed to the "auto-updates" branch

4. **Branch Management**:
   - The `run_on_autoupdates.sh` script:
     - Creates the "auto-updates" branch if it doesn't exist
     - Switches to this branch before running operations
     - Runs the incremental script directly on this branch
     - Pushes changes to remote if available
     - Returns to your original branch
     - Leaves main branch untouched until you're ready to review

### Detailed Integration

- **Scheduler ↔ Processing Scripts**: The scheduler activates the processing script at configured intervals.
- **Processing Scripts ↔ Cookie Check**: Processing scripts automatically check for valid cookies.
- **Processing Scripts ↔ Git Commits**: When changes are detected, they are committed to the local repository.
- **Git Integration**: All operations happen directly on the auto-updates branch when using the `run_on_autoupdates.sh` script, keeping your main branch clean.

## Automation Modes

OpTrack supports different automation approaches for different needs:

1. **Local-Only Mode**:
   - Changes are committed locally but not pushed
   - Good for personal use without remote repository

2. **Branch Management Mode**:
   - Changes are committed locally and pushed to auto-updates branch
   - Good for teams who want to review changes before merging
   - Requires setting up a remote repository

3. **Direct Push Mode**:
   - Changes are committed locally and pushed directly to main branch
   - Requires modifying the scripts to add a `git push` command
   - Not recommended for most use cases

## Setting Up Automation

1. Choose the right scheduler for your environment:
   - For personal computers: `setup_local_scheduler.sh` (macOS only)
   - For servers/always-on systems: `setup_cron.sh`

2. Configure branch management:
   - Ensure `run_on_autoupdates.sh` is executable
   - The scheduler is configured to run this script directly

3. Run processing scripts manually first to verify:
   - `bash scripts/optrack_incremental.sh --test`
   - `bash scripts/optrack_full.sh --test`

4. Switch to production mode for actual data collection:
   - `bash scripts/optrack_full.sh` (first run)
   - `bash scripts/optrack_incremental.sh` (subsequent runs)

## Troubleshooting

- **No Changes Detected**: Check the logs in `logs/scheduled_runs/` for details.
- **Cookie Errors**: Run `python core/login_and_save_cookies.py` to refresh cookies.
- **Git Issues**: Use `git status` to check the repository state and resolve any conflicts.
- **Branch Management**: Run `test_branch_system.sh` to verify branch management is working.