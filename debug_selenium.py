#!/usr/bin/env python
"""
Debug script to check Selenium access to the InfoReady site.
"""
import pickle
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

COOKIE_PATH = Path("cookies.pkl")

def main():
    print("Starting Selenium debug session...")
    
    # Load cookies
    if not COOKIE_PATH.exists():
        print(f"Error: Cookie file {COOKIE_PATH} does not exist")
        return
    
    cookies = pickle.load(COOKIE_PATH.open("rb"))
    print(f"Loaded {len(cookies)} cookies")
    
    # Initialize Chrome
    print("Initializing Chrome...")
    driver = webdriver.Chrome()
    
    try:
        # First load the domain to set cookies
        print("Loading domain...")
        driver.get("https://umich.infoready4.com")
        time.sleep(3)
        
        # Add cookies
        print("Adding cookies...")
        for cookie in cookies:
            # Clean cookie to prevent issues
            if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                cookie['expiry'] = int(cookie['expiry'])
            driver.add_cookie(cookie)
        
        # Navigate to the home page
        print("Navigating to home page with cookies...")
        driver.get("https://umich.infoready4.com/#homePage")
        time.sleep(5)
        
        # Check for listings
        print("Looking for competition listings...")
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            print("Page loaded")
            
            anchors = driver.find_elements(By.CSS_SELECTOR, "a[competitionid]")
            print(f"Found {len(anchors)} competition listings")
            
            if anchors:
                for i, anchor in enumerate(anchors[:3]):
                    title = anchor.text.strip()
                    comp_id = anchor.get_attribute("competitionid")
                    print(f"  {i+1}. {title} (ID: {comp_id})")
            else:
                print("No competition links found. HTML snippet around where listings should be:")
                content = driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
                print(content[:500] + "...")  # Print first 500 chars
                
        except Exception as e:
            print(f"Error: {e}")
    
    finally:
        print("Cleaning up...")
        driver.quit()
        print("Debug session complete")

if __name__ == "__main__":
    main()