# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Setup
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Common Commands
```bash
# Always activate venv first
source venv/bin/activate

# Login (one-time, requires Duo)
python core/login_and_save_cookies.py

# Scrape grants
python utils/scrape_grants.py --website umich --incremental
python utils/scrape_grants.py --website umms --incremental

# Run full update
./scripts/run_optrack_update.sh

# Setup cron job
./scripts/setup_cron.sh
```

## Key Files
- `core/login_and_save_cookies.py` - Cookie generation with Duo 2FA
- `utils/scrape_grants.py` - Main scraper
- `scripts/run_optrack_update.sh` - Runs incremental update
- `scripts/setup_cron.sh` - Sets up automated cron job
- `data/cookies.pkl` - Session cookies (git-ignored)
- `output/db/` - Grant databases (JSON and CSV)

## Architecture
- Two sources: `umich` and `umms` (InfoReady portals)
- Each source has its own database: `{site}_grants.json`
- Incremental scraping tracks seen IDs to avoid duplicates
- Falls back to Selenium when API unavailable

## Code Style
- Type annotations for function signatures
- snake_case for variables/functions
- Docstrings for functions
- 4-space indentation
