# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- **Setup**: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- **Login**: `python core/login_and_save_cookies.py` (one-time interactive login)
- **Scrape**: `python utils/scrape_grants.py [--site SITE] [--max-items N] [--incremental] [--batch-size N]`
- **Track IDs**: `python core/source_tracker.py [--list] [--source SITE] [--list-ids]` (source-specific ID tracking)
- **Convert**: `python utils/json_converter.py [--site SITE] [--output-dir DIR]` (CSV conversion)
- **Compact**: `python utils/scrape_grants.py --site SITE --compact` (optimize storage)
- **Stats**: `python core/stats.py [--site SITE] [--output FORMAT] [--json] [--test]` (database statistics)

### Testing Commands
- **Test Components**: `python tests/test_scraper.py [--items N] [--base-url URL]`
- **Test Shell Scripts**: `python tests/test_shell_scripts.py [--all|--incremental|--full] [--site SITE] [--verbose]`
- **List Test Files**: `python tests/test_shell_scripts.py --list-files`
- **Cleanup**: `python tests/purge_tests.py [--force] [--list-only]`

### Production Shell Scripts
- **Incremental Run**: `bash scripts/optrack_incremental.sh [--site SITE] [--max-items N]`
- **Full Run**: `bash scripts/optrack_full.sh [--site SITE] [--max-items N]`

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
- **Efficient storage**: Append-only storage with index for fast lookups
- **Database structure**:
  - `output/db/{site}_grants_data.jsonl` - Append-only data file (one grant per line)
  - `output/db/{site}_grants_index.json` - Index mapping IDs to positions in data file
  - `output/db/{site}_grants.json` - Legacy format database (for compatibility)
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
- Use append-only JSONL for efficient storage with indexing
- Maintain legacy JSON format for backward compatibility
- Generate CSV files for analysis and data sharing
- Isolate test activities to dedicated test directory
- Source-specific tracking of seen competition IDs
- Handle edge cases (missing cookies, timeout errors) gracefully
- Periodically compact databases to optimize storage

## Script Behaviors
- `utils/scrape_grants.py`: Main scraper with site-specific database support
  - Supports incremental mode to avoid duplicate entries
  - Uses core/source_tracker.py for tracking seen competition IDs
  - Has fast-scan mode to quickly identify new grants without details
  - Supports batch processing for large sources
  - Uses append-only storage with core/append_store.py
  - Provides compaction feature for storage optimization
- `core/append_store.py`: Efficient append-only storage implementation
  - Handles appending new grants without rewriting entire files
  - Maintains index for fast ID lookups
  - Reduces memory usage with on-demand loading
  - Preserves compatibility with existing JSON format
- `core/source_tracker.py`: Manages seen competition IDs for each source separately
  - Provides CLI for listing sources and IDs
  - Creates and maintains source-specific tracking files
- `core/stats.py`: Provides detailed database statistics
  - Reports grant counts, seen IDs, and pending details
  - Shows storage metrics (file sizes, formats)
  - Supports multiple output formats (text, CSV, JSON)
  - Works with both production and test environments
- `utils/json_converter.py`: Converts JSON databases to properly formatted CSVs
  - Handles special characters and newlines correctly
  - Can convert site-specific databases directly with `--site` flag
- `scripts/optrack_incremental.sh`: Runs incremental update on all or specific websites
  - First does fast scan to identify new grants
  - Then gets details for new grants only
  - Preserves existing data
- `scripts/optrack_full.sh`: Runs full update on all or specific websites
  - Completely rebuilds the database (can overwrite existing data)
  - Use with caution as it may replace existing data
- `tests/test_scraper.py`: Runs tests in isolated directory with minimal side effects
- `tests/test_shell_scripts.py`: Tests shell scripts with nice emoji-based output
- `tests/purge_tests.py`: Safely cleans up test output

## Development Workflow
1. Use `test_scraper.py` to validate changes to scraper components
2. Use `test_shell_scripts.py` to test shell script functionality with all websites
3. For changes to the ID tracking and comparison logic, use `test_id_comparison.py`
4. Clean up with `purge_tests.py` when done testing
5. Run `login_and_save_cookies.py` when cookies expire
6. Use the shell scripts for production runs:
   - `optrack_incremental.sh` for regular updates (preserves existing data)
   - `optrack_full.sh` for complete rebuilds (overwrites existing data)
7. Run database compaction periodically to optimize storage:
   - `python utils/scrape_grants.py --site SITE --compact`
8. Monitor database statistics to track progress and identify issues:
   - `python core/stats.py [--site SITE] [--output FORMAT]`
9. Use `json_converter.py` for final data preparation as CSV if needed

## Local Cron Job Setup

For automated scraping, use the local cron setup:

### Quick Setup (Interactive)

```bash
./scripts/setup_cron.sh
```

This will guide you through setting up a cron job with your preferred schedule.

### Manual Setup

```bash
# Edit crontab
crontab -e

# Add one of these lines:
# Daily at 7 AM (with auto-push to GitHub)
0 7 * * * cd /path/to/optrack && ./scripts/run_optrack_update.sh --push >> output/logs/cron.log 2>&1

# Daily at 7 AM (local only, no push)
0 7 * * * cd /path/to/optrack && ./scripts/run_optrack_update.sh >> output/logs/cron.log 2>&1
```

### Available Scripts

- `scripts/run_optrack_update.sh` - Main update script (runs on current branch)
  - `--push` - Automatically commit and push changes to GitHub
  - `--full` - Run full scan instead of incremental
- `scripts/optrack_incremental.sh` - Incremental scan (fast scan + new grant details)
- `scripts/optrack_full.sh` - Full database rebuild

### Manual Scraping

```bash
# Activate virtual environment first
source venv/bin/activate

# Quick scan (just check for new IDs)
python utils/scrape_grants.py --site umich --fast-scan
python utils/scrape_grants.py --site umms --fast-scan

# Incremental scan (get details for new grants only)
python utils/scrape_grants.py --site umich --incremental
python utils/scrape_grants.py --site umms --incremental

# Convert databases to CSV
python utils/json_converter.py --site umich
python utils/json_converter.py --site umms
```

The source-specific incremental mode ensures:
- Only new grants for each source are processed
- History of seen IDs is maintained separately for each source
- Duplicate entries are avoided within each source-specific database