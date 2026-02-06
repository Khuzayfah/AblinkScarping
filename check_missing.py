from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time

urls = [
    "https://www.sgcarmart.com/used_cars/info.php?ID=1467452",  # Isuzu NMR85U
    "https://www.sgcarmart.com/used_cars/info.php?ID=1425930",  # Honda N-Van
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="en-SG")
    page = context.new_page()
    stealth_sync(page)
    
    page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded")
    time.sleep(3)
    
    for url in urls:
        print(f"\n{'='*70}")
        print(f"URL: {url}")
        
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)
        
        title = page.title()
        print(f"Page Title: {title}")
        
        # Extract dealer
        match = page.evaluate("""
            () => {
                const pageTitle = document.title || '';
                const match = pageTitle.match(/\|\s*([^-|]+?)\s*-\s*Sgcarmart/i);
                return match ? match[1] : 'NOT FOUND';
            }
        """)
        
        print(f"Dealer Extracted: {match}")
    
    input("\nPress Enter...")
    browser.close()
