"""
Script to fix missing dealer names by re-scraping detail pages
"""
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time
from database import SessionLocal, VehicleListing

def extract_dealer_from_detail_page(url):
    """Extract dealer name from detail page"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        stealth_sync(page)

        try:
            print(f"Visiting: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # Debug: Save page title and check for dealer info
            title = page.title()
            print(f"Page title: {title}")

            # Extract dealer info using multiple methods
            dealer_info = page.evaluate(r"""
                () => {
                    const bodyText = document.body.textContent;
                    const bodyHTML = document.body.innerHTML;
                    const pageTitle = document.title || '';

                    let dealer = '';
                    let dealerId = null;

                    // Check if this is a private seller first
                    const isPrivateSeller = bodyText.toLowerCase().includes('direct owner') ||
                                          bodyText.toLowerCase().includes('private seller');

                    // Method 1: Check for "Direct Owner" in first DL link
                    const firstDLLink = document.querySelector('a[href*="DL="], a[href*="dl="]');
                    if (firstDLLink) {
                        const linkText = (firstDLLink.textContent || '').trim().toLowerCase();
                        if (linkText === 'direct owner' || linkText === 'private seller') {
                            dealer = 'Direct Owner';
                            console.log('Found private seller');
                            return {dealer: dealer, dealerId: null, isPrivate: true};
                        }
                    }

                    // Method 2: Extract from page title
                    // Format: "Used 2020 Isuzu NMR85U for Sale | Dealer Name - Sgcarmart"
                    const titleMatch = pageTitle.match(/\|\s*(.+?)\s*-\s*Sgcarmart/i);
                    if (titleMatch) {
                        dealer = titleMatch[1].trim();
                        console.log('Found dealer in title:', dealer);
                    }

                    // Method 3: Look for dealer link with DL parameter
                    if (!dealer || dealer.length < 3) {
                        const dealerLinks = document.querySelectorAll('a[href*="DL="], a[href*="dl="]');
                        for (const link of dealerLinks) {
                            const text = (link.textContent || '').trim();
                            const href = link.getAttribute('href') || '';

                            // Extract dealer ID
                            const dlMatch = href.match(/[?&]dl=(\d+)/i);
                            if (dlMatch) {
                                dealerId = dlMatch[1];
                            }

                            // Get dealer name - skip navigation/UI text
                            if (text && text.length > 3 && text.length < 100 &&
                                !text.includes('Printable') && !text.includes('Version') &&
                                !text.includes('Search') && !text.includes('View') &&
                                !text.includes('Home') && !text.includes('Contact') &&
                                !text.toLowerCase().includes('dealer') &&
                                !text.includes('imported') &&
                                !text.includes('$')) {
                                dealer = text;
                                console.log('Found dealer in link:', dealer);
                                break;
                            }
                        }
                    }

                    // Method 3: Look in structured data / JSON-LD
                    if (!dealer || dealer.length < 3) {
                        const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                        for (const script of scripts) {
                            try {
                                const data = JSON.parse(script.textContent);
                                if (data.seller && data.seller.name) {
                                    dealer = data.seller.name;
                                    console.log('Found dealer in JSON-LD:', dealer);
                                    break;
                                }
                            } catch (e) {}
                        }
                    }

                    // Method 4: Look for "Dealer:" label in text
                    if (!dealer || dealer.length < 3) {
                        const dealerMatch = bodyText.match(/Dealer[:\s]+([A-Z][A-Za-z\s&.\-]+(?:Pte\s*Ltd)?)/i);
                        if (dealerMatch) {
                            dealer = dealerMatch[1].trim();
                            console.log('Found dealer with label:', dealer);
                        }
                    }

                    // Clean dealer name
                    if (dealer) {
                        dealer = dealer.replace(/\s+/g, ' ').trim();
                        // Normalize "Pte Ltd" variations
                        dealer = dealer.replace(/\s*Pte\.?\s*Ltd\.?.*$/i, ' Pte Ltd').trim();
                        // Remove trailing punctuation
                        dealer = dealer.replace(/[,;.\s]+$/, '').trim();
                        // Limit length
                        if (dealer.length > 80) {
                            dealer = dealer.substring(0, 80).trim();
                        }
                        // Final validation - must be reasonable length
                        if (dealer.length < 3 || dealer.length > 80) {
                            dealer = '';
                        }
                    }

                    return {dealer: dealer || '', dealerId: dealerId, isPrivate: isPrivateSeller};
                }
            """)

            return dealer_info

        except Exception as e:
            print(f"Error: {e}")
            return {'dealer': '', 'dealerId': None}
        finally:
            browser.close()


def fix_missing_dealers():
    """Find and fix all items with missing dealer names"""
    db = SessionLocal()

    try:
        # Find items without dealer name
        items = db.query(VehicleListing).filter(
            VehicleListing.dealer_name == '–'
        ).all()

        print(f"Found {len(items)} items without dealer name\n")

        # Group by URL to avoid duplicates
        url_to_items = {}
        for item in items:
            if item.listing_url not in url_to_items:
                url_to_items[item.listing_url] = []
            url_to_items[item.listing_url].append(item)

        print(f"Processing {len(url_to_items)} unique URLs\n")

        fixed_count = 0
        for url, items_group in url_to_items.items():
            print(f"\n{'='*60}")
            print(f"Processing: {url}")

            dealer_info = extract_dealer_from_detail_page(url)
            dealer_name = dealer_info.get('dealer', '')
            is_private = dealer_info.get('isPrivate', False)

            if dealer_name and len(dealer_name) > 2:
                if is_private or dealer_name == 'Direct Owner':
                    print(f"[INFO] Private seller detected: {dealer_name}")
                else:
                    print(f"[OK] Found dealer: {dealer_name}")

                # Update all items with this URL
                for item in items_group:
                    item.dealer_name = dealer_name
                    print(f"  Updated: {item.make_model[:50]}")

                db.commit()
                fixed_count += len(items_group)
            else:
                print(f"[X] Could not find dealer name - listing may be inactive or removed")

            time.sleep(2)  # Be polite

        print(f"\n{'='*60}")
        print(f"Fixed {fixed_count} items")
        print(f"{'='*60}")

    finally:
        db.close()


if __name__ == "__main__":
    fix_missing_dealers()
