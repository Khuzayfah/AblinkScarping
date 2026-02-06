"""
Safe test script for SGCarMart scraper
Run this to test the scraper functionality safely
"""
from js_scraper import SGCarMartJSScraper
from datetime import datetime
import sys

def main():
    print("="*70)
    print("SGCarMart Scraper - Safe Test")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Ask user for headless mode
    headless = True
    if "--headed" in sys.argv or "-h" in sys.argv:
        headless = False
        print("Running in HEADED mode (browser visible)")
    else:
        print("Running in HEADLESS mode (browser hidden)")
        print("Tip: Use --headed flag to see browser: python test_safe_scraper.py --headed")

    print()
    print("Target vehicles to scrape:")
    print("-" * 70)
    target_vehicles = [
        "10FT DIESEL", "14FT DIESEL",
        "HINO DUTRO 2.8", "HINO XZU710",
        "TOYOTA DYNA 2.8", "TOYOTA DYNA 3.0",
        "TOYOTA HIACE 3.0M", "TOYOTA HIACE 3.0A", "TOYOTA HIACE 2.8A", "TOYOTA HIACE 2.0",
        "NISSAN CABSTAR", "NISSAN NV350 2.5M", "NISSAN NV350 2.0",
        "NISSAN NV200 1.5M", "NISSAN NV200 1.6A",
        "ISUZU NHR / NJR", "ISUZU NPR85", "ISUZU NMR85", "ISUZU NNR85",
        "MITSUBISHI FEA01", "MITSUBISHI FEA21",
        "KIA 2500", "HONDA N-VAN",
        "VAN DIESEL", "VAN PETROL"
    ]

    for i, vehicle in enumerate(target_vehicles, 1):
        print(f"{i:2d}. {vehicle}")

    print()
    print("="*70)
    print("Starting scrape...")
    print("="*70)
    print()

    try:
        scraper = SGCarMartJSScraper(headless=headless)
        results = scraper.scrape_vehicle_listings()

        print()
        print("="*70)
        print("SCRAPING COMPLETED")
        print("="*70)
        print(f"Total vehicles found: {len(results)}")
        print()

        if len(results) > 0:
            print("Sample of scraped data:")
            print("-" * 70)
            for i, item in enumerate(results[:5], 1):
                print(f"\n{i}. {item.get('make_model', 'N/A')}")
                print(f"   Price: ${item.get('price', 0):,.0f}")
                print(f"   Year: {item.get('registered_year', 'N/A')}")
                print(f"   Depreciation: {item.get('depreciation', 'N/A')}")
                print(f"   Dealer: {item.get('dealer_name', 'N/A')}")
                print(f"   URL: {item.get('listing_url', 'N/A')[:60]}...")

            if len(results) > 5:
                print(f"\n... and {len(results) - 5} more vehicles")

            print()
            print("="*70)
            print("Data has been saved to database")
            print("You can now view it in the web interface at http://localhost:8000")
            print("="*70)
        else:
            print("WARNING: No vehicles found!")
            print()
            print("Troubleshooting tips:")
            print("1. Run with --headed to see browser: python test_safe_scraper.py --headed")
            print("2. Check if https://www.sgcarmart.com is accessible")
            print("3. Try running from Singapore VPN/proxy")
            print("4. Website may have changed structure - contact developer")

        print()
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
