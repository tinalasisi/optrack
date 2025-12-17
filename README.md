# OpTrack: Opportunity Tracker

Tracks funding opportunities from U-M InfoReady portals.

[![Dashboard](https://img.shields.io/badge/Live-Dashboard-blue)](https://tinalasisi.github.io/optrack/)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/tinalasisi/optrack.git
cd optrack
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Generate Cookies (One-Time, Requires Duo 2FA)

```bash
source venv/bin/activate
python core/login_and_save_cookies.py
```

A Chrome window will open. Complete the Duo login, then press Enter in the terminal.

### 3. Run the Scraper

```bash
source venv/bin/activate

# Quick scan to find new grants
python utils/scrape_grants.py --website umich --fast-scan

# Full scrape with details
python utils/scrape_grants.py --website umich --incremental
```

### 4. Set Up Automated Runs (Cron Job)

```bash
source venv/bin/activate
./scripts/setup_cron.sh
```

Follow the prompts to choose your schedule (daily, twice weekly, etc.).

To run manually at any time:

```bash
source venv/bin/activate
./scripts/run_optrack_update.sh
```

---

## What Gets Scraped

The scraper tracks two InfoReady portals:
- **umich**: University of Michigan InfoReady (https://umich.infoready4.com)
- **umms**: UM Medical School InfoReady (https://umms.infoready4.com)

Data is saved to:
- `output/db/{site}_grants.json` - Full grant database
- `output/db/{site}_grants.csv` - CSV export for analysis
- `output/db/{site}_seen_competitions.json` - Tracking file to avoid duplicates

---

## Common Commands

Always activate the virtual environment first:

```bash
source venv/bin/activate
```

| Task | Command |
|------|---------|
| Generate cookies | `python core/login_and_save_cookies.py` |
| Quick scan | `python utils/scrape_grants.py --website umich --fast-scan` |
| Full incremental scrape | `python utils/scrape_grants.py --website umich --incremental` |
| Convert to CSV | `python utils/json_converter.py --site umich` |
| View stats | `python core/stats.py` |
| Run full update | `./scripts/run_optrack_update.sh` |
| Setup cron | `./scripts/setup_cron.sh` |

---

## Cookie Refresh

Cookies expire periodically. When scraping fails with authentication errors:

1. Re-run the login script:
   ```bash
   source venv/bin/activate
   python core/login_and_save_cookies.py
   ```

2. Complete Duo 2FA in the Chrome window

3. Press Enter when logged in

---

## Directory Structure

```
optrack/
├── core/                    # Core functionality
│   ├── login_and_save_cookies.py  # Cookie generation (Duo login)
│   ├── source_tracker.py          # ID tracking
│   └── stats.py                   # Database statistics
├── scripts/                 # Automation scripts
│   ├── run_optrack_update.sh      # Main update script
│   ├── setup_cron.sh              # Cron job setup
│   └── optrack_incremental.sh     # Incremental scraping
├── utils/                   # Utility scripts
│   ├── scrape_grants.py           # Main scraper
│   └── json_converter.py          # JSON to CSV conversion
├── data/                    # Configuration
│   ├── cookies.pkl                # Session cookies (git-ignored)
│   └── websites.json              # Portal configuration
├── output/db/               # Output data
│   ├── {site}_grants.json         # Grant databases
│   ├── {site}_grants.csv          # CSV exports
│   └── grant_summary.txt          # Summary report
├── website/                 # Dashboard (React app)
├── requirements.txt         # Python dependencies
└── venv/                    # Virtual environment (git-ignored)
```

---

## Troubleshooting

### "Cookies not found" or authentication errors
Re-run `python core/login_and_save_cookies.py`

### Scraper times out or hangs
The InfoReady site can be slow. Try:
- Running with `--visible` flag to see what's happening
- Running at off-peak times
- Checking your internet connection

### Virtual environment issues
```bash
# Recreate the virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
