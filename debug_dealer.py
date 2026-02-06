"""
Debug script to analyze SGCarMart page structure and find dealer information
Run with: python debug_dealer.py
"""
from playwright.sync_api import sync_playwright
import time

def debug_sgcarmart_structure():
    """Analyze the page structure to find where dealer info is located"""

    with sync_playwright() as p:
        # Launch browser in headed mode to see what's happening
        browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="en-SG"
        )
        page = context.new_page()

        # Navigate to commercial vehicles listing
        url = "https://www.sgcarmart.com/used_cars/listing.php?veh=1"
        print(f"\n{'='*80}")
        print(f"Loading: {url}")
        print(f"{'='*80}\n")

        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        # Scroll to load content
        print("Scrolling to load all listings...")
        for i in range(3):
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})")
            time.sleep(2)

        # Analyze page structure
        analysis = page.evaluate("""
            () => {
                const results = {
                    listingCount: 0,
                    dealerLinksCount: 0,
                    sampleListings: []
                };

                // Find all vehicle listings
                const listings = document.querySelectorAll('article, div[class*="listing"], tr');
                results.listingCount = listings.length;

                // Count dealer links
                const dealerLinks = document.querySelectorAll('a[href*="DL="]');
                results.dealerLinksCount = dealerLinks.length;

                // Get sample of first 3 listings with detailed structure
                let count = 0;
                for (const listing of listings) {
                    if (count >= 3) break;

                    // Check if this listing has a vehicle link
                    const carLink = listing.querySelector('a[href*="info.php?ID="], a[href*="used-cars/info"]');
                    if (!carLink) continue;

                    const carName = (carLink.textContent || '').trim();
                    if (!carName || carName.length < 3) continue;

                    // Find dealer info in various ways
                    const sample = {
                        carName: carName,
                        carHref: carLink.getAttribute('href'),
                        dealerInfo: [],
                        fullText: listing.textContent.substring(0, 300),
                        html: listing.outerHTML.substring(0, 600)
                    };

                    // Method 1: Look for dealer links
                    const dealerLinks = listing.querySelectorAll('a[href*="DL="]');
                    dealerLinks.forEach(link => {
                        sample.dealerInfo.push({
                            method: 'DL link',
                            text: (link.textContent || '').trim(),
                            href: link.getAttribute('href')
                        });
                    });

                    // Method 2: Look for text containing "dealer"
                    const allText = listing.textContent || '';
                    const dealerMatches = allText.match(/dealer[:\\s]+([^\\n\\|]+)/gi);
                    if (dealerMatches) {
                        dealerMatches.forEach(match => {
                            sample.dealerInfo.push({
                                method: 'text match',
                                text: match
                            });
                        });
                    }

                    // Method 3: Look for all links in listing
                    const allLinks = listing.querySelectorAll('a');
                    sample.allLinksCount = allLinks.length;
                    sample.allLinks = [];
                    allLinks.forEach((link, idx) => {
                        if (idx < 5) {  // Only first 5 links
                            sample.allLinks.push({
                                text: (link.textContent || '').trim().substring(0, 50),
                                href: (link.getAttribute('href') || '').substring(0, 100)
                            });
                        }
                    });

                    results.sampleListings.push(sample);
                    count++;
                }

                return results;
            }
        """)

        # Print analysis
        print(f"\n{'='*80}")
        print("PAGE ANALYSIS RESULTS")
        print(f"{'='*80}")
        print(f"Total listings found: {analysis['listingCount']}")
        print(f"Total dealer links (DL=): {analysis['dealerLinksCount']}")
        print(f"\n{'='*80}")
        print("SAMPLE LISTINGS (First 3):")
        print(f"{'='*80}\n")

        for idx, sample in enumerate(analysis['sampleListings'], 1):
            print(f"\n--- LISTING {idx} ---")
            print(f"Car: {sample['carName']}")
            print(f"Car Link: {sample['carHref']}")
            print(f"\nDealer Info Found ({len(sample['dealerInfo'])} methods):")
            if sample['dealerInfo']:
                for info in sample['dealerInfo']:
                    print(f"  • Method: {info['method']}")
                    print(f"    Text: {info['text']}")
                    if 'href' in info:
                        print(f"    Href: {info['href']}")
            else:
                print("  [!] NO DEALER INFO FOUND!")

            print(f"\nAll Links in Listing ({sample['allLinksCount']} total, showing first 5):")
            for link in sample['allLinks']:
                print(f"  • Text: {link['text']}")
                print(f"    Href: {link['href']}")

            print(f"\nFull Text Preview:")
            print(f"  {sample['fullText']}")

            print(f"\nHTML Preview:")
            print(f"  {sample['html'][:400]}...")
            print("\n" + "="*80)

        print("\n\nBrowser will stay open for 30 seconds for manual inspection...")
        print("Check the page structure and look for dealer information manually.")
        time.sleep(30)

        browser.close()
        print("\nDebug complete!")

if __name__ == "__main__":
    debug_sgcarmart_structure()
