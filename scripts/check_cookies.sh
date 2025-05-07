#!/bin/bash
# Script to check if cookies are valid and prompt for renewal if needed

# Get the project root directory
REPO_PATH=$(cd "$(dirname "$0")/.." && pwd)
COOKIE_FILE="$REPO_PATH/data/cookies.pkl"

# Check if cookie file exists
if [ ! -f "$COOKIE_FILE" ]; then
  echo "⚠️  Cookie file not found. You need to log in first."
  read -p "Do you want to run the login script now? (y/n): " choice
  if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
    cd "$REPO_PATH"
    python core/login_and_save_cookies.py
  else
    echo "Login skipped. Cookies are required for non-interactive operation."
    exit 1
  fi
  exit 0
fi

# Check cookie age
COOKIE_AGE=$(( ($(date +%s) - $(stat -c %Y "$COOKIE_FILE")) / 86400 ))
COOKIE_AGE_HOURS=$(( ($(date +%s) - $(stat -c %Y "$COOKIE_FILE")) / 3600 ))

if [ $COOKIE_AGE -ge 7 ]; then
  echo "⚠️  Cookie file is $COOKIE_AGE days old and may be expired."
  read -p "Do you want to refresh cookies now? (y/n): " choice
  if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
    cd "$REPO_PATH"
    python core/login_and_save_cookies.py
  else
    echo "Cookie refresh skipped. The script will try to use existing cookies."
  fi
else
  echo "✅ Cookie file is $COOKIE_AGE days and $COOKIE_AGE_HOURS hours old (should be valid)."
fi

# Run a test query to verify cookies
echo "Testing cookie validity..."
cd "$REPO_PATH"
python -c "
import pickle
import requests
from pathlib import Path

try:
    with open('$COOKIE_FILE', 'rb') as f:
        cookies = pickle.load(f)
    
    # Create a session with cookies
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
    
    # Test the session (try the homepage of the most important site)
    config_file = Path('data/websites.json')
    if config_file.exists():
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        if config.get('websites'):
            test_url = config['websites'][0].get('url', 'https://umich.infoready4.com')
        else:
            test_url = 'https://umich.infoready4.com'
    else:
        test_url = 'https://umich.infoready4.com'
    
    # Make a test request
    r = session.get(test_url, timeout=10)
    r.raise_for_status()
    
    # Check for redirect to login page or authentication errors
    if 'login' in r.url.lower() or 'auth' in r.url.lower() or r.status_code in (401, 403):
        print('⚠️  Warning: Cookies appear to be expired. You should refresh them.')
        choice = input('Do you want to refresh cookies now? (y/n): ')
        if choice.lower() in ('y', 'yes'):
            import subprocess
            subprocess.run(['python', 'core/login_and_save_cookies.py'])
        else:
            print('Cookie refresh skipped. The script will attempt to use Selenium fallback.')
    else:
        print('✅ Cookies are valid!')
        
except Exception as e:
    print(f'⚠️  Error checking cookies: {e}')
    print('It\\'s recommended to refresh cookies to ensure proper operation.')
    choice = input('Do you want to refresh cookies now? (y/n): ')
    if choice.lower() in ('y', 'yes'):
        import subprocess
        subprocess.run(['python', 'core/login_and_save_cookies.py'])
    else:
        print('Cookie refresh skipped. The script will attempt to use Selenium fallback.')
"