"""
Test detail page extraction to improve dealer/depreciation logic
"""
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
    
    # Load homepage first
    page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded")
    time.sleep(3)
    
    for url in test_urls[:1]:  # Test first URL
        print(f"\n{'='*80}")
        print(f"Testing: {url}")
        print('='*80)
        
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(3)
        
        # Extract with detailed debugging
        result = page.evaluate(r"""
            () => {
                const bodyText = document.body.textContent;
                
                // Find all dealer links
                const dealerLinks = document.querySelectorAll('a[href*="DL="], a[href*="dlrprofile"], a[href*="dealer"]');
                let dealerCandidates = [];
                for (const link of dealerLinks) {
                    dealerCandidates.push({
                        text: (link.textContent || '').trim(),
                        href: link.getAttribute('href')
                    });
                }
                
                // Find depreciation patterns
                const depreciationMatches = [];
                const regex = /\$\s*(\d[\d,]*)\s*\/\s*yr/gi;
                let match;
                while ((match = regex.exec(bodyText)) !== null) {
                    depreciationMatches.push(match[0]);
                }
                
                // Look for "Dealer:" label
                const dealerLabelMatch = bodyText.match(/Dealer[:\s]+([A-Za-z0-9\s&\(\)\.,\-']+?)(?:\s{2,}|\n|\r|Tel|Email|Contact|\d{4,}|Address|$)/i);
                
                // Get page title
                const title = document.title;
                
                return {
                    title,
                    dealerCandidates,
                    depreciationMatches,
                    dealerLabelMatch: dealerLabelMatch ? dealerLabelMatch[1].trim() : null,
                    bodyTextSample: bodyText.substring(0, 500)
                };
            }
        """)
        
        print(f"\nPage Title: {result['title']}")
        print(f"\n--- Dealer Candidates ({len(result['dealerCandidates'])}) ---")
        for i, candidate in enumerate(result['dealerCandidates'][:10]):
            print(f"{i+1}. Text: {candidate['text'][:60]}")
            print(f"   Href: {candidate['href']}")
        
        print(f"\n--- Depreciation Matches ({len(result['depreciationMatches'])}) ---")
        for match in result['depreciationMatches']:
            print(f"  - {match}")
        
        print(f"\n--- Dealer Label Match ---")
        print(f"  {result['dealerLabelMatch']}")
        
        print(f"\n--- Body Text Sample ---")
        print(result['bodyTextSample'])
        
        input("\nPress Enter to continue...")
    
    browser.close()
