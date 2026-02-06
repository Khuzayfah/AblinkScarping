"""
SGCarMart scraper - CLOUDFLARE BYPASS VERSION
Uses playwright-stealth to bypass Cloudflare protection
"""
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import playwright_stealth
import time
import config
from database import SessionLocal, VehicleListing

# JavaScript extraction - SIMPLE & WORKING
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
            const price = extractPrice(text);
            const depre = extractDepreciation(text);
            const regDate = extractRegDate(text);
            const dealerInfo = extractDealer(article, url);

            if (!price && name.length < 5) continue;

            results.push({
                make_model: name,
                price: price,
                depreciation: depre,
                reg_date: regDate,
                dealer_name: dealerInfo.dealer,
                dealer_id: dealerInfo.dealerId,
                listing_url: url
            });
        } catch (e) {
            continue;
        }
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

                let container = a.closest('tr') || a.closest('div');
                let text = '';
                for (let i = 0; i < 5 && container; i++) {
                    text += ' ' + (container.textContent || '');
                    container = container.parentElement;
                }

                const price = extractPrice(text);
                const depre = extractDepreciation(text);
                const regDate = extractRegDate(text);
                const dealerInfo = extractDealer(a, url);

                results.push({
                    make_model: name,
                    price: price,
                    depreciation: depre,
                    reg_date: regDate,
                    dealer_name: dealerInfo.dealer,
                    dealer_id: dealerInfo.dealerId,
                    listing_url: url
                });
            } catch (e) {
                continue;
            }
        }
    }

    return results;
}
"""


def get_browser(playwright, headless=True):
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu"
    ]
    try:
        return playwright.chromium.launch(channel="chrome", headless=headless, args=args)
    except Exception:
        return playwright.chromium.launch(headless=headless, args=args)


def extract_year(reg_date):
    if not reg_date:
        return None
    m = re.search(r'\d{1,2}-\w{3}-(\d{2,4})', reg_date)
    if m:
        y = int(m.group(1))
        return y if y > 100 else (2000 + y if y < 50 else 1900 + y)
    m = re.search(r'(19|20)\d{2}', reg_date)
    return int(m.group(0)) if m else None


class SGCarMartJSScraper:
    """Cloudflare bypass scraper with dealer extraction"""

    def __init__(self, headless=True):
        self.url = getattr(config, 'COMMERCIAL_LISTING_URL', config.USED_CARS_URL)
        self.target_vehicles = config.TARGET_VEHICLES
        self.headless = headless

    def normalize(self, s):
        return re.sub(r'\s+', ' ', (s or '').upper().strip())

    def match_target(self, name):
        n = self.normalize(name)
        return any(self.normalize(t) in n or n in self.normalize(t) for t in self.target_vehicles)

    def scrape_vehicle_listings(self):
        print(f"Starting CLOUDFLARE BYPASS scrape at {datetime.now()}")
        scraped_data = []

        with sync_playwright() as p:
            browser = get_browser(p, headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                locale="en-SG"
            )
            page = context.new_page()

            # Apply stealth mode - ANTI CLOUDFLARE
            print("Applying stealth mode (anti-detection)...")
            playwright_stealth.stealth.stealth_sync(page)

            try:
                # Step 1: Load homepage first (establish session)
                print("\nStep 1: Loading homepage (establish session)...")
                page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)  # Wait for Cloudflare check

                title = page.title()
                print(f"  Homepage title: {title[:60]}")

                if "just a moment" in title.lower():
                    print("  Waiting for Cloudflare check to complete...")
                    time.sleep(10)
                    title = page.title()
                    print(f"  New title: {title[:60]}")

                # Step 2: Navigate to listings
                urls_to_scrape = [
                    "https://www.sgcarmart.com/used-cars/listing?veh=1&limit=100",
                    "https://www.sgcarmart.com/used_cars/listing.php?veh=1",
                ]

                for url_idx, url in enumerate(urls_to_scrape):
                    try:
                        print(f"\nStep 2.{url_idx+1}: Loading listings page...")
                        print(f"  URL: {url}")
                        page.goto(url, wait_until="domcontentloaded", timeout=60000)

                        # Wait longer for Cloudflare + page load
                        time.sleep(8)

                        page_title = page.title()
                        print(f"  Page title: {page_title[:60]}")

                        if "just a moment" in page_title.lower():
                            print("  ⚠️  Cloudflare detected, waiting...")
                            time.sleep(15)
                            page_title = page.title()
                            print(f"  New title: {page_title[:60]}")

                        # Check if page loaded
                        link_count = page.evaluate("() => document.querySelectorAll('a[href*=\"info\"]').length")
                        print(f"  Found {link_count} info links on page")

                        if link_count == 0:
                            print("  ⚠️  No listings found, skipping this URL...")
                            continue

                        # Scroll to load lazy content
                        print("  Scrolling to load all content...")
                        for i in range(3):
                            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})")
                            time.sleep(2)

                        page.evaluate("window.scrollTo(0, 0)")
                        time.sleep(2)

                        # Extract data
                        raw = page.evaluate(EXTRACT_JS)
                        print(f"  ✓ Extracted {len(raw)} raw items")

                        for item in raw:
                            name = item.get("make_model") or ""
                            if not name or not self.match_target(name):
                                continue

                            dealer_name = item.get("dealer_name") or "–"
                            dealer_id = item.get("dealer_id")

                            # Fetch dealer if needed
                            if (dealer_name == "–" or len(dealer_name) < 3) and dealer_id:
                                try:
                                    print(f"    Fetching dealer ID: {dealer_id}")
                                    time.sleep(1)
                                    dealer_url = f"https://www.sgcarmart.com/dealers/dlrprofile.php?DL={dealer_id}"
                                    page.goto(dealer_url, wait_until="domcontentloaded", timeout=10000)
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
                                        print(f"      Found: {dealer_name}")
                                except Exception as e:
                                    print(f"      Error: {e}")

                            listing_item = {
                                "make_model": name,
                                "registered_year": extract_year(item.get("reg_date")),
                                "depreciation": item.get("depreciation") or "",
                                "dealer_name": dealer_name,
                                "price": item.get("price"),
                                "listing_url": item.get("listing_url") or "",
                                "additional_info": item.get("reg_date") or "",
                            }
                            scraped_data.append(listing_item)

                            if dealer_name and dealer_name != "–":
                                print(f"  [OK] {name} - ${item.get('price')} - Dealer: [{dealer_name}]")
                            else:
                                print(f"  [!] {name} - ${item.get('price')} - Dealer: [NOT FOUND]")

                    except Exception as e:
                        print(f"  Error loading URL: {e}")
                        continue

                # Dedupe
                seen = set()
                unique = []
                for item in scraped_data:
                    key = item.get("listing_url") or f"{item.get('make_model', '')}_{item.get('price', 0)}"
                    if key and key not in seen:
                        seen.add(key)
                        unique.append(item)
                scraped_data = unique

                print(f"\n{'='*50}")
                print(f"Total target vehicles found: {len(scraped_data)}")
                print(f"{'='*50}\n")

            except Exception as e:
                print(f"Error during scraping: {e}")
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

        print(f"Scraping completed. Found {len(scraped_data)} target vehicles")
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
            print(f"Saved {len(data)} listings to database")
        except Exception as e:
            print(f"Error saving: {e}")
            db.rollback()
        finally:
            db.close()


if __name__ == "__main__":
    import sys
    headless = "--headed" not in sys.argv
    scraper = SGCarMartJSScraper(headless=headless)
    scraper.scrape_vehicle_listings()
