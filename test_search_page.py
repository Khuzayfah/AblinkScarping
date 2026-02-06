"""Test to see structure of search results page"""
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    stealth_sync(page)

    # Load homepage
    page.goto("https://www.sgcarmart.com")
    time.sleep(3)

    # Search Toyota Hiace
    page.goto("https://www.sgcarmart.com/search?q=Toyota+Hiace")
    time.sleep(5)

    # Check one listing URL
    page.goto("https://www.sgcarmart.com/used_cars/info.php?ID=1436938")
    time.sleep(5)

    # Extract dealer and depreciation
    details = page.evaluate("""
        () => {
            const bodyText = document.body.textContent;

            // Look for depreciation patterns
            const depreciationMatch = bodyText.match(/\\$\\s*([\\d,]+)\\s*\\/\\s*yr/i);
            const depreciation = depreciationMatch ? '$' + depreciationMatch[1] + '/yr' : 'NOT FOUND';

            // Look for dealer name
            let dealer = 'NOT FOUND';

            // Method 1: Look for "Dealer:" label
            const dealerMatch = bodyText.match(/Dealer[:\\s]+([^\\n\\r]+?)(?:\\n|\\r|$)/i);
            if (dealerMatch) {
                dealer = dealerMatch[1].trim().substring(0, 100);
            }

            // Method 2: Look for dealer link
            const dealerLink = document.querySelector('a[href*="DL="], a[href*="dlrprofile"]');
            if (dealerLink && dealer === 'NOT FOUND') {
                dealer = (dealerLink.textContent || '').trim().substring(0, 100);
            }

            // Get page HTML structure (first listing card)
            const firstCard = document.querySelector('.car-listing, .listing-card, article, .result-item');
            const sampleHTML = firstCard ? firstCard.outerHTML.substring(0, 500) : 'NO CARD FOUND';

            return {
                depreciation,
                dealer,
                sampleHTML,
                pageTitle: document.title
            };
        }
    """)

    print(f"Page: {details['pageTitle']}")
    print(f"Depreciation: {details['depreciation']}")
    print(f"Dealer: {details['dealer']}")
    print(f"\nSample HTML:\n{details['sampleHTML']}")

    input("\nBrowser stays open. Check the page structure and press Enter...")
    browser.close()
