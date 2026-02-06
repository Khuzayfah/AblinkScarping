"""Quick debug script to see actual HTML structure"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("Loading SGCarmart...")
    page.goto("https://www.sgcarmart.com/used-cars/listing?veh=1&limit=100", wait_until="domcontentloaded")

    # Wait longer for JS to load
    print("Waiting for page to fully load...")
    time.sleep(10)

    # Get page title
    title = page.title()
    print(f"Page title: {title}")

    # Check if we can see any listings
    html = page.content()

    # Save HTML to file
    with open("debug_page_structure.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Saved HTML to: debug_page_structure.html")

    # Count various elements
    info = page.evaluate("""
        () => {
            return {
                total_links: document.querySelectorAll('a').length,
                info_links: document.querySelectorAll('a[href*="info"]').length,
                articles: document.querySelectorAll('article').length,
                cards: document.querySelectorAll('[class*="card"]').length,
                divs_listing: document.querySelectorAll('div[class*="listing"]').length,
                tables: document.querySelectorAll('table').length,
                all_text_sample: document.body.textContent.substring(0, 500)
            }
        }
    """)

    print(f"\n📊 Element counts:")
    print(f"   Total links: {info['total_links']}")
    print(f"   Info links: {info['info_links']}")
    print(f"   Articles: {info['articles']}")
    print(f"   Cards: {info['cards']}")
    print(f"   Listing divs: {info['divs_listing']}")
    print(f"   Tables: {info['tables']}")

    print(f"\n📄 Sample text from page:")
    print(info['all_text_sample'][:300])

    input("\n👁️ Check the browser window and HTML file. Press Enter to close...")
    browser.close()
