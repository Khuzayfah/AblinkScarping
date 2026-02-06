"""
Find correct URL for commercial vehicles on SGCarmart
"""
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time

print("Searching for correct commercial vehicles URL...")

urls_to_test = [
    ("Homepage", "https://www.sgcarmart.com"),
    ("Used cars main", "https://www.sgcarmart.com/used_cars/listing.php"),
    ("Search: Toyota Hiace", "https://www.sgcarmart.com/used_cars/listing.php?s=Toyota+Hiace"),
    ("Search: Hino Dutro", "https://www.sgcarmart.com/used_cars/listing.php?s=Hino+Dutro"),
    ("Search: lorry", "https://www.sgcarmart.com/used_cars/listing.php?s=lorry"),
    ("Search: van", "https://www.sgcarmart.com/used_cars/listing.php?s=van"),
    ("AVL=2", "https://www.sgcarmart.com/used_cars/listing.php?AVL=2"),
    ("veh=5", "https://www.sgcarmart.com/used_cars/listing.php?veh=5"),
    ("CAT=4", "https://www.sgcarmart.com/used_cars/listing.php?CAT=4"),
    ("TYPE=van", "https://www.sgcarmart.com/used_cars/listing.php?TYPE=van"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="en-SG")
    page = context.new_page()
    stealth_sync(page)

    # Load homepage first
    print("\nLoading homepage first...")
    page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded")
    time.sleep(5)

    results = []

    for name, url in urls_to_test:
        print(f"\n{'='*70}")
        print(f"Testing: {name}")
        print(f"URL: {url}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)

            title = page.title()
            print(f"  Title: {title[:60]}")

            # Check for commercial vehicles
            check = page.evaluate("""
                () => {
                    const text = document.body.textContent.toLowerCase();
                    const links = document.querySelectorAll('a');
                    let commercialCount = 0;
                    let samples = [];

                    // Check for commercial vehicle keywords in links
                    for (const link of links) {
                        const linkText = (link.textContent || '').toLowerCase();
                        if (linkText.includes('hiace') || linkText.includes('hino') ||
                            linkText.includes('dyna') || linkText.includes('dutro') ||
                            linkText.includes('cabstar') || linkText.includes('lorry') ||
                            linkText.includes('nv350') || linkText.includes('nv200')) {
                            commercialCount++;
                            if (samples.length < 5) {
                                samples.push((link.textContent || '').trim().substring(0, 60));
                            }
                        }
                    }

                    return {
                        total_links: document.querySelectorAll('a[href*="info"]').length,
                        commercial_count: commercialCount,
                        samples: samples,
                        has_hiace: text.includes('hiace'),
                        has_hino: text.includes('hino'),
                        has_dyna: text.includes('dyna'),
                        has_lorry: text.includes('lorry')
                    };
                }
            """)

            print(f"  Total info links: {check['total_links']}")
            print(f"  Commercial vehicles found: {check['commercial_count']}")
            print(f"  Has Hiace: {check['has_hiace']}")
            print(f"  Has Hino: {check['has_hino']}")
            print(f"  Has Dyna: {check['has_dyna']}")
            print(f"  Has Lorry: {check['has_lorry']}")

            if check['samples']:
                print(f"  Sample listings:")
                for s in check['samples']:
                    print(f"    - {s}")

            results.append({
                "name": name,
                "url": url,
                "commercial_count": check['commercial_count'],
                "total_links": check['total_links']
            })

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"name": name, "url": url, "commercial_count": 0, "total_links": 0})

    # Summary
    print("\n" + "="*70)
    print("SUMMARY - BEST URLs FOR COMMERCIAL VEHICLES:")
    print("="*70)

    # Sort by commercial count
    results.sort(key=lambda x: x['commercial_count'], reverse=True)

    for r in results[:5]:
        if r['commercial_count'] > 0:
            print(f"\n[{r['commercial_count']} commercial] {r['name']}")
            print(f"  URL: {r['url']}")

    if results[0]['commercial_count'] > 0:
        print("\n" + "="*70)
        print("RECOMMENDED URL:")
        print(f"  {results[0]['url']}")
        print("="*70)
    else:
        print("\n[WARN] No commercial vehicles found in any URL!")
        print("Possible reasons:")
        print("  1. Need specific search parameters")
        print("  2. Commercial vehicles in different section")
        print("  3. Need to navigate through menus")

    input("\n\nPress Enter to close browser...")
    browser.close()
