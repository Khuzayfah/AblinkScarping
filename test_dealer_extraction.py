"""
Simple test script to verify dealer extraction works
Run with: python test_dealer_extraction.py
"""
from js_scraper import SGCarMartJSScraper

if __name__ == "__main__":
    print("\n" + "="*80)
    print("Testing Dealer Extraction - Running Scraper in HEADED mode")
    print("="*80 + "\n")
    print("Watch the browser to see the dealer extraction process...")
    print("Look for:")
    print("  [OK] = Dealer name found")
    print("  [!]  = Dealer name NOT found\n")

    # Run scraper in headed mode (visible browser) so we can see what's happening
    scraper = SGCarMartJSScraper(headless=False)
    results = scraper.scrape_vehicle_listings()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total vehicles scraped: {len(results)}")

    dealers_found = sum(1 for r in results if r.get('dealer_name') and r['dealer_name'] != '–')
    dealers_missing = len(results) - dealers_found

    print(f"Dealers found: {dealers_found}")
    print(f"Dealers missing: {dealers_missing}")
    print(f"Success rate: {(dealers_found/len(results)*100):.1f}%" if results else "N/A")

    if dealers_found > 0:
        print("\nSample vehicles WITH dealer:")
        for r in results[:5]:
            if r.get('dealer_name') and r['dealer_name'] != '–':
                print(f"  • {r['make_model']} - {r['dealer_name']}")

    if dealers_missing > 0:
        print("\nSample vehicles WITHOUT dealer:")
        count = 0
        for r in results:
            if not r.get('dealer_name') or r['dealer_name'] == '–':
                print(f"  • {r['make_model']} - URL: {r.get('listing_url', 'N/A')[:80]}")
                count += 1
                if count >= 5:
                    break

    print("\n" + "="*80)
