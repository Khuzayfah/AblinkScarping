"""
Navigate SGCarmart via menu clicks to find commercial vehicles
"""
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time

print("Navigating SGCarmart via menu to find commercial vehicles...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=1000)  # Slow for observation
    context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="en-SG")
    page = context.new_page()
    stealth_sync(page)

    print("\n[1] Loading homepage...")
    page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded")
    time.sleep(5)

    print("\n[2] Looking for navigation menu...")

    # Try to find and click commercial/van/lorry links
    possible_texts = [
        "Commercial",
        "Van",
        "Lorry",
        "Truck",
        "Goods Vehicle",
        "Commercial Vehicles",
        "Vans & Lorries"
    ]

    found = False
    for text in possible_texts:
        try:
            print(f"  Looking for: '{text}'...")
            # Try to find link with this text
            link = page.get_by_text(text, exact=False).first
            if link.is_visible(timeout=1000):
                print(f"    Found! Clicking...")
                current_url_before = page.url
                link.click()
                time.sleep(3)
                current_url_after = page.url

                if current_url_after != current_url_before:
                    print(f"    SUCCESS! Navigated to: {current_url_after}")
                    found = True
                    break
        except:
            pass

    if not found:
        print("\n  No direct menu link found. Trying search box...")

        # Try search for "Toyota Hiace"
        try:
            search_box = page.locator('input[type="search"], input[name="s"], input[placeholder*="Search"]').first
            if search_box.is_visible(timeout=2000):
                print("  Found search box, typing 'Toyota Hiace'...")
                search_box.fill("Toyota Hiace")
                search_box.press("Enter")
                time.sleep(5)
                print(f"  Current URL: {page.url}")
        except Exception as e:
            print(f"  Search failed: {e}")

    # Check current page
    print("\n[3] Analyzing current page...")
    time.sleep(3)

    analysis = page.evaluate("""
        () => {
            const links = document.querySelectorAll('a');
            let hiace_count = 0;
            let hino_count = 0;
            let dyna_count = 0;
            let samples = [];

            for (const link of links) {
                const text = (link.textContent || '').toLowerCase();
                const href = link.href || '';

                if ((text.includes('hiace') || text.includes('hino') || text.includes('dyna') ||
                     text.includes('dutro') || text.includes('cabstar') || text.includes('nv350')) &&
                    href.includes('info')) {
                    if (samples.length < 10) {
                        samples.push({
                            text: (link.textContent || '').trim().substring(0, 80),
                            href: href.substring(0, 100)
                        });
                    }
                    if (text.includes('hiace')) hiace_count++;
                    if (text.includes('hino')) hino_count++;
                    if (text.includes('dyna')) dyna_count++;
                }
            }

            return {
                current_url: window.location.href,
                title: document.title,
                hiace_count,
                hino_count,
                dyna_count,
                samples
            };
        }
    """)

    print(f"  Current URL: {analysis['current_url']}")
    print(f"  Page Title: {analysis['title']}")
    print(f"  Toyota Hiace found: {analysis['hiace_count']}")
    print(f"  Hino found: {analysis['hino_count']}")
    print(f"  Toyota Dyna found: {analysis['dyna_count']}")

    if analysis['samples']:
        print(f"\n  Commercial vehicle listings found:")
        for s in analysis['samples']:
            print(f"    - {s['text']}")
            print(f"      URL: {s['href']}")

        print("\n" + "="*70)
        print("SUCCESS! Found commercial vehicles at:")
        print(f"  {analysis['current_url']}")
        print("="*70)
    else:
        print("\n  [WARN] Still no commercial vehicles found!")
        print("  Trying one more thing - check page source for hidden filters...")

        # Check for filter buttons/dropdowns
        filters = page.evaluate("""
            () => {
                const selects = document.querySelectorAll('select');
                const result = [];
                for (const sel of selects) {
                    const options = Array.from(sel.options).map(o => o.text);
                    if (options.some(opt => opt.toLowerCase().includes('van') ||
                                           opt.toLowerCase().includes('lorry') ||
                                           opt.toLowerCase().includes('commercial'))) {
                        result.push({
                            name: sel.name || sel.id,
                            options: options
                        });
                    }
                }
                return result;
            }
        """)

        if filters:
            print("\n  Found filter dropdown with commercial options:")
            for f in filters:
                print(f"    {f['name']}: {f['options']}")

    input("\n\nBrowser will stay open. Check manually and press Enter to close...")
    browser.close()

print("\nDone!")
