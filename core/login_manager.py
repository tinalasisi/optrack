"""
login_manager.py
Enhanced login manager that handles multiple sites with separate cookie storage.
Each site gets its own cookie file to prevent overwriting.
"""

import argparse
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional

from selenium import webdriver


class LoginManager:
    """Manages authentication cookies for multiple InfoReady sites."""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.cookies_dir = data_dir / "cookies"
        self.cookies_dir.mkdir(exist_ok=True)
        self.websites_config = data_dir / "websites.json"
        
    def get_cookie_path(self, site_name: str) -> Path:
        """Get the cookie file path for a specific site."""
        return self.cookies_dir / f"{site_name}_cookies.pkl"
    
    def load_websites(self) -> Dict:
        """Load website configuration."""
        with open(self.websites_config, 'r') as f:
            return json.load(f)
    
    def login_to_site(self, site_name: Optional[str] = None, url: Optional[str] = None) -> None:
        """
        Open browser for login and save cookies for a specific site.
        
        Args:
            site_name: Name of the site from websites.json
            url: Direct URL to use (overrides site_name)
        """
        if url:
            # Direct URL provided
            # Extract site name from URL for cookie storage
            if "umich.infoready4.com" in url:
                site_name = "umich"
            elif "umms.infoready4.com" in url:
                site_name = "umms"
            else:
                # Use domain as site name
                from urllib.parse import urlparse
                site_name = urlparse(url).netloc.replace('.', '_')
            target_url = url
        elif site_name:
            # Load URL from config
            config = self.load_websites()
            site_info = next((s for s in config["websites"] if s["name"] == site_name), None)
            if not site_info:
                raise ValueError(f"Site '{site_name}' not found in websites.json")
            target_url = site_info["url"]
        else:
            raise ValueError("Either site_name or url must be provided")
        
        print(f"\n🌐 Opening browser for: {site_name} ({target_url})")
        
        driver = webdriver.Chrome()
        driver.get(target_url)
        
        print("\n🛂 Complete login with Weblogin + Duo in the Chrome window.")
        print("When the protected page loads, return here and press <Enter>...")
        
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            print("\nInput interrupted. Continuing anyway after 10 seconds...")
            import time
            time.sleep(10)
        
        # Save cookies for this specific site
        cookie_path = self.get_cookie_path(site_name)
        cookies = driver.get_cookies()
        
        with cookie_path.open("wb") as fh:
            pickle.dump(cookies, fh)
        
        print(f"✅ Cookies saved for {site_name} → {cookie_path.resolve()}")
        driver.quit()
    
    def login_all_sites(self) -> None:
        """Login to all enabled sites in sequence."""
        config = self.load_websites()
        enabled_sites = [s for s in config["websites"] if s.get("enabled", True)]
        
        print(f"\n📋 Found {len(enabled_sites)} enabled sites to login:")
        for site in enabled_sites:
            print(f"  - {site['name']}: {site['description']}")
        
        for i, site in enumerate(enabled_sites, 1):
            print(f"\n[{i}/{len(enabled_sites)}] Logging into {site['name']}...")
            self.login_to_site(site_name=site['name'])
            
            if i < len(enabled_sites):
                print("\nPress <Enter> to continue to the next site...")
                input()
        
        print("\n✅ All sites logged in successfully!")
        self.check_status()
    
    def check_status(self) -> None:
        """Check which sites have saved cookies."""
        config = self.load_websites()
        print("\n📊 Cookie Status:")
        print("-" * 50)
        
        for site in config["websites"]:
            cookie_path = self.get_cookie_path(site['name'])
            if cookie_path.exists():
                size = cookie_path.stat().st_size
                if size > 10:  # More than just an empty pickle
                    status = f"✅ Logged in ({size} bytes)"
                else:
                    status = "⚠️  Empty cookie file"
            else:
                status = "❌ Not logged in"
            
            enabled = "Enabled" if site.get("enabled", True) else "Disabled"
            print(f"{site['name']:10} | {enabled:8} | {status}")
        print("-" * 50)
    
    def load_cookies_for_site(self, site_name: str) -> List[Dict]:
        """Load cookies for a specific site."""
        cookie_path = self.get_cookie_path(site_name)
        
        if not cookie_path.exists():
            return []
        
        try:
            with cookie_path.open("rb") as fh:
                return pickle.load(fh)
        except Exception:
            return []
    
    def clear_cookies(self, site_name: Optional[str] = None) -> None:
        """Clear cookies for a specific site or all sites."""
        if site_name:
            cookie_path = self.get_cookie_path(site_name)
            if cookie_path.exists():
                cookie_path.unlink()
                print(f"✅ Cleared cookies for {site_name}")
            else:
                print(f"ℹ️  No cookies found for {site_name}")
        else:
            # Clear all cookies
            for cookie_file in self.cookies_dir.glob("*_cookies.pkl"):
                cookie_file.unlink()
            print("✅ Cleared all cookies")


def main():
    parser = argparse.ArgumentParser(
        description="Manage authentication cookies for multiple InfoReady sites."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Login command
    login_parser = subparsers.add_parser("login", help="Login to a site")
    login_parser.add_argument("--site", help="Site name from websites.json")
    login_parser.add_argument("--url", help="Direct URL to login to")
    login_parser.add_argument("--all", action="store_true", help="Login to all enabled sites")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check login status for all sites")
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear saved cookies")
    clear_parser.add_argument("--site", help="Clear cookies for specific site (or all if not specified)")
    
    args = parser.parse_args()
    
    manager = LoginManager()
    
    if args.command == "login":
        if args.all:
            manager.login_all_sites()
        elif args.site or args.url:
            manager.login_to_site(site_name=args.site, url=args.url)
        else:
            print("Error: Specify --site, --url, or --all")
            login_parser.print_help()
    elif args.command == "status":
        manager.check_status()
    elif args.command == "clear":
        manager.clear_cookies(site_name=args.site)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
