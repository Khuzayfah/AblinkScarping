"""Test basic access to SGCarmart without complex stealth"""
from playwright.sync_api import sync_playwright
import time

print("Testing basic access to SGCarmart...")

with sync_playwright() as p:
    # Simple browser without stealth
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    try:
        print("\n1. Loading homepage...")
        page.goto("https://www.sgcarmart.com", timeout=30000)
        time.sleep(3)

        title = page.title()
        print(f"   Homepage title: {title}")

        if title:
            print("   ✓ Homepage loaded OK")
        else:
            print("   ✗ Homepage title empty - might be blocked")

        print("\n2. Loading used cars listing...")
        page.goto("https://www.sgcarmart.com/used-cars/listing?veh=1", timeout=30000)
        time.sleep(5)

        title2 = page.title()
        print(f"   Listing page title: {title2}")

        # Check for listings
        links = page.evaluate("""
            () => {
                const all = document.querySelectorAll('a[href*="info"]');
                return {
                    count: all.length,
                    samples: Array.from(all).slice(0, 3).map(a => ({
                        href: a.href,
                        text: a.textContent.trim().substring(0, 50)
                    }))
                };
            }
        """)

        print(f"\n3. Found {links['count']} info links")
        if links['samples']:
            print("   Sample listings:")
            for s in links['samples']:
                print(f"   - {s['text']}")
                print(f"     {s['href'][:80]}...")

        if links['count'] > 0:
            print("\n✅ Website is ACCESSIBLE - listings found!")
            print("   → Problem is in the scraper logic, not website blocking")
        else:
            print("\n⚠️ No listings found - need to investigate")

        input("\nPress Enter to close...")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        browser.close()
