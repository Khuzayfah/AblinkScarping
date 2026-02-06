"""Final test of updated extraction"""
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time

test_urls = [
    "https://www.sgcarmart.com/used_cars/info.php?ID=1436938",
    "https://www.sgcarmart.com/used_cars/info.php?ID=1471258",
    "https://www.sgcarmart.com/used_cars/info.php?ID=1472956",
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
        print(f"URL: {url}")
        
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)
        
        details = page.evaluate(r"""
            () => {
                const bodyText = document.body.textContent;
                const bodyHTML = document.body.innerHTML;
                const pageTitle = document.title || '';

                // Extract depreciation - find the actual listing depreciation
                let depreciation = '';

                // Method 1: Look in JSON data (most reliable)
                const jsonMatch = bodyHTML.match(/"depreciation":\s*"[^\$]*\$\$?([\d,]+)\s*\/\s*yr"/i);
                if (jsonMatch) {
                    depreciation = '$' + jsonMatch[1] + '/yr';
                }

                // Method 2: Look near "Depreciation" label in text
                if (!depreciation) {
                    const depreciationContext = bodyText.match(/Depreciation[^\$]*\$\s*([\d,]+)\s*\/\s*yr/i);
                    if (depreciationContext) {
                        depreciation = '$' + depreciationContext[1] + '/yr';
                    }
                }

                // Extract dealer name from page title
                let dealer = '';
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
        
        print(f"Dealer: {details['dealer']}")
        print(f"Depreciation: {details['depreciation']}")
    
    input("\nPress Enter to close...")
    browser.close()
