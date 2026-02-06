"""Test different URLs to find working one"""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

urls_to_test = [
    ("Homepage", "https://www.sgcarmart.com"),
    ("Used cars main", "https://www.sgcarmart.com/used-cars"),
    ("Used cars listing", "https://www.sgcarmart.com/used-cars/listing"),
    ("Commercial veh=1", "https://www.sgcarmart.com/used-cars/listing?veh=1"),
    ("Old format", "https://www.sgcarmart.com/used_cars/listing.php?veh=1"),
    ("Search all", "https://www.sgcarmart.com/used_cars/listing.php"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    results = []

    for name, url in urls_to_test:
        print(f"\nTesting: {name}")
        print(f"URL: {url}")

        try:
            page.goto(url, timeout=20000)
            time.sleep(5)

            title = page.title()
            info_count = page.evaluate("() => document.querySelectorAll('a[href*=\"info\"]').length")

            print(f"  Title: {title[:60] if title else '(empty)'}")
            print(f"  Info links: {info_count}")

            results.append((name, url, title, info_count))

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((name, url, f"ERROR: {e}", 0))

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for name, url, title, count in results:
        status = "OK" if count > 0 else ("TITLE OK" if title and not title.startswith("ERROR") else "FAIL")
        print(f"{status:10s} | {count:3d} links | {name:20s} | {title[:40]}")

    print("\nBest working URL:")
    best = max([r for r in results if not str(r[2]).startswith("ERROR")], key=lambda x: x[3], default=None)
    if best:
        print(f"  {best[1]}")
        print(f"  Found {best[3]} info links")
    else:
        print("  None found - all URLs failed!")

    input("\nPress Enter to close...")
    browser.close()
