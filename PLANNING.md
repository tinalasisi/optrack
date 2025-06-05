# PLANNING.md: OpTrack System Architecture & Implementation Plan

## 1. System Overview
OpTrack is an automated grant opportunity tracker that discovers, collects, and centralizes funding opportunities from specified online portals (initially InfoReady at U-M and UMMS). The system is designed to run primarily via scheduled GitHub Actions, storing data in the repository and presenting it via a public dashboard.

## 2. High-Level Architecture

- **Data Sources:** InfoReady portals (U-M, UMMS) accessed via HTTP requests with pre-generated session cookies.
- **Automation:** GitHub Actions orchestrate scraping, data processing, statistics generation, and dashboard deployment on a schedule.
- **Data Storage:** All grant data, tracking info, and statistics are stored as version-controlled files in the repository (JSONL, JSON, CSV).
- **Dashboard:** A React-based static site (in `website/`) built and deployed to GitHub Pages, displaying aggregated grant data and statistics.
- **Authentication:** Pre-generated session cookies (pickled, base64-encoded) are stored as GitHub Secrets and loaded by Actions.

## 3. Core Components & Key Files

### 3.1. Scraping & Data Collection
- **`core/login_and_save_cookies.py`**: Local script for interactive login and cookie generation (manual, not run in Actions).
- **`utils/scrape_grants.py`**: Main scraping logic using `requests` and cookies; fetches and parses grant data from portals.
- **`data/websites.json`**: Configuration for target portals (URLs, site names, etc.).
- **`data/cookies.pkl`**: Pickled session cookies (generated locally, stored as a secret in Actions).

### 3.2. Data Storage & Processing
- **`core/append_store.py`**: Handles append-only storage of grant data in JSONL and index files.
- **`core/source_tracker.py`**: Tracks seen competition IDs to enable incremental updates.
- **`utils/json_converter.py`**: Converts JSONL data to standardized CSV for export.
- **Data Files (per site, in `output/db/`):**
  - `{site}_grants_data.jsonl`: Append-only grant records.
  - `{site}_grants_index.json`: Index for fast lookup.
  - `{site}_grants.json`: Legacy full-data format.
  - `{site}_grants.csv`: CSV export.
  - `{site}_seen_competitions.json`: Seen IDs for incremental scraping.

### 3.3. Statistics & Dashboard
- **`core/stats.py`**: Aggregates statistics and outputs `docs/sample-data.json` for the dashboard.
- **`website/`**: React app for the public dashboard.
  - **`website/src/App.js`**: Main dashboard logic.
  - **`website/update-stats.sh`**: Script to update dashboard data.
  - **`docs/`**: Built static site and data for GitHub Pages.

### 3.4. Automation & Orchestration
- **`.github/workflows/scheduled-optrack.yml`**: Main GitHub Actions workflow (to be created/adapted).
- **`scripts/optrack_incremental.sh`**: Orchestrates incremental scraping (logic to be ported to Python or used as reference).
- **`scripts/run_on_autoupdates.sh`**: Handles branch management and commits in Actions.

## 4. Input/Output Structure

### 4.1. Inputs
- **Portal Configurations:** `data/websites.json`
- **Session Cookies:** `data/cookies.pkl` (loaded from GitHub Secret in Actions)
- **Existing Data:** Grant data and seen IDs from previous runs (in repo)

### 4.2. Outputs
- **Grant Data Files:** `{site}_grants_data.jsonl`, `{site}_grants_index.json`, `{site}_grants.json`, `{site}_grants.csv`, `{site}_seen_competitions.json` (in `output/db/`)
- **Statistics:** `docs/sample-data.json`
- **Dashboard:** Built static site in `docs/` (deployed via GitHub Pages)
- **Logs:** GitHub Actions logs, plus optional log files in `logs/`

## 5. Data Flow Summary
1. **Manual Step:** Maintainer runs `core/login_and_save_cookies.py` locally, updates GitHub Secret with new cookies.
2. **Scheduled Action:**
   - Checks out repo, sets up Python/Node.js environments.
   - Loads cookies from secret, writes to `data/cookies.pkl`.
   - Runs scraping scripts for each portal, updating data files incrementally.
   - Runs statistics script to generate dashboard data.
   - Builds React dashboard and copies output to `docs/`.
   - Commits and pushes all changed files.
   - GitHub Pages deploys updated dashboard.

## 6. Extensibility & Future Considerations
- **Adding New Sources:** Update `data/websites.json` and extend scraping logic as needed.
- **Cookie Expiry Handling:** Add lightweight auth checks and notification mechanisms.
- **Data Storage Scaling:** Consider external storage if repo size becomes an issue.
- **Dashboard Enhancements:** Modularize for future interactive features.

---
This plan provides a clear mapping from the PRD to concrete system components, file structure, and data flow for OpTrack's MVP and future growth.
