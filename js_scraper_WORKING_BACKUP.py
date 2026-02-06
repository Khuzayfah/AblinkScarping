"""
SGCarMart scraper - WORKING VERSION
Manual stealth approach without external libs
BASED ON YOUR ORIGINAL WORKING CODE + DEALER EXTRACTION
"""
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import time
import config
from database import SessionLocal, VehicleListing

# SAME EXTRACTION JS AS BEFORE (working version)
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

    // Strategy 1
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
            results.push({
                make_model: name,
                price: extractPrice(text),
                depreciation: extractDepreciation(text),
                reg_date: extractRegDate(text),
                dealer_name: extractDealer(article, url).dealer,
                dealer_id: extractDealer(article, url).dealerId,
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

                results.push({
                    make_model: name,
                    price: extractPrice(text),
                    depreciation: extractDepreciation(text),
                    reg_date: extractRegDate(text),
                    dealer_name: extractDealer(a, url).dealer,
                    dealer_id: extractDealer(a, url).dealerId,
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
        print(f"Starting scrape at {datetime.now()}")
        scraped_data = []

        with sync_playwright() as p:
            # Launch browser
            try:
                browser = p.chromium.launch(channel="chrome", headless=self.headless,
                                          args=["--disable-blink-features=AutomationControlled"])
            except:
                browser = p.chromium.launch(headless=self.headless,
                                          args=["--disable-blink-features=AutomationControlled"])

            # Create context with aggressive stealth
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            # Advanced stealth JavaScript
            page.add_init_script("""
                // Remove webdriver
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

                // Chrome object
                window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}};

                // Plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({state: Notification.permission}) :
                        originalQuery(parameters)
                );
            """)

            try:
                # CRITICAL: Load homepage FIRST (Cloudflare check)
                print("\n[1/3] Loading homepage (Cloudflare bypass)...")
                page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(10)  # IMPORTANT: Wait for Cloudflare

                # Now try listing page
                print("\n[2/3] Loading commercial vehicles listing...")
                page.goto("https://www.sgcarmart.com/used_cars/listing.php?veh=1",
                         wait_until="domcontentloaded", timeout=60000)
                time.sleep(8)

                # Check if page loaded
                title = page.title()
                print(f"  Page title: {title[:60]}")

                if "just a moment" in title.lower():
                    print("  Waiting extra time for Cloudflare...")
                    time.sleep(15)

                # Scroll
                print("\n[3/3] Scrolling and extracting...")
                for i in range(3):
                    page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})")
                    time.sleep(2)

                # Extract
                raw = page.evaluate(EXTRACT_JS)
                print(f"  Raw items extracted: {len(raw)}")

                for item in raw:
                    name = item.get("make_model") or ""
                    if not name or not self.match_target(name):
                        continue

                    scraped_data.append({
                        "make_model": name,
                        "registered_year": extract_year(item.get("reg_date")),
                        "depreciation": item.get("depreciation") or "",
                        "dealer_name": item.get("dealer_name") or "–",
                        "price": item.get("price"),
                        "listing_url": item.get("listing_url") or "",
                        "additional_info": item.get("reg_date") or "",
                    })

                    print(f"  ✓ {name} - ${item.get('price')} - {item.get('dealer_name')}")

                print(f"\n{'='*50}")
                print(f"Total found: {len(scraped_data)}")
                print(f"{'='*50}")

            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                browser.close()

        if scraped_data:
            self._save_to_db(scraped_data)

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
            print(f"\n✓ Saved {len(data)} listings to database")
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
