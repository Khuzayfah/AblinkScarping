"""
SIMPLIFIED VERSION - Back to basics with minimal enhancements
"""
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import time
import random
import config
from database import SessionLocal, VehicleListing

# Simplified JavaScript extraction (SAME AS BEFORE but with fixed regex)
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
                if (text && text.length > 2 && text.length < 100) {
                    dealer = text;
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
    args = ["--disable-blink-features=AutomationControlled"]
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
    return None


class SGCarMartJSScraperSimplified:
    """Simplified scraper - back to basics"""

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
        print(f"Starting SIMPLIFIED scrape at {datetime.now()}")
        scraped_data = []

        with sync_playwright() as p:
            browser = get_browser(p, headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            # Minimal stealth
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            try:
                urls_to_scrape = [
                    config.COMMERCIAL_LISTING_URL,
                    f"{config.USED_CARS_URL}?veh=1&limit=200",
                ]

                for url_idx, url in enumerate(urls_to_scrape):
                    try:
                        print(f"Loading page {url_idx + 1}/{len(urls_to_scrape)}: {url}")
                        page.goto(url, wait_until="domcontentloaded", timeout=60000)

                        # Simple wait
                        time.sleep(5)

                        # Simple scroll
                        for i in range(3):
                            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})")
                            time.sleep(2)

                        # Extract
                        raw = page.evaluate(EXTRACT_JS)
                        print(f"JS extracted {len(raw)} raw items from page {url_idx + 1}")

                        for item in raw:
                            name = item.get("make_model") or ""
                            if not name or not self.match_target(name):
                                continue

                            dealer_name = item.get("dealer_name") or "–"

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
                            print(f"✓ {name} - ${item.get('price')} - {dealer_name}")

                    except Exception as e:
                        print(f"Error loading URL {url}: {e}")
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

                print(f"\nTotal found: {len(scraped_data)}")

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
            print(f"Saved {len(data)} listings to database")
        except Exception as e:
            print(f"Error saving: {e}")
            db.rollback()
        finally:
            db.close()


if __name__ == "__main__":
    import sys
    headless = "--headed" not in sys.argv
    scraper = SGCarMartJSScraperSimplified(headless=headless)
    scraper.scrape_vehicle_listings()
