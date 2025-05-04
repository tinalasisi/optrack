"""
login_and_save_cookies.py
Opens a visible Chrome window for Weblogin + Duo,
then stores session cookies to cookies.pkl.
Pass --url to choose the starting site.
"""

import pickle
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import argparse

COOKIE_PATH = Path("cookies.pkl")

DEFAULT_URL = "https://umich.infoready4.com"   # first U‑M InfoReady host

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open Chrome, authenticate, then save session cookies."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Initial URL to open for login (default: %(default)s)",
    )
    args = parser.parse_args()
    target_url = args.url

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(target_url)

    input(
        "\n🛂  Finish Weblogin + Duo in the Chrome window.\n"
        "When the protected page loads, return here and press <Enter>…"
    )

    with COOKIE_PATH.open("wb") as fh:
        pickle.dump(driver.get_cookies(), fh)
    print(f"✅  Cookies saved → {COOKIE_PATH.resolve()}")

    driver.quit()

if __name__ == '__main__':
    main()