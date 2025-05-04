# scrape-websites

A collection of Python scripts that authenticate through U‑M Weblogin, reuse session cookies, and scrape data from protected portals (e.g., InfoReady grant listings) into tidy JSON and CSV files.

## Features
- **Interactive login flow** using Selenium with Duo support, then hand‑off cookies to `requests` for faster scraping.
- **Graceful fallback** to Selenium when APIs are unavailable or cookies are invalid.
- **Configurable selectors** for any table or card‑based listing.
- **Rate‑limited polite requests** and custom User‑Agent header to avoid overwhelming servers.
- **Clean output organization** with JSON and multiple CSV formats for easy analysis.
- **Testing infrastructure** for safe development and validation.

## Quick start

```bash
git clone https://github.com/tlasisi/scrape-websites.git
cd scrape-websites
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python login_and_save_cookies.py                 # one‑time interactive login
python scrape_grants.py --max-items 10 --suffix test   # scrape 10 items with test tag
python improved_json_to_csv.py output/scraped_data_*.json  # convert to clean CSV
```

## Directory layout

```
scrape-websites/
├── login_and_save_cookies.py   # Selenium login & cookie saver
├── scrape_grants.py            # Main scraper with JSON+CSV output
├── improved_json_to_csv.py     # Convert JSON to clean CSV
├── test_scraper.py             # Run scraper in test mode
├── purge_tests.py              # Clean up test files
├── output/                     # Directory for all output files
│   ├── test-output/            # Isolated test output directory
├── requirements.txt            # Pinned dependencies
├── CLAUDE.md                   # Guide for Claude Code
└── README.md                   # Project documentation
```

## Advanced Usage

### Scraping Options

```bash
# Basic usage
python scrape_grants.py

# Limit to specific number of items
python scrape_grants.py --max-items 20

# Scrape from multiple sources
python scrape_grants.py --base https://umich.infoready4.com --base https://umms.infoready4.com

# Add a custom tag to output files
python scrape_grants.py --suffix daily

# Only generate JSON (no auto-CSV)
python scrape_grants.py --no-csv

# Change output directory
python scrape_grants.py --output-dir custom-output
```

### Data Conversion

```bash
# Convert JSON to clean CSV
python improved_json_to_csv.py output/scraped_data_TIMESTAMP.json

# Specify output file name
python improved_json_to_csv.py output/scraped_data_TIMESTAMP.json -o output/custom-name.csv
```

### Testing

```bash
# Run test with default settings (2 items)
python test_scraper.py

# Test with different parameters
python test_scraper.py --items 5 --base-url https://alt-source.edu

# List test files without deleting
python purge_tests.py --list-only

# Delete test files with confirmation
python purge_tests.py

# Force delete test files without confirmation
python purge_tests.py --force
```

## Customizing for another site
1. Edit CSS selectors in `scrape_grants.py` to match the new portal.
2. Update `DEFAULT_BASE` and pagination logic if needed.
3. Run the two scripts; cookies are re‑used automatically.

## Error Handling
- Handles missing or corrupt cookie files gracefully
- Falls back to Selenium when JSON API is unavailable
- Provides detailed error messages for troubleshooting

## License
MIT