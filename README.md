# scrape-websites

A collection of Python scripts that authenticate through U‑M Weblogin, reuse session cookies, and scrape data from protected portals (e.g., InfoReady grant listings) into tidy CSV/Excel files.

## Features
- **Interactive login flow** using Selenium with Duo support, then hand‑off cookies to `requests` for faster scraping.
- **Configurable selectors** for any table or card‑based listing.
- **Rate‑limited polite requests** and custom User‑Agent header to avoid overwhelming servers.
- Outputs to **CSV or Excel** via pandas for easy downstream analysis.

## Quick start

```bash
git clone https://github.com/tlasisi/scrape-websites.git
cd scrape-websites
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python login_and_save_cookies.py     # one‑time interactive login
python scrape_grants.py              # pulls all pages into um_grants.csv
```

## Directory layout

```
scrape-websites/
├── login_and_save_cookies.py   # Selenium login & cookie saver
├── scrape_grants.py            # requests + BeautifulSoup crawler
├── requirements.txt            # pinned dependencies
└── README.md
```

## Customizing for another site
1. Edit CSS selectors in `scrape_grants.py` to match the new portal.
2. Update `BASE` and pagination logic.
3. Run the two scripts; cookies are re‑used automatically.

Example run command with multiple bases:

```bash
python scrape_grants.py \
  --base https://umich.infoready4.com \
  --base https://umms.infoready4.com
```

## License
MIT