# OpTrack: Opportunity Tracker

A comprehensive system for tracking funding opportunities from multiple sources, focusing on U-M InfoReady portal grants.

## Features
- **Interactive login flow** using Selenium with Duo support, then hand‑off cookies to `requests` for faster scraping.
- **Multi-source tracking** with unified database for grants from different portals.
- **Graceful fallback** to Selenium when APIs are unavailable or cookies are invalid.
- **Incremental scraping** that only fetches new grants not already in the database.
- **Configurable selectors** for any table or card‑based listing.
- **Rate‑limited polite requests** and custom User‑Agent header to avoid overwhelming servers.
- **Clean output organization** with JSON and multiple CSV formats for easy analysis.
- **Automated monitoring** with shell scripts for scheduling through cron jobs.
- **Testing infrastructure** for safe development and validation.

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
│   └── (for cookies and other data files)
├── output/
│   ├── tracked_grants.json         # Main grant database
│   ├── grant_summary.txt           # Database summary report
│   └── scan_log.txt                # Scan operations log
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

#### Automation with scan_grants.sh

For automatic scanning of multiple sources, use the provided shell script:

```bash
# Scan all configured sources
./scripts/scan_grants.sh

# Set up cron job
./scripts/setup_cron.sh
```

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

### Data Conversion

```bash
# Convert JSON to clean CSV
python utils/json_converter.py output/scraped_data_TIMESTAMP.json

# Specify output file name
python utils/json_converter.py output/scraped_data_TIMESTAMP.json -o output/custom-name.csv
```

### Testing

```bash
# Run test with default settings (2 items)
python tests/test_scraper.py

# Test with different parameters
python tests/test_scraper.py --items 5 --base-url https://alt-source.edu

# List test files without deleting
python tests/purge_tests.py --list-only

# Delete test files with confirmation
python tests/purge_tests.py

# Force delete test files without confirmation
python tests/purge_tests.py --force
```

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