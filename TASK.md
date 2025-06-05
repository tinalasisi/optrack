# TASK.md: OpTrack Implementation Task Breakdown

This document organizes remaining work for OpTrack into actionable categories, grouped by subsystem and mapped to the current codebase and planning document.

---

## 1. Scraping & Data Collection

### Reuse
- `core/login_and_save_cookies.py`  
  *Local, manual cookie generation. No changes needed for MVP.*
- `data/websites.json`  
  *Portal configuration. Update only as new sources are added.*

### Modify
- `utils/scrape_grants.py`  
  *Ensure robust error handling, incremental scraping, and compatibility with GitHub Actions (e.g., path handling, logging).*
- `data/cookies.pkl`  
  *Document manual update process; ensure Actions can load from secret.*

### Remove
- None (all current files are relevant for MVP).

### Build New
- None (core scraping logic exists; see Automation for orchestration).

---

## 2. Data Storage & Processing

### Reuse
- `core/append_store.py`  
  *Append-only storage for grant data.*
- `core/source_tracker.py`  
  *Tracks seen competition IDs.*
- `utils/json_converter.py`  
  *Converts JSONL to CSV.*

### Modify
- Data file paths in scripts (e.g., ensure all outputs go to `output/db/` and are relative for Actions).
- Logging: Standardize and improve error/warning output for all processing scripts.

### Remove
- Legacy or duplicate data files in `output/db/` or `test/` that are not referenced by the MVP pipeline.

### Build New
- None (all required processing scripts exist; may need minor enhancements).

---

## 3. Statistics & Dashboard

### Reuse
- `core/stats.py`  
  *Statistics aggregation for dashboard.*
- `website/` (React app)  
  *Dashboard UI and build scripts.*

### Modify
- `website/update-stats.sh`  
  *Ensure it works with new data locations and is called by Actions as needed.*
- `docs/sample-data.json`  
  *Automate generation and ensure it is always up-to-date.*

### Remove
- Any unused or outdated dashboard assets in `docs/` or `website/build/` (clean up as part of deployment process).

### Build New
- None (dashboard and stats scripts exist; focus on integration).

---

## 4. Automation & Orchestration

### Reuse
- `scripts/optrack_incremental.sh` (as reference)  
  *Use as a guide for orchestration logic, but port to Python or integrate into Actions.*
- `scripts/run_on_autoupdates.sh` (as reference)  
  *Use for git commit/push logic in Actions.*

### Modify
- **Build new main workflow:** `.github/workflows/scheduled-optrack.yml`  
  *Create or adapt a GitHub Actions workflow to orchestrate scraping, processing, stats, dashboard build, and commit/push. Integrate secret handling for cookies.*
- `scripts/auto_git_updates.sh`, `scripts/check_cookies.sh`, `scripts/optrack_full.sh`, `scripts/setup_cron.sh`, `scripts/setup_local_scheduler.sh`  
  *Deprecate or update documentation to clarify these are for local/manual use only, not part of the MVP pipeline.*

### Remove
- Any shell scripts not referenced by the new GitHub Actions workflow and not needed for local/manual runs.

### Build New
- `.github/workflows/scheduled-optrack.yml`  
  *Main orchestrator for the MVP pipeline.*
- Python orchestration script (optional): If shell orchestration is too complex, create a new Python script to handle the full scraping and data update pipeline for Actions.
- Notification/alert logic for cookie expiry (optional, for future enhancement).

---

## 5. Testing & Validation

### Reuse
- `tests/` directory and all test scripts  
  *Maintain and expand as needed.*

### Modify
- Add/expand tests for incremental scraping, error handling, and data export.
- Add a "dry run" or limited mode for scraping scripts for workflow testing.

### Remove
- Outdated or redundant test data in `test/`.

### Build New
- Add GitHub Actions job for running tests on PRs and main branch.

---

## 6. Documentation

### Reuse
- `README.md`, `PLANNING.md`, `PRD.md`, `ROADMAP.md`

### Modify
- Update documentation to reflect new workflow, manual cookie process, and MVP architecture.
- Add clear instructions for maintainers on cookie refresh and secret update.

### Remove
- Outdated instructions or references to deprecated scripts.

### Build New
- Add a CONTRIBUTING.md for onboarding new contributors.

---

## Summary Table
| Subsystem         | Reuse                        | Modify                                 | Remove                        | Build New                                 |
|-------------------|------------------------------|----------------------------------------|-------------------------------|-------------------------------------------|
| Scraping          | login_and_save_cookies.py    | scrape_grants.py, cookies.pkl docs     | None                          | None                                      |
| Data Processing   | append_store.py, source_tracker.py, json_converter.py | Data paths, logging         | Legacy data files              | None                                      |
| Statistics/Dashboard | stats.py, website/         | update-stats.sh, sample-data.json      | Old dashboard assets          | None                                      |
| Automation        | optrack_incremental.sh (ref), run_on_autoupdates.sh (ref) | Build new workflow, deprecate old scripts | Unused shell scripts         | scheduled-optrack.yml, orchestration script|
| Testing           | tests/                       | Expand tests, add dry run              | Old test data                 | Actions test job                          |
| Documentation     | README.md, PLANNING.md, etc. | Update for new flow                    | Old instructions              | CONTRIBUTING.md                           |

---
This breakdown should guide the next steps for OpTrack MVP completion and future maintainability.
