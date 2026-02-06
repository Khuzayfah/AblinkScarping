"""Test script to analyze new SGCarMart page structure"""
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time
import json

NEW_EXTRACT_JS = """
() => {
    const results = [];
    const base = 'https://www.sgcarmart.com';
    const seen = new Set();

    // New structure: listing containers with id="listing_N"
    const listings = document.querySelectorAll('[id^="listing_"]');

    for (const listing of listings) {
        try {
            // Skip header row
            if (listing.id === 'listing_search_grey_header') continue;

            // Find the vehicle link
            const link = listing.querySelector('a[href*="used-cars/info"]');
            if (!link) continue;

            const href = link.getAttribute('href') || '';
            const url = href.startsWith('http') ? href : base + href;
            if (seen.has(url)) continue;
            seen.add(url);

            // Get vehicle name from the link with class containing 'text_link'
            const nameLink = listing.querySelector('a[class*="text_link"]');
            const name = nameLink ? nameLink.textContent.trim() : (link.textContent.trim() || '');
            if (!name || name.length < 3) continue;

            // Get full text for extraction
            const text = listing.innerText || '';

            // Extract price: $155,000
            let price = null;
            const priceMatch = text.match(/\\$(\\d{1,3}(?:,\\d{3})*)/);
            if (priceMatch) {
                price = parseFloat(priceMatch[1].replace(/,/g, ''));
            }

            // Extract depreciation: $37,560 /yr
            let depreciation = '';
            const depMatch = text.match(/\\$(\\d{1,3}(?:,\\d{3})*)\\s*\\/yr/i);
            if (depMatch) {
                depreciation = '$' + depMatch[1] + '/yr';
            }

            // Extract reg date: 29-Sep-2017
            let regDate = '';
            const dateMatch = text.match(/(\\d{1,2}-[A-Z][a-z]{2}-\\d{4})/);
            if (dateMatch) {
                regDate = dateMatch[1];
            }

            // Extract dealer from dealer link or listing text
            let dealer = '';
            // Check for "DIRECT OWNER" text
            if (text.includes('DIRECT OWNER')) {
                dealer = 'Direct Owner';
            }
            // Check for dealer links (links with dl= parameter)
            const dealerLink = listing.querySelector('a[href*="dl="]');
            if (dealerLink && !dealer) {
                // The dealer name might be in a separate element
                // Check for company-like names in the listing
            }

            // Extract from URL dl= parameter
            let dealerId = null;
            const dlMatch = href.match(/[?&]dl=(\\d+)/i);
            if (dlMatch) {
                dealerId = dlMatch[1];
            }

            results.push({
                make_model: name,
                price: price,
                depreciation: depreciation,
                reg_date: regDate,
                dealer_name: dealer || '',
                dealer_id: dealerId,
                listing_url: url
            });
        } catch (e) {}
    }

    return results;
}
"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox',
                  '--disable-dev-shm-usage', '--disable-gpu']
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-SG"
        )
        page = context.new_page()
        stealth_sync(page)

        # Step 1: Homepage
        page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
        print(f"Homepage: {page.title()}")

        # Step 2: Listing page (general - no filter)
        page.goto("https://www.sgcarmart.com/used-cars/listing", wait_until="domcontentloaded", timeout=30000)
        time.sleep(8)
        print(f"\nListing page: {page.title()}")

        # Test extraction
        results = page.evaluate(NEW_EXTRACT_JS)
        print(f"\nExtracted {len(results)} listings")
        for r in results[:5]:
            print(f"  Name: {r['make_model']}")
            print(f"  Price: {r['price']}")
            print(f"  Depreciation: {r['depreciation']}")
            print(f"  Reg Date: {r['reg_date']}")
            print(f"  Dealer: {r['dealer_name']}")
            print(f"  URL: {r['listing_url'][:80]}")
            print()

        # Check pagination - look for "next" or pagination elements
        pagination = page.evaluate("""() => {
            const els = document.querySelectorAll('a, button');
            const results = [];
            for (const el of els) {
                const text = (el.textContent || '').trim();
                const href = el.getAttribute('href') || '';
                if (text === 'Next' || text === '>' || text === 'Load More' ||
                    href.includes('page=') || text.match(/^\\d+$/) ||
                    el.className.includes('pagination') || el.className.includes('page')) {
                    results.push({
                        tag: el.tagName,
                        text: text.substring(0, 30),
                        href: href.substring(0, 100),
                        cls: el.className.substring(0, 80)
                    });
                }
            }
            return results;
        }""")
        print(f"\nPagination elements ({len(pagination)}):")
        for p_el in pagination[:10]:
            print(f"  [{p_el['tag']}] text='{p_el['text']}' href='{p_el['href']}' cls={p_el['cls']}")

        # Check how the listing body text looks for dealer extraction
        listing_texts = page.evaluate("""() => {
            const listings = document.querySelectorAll('[id^="listing_"]');
            const result = [];
            for (const listing of Array.from(listings).slice(1, 4)) {
                result.push(listing.innerText.substring(0, 400));
            }
            return result;
        }""")
        print("\nFull listing text samples:")
        for i, text in enumerate(listing_texts):
            print(f"\n--- Listing {i} ---")
            print(text)

        # Check detail page structure (for dealer extraction)
        if results:
            detail_url = results[0]['listing_url']
            # Remove utm params
            if '?' in detail_url:
                detail_url = detail_url.split('?')[0]

            print(f"\n\nFetching detail page: {detail_url}")
            page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)

            title = page.title()
            print(f"Detail title: {title}")

            # Extract dealer from detail page title
            # Format: "Used 2017 BMW 7 Series 750Li for Sale | Dealer Name - Sgcarmart"
            import re
            title_match = re.search(r'\|\s*(.+?)\s*-\s*Sgcarmart', title, re.I)
            if title_match:
                print(f"Dealer from title: {title_match.group(1)}")

            # Get depreciation from detail page
            detail_text = page.evaluate("() => document.body.innerText.substring(0, 2000)")
            dep_match = re.search(r'\$\s*([\d,]+)\s*/\s*yr', detail_text)
            if dep_match:
                print(f"Depreciation: ${dep_match.group(1)}/yr")

        browser.close()

if __name__ == "__main__":
    main()
