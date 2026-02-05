#!/usr/bin/env python3
"""
QUICK PRODUCTION TEST
Run this to quickly diagnose scraping issues
"""
import sys
import os

print("=" * 70)
print("QUICK SCRAPER DIAGNOSTIC TEST")
print("=" * 70)

# Test 1: Basic imports
print("\n[TEST 1/6] Checking imports...")
try:
    from playwright.sync_api import sync_playwright
    from undetected_playwright import stealth_sync
    import requests
    print("  ✓ All imports OK")
except ImportError as e:
    print(f"  ✗ FAILED: {e}")
    print("\n  FIX: pip install playwright undetected-playwright requests")
    sys.exit(1)

# Test 2: Network connectivity
print("\n[TEST 2/6] Testing network to sgcarmart.com...")
try:
    r = requests.get("https://www.sgcarmart.com", timeout=10)
    print(f"  ✓ Network OK: HTTP {r.status_code}")
    if r.status_code != 200:
        print(f"  ⚠ WARNING: Expected 200, got {r.status_code}")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    print("  This means container cannot reach sgcarmart.com")
    print("  Check: firewall, DNS, or IP blocking")

# Test 3: Chromium availability
print("\n[TEST 3/6] Checking Chromium...")
try:
    with sync_playwright() as p:
        print("  ✓ Playwright started")

        # Try to launch browser
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        print("  ✓ Chromium launched successfully")
        browser.close()
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    print("\n  FIX: Run these commands:")
    print("    playwright install chromium")
    print("    playwright install-deps chromium")
    sys.exit(1)

# Test 4: Can we load sgcarmart?
print("\n[TEST 4/6] Testing page load...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        context = browser.new_context()
        page = context.new_page()

        # Try to load homepage
        print("  Loading https://www.sgcarmart.com...")
        page.goto("https://www.sgcarmart.com", timeout=30000)

        title = page.title()
        print(f"  ✓ Page loaded: {title[:50]}")

        # Check if we're blocked
        body_text = page.evaluate("() => document.body.textContent")
        if "cloudflare" in body_text.lower() or "blocked" in body_text.lower():
            print("  ⚠ WARNING: Possible Cloudflare/blocking detected")
            print("    Solution: Use undetected-playwright stealth mode")
        else:
            print("  ✓ No blocking detected")

        browser.close()
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    print("  This means browser can't load the page")

# Test 5: Stealth mode
print("\n[TEST 5/6] Testing stealth mode...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        context = browser.new_context()
        page = context.new_page()

        # Apply stealth
        stealth_sync(page)
        print("  ✓ Stealth mode applied")

        page.goto("https://www.sgcarmart.com", timeout=30000)
        title = page.title()
        print(f"  ✓ Page loaded with stealth: {title[:50]}")

        browser.close()
except Exception as e:
    print(f"  ✗ FAILED: {e}")

# Test 6: Mini scrape test
print("\n[TEST 6/6] Testing actual scrape (Toyota Hiace only)...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        context = browser.new_context()
        page = context.new_page()
        stealth_sync(page)

        # Load search page
        url = "https://www.sgcarmart.com/search?q=Toyota+Hiace"
        print(f"  Loading {url}")
        page.goto(url, timeout=30000)

        # Count links
        import time
        time.sleep(3)  # Wait for dynamic content

        link_count = page.evaluate('() => document.querySelectorAll(\'a[href*="info"]\').length')
        print(f"  ✓ Found {link_count} info links")

        if link_count == 0:
            print("  ⚠ WARNING: No listings found!")
            print("    Possible causes:")
            print("      - Search returned no results")
            print("      - Page structure changed")
            print("      - JavaScript not executing")
        else:
            # Try to extract one item
            result = page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href*="info"]');
                    if (links.length === 0) return null;

                    const first = links[0];
                    const name = first.textContent.trim();
                    const href = first.getAttribute('href');

                    return {name, href};
                }
            """)

            if result:
                print(f"  ✓ Sample listing: {result['name'][:50]}")
                print(f"    URL: {result['href'][:50]}...")
            else:
                print("  ✗ Could not extract listing data")

        browser.close()
        print("  ✓ Mini scrape test completed")

except Exception as e:
    print(f"  ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
print("\nIf all tests passed but scraping still fails:")
print("  1. Check Coolify logs after clicking REFRESH DATA")
print("  2. Look for specific error messages")
print("  3. Verify database is writable (/app/data permissions)")
print("\nIf Test 6 shows 0 links:")
print("  - SGCarmart might have changed their page structure")
print("  - Need to update scraper selectors")
print("\nIf Test 4/5 fails:")
print("  - Chromium/Playwright issue in container")
print("  - Check Dockerfile has all dependencies")
