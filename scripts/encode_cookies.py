"""
encode_cookies.py
Reads cookies.pkl and outputs a base64-encoded string for GitHub Secrets.
"""

import base64
import pickle
from pathlib import Path

COOKIE_PATH = Path("data/cookies.pkl")

def main() -> None:
    if not COOKIE_PATH.exists():
        print(f"❌ Cookie file not found: {COOKIE_PATH.resolve()}")
        print("Run 'python core/login_and_save_cookies.py' first to generate cookies.")
        return

    # Read the pickle file
    with COOKIE_PATH.open("rb") as fh:
        cookie_data = fh.read()
    
    # Encode to base64
    encoded = base64.b64encode(cookie_data).decode('utf-8')
    
    print("=" * 80)
    print("📋 Base64-encoded cookies for GitHub Secret:")
    print("=" * 80)
    print(encoded)
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Copy the string above")
    print("2. Go to: Repository Settings > Secrets and variables > Actions")
    print("3. Create or update secret: INFOREADY_COOKIES")
    print("4. Paste the base64 string")
    print()

if __name__ == '__main__':
    main()
