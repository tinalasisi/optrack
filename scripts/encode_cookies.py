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

    print(f"Original cookies.pkl size: {len(cookie_data)} bytes")

    encoded = base64.b64encode(cookie_data).decode("utf-8")

    # Verify the encoding is correct by decoding it back
    try:
        decoded = base64.b64decode(encoded)
        import pickle
        cookies = pickle.loads(decoded)
        print(f"Verification: Successfully decoded {len(cookies)} cookies")
    except Exception as e:
        print(f"WARNING: Verification failed: {e}")
        sys.exit(1)

    print("")
    print("=" * 60)
    print("GITHUB SECRET VALUE")
    print("=" * 60)
    print("")
    print(f"Base64 string length: {len(encoded)} characters")
    print("")
    print("Copy the entire string below (it's all one line, no spaces):")
    print("")
    print(encoded)
    print("")
    print("=" * 60)
    print("")
    print("IMPORTANT: When pasting into GitHub:")
    print("- Make sure there are NO extra spaces or newlines")
    print("- The string should be exactly one line")
    print("")
    print("Next steps:")
    print("1. Go to your repo: Settings > Secrets and variables > Actions")
    print("2. Create or update secret named: INFOREADY_COOKIES")
    print("3. Paste the base64 string above as the value")
    print("")

    # Also save to a file for convenience (easier to copy from)
    # This file is gitignored so it won't be committed
    output_file = Path("data/cookies_base64.txt")
    with open(output_file, "w") as f:
        f.write(encoded)
    print(f"Also saved to: {output_file}")
    print("TIP: You can copy directly from this file to avoid formatting issues")
    print("     cat data/cookies_base64.txt | pbcopy  # macOS")
    print("     cat data/cookies_base64.txt | xclip   # Linux")


if __name__ == "__main__":
    main()
