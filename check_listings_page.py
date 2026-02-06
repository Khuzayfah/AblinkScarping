"""Check listings page structure - proper encoding"""
from playwright.sync_api import sync_playwright
import time
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("Loading listings page...")
    page.goto("https://www.sgcarmart.com/used-cars/listing?veh=1&limit=100", timeout=30000)
    time.sleep(8)  # Wait for JS to load

    title = page.title()
    print(f"Page title: {title}")

    # Check various selectors
    info = page.evaluate("""
        () => {
            const result = {
                articles: document.querySelectorAll('article').length,
                info_links_1: document.querySelectorAll('a[href*="/used-cars/info/"]').length,
                info_links_2: document.querySelectorAll('a[href*="info.php?ID="]').length,
                info_links_3: document.querySelectorAll('a[href*="info"]').length,
                cards: document.querySelectorAll('[class*="card"]').length,
                listings: document.querySelectorAll('[class*="listing"]').length,
                sample_hrefs: [],
                sample_text: []
            };

            // Get sample links
            const links = document.querySelectorAll('a');
            let count = 0;
            for (const link of links) {
                const href = link.href || '';
                const text = (link.textContent || '').trim();
                if (href.includes('info') && text.length > 5 && count < 5) {
                    result.sample_hrefs.push(href.substring(0, 80));
                    result.sample_text.push(text.substring(0, 50));
                    count++;
                }
            }

            return result;
        }
    """)

    print(f"\nElement counts:")
    print(f"  Articles: {info['articles']}")
    print(f"  Links with '/used-cars/info/': {info['info_links_1']}")
    print(f"  Links with 'info.php?ID=': {info['info_links_2']}")
    print(f"  Links with 'info': {info['info_links_3']}")
    print(f"  Cards: {info['cards']}")
    print(f"  Listings: {info['listings']}")

    print(f"\nSample links found:")
    for i, (href, text) in enumerate(zip(info['sample_hrefs'], info['sample_text'])):
        print(f"  {i+1}. {text}")
        print(f"     {href}")

    if info['info_links_1'] == 0 and info['info_links_2'] == 0:
        print("\nWARNING: NO INFO LINKS FOUND!")
        print("Possible reasons:")
        print("  1. Website structure changed completely")
        print("  2. Page requires JavaScript that hasn't loaded yet")
        print("  3. Listings are loaded via AJAX/fetch")

        print("\nChecking if it's AJAX loaded...")
        time.sleep(5)
        print("Waiting 5 more seconds...")

        info2 = page.evaluate("() => document.querySelectorAll('a[href*=\"info\"]').length")
        print(f"After waiting: {info2} info links")

    input("\nCheck browser window. Press Enter to close...")
    browser.close()
