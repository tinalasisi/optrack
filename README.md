# OpTrack: Opportunity Tracker

A comprehensive system for tracking funding opportunities from multiple sources, focusing on U-M InfoReady portal grants.

## Features
- **Interactive login flow** using Selenium with Duo support, then hand‑off cookies to `requests` for faster scraping.
- **Multi-source tracking** with unified database for grants from different portals.
- **Graceful fallback** to Selenium when APIs are unavailable or cookies are invalid.
- **Incremental scraping** that only fetches new grants not already in the database.
- **Configurable selectors** for any table or card‑based listing.
- **Rate‑limited polite requests** and custom User‑Agent header to avoid overwhelming servers.
- **Clean output organization** with JSON and standardized CSV format for easy analysis.
- **Automated monitoring** with shell scripts for scheduling through cron jobs.
- **Testing infrastructure** for safe development and validation.
- **Simplified directory structure** with separate `/output/db/` and `/output/test/` folders.

## Quick start

```bash
git clone https://github.com/tlasisi/optrack.git
cd optrack
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python core/login_and_save_cookies.py                  # one‑time interactive login
python core/grant_tracker.py --fetch-details --source umich  # initialize database
```

## Directory layout

```
optrack/
├── core/
│   ├── grant_tracker.py            # Multi-source grant tracking system
│   ├── login_and_save_cookies.py   # Selenium login & cookie saver
│   └── export_grants.py            # Database export tool
├── scripts/
│   ├── scan_grants.sh              # Multi-source automation script
│   └── setup_cron.sh               # Cron job setup helper
├── utils/
│   ├── json_converter.py           # Convert JSON to clean CSV
│   └── scrape_grants.py            # Main scraper with JSON+CSV output
├── tests/
│   ├── test_scraper.py             # Run scraper in test mode
│   ├── test_incremental.py         # Test incremental functionality
│   └── purge_tests.py              # Clean up test files
├── data/
│   └── (for cookies and website configuration files)
├── output/
│   ├── db/                         # Main production database files
│   │   ├── tracked_grants.json     # Main unified database
│   │   ├── seen_competitions.json  # Tracking for incremental mode
│   │   ├── grant_summary.txt       # Database summary report
│   │   └── scan_log.txt            # Scan operations log
│   └── test/                       # Test output directory
│       └── (all test files isolated here)
├── README.md                       # Project documentation
├── requirements.txt                # Pinned dependencies
└── CHANGELOG.md                    # Version history
```

## Advanced Usage

### Grant Tracking System

The repository includes a powerful multi-source, database-driven grant tracking system:

```bash
# Quick scan to identify new grants (fast)
python core/grant_tracker.py --scan-only --source umich --base "https://umich.infoready4.com"

# Scan and download details for new grants
python core/grant_tracker.py --fetch-details --source umms --base "https://umms.infoready4.com"

# List all grants in the database
python core/grant_tracker.py --list

# Show a database summary
python core/grant_tracker.py --summary
```

#### How it works

1. Maintains a unified database of all grants from all sources in `output/tracked_grants.json`
2. Uses source-specific IDs to prevent duplicates even across sources with identical IDs
3. Only downloads details for grants not already in the database
4. Creates timestamped output files for new grants by source
5. Tracks source information for each grant for better organization

#### Multi-Source Support

The system currently tracks two InfoReady portals:
- `umich`: University of Michigan InfoReady portal (https://umich.infoready4.com)
- `umms`: UM Medical School InfoReady portal (https://umms.infoready4.com)

Additional sources can be added by updating the scan_grants.sh script and following the same pattern.

#### Directory Organization

All files are organized in a simplified structure:

- `/output/db/`: Contains all production database files, including:
  - `{source}_grants.json`: Source-specific database files (e.g., `umich_grants.json`)
  - `{source}_grants.csv`: CSV versions of each database with clean format
  - `seen_competitions.json`: History file for incremental scraping
  - `grant_summary.txt`: Summary report of the database contents
  - `scan_log.txt`: Log of scanning operations
  - Additional export files are only created when explicitly requested with `--export`

- `/output/test/`: Isolated test environment, including:
  - Separate test databases that won't affect production
  - Test outputs from test scripts
  - Automatically cleaned up with `purge_tests.py`

This structure keeps your data neatly organized:
1. **Source-Specific Databases**: Each source has its own JSON and CSV files
2. **Clean Organization**: Permanent databases are clearly separated from temporary exports
3. **Test Isolation**: All test files are kept separate from production data
4. **Standard CSV Format**: All CSV files use the same standardized format with a `details_json` column

#### Scheduled Automation

OpTrack provides two different options for automating your grant scans:

##### Option 1: Local Scheduler (Recommended for Personal Use)

```bash
# Set up local scheduler for macOS 
bash scripts/setup_local_scheduler.sh
```

The `setup_local_scheduler.sh` script creates a launchd configuration for macOS that:
- Runs at your chosen schedule (daily, twice daily, morning, or evening)
- **Only executes when your computer is awake** (ideal for laptops)
- Automatically commits changes to Git
- Maintains detailed logs of each run
- Works with your local repository path (no hardcoding)

This is the recommended approach for personal use on macOS machines that aren't always running.

##### Option 2: Traditional Cron Job (For Servers/Always-On Systems)

```bash
# Set up traditional cron job
bash scripts/setup_cron.sh
```

The `setup_cron.sh` script creates a traditional cron job that:
- Runs at a specific time regardless of system state
- Works on Linux, macOS, and most Unix-like systems
- Requires the system to be running at the scheduled time

This approach is better for server environments where the system is always on and the job needs to run at precise times.

#### Exporting Grant Data

Extract data from the database for analysis with `export_grants.py`:

```bash
# List available sources
python core/export_grants.py --list-sources

# Export grants from specific sources
python core/export_grants.py --sources umich umms

# Export all grants to a single file
python core/export_grants.py --all
```

### Direct Scraping Options

```bash
# Basic usage
python utils/scrape_grants.py

# Limit to specific number of items
python utils/scrape_grants.py --max-items 20

# Scrape from multiple sources
python utils/scrape_grants.py --base https://umich.infoready4.com --base https://umms.infoready4.com

# Add a custom tag to output files
python utils/scrape_grants.py --suffix daily

# Only generate JSON (no auto-CSV)
python utils/scrape_grants.py --no-csv

# Change output directory
python utils/scrape_grants.py --output-dir custom-output
```

### Data Management

OpTrack maintains one database file and CSV per source, which are automatically updated when you run the scraper or tracker:

```bash
# Update the umich database
python core/grant_tracker.py --fetch-details --source umich

# Update the umms database 
python core/grant_tracker.py --fetch-details --source umms

# Update multiple source databases at once
python utils/scrape_grants.py
```

You can also export additional files when needed:

```bash
# Export new grants when running the tracker
python core/grant_tracker.py --fetch-details --source umich --export

# Export when running the scraper
python utils/scrape_grants.py --export

# Export from specific sources
python core/export_grants.py --sources umich umms
```

#### CSV Format

All CSV exports use a standardized format with the following columns:

- `title`: Grant title
- `link`: URL to the grant details
- `competition_id`: Unique identifier from the source
- `site`: Source identifier (e.g., "umich", "umms")
- `description`: Full description text when available
- `details_json`: JSON-encoded string containing all other details

This clean format makes it easy to:
1. Filter and sort grants across all sources
2. Access the complete details in a structured format
3. Import into data analysis tools or databases

### Testing

All test operations use the isolated `/output/test/` directory to prevent affecting production data.

#### Testing Individual Components

```bash
# Run test with default settings (2 items)
python tests/test_scraper.py

# Test with different parameters
python tests/test_scraper.py --items 5 --base-url https://alt-source.edu

# Test incremental scraping functionality
python tests/test_incremental.py
```

#### Testing Shell Scripts

Use the test_shell_scripts.py script to test both optrack_incremental.sh and optrack_full.sh scripts:

```bash
# Test both scripts on all websites
python tests/test_shell_scripts.py --all

# Test only the incremental script
python tests/test_shell_scripts.py --incremental

# Test only the full script
python tests/test_shell_scripts.py --full

# Test with a specific site
python tests/test_shell_scripts.py --site umich

# Get more detailed output
python tests/test_shell_scripts.py --verbose

# Just list current test files without running tests
python tests/test_shell_scripts.py --list-files
```

### Running OpTrack Scripts

OpTrack provides two main scripts for database maintenance:

1. **Full Script** (`optrack_full.sh`): Rebuilds the entire database from scratch
   - Use this for initial setup or complete database refresh
   - Overwrites existing data for all grants

2. **Incremental Script** (`optrack_incremental.sh`): Only processes new grants
   - Use this for regular updates (daily/weekly runs)
   - Preserves existing data and only adds new grants
   - Much faster than full script for routine updates

#### Testing Mode vs. Production Mode

All scripts can run in two modes:

- **Production Mode**: Updates the main database in `output/db/`
- **Test Mode**: Uses isolated test environment in `output/test/` (won't affect production data)

Always use test mode first when making changes or testing new features.

#### Running in Test Mode

```bash
# Test incremental update (safe, won't affect production data)
bash scripts/optrack_incremental.sh --test --site umich

# Test full update (safe, won't affect production data)  
bash scripts/optrack_full.sh --test --site umich

# Limit items for faster testing
bash scripts/optrack_incremental.sh --test --max-items 5 --site umich

# Clean up test files when done
python tests/purge_tests.py --force
```

#### Running in Production Mode

Only run in production mode when you're confident everything works correctly:

```bash
# First-time setup (full database build)
bash scripts/optrack_full.sh

# Regular daily/weekly updates (incremental, much faster)
bash scripts/optrack_incremental.sh

# Process only a specific site
bash scripts/optrack_full.sh --site umich
```

#### When to Use --max-items

The `--max-items` parameter limits how many grants to process:

- **For testing**: Use `--max-items 1` or `--max-items 5` to quickly verify functionality
- **For production**: Generally omit this parameter to process all available grants
- **For debugging**: Use with small numbers to troubleshoot issues
- **For rate limiting**: Use on very large sources to avoid overloading servers

#### Headless vs. Visible Browser Mode

By default, all scripts run with Chrome in headless mode (no visible browser window). This is ideal for:
- Scheduled jobs
- Server environments
- Background processing

If you need to see the browser for troubleshooting, you can use the `--visible` flag:

```bash
# Run with visible browser window
python utils/scrape_grants.py --visible
```

#### Cookie Management

Cookies are used to avoid interactive login for each run. To manage cookies:

```bash
# Check if cookies are valid and prompt to refresh if needed
bash scripts/check_cookies.sh

# Force refresh cookies (requires interactive login)
python core/login_and_save_cookies.py
```

Cookies typically expire after 7-14 days. If cookies expire during a scheduled run:
1. The script will automatically fall back to Selenium
2. It will log warnings about cookie expiration
3. Next time you run the script interactively, it will prompt to refresh cookies

#### Automated Git Integration

The scripts automatically manage Git operations when run in production mode (without the `--test` flag):

##### Automated Commits

- **Incremental Script**: Commits with message "Auto-update: Found X new grants on YYYY-MM-DD"
- **Full Script**: Commits with message "Full database rebuild: X grants on YYYY-MM-DD"

This provides a clear history of when new grants were found. No commits are made when:
- The script is run in test mode
- No changes are detected in the database

##### Branch Management

The system can automatically push changes to a separate "auto-updates" branch for review:

```bash
# Test the branch management system
bash scripts/test_branch_system.sh

# Push existing commits to the auto-updates branch
bash scripts/push_to_updates_branch.sh
```

This workflow:
1. Automatically commits changes to the local Git repository
2. Pushes those changes to a separate "auto-updates" branch
3. Keeps the main branch untouched until you're ready to merge

You can then review the changes on the "auto-updates" branch before merging them into your main branch. This is especially useful for automated systems that might make changes while you're away.

#### Logging

All script runs are logged in the `logs/scheduled_runs` directory:

- Each run creates a timestamped log file: `run_YYYYMMDD_HHMMSS.log`
- Logs contain information about the run mode, sites processed, and any changes made
- Logs are automatically included in Git commits when changes are detected

These logs provide a complete history of all scheduled runs and make it easy to track when and how the database was updated.

#### Managing Test Files

```bash
# List test files without deleting
python tests/purge_tests.py --list-only

# Delete test files with confirmation
python tests/purge_tests.py

# Force delete test files without confirmation
python tests/purge_tests.py --force
```

This isolated test environment ensures that test runs won't affect your production database or tracking history.

## Customizing for another site
1. Edit CSS selectors in `utils/scrape_grants.py` to match the new portal.
2. Update `DEFAULT_BASE` and pagination logic if needed.
3. Run the two scripts; cookies are re‑used automatically.

## Error Handling
- Handles missing or corrupt cookie files gracefully
- Falls back to Selenium when JSON API is unavailable
- Provides detailed error messages for troubleshooting

## License
MIT