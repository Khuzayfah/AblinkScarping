"""Quick test of the updated extraction logic"""
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time
import re

def extract_year(reg_date):
    if not reg_date:
        return None
    m = re.search(r'\d{1,2}-\w{3}-(\d{2,4})', reg_date)
    if m:
        y = int(m.group(1))
        return y if y > 100 else (2000 + y if y < 50 else 1900 + y)
    return None

# Test URLs from database
test_urls = [
    "https://www.sgcarmart.com/used_cars/info.php?ID=1436938",
    "https://www.sgcarmart.com/used_cars/info.php?ID=1471258",
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="en-SG")
    page = context.new_page()
    stealth_sync(page)
    
    page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded")
    time.sleep(3)
    
    for url in test_urls:
        print(f"\n{'='*70}")
        print(f"Testing: {url}")
        
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)
        
        details = page.evaluate(r"""
            () => {
                const bodyText = document.body.textContent;
                const pageTitle = document.title || '';

                // Extract depreciation - take FIRST match only
                const depreciationMatch = bodyText.match(/\$\s*([\d,]+)\s*\/\s*yr/i);
                const depreciation = depreciationMatch ? '$' + depreciationMatch[1] + '/yr' : '';

                // Extract dealer name from page title
                let dealer = '';

                // Method 1: Extract from title
                const titleMatch = pageTitle.match(/\|\s*([^-|]+?)\s*-\s*Sgcarmart/i);
                if (titleMatch) {
                    dealer = titleMatch[1].trim();
                }

                // Clean dealer name
                if (dealer) {
                    dealer = dealer.replace(/\s+/g, ' ').trim();
                    dealer = dealer.replace(/\s*Pte\.?\s*Ltd\.?.*$/i, ' Pte Ltd').trim();
                    dealer = dealer.replace(/[,;.\s]+$/, '').trim();
                    if (dealer.length > 80) {
                        dealer = dealer.substring(0, 80).trim();
                    }
                }

                return {depreciation, dealer, pageTitle};
            }
        """)
        
        print(f"Page Title: {details['pageTitle']}")
        print(f"Dealer Extracted: {details['dealer']}")
        print(f"Depreciation: {details['depreciation']}")
    
    input("\nPress Enter to close...")
    browser.close()
