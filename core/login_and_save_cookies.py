"""
login_and_save_cookies.py
Opens a visible Chrome window for Weblogin + Duo,
then stores session cookies to cookies.pkl.
Pass --url to choose the starting site.
"""

import argparse
import pickle
import time
from pathlib import Path

from selenium import webdriver

COOKIE_PATH = Path("data/cookies.pkl")

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

    driver = webdriver.Chrome()  # Selenium Manager auto‑downloads the driver
    driver.get(target_url)

    # Use a more robust approach that won't fail in non-interactive environments
    print("\n🛂  Finish Weblogin + Duo in the Chrome window.")
    print("When the protected page loads, return here and press <Enter>…")
    
    try:
        input()  # Wait for user to press Enter
    except (EOFError, KeyboardInterrupt):
        print("\nInput interrupted. Continuing anyway after 10 seconds...")
        time.sleep(10)

    with COOKIE_PATH.open("wb") as fh:
        pickle.dump(driver.get_cookies(), fh)
    print(f"✅  Cookies saved → {COOKIE_PATH.resolve()}")

    driver.quit()

if __name__ == '__main__':
    main()
