"""
SGCarMart scraper - ULTIMATE CLOUDFLARE BYPASS
Uses undetected-playwright for maximum stealth
"""
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time
import config
from database import SessionLocal, VehicleListing

# JavaScript extraction
EXTRACT_JS = r"""
() => {
    const results = [];
    const base = 'https://www.sgcarmart.com';
    const seen = new Set();

    function getFullUrl(href) {
        if (!href) return '';
        return href.startsWith('http') ? href : (href.startsWith('/') ? base + href : base + '/' + href);
    }

    function extractPrice(text) {
        const match = text.match(/(?:SGD|\$)\s*([\d,]+)/);
        return match ? parseFloat(match[1].replace(/,/g, '')) : null;
    }

    function extractDepreciation(text) {
        const match = text.match(/\$\s*([\d,]+)\s*\/\s*yr/i);
        return match ? '$' + match[1] + '/yr' : '';
    }

    function extractRegDate(text) {
        const match = text.match(/(\d{1,2}[-\/]\w{3}[-\/]\d{2,4})/);
        return match ? match[1] : '';
    }

    function extractDealerIdFromUrl(url) {
        if (!url) return null;
        const match = url.match(/[?&]dl=(\d+)/i);
        return match ? match[1] : null;
    }

    function extractDealer(element, carUrl) {
        let dealer = '–';
        let dealerId = null;

        if (carUrl) {
            dealerId = extractDealerIdFromUrl(carUrl);
        }

        const row = element.closest('tr') || element.closest('div[class*="row"]') || element.closest('article') || element.closest('div[class*="item"]');
        if (row) {
            const dealerLink = row.querySelector('a[href*="DL="], a[href*="dl="], a[href*="dealer"]');
            if (dealerLink) {
                const text = (dealerLink.textContent || '').trim();
                if (text && text.length > 2 && text.length < 100 && !text.includes('$')) {
                    dealer = text;
                }
                if (!dealerId) {
                    const href = dealerLink.getAttribute('href') || '';
                    dealerId = extractDealerIdFromUrl(href);
                }
            }
        }

        if (dealer !== '–') {
            dealer = dealer.replace(/\s+/g, ' ').trim();
            if (dealer.length < 3 || dealer.length > 80) {
                dealer = '–';
            }
        }

        return { dealer: dealer || '–', dealerId: dealerId };
    }

    // Strategy 1: Modern structure
    const articles = document.querySelectorAll('article, div[class*="card"], div[class*="listing"]');
    for (const article of articles) {
        try {
            const link = article.querySelector('a[href*="/used-cars/info/"], a[href*="info.php?ID="]');
            if (!link) continue;

            const href = (link.getAttribute('href') || '').trim();
            if (href.includes('DL=') && !href.includes('ID=')) continue;

            const url = getFullUrl(href);
            if (!url || seen.has(url)) continue;

            const name = (link.textContent || '').trim();
            if (!name || name.length < 3) continue;

            seen.add(url);

            const text = article.textContent || '';
            const dealerInfo = extractDealer(article, url);

            results.push({
                make_model: name,
                price: extractPrice(text),
                depreciation: extractDepreciation(text),
                reg_date: extractRegDate(text),
                dealer_name: dealerInfo.dealer,
                dealer_id: dealerInfo.dealerId,
                listing_url: url
            });
        } catch (e) {}
    }

    // Strategy 2: Fallback
    if (results.length === 0) {
        const links = document.querySelectorAll('a[href*="info.php?ID="], a[href*="/used-cars/info/"]');
        for (const a of links) {
            try {
                const href = (a.getAttribute('href') || '').trim();
                if (href.includes('DL=') && !href.includes('ID=')) continue;

                const url = getFullUrl(href);
                if (!url || seen.has(url)) continue;
                seen.add(url);

                const name = (a.textContent || '').trim();
                if (!name || name.length < 3) continue;

                let text = '';
                let container = a.closest('tr') || a.closest('div');
                for (let i = 0; i < 5 && container; i++) {
                    text += ' ' + (container.textContent || '');
                    container = container.parentElement;
                }

                const dealerInfo = extractDealer(a, url);

                results.push({
                    make_model: name,
                    price: extractPrice(text),
                    depreciation: extractDepreciation(text),
                    reg_date: extractRegDate(text),
                    dealer_name: dealerInfo.dealer,
                    dealer_id: dealerInfo.dealerId,
                    listing_url: url
                });
            } catch (e) {}
        }
    }

    return results;
}
"""


def extract_year(reg_date):
    if not reg_date:
        return None
    m = re.search(r'\d{1,2}-\w{3}-(\d{2,4})', reg_date)
    if m:
        y = int(m.group(1))
        return y if y > 100 else (2000 + y if y < 50 else 1900 + y)
    return None


class SGCarMartJSScraper:
    """ULTIMATE Cloudflare bypass scraper"""

    def __init__(self, headless=True):
        self.url = config.COMMERCIAL_LISTING_URL
        self.target_vehicles = config.TARGET_VEHICLES
        self.headless = headless

    def normalize(self, s):
        return re.sub(r'\s+', ' ', (s or '').upper().strip())

    def match_target(self, name):
        n = self.normalize(name)
        return any(self.normalize(t) in n or n in self.normalize(t) for t in self.target_vehicles)

    def scrape_vehicle_listings(self):
        print(f"[ULTIMATE] Starting ULTIMATE scrape at {datetime.now()}")
        print("Using undetected-playwright for Cloudflare bypass...")
        scraped_data = []

        with sync_playwright() as p:
            # Undetected browser automatically bypasses most detections
            print("\n[1/4] Launching undetected browser...")
            browser = p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="en-SG"
            )
            page = context.new_page()

            # Apply undetected stealth
            print("  OK Applying stealth mode...")
            stealth_sync(page)

            try:
                # Step 1: Homepage first
                print("\n[2/4] Loading homepage (establish session)...")
                page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)

                title1 = page.title()
                print(f"  OK Homepage: {title1[:50]}")

                # Step 2: Navigate to listings - SEARCH FOR SPECIFIC MODELS
                print("\n[3/4] Loading commercial vehicles listing...")
                # Try search for lorry/van keywords
                page.goto("https://www.sgcarmart.com/used_cars/listing.php?s=Toyota+Hiace",
                         wait_until="domcontentloaded", timeout=60000)
                time.sleep(8)

                title2 = page.title()
                print(f"  Page title: {title2[:60]}")

                # Check if Cloudflare
                if "just a moment" in title2.lower():
                    print("  [WAIT] Cloudflare check detected, waiting...")
                    time.sleep(15)
                    title2 = page.title()
                    print(f"  New title: {title2[:60]}")

                # Check listings count
                link_count = page.evaluate("() => document.querySelectorAll('a[href*=\"info\"]').length")
                print(f"  Found {link_count} info links")

                if link_count == 0:
                    print("  [WARN] No listings found on this URL, trying alternate...")

                    # Try alternate URL
                    page.goto("https://www.sgcarmart.com/used-cars/listing",
                             wait_until="domcontentloaded", timeout=60000)
                    time.sleep(5)
                    link_count = page.evaluate("() => document.querySelectorAll('a[href*=\"info\"]').length")
                    print(f"  Alternate URL: Found {link_count} info links")

                if link_count == 0:
                    print("\n  [ERROR] Still no listings. Possible reasons:")
                    print("     1. Cloudflare still blocking (even with undetected)")
                    print("     2. VPN IP might be flagged")
                    print("     3. Website structure changed")
                    browser.close()
                    return []

                # Step 3: Scroll and extract
                print("\n[4/4] Scrolling and extracting data...")
                for i in range(3):
                    page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})")
                    time.sleep(2)

                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(2)

                # Extract
                raw = page.evaluate(EXTRACT_JS)
                print(f"  OK Raw items extracted: {len(raw)}")

                # Filter and process
                print(f"\n  Processing {len(raw)} items...")
                for idx, item in enumerate(raw):
                    name = item.get("make_model") or ""
                    if not name:
                        continue

                    # DEBUG: Show first 5 items
                    if idx < 5:
                        print(f"    Item {idx+1}: {name[:50]}")

                    if not self.match_target(name):
                        continue

                    dealer_name = item.get("dealer_name") or "–"
                    dealer_id = item.get("dealer_id")

                    # Fetch dealer if needed
                    if (dealer_name == "–" or len(dealer_name) < 3) and dealer_id:
                        try:
                            print(f"    Fetching dealer ID: {dealer_id}")
                            time.sleep(1)
                            page.goto(f"https://www.sgcarmart.com/dealers/dlrprofile.php?DL={dealer_id}",
                                    wait_until="domcontentloaded", timeout=10000)
                            time.sleep(1)

                            fetched_dealer = page.evaluate("""
                                () => {
                                    let name = '';
                                    const title = document.querySelector('h1, h2, .dealer-name');
                                    if (title) name = (title.textContent || '').trim();
                                    if (!name || name.length < 3) {
                                        const pageTitle = document.title || '';
                                        const match = pageTitle.match(/^([^-|]+)/);
                                        if (match) name = match[1].trim();
                                    }
                                    return name;
                                }
                            """)

                            if fetched_dealer and len(fetched_dealer) > 2:
                                dealer_name = fetched_dealer.strip()
                                print(f"      OK Found: {dealer_name}")
                        except Exception as e:
                            print(f"      X Error: {e}")

                    scraped_data.append({
                        "make_model": name,
                        "registered_year": extract_year(item.get("reg_date")),
                        "depreciation": item.get("depreciation") or "",
                        "dealer_name": dealer_name,
                        "price": item.get("price"),
                        "listing_url": item.get("listing_url") or "",
                        "additional_info": item.get("reg_date") or "",
                    })

                    status = "OK" if dealer_name != "–" else "!"
                    print(f"  [{status}] {name} - ${item.get('price')} - {dealer_name}")

                # Dedupe
                seen = set()
                unique = []
                for item in scraped_data:
                    key = item.get("listing_url") or f"{item.get('make_model', '')}_{item.get('price', 0)}"
                    if key and key not in seen:
                        seen.add(key)
                        unique.append(item)
                scraped_data = unique

                print(f"\n{'='*60}")
                print(f"[SUCCESS] Total target vehicles found: {len(scraped_data)}")
                print(f"{'='*60}")

            except Exception as e:
                print(f"\n[ERROR] Error during scraping: {e}")
                import traceback
                traceback.print_exc()
            finally:
                browser.close()

        if scraped_data:
            self._save_to_db(scraped_data)
            try:
                from sold_log_service import detect_and_log_sold
                detect_and_log_sold()
            except Exception as e:
                print(f"Sold log failed: {e}")

        return scraped_data

    def _save_to_db(self, data):
        db = SessionLocal()
        try:
            for item in data:
                db.add(VehicleListing(
                    scrape_date=datetime.now(),
                    make_model=item.get("make_model", ""),
                    registered_year=item.get("registered_year"),
                    depreciation=item.get("depreciation", ""),
                    dealer_name=item.get("dealer_name", ""),
                    price=item.get("price"),
                    listing_url=item.get("listing_url", ""),
                    additional_info=item.get("additional_info", "")[:500],
                ))
            db.commit()
            print(f"\n[OK] Saved {len(data)} listings to database")
        except Exception as e:
            print(f"[ERROR] Error saving: {e}")
            db.rollback()
        finally:
            db.close()


if __name__ == "__main__":
    import sys
    headless = "--headed" not in sys.argv
    scraper = SGCarMartJSScraper(headless=headless)
    scraper.scrape_vehicle_listings()
