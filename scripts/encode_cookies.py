#!/usr/bin/env python3
"""
encode_cookies.py

Encodes cookies.pkl as base64 for use as a GitHub secret.
Run this after login_and_save_cookies.py to get the string to paste into GitHub.
"""

import base64
import sys
from pathlib import Path

COOKIE_PATH = Path("data/cookies.pkl")


def main() -> None:
    if not COOKIE_PATH.exists():
        print("Error: data/cookies.pkl not found!")
        print("")
        print("First run: python core/login_and_save_cookies.py")
        print("Then run this script again.")
        sys.exit(1)

    # Read and encode
    with open(COOKIE_PATH, "rb") as f:
        cookie_data = f.read()

    encoded = base64.b64encode(cookie_data).decode("utf-8")

    print("=" * 60)
    print("GITHUB SECRET VALUE")
    print("=" * 60)
    print("")
    print("Copy the entire string below (it's all one line):")
    print("")
    print(encoded)
    print("")
    print("=" * 60)
    print("")
    print("Next steps:")
    print("1. Go to your repo: Settings > Secrets and variables > Actions")
    print("2. Create or update secret named: INFOREADY_COOKIES")
    print("3. Paste the base64 string above as the value")
    print("")

    # Also save to a file for convenience
    output_file = Path("data/cookies_base64.txt")
    with open(output_file, "w") as f:
        f.write(encoded)
    print(f"Also saved to: {output_file}")
    print("(This file is gitignored for security)")


if __name__ == "__main__":
    main()
