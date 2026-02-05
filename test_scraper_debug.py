"""Debug script to test scraper in production"""
import sys
import traceback
from datetime import datetime

print("="*60)
print("SCRAPER DEBUG TEST")
print("="*60)

# Test 1: Import
print("\n[1/7] Testing imports...")
try:
    from js_scraper import SGCarMartJSScraper
    print("  ✓ Import OK")
except Exception as e:
    print(f"  ✗ Import FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 2: Playwright
print("\n[2/7] Testing Playwright...")
try:
    from playwright.sync_api import sync_playwright
    print("  ✓ Playwright import OK")
except Exception as e:
    print(f"  ✗ Playwright FAILED: {e}")
    sys.exit(1)

# Test 3: Chromium
print("\n[3/7] Testing Chromium launch...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu']
        )
        print("  ✓ Chromium launch OK")
        browser.close()
except Exception as e:
    print(f"  ✗ Chromium FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 4: Network
print("\n[4/7] Testing network connectivity...")
try:
    import requests
    response = requests.get("https://www.sgcarmart.com", timeout=10)
    print(f"  ✓ Network OK: HTTP {response.status_code}")
except Exception as e:
    print(f"  ✗ Network FAILED: {e}")

# Test 5: Database
print("\n[5/7] Testing database...")
try:
    from database import SessionLocal, VehicleListing
    db = SessionLocal()
    count = db.query(VehicleListing).count()
    print(f"  ✓ Database OK: {count} listings")
    db.close()
except Exception as e:
    print(f"  ✗ Database FAILED: {e}")
    traceback.print_exc()

# Test 6: Config
print("\n[6/7] Testing config...")
try:
    import config
    print(f"  ✓ Target vehicles: {len(config.TARGET_VEHICLES)}")
    print(f"  ✓ URL: {config.COMMERCIAL_LISTING_URL[:50]}...")
except Exception as e:
    print(f"  ✗ Config FAILED: {e}")

# Test 7: Actual Scrape (1 keyword only)
print("\n[7/7] Testing actual scrape (Toyota Hiace only)...")
try:
    scraper = SGCarMartJSScraper(headless=True)

    # Override to test only 1 keyword
    print("  Starting mini scrape...")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        context = browser.new_context()
        page = context.new_page()

        print("  Accessing SGCarMart...")
        page.goto("https://www.sgcarmart.com", timeout=30000)
        title = page.title()
        print(f"  ✓ Page title: {title[:50]}")

        print("  Searching for Toyota Hiace...")
        page.goto("https://www.sgcarmart.com/search?q=Toyota+Hiace", timeout=30000)

        # Count links
        links = page.query_selector_all('a[href*="info"]')
        print(f"  ✓ Found {len(links)} info links")

        browser.close()

    print("  ✓ Mini scrape completed")

except Exception as e:
    print(f"  ✗ Scrape FAILED: {e}")
    traceback.print_exc()

print("\n" + "="*60)
print("DEBUG TEST COMPLETE")
print("="*60)
print("\nIf all tests pass, scraper should work!")
print("If scrape test fails, check logs above for specific error.")
