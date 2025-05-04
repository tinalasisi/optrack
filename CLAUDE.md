# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- **Setup**: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- **Login**: `python login_and_save_cookies.py` (one-time interactive login)
- **Scrape**: `python scrape_grants.py [--max-items N] [--suffix TAG] [--output-dir DIR] [--no-csv]`
- **Track**: `python grant_tracker.py [--scan-only|--fetch-details|--list|--summary]` (database-driven grant tracker)
- **Convert**: `python improved_json_to_csv.py output/file.json [--output-dir DIR]`
- **Test**: `python test_scraper.py [--items N] [--base-url URL]`
- **Cleanup**: `python purge_tests.py [--force] [--list-only]`

## Output Structure
- All output goes to the `output/` directory by default
- Test output goes to `output/test-output/` for isolation
- File naming convention: `scraped_data_YYYYMMDD_HHMMSS_SUFFIX.json/csv`
- Clean CSV files have `_clean` suffix

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
- Handle edge cases (missing cookies, timeout errors) gracefully

## Script Behaviors
- `scrape_grants.py`: Main scraper, outputs JSON and basic CSV to output directory
  - Supports incremental mode to avoid duplicate entries
  - Tracks seen competition IDs in `output/seen_competitions.json`
  - Has fast-scan mode to quickly identify new grants without details
- `improved_json_to_csv.py`: Converts JSON to clean CSV with better formatting
- `test_scraper.py`: Runs tests in isolated directory with minimal side effects
- `purge_tests.py`: Safely cleans up test output

## Development Workflow
1. Use `test_scraper.py` to validate changes without affecting main output
2. Clean up with `purge_tests.py` when done testing
3. Run `login_and_save_cookies.py` when cookies expire
4. Use `improved_json_to_csv.py` for final data preparation

## Cron Job Setup
For automated scraping, use a two-step process:
```bash
# Daily quick scan (just check for new IDs, very fast)
python scrape_grants.py --fast-scan

# Weekly full scan (get details for any new grants)
python scrape_grants.py --incremental --suffix weekly
```

The incremental mode ensures:
- Only new grants are processed
- History of seen IDs is maintained
- Duplicate entries are avoided