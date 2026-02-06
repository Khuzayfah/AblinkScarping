"""
Inspect the problem page to see what data is available
"""
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time

url = "https://www.sgcarmart.com/used_cars/info.php?ID=1467452"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    stealth_sync(page)

    print(f"Loading: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)

    # Get page info
    title = page.title()
    print(f"\nPage Title: {title}")

    # Check all links with DL parameter
    dealer_links = page.evaluate(r"""
        () => {
            const links = document.querySelectorAll('a[href*="DL="], a[href*="dl="]');
            return Array.from(links).map(link => ({
                text: link.textContent.trim(),
                href: link.getAttribute('href'),
                html: link.outerHTML
            }));
        }
    """)

    print(f"\nFound {len(dealer_links)} links with DL parameter:")
    for i, link in enumerate(dealer_links, 1):
        print(f"\n{i}. Text: {link['text'][:80]}")
        print(f"   Href: {link['href'][:80]}")

    # Check for any text that looks like dealer/company name
    potential_dealers = page.evaluate(r"""
        () => {
            const bodyText = document.body.textContent;
            const lines = bodyText.split('\n').map(l => l.trim()).filter(l => l);

            // Look for patterns like "Pte Ltd", company names
            const companyPattern = /[A-Z][A-Za-z\s&.\-]+(Pte\s*Ltd|Private Limited)/i;
            const matches = [];

            for (const line of lines) {
                if (companyPattern.test(line) && line.length < 100) {
                    matches.push(line);
                }
            }

            return matches;
        }
    """)

    print(f"\n\nPotential dealer names found:")
    for i, dealer in enumerate(potential_dealers[:10], 1):
        print(f"{i}. {dealer}")

    # Check if this is a private listing
    is_private = page.evaluate(r"""
        () => {
            const bodyText = document.body.textContent.toLowerCase();
            return bodyText.includes('private seller') ||
                   bodyText.includes('direct owner') ||
                   bodyText.includes('individual seller');
        }
    """)

    print(f"\n\nIs private seller: {is_private}")

    # Keep browser open for manual inspection
    print("\n\nBrowser will stay open for 30 seconds for manual inspection...")
    time.sleep(30)

    browser.close()
