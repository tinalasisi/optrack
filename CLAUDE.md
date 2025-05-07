# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- **Setup**: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- **Login**: `python core/login_and_save_cookies.py` (one-time interactive login)
- **Scrape**: `python utils/scrape_grants.py [--site SITE] [--max-items N] [--incremental] [--batch-size N]`
- **Track IDs**: `python core/source_tracker.py [--list] [--source SITE] [--list-ids]` (source-specific ID tracking)
- **Convert**: `python utils/json_converter.py [--site SITE] [--output-dir DIR]` (CSV conversion)
- **Test**: `python tests/test_scraper.py [--items N] [--base-url URL]`
- **Cleanup**: `python tests/purge_tests.py [--force] [--list-only]`

## Virtual Environment
⚠️ **IMPORTANT:** Always activate the virtual environment before running any scripts:
```bash
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

All Python commands should be run within the activated virtual environment. Never use system Python directly.

## Architecture
- **Source-specific databases**: Each source (e.g., umich, umms) has its own database and ID tracker
- **Separated concerns**: Scraping, ID tracking, and CSV conversion are handled by separate scripts
- **Database structure**: 
  - `output/db/{site}_grants.json` - Site-specific grant database
  - `output/db/{site}_grants.csv` - CSV export of site-specific database
  - `output/db/{site}_seen_competitions.json` - List of seen competition IDs for each source

## Output Structure
- All output goes to the `output/db/` directory by default
- Test output goes to `output/test/` for isolation
- Site-specific file pattern: `{site}_grants.json` and `{site}_grants.csv`
- Seen IDs tracked in source-specific files: `{site}_seen_competitions.json`

## Code Style
- **Imports**: Group by stdlib, external packages, then local modules; alphabetize within groups
- **Typing**: Use type annotations for function signatures and return types
- **Naming**: Use snake_case for variables/functions, descriptive names
- **Documentation**: Include docstrings with function descriptions and parameter explanations
- **Error Handling**: Use try/except with specific exceptions; graceful fallbacks with contextlib
- **Formatting**: Break long lines > 100 chars; indent with 4 spaces
- **Constants**: Define at module level in UPPERCASE
- **Structure**: Clear section separators with comment blocks (e.g., `# ------------------------------------------------------------------`)

## Key Patterns
- Session reuse with cookies is preferred over browser automation
- Fall back to Selenium when APIs are unavailable
- Always use proper rate limiting (`time.sleep`) between requests
- Use JSON as primary storage format, with CSV for analysis
- Isolate test activities to dedicated test directory
- Source-specific tracking of seen competition IDs
- Handle edge cases (missing cookies, timeout errors) gracefully

## Script Behaviors
- `utils/scrape_grants.py`: Main scraper with site-specific database support
  - Supports incremental mode to avoid duplicate entries
  - Uses core/source_tracker.py for tracking seen competition IDs
  - Has fast-scan mode to quickly identify new grants without details
  - Supports batch processing for large sources
- `core/source_tracker.py`: Manages seen competition IDs for each source separately
  - Provides CLI for listing sources and IDs
  - Creates and maintains source-specific tracking files
- `utils/json_converter.py`: Converts JSON databases to properly formatted CSVs
  - Handles special characters and newlines correctly
  - Can convert site-specific databases directly with `--site` flag
- `tests/test_scraper.py`: Runs tests in isolated directory with minimal side effects
- `tests/purge_tests.py`: Safely cleans up test output

## Development Workflow
1. Use `test_scraper.py` to validate changes without affecting main output
2. Clean up with `purge_tests.py` when done testing
3. Run `login_and_save_cookies.py` when cookies expire
4. Use `scrape_grants.py` to update source-specific databases
5. Use `json_converter.py` for final data preparation as CSV

## Cron Job Setup
For automated scraping, use a two-step process:
```bash
# Daily quick scan (just check for new IDs, very fast)
python utils/scrape_grants.py --site umich --fast-scan
python utils/scrape_grants.py --site umms --fast-scan

# Weekly full scan (get details for any new grants)
# Use --incremental to only process new grants
python utils/scrape_grants.py --site umich --incremental
python utils/scrape_grants.py --site umms --incremental

# Convert all databases to CSV
python utils/json_converter.py --site umich
python utils/json_converter.py --site umms
```

The source-specific incremental mode ensures:
- Only new grants for each source are processed
- History of seen IDs is maintained separately for each source
- Duplicate entries are avoided within each source-specific database