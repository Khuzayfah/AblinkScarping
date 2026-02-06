"""
SGCarMart scraper using JavaScript (no API) - extracts data from DOM via page.evaluate
"""
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import time
import random
import config
from database import SessionLocal, VehicleListing

# JavaScript to extract listings from the page DOM (no API)
EXTRACT_JS = """
() => {
    const results = [];
    const base = 'https://www.sgcarmart.com';
    const seen = new Set();

    function getFullUrl(href) {
        if (!href) return '';
        return href.startsWith('http') ? href : (href.startsWith('/') ? base + href : base + '/' + href);
    }

    function extractPrice(text) {
        // Match price like $78,800 or SGD 80,000
        const match = text.match(/(?:SGD|\\$)\\s*([\\d,]+)/);
        return match ? parseFloat(match[1].replace(/,/g, '')) : null;
    }

    function extractDepreciation(text) {
        // Match depreciation like $15,110 /yr or $15,110/yr
        const match = text.match(/\\$\\s*([\\d,]+)\\s*\\/\\s*yr/i);
        return match ? '$' + match[1] + '/yr' : '';
    }

    function extractRegDate(text) {
        // Match date like 09-Sep-2019 or 14-Jan-2020
        const match = text.match(/(\\d{1,2}[\\-\\/]\\w{3}[\\-\\/]\\d{2,4})/);
        return match ? match[1] : '';
    }

    function extractDealerIdFromUrl(url) {
        // Extract dealer ID from URL parameter ?dl=XXXX or &dl=XXXX
        if (!url) return null;
        const match = url.match(/[?&]dl=(\\d+)/i);
        return match ? match[1] : null;
    }

    function extractDealer(element, carUrl) {
        // Try multiple strategies to find dealer name
        let dealer = '–';
        let dealerId = null;

        // Priority Method: Extract dealer ID from car listing URL
        if (carUrl) {
            dealerId = extractDealerIdFromUrl(carUrl);
        }

        // Method 1: Look for dealer link with DL parameter (most reliable)
        const row = element.closest('tr') || element.closest('div[class*="row"]') || element.closest('article') || element.closest('div[class*="item"]');
        if (row) {
            // Try various dealer link patterns
            const dealerLink = row.querySelector('a[href*="DL="], a[href*="dl="], a[href*="dealer"], a[href*="Dealer"], a[onclick*="dealer"]');
            if (dealerLink) {
                const text = (dealerLink.textContent || '').trim();
                if (text && text.length > 0 && text.length < 100 && !text.includes('$') && !text.includes('Toyota') && !text.includes('Nissan')) {
                    dealer = text;
                }
                // Also try to extract dealer ID from this link
                if (!dealerId) {
                    const href = dealerLink.getAttribute('href') || '';
                    dealerId = extractDealerIdFromUrl(href);
                }
            }
        }

        // Method 2: Look for text patterns "Dealer:", "By:", "Dealer Name:"
        if (dealer === '–') {
            const container = element.closest('div[class*="listing"]') || element.closest('article') || element.closest('tr') || element.closest('div');
            if (container) {
                const text = container.textContent || '';
                // Match various dealer patterns
                const patterns = [
                    /Dealer[:\\s]+([A-Za-z0-9\\s&\\(\\)\\.,-]+?)(?:\\n|\\||$|\\\\|Price|Deprec|COE|OMV|\\d{2}-\\w{3})/i,
                    /By[:\\s]+([A-Za-z0-9\\s&\\(\\)\\.,-]+?)(?:\\n|\\||$|\\\\|Price|Deprec|COE|OMV|\\d{2}-\\w{3})/i,
                    /Dealer Name[:\\s]+([A-Za-z0-9\\s&\\(\\)\\.,-]+?)(?:\\n|\\||$|\\\\|Price|Deprec)/i,
                    /Sold By[:\\s]+([A-Za-z0-9\\s&\\(\\)\\.,-]+?)(?:\\n|\\||$|\\\\|Price|Deprec)/i
                ];
                for (const pattern of patterns) {
                    const match = text.match(pattern);
                    if (match && match[1]) {
                        const d = match[1].trim();
                        if (d.length > 2 && d.length < 80) {
                            dealer = d;
                            break;
                        }
                    }
                }
            }
        }

        // Method 3: Look for elements with dealer-related classes
        if (dealer === '–') {
            const dealerEl = row ? row.querySelector('[class*="dealer"], [class*="Dealer"], [class*="seller"], [class*="Seller"], [data-dealer], [data-seller]') : null;
            if (dealerEl) {
                const text = (dealerEl.textContent || '').trim();
                if (text && text.length > 2 && text.length < 80) {
                    dealer = text.replace(/^(Dealer|By|Seller)[::\s]+/i, '').trim();
                }
            }
        }

        // Method 4: Search in all links within the container
        if (dealer === '–' && row) {
            const allLinks = row.querySelectorAll('a');
            for (const link of allLinks) {
                const href = link.getAttribute('href') || '';
                const text = (link.textContent || '').trim();
                // If link contains DL parameter and text looks like a dealer name
                if (href.includes('DL=') && text.length > 3 && text.length < 80 &&
                    !text.includes('$') && !href.includes('ID=') && !href.includes('info')) {
                    dealer = text;
                    break;
                }
            }
        }

        // Clean up dealer name
        if (dealer !== '–') {
            dealer = dealer
                .replace(/\s+/g, ' ')
                .replace(/^\|+|\|+$/g, '')
                .trim();
            // If it's too short or looks suspicious, reset to '–'
            if (dealer.length < 3 || dealer.length > 80 || /^\\d+$/.test(dealer)) {
                dealer = '–';
            }
        }

        return { dealer: dealer || '–', dealerId: dealerId };
    }

    // Strategy 1: Try modern Next.js structure (cards/articles)
    const articles = document.querySelectorAll('article, div[class*="card"], div[class*="listing"]');
    for (const article of articles) {
        try {
            // Find car detail link
            const link = article.querySelector('a[href*="/used-cars/info/"], a[href*="info.php?ID="]');
            if (!link) continue;

            const href = (link.getAttribute('href') || '').trim();
            if (href.includes('DL=') && !href.includes('ID=') && !href.includes('info')) continue;

            const url = getFullUrl(href);
            if (!url || seen.has(url)) continue;

            // Get car name
            const name = (link.textContent || '').trim();
            if (!name || name.length < 3) continue;

            seen.add(url);

            // Get all text from article
            const text = article.textContent || '';

            // Extract data
            const price = extractPrice(text);
            const depre = extractDepreciation(text);
            const regDate = extractRegDate(text);
            const dealerInfo = extractDealer(article, url);

            // Additional validation: must have at least price or name
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

    // Strategy 2: Fallback to table-based structure (old site)
    if (results.length === 0) {
        const links = document.querySelectorAll('a[href*="info.php?ID="], a[href*="/used-cars/info/"], a[href*="used_cars/info"]');

        for (const a of links) {
            try {
                const href = (a.getAttribute('href') || '').trim();
                if (href.includes('DL=') && !href.includes('ID=')) continue;

                const url = getFullUrl(href);
                if (!url || seen.has(url)) continue;
                seen.add(url);

                const name = (a.textContent || '').trim();
                if (!name || name.length < 3) continue;

                // Get container text for price, depre, reg date
                let container = a.closest('tr') || a.closest('div[class*="row"]') || a.closest('div[class*="listing"]') || a.closest('div') || a.parentElement;
                let text = '';
                for (let i = 0; i < 8 && container; i++) {
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
    args = ["--disable-blink-features=AutomationControlled", "--no-sandbox"]
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
    """Scrape using JavaScript DOM extraction - no API"""

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
        print(f"Starting JS scrape at {datetime.now()}")
        scraped_data = []

        with sync_playwright() as p:
            browser = get_browser(p, headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="en-SG",
                timezone_id="Asia/Singapore",
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-SG,en;q=0.9,id;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"'
                }
            )
            page = context.new_page()

            # Add stealth JavaScript to avoid detection
            page.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

                // Add chrome object
                window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };

                // Randomize plugins to look real
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer'},
                        {name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                        {name: 'Native Client', description: '', filename: 'internal-nacl-plugin'}
                    ]
                });

                // Proper languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-SG', 'en', 'id']
                });

                // Add hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });

                // Add device memory
                Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Mock canvas fingerprinting - add subtle randomness
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                    const shift = Math.random() * 0.0000001;
                    const context = this.getContext('2d');
                    if (context) {
                        const imageData = context.getImageData(0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] += shift;
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                    return originalToDataURL.apply(this, arguments);
                };
            """)

            try:
                # Try multiple URLs to maximize data collection
                urls_to_scrape = [
                    config.COMMERCIAL_LISTING_URL,  # Commercial vehicles (veh=1)
                    f"{config.USED_CARS_URL}?veh=1&limit=200",  # More results
                ]

                for url_idx, url in enumerate(urls_to_scrape):
                    try:
                        print(f"Loading page {url_idx + 1}/{len(urls_to_scrape)}: {url}")

                        # Random delay before loading page (simulate human thinking time)
                        if url_idx > 0:
                            think_time = random.uniform(3.5, 7.2)
                            print(f"  Waiting {think_time:.1f}s before next page...")
                            time.sleep(think_time)

                        page.goto(url, wait_until="domcontentloaded", timeout=60000)

                        # Random initial wait (simulate human reading)
                        initial_wait = random.uniform(4.5, 8.3)
                        print(f"  Reading page content ({initial_wait:.1f}s)...")
                        time.sleep(initial_wait)

                        # Simulate random mouse movements (humans move mouse while browsing)
                        page.evaluate("""
                            () => {
                                const event = new MouseEvent('mousemove', {
                                    clientX: Math.random() * window.innerWidth,
                                    clientY: Math.random() * window.innerHeight
                                });
                                document.dispatchEvent(event);
                            }
                        """)

                        # Natural scrolling behavior - simulate human reading pattern
                        print("Scrolling naturally...")
                        scroll_steps = random.randint(4, 7)
                        for i in range(scroll_steps):
                            # Scroll with slight randomness in position
                            scroll_pos = (i + 1) / scroll_steps
                            jitter = random.uniform(-0.05, 0.05)
                            scroll_fraction = min(1.0, max(0.0, scroll_pos + jitter))

                            # Use smooth scrolling like humans
                            page.evaluate(f"window.scrollTo({{top: document.body.scrollHeight * {scroll_fraction}, behavior: 'smooth'}})")

                            # Random pause at each scroll (simulate reading)
                            scroll_pause = random.uniform(1.8, 4.5)
                            time.sleep(scroll_pause)

                            # Occasionally move mouse (30% chance per scroll)
                            if random.random() < 0.3:
                                page.evaluate("""
                                    () => {
                                        const event = new MouseEvent('mousemove', {
                                            clientX: Math.random() * window.innerWidth,
                                            clientY: Math.random() * window.innerHeight
                                        });
                                        document.dispatchEvent(event);
                                    }
                                """)

                        # Scroll back to top (humans sometimes do this)
                        if random.random() > 0.3:  # 70% chance to scroll back
                            print("  Scrolling back to top...")
                            page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
                            time.sleep(random.uniform(1.5, 3.0))

                        # Wait for any final renders
                        try:
                            page.wait_for_load_state("networkidle", timeout=10000)
                        except:
                            pass

                        # Debug: count links matching our patterns and sample HTML structure
                        debug_info = page.evaluate("""
                            () => {
                                const all = document.querySelectorAll('a[href]');
                                let info = {
                                    info_php: 0,
                                    used_cars_info: 0,
                                    any_info: 0,
                                    articles: 0,
                                    dealer_links: 0,
                                    sampleHrefs: [],
                                    sampleDealerLinks: [],
                                    sampleHTML: ''
                                };

                                all.forEach(a => {
                                    const h = a.getAttribute('href') || '';
                                    if (h.includes('info.php?ID=')) info.info_php++;
                                    if (h.includes('used-cars/info') || h.includes('used_cars/info')) info.used_cars_info++;
                                    if (h.includes('info')) info.any_info++;
                                    if (h.includes('DL=') || h.includes('dealer')) {
                                        info.dealer_links++;
                                        if (info.sampleDealerLinks.length < 3) {
                                            info.sampleDealerLinks.push({
                                                href: h.substring(0, 100),
                                                text: (a.textContent || '').trim().substring(0, 50)
                                            });
                                        }
                                    }
                                    if (info.sampleHrefs.length < 5 && h.includes('info')) {
                                        info.sampleHrefs.push(h.substring(0,80));
                                    }
                                });

                                info.articles = document.querySelectorAll('article, div[class*="card"], div[class*="listing"]').length;

                                // Get sample HTML of first listing
                                const firstListing = document.querySelector('article, div[class*="listing"], tr[class*="row"]');
                                if (firstListing) {
                                    info.sampleHTML = firstListing.outerHTML.substring(0, 500);
                                }

                                return info;
                            }
                        """)
                        print(f"Debug: info_php={debug_info.get('info_php')}, used_cars_info={debug_info.get('used_cars_info')}, articles={debug_info.get('articles')}, dealer_links={debug_info.get('dealer_links')}")
                        if debug_info.get('sampleHrefs'):
                            print("Sample hrefs:", debug_info['sampleHrefs'])
                        if debug_info.get('sampleDealerLinks'):
                            print("Sample dealer links:", debug_info['sampleDealerLinks'])
                        if debug_info.get('sampleHTML'):
                            print(f"Sample HTML structure:\n{debug_info['sampleHTML'][:300]}...")

                        # Extract via JavaScript
                        raw = page.evaluate(EXTRACT_JS)
                        print(f"JS extracted {len(raw)} raw items from page {url_idx + 1}")

                        for item in raw:
                            name = item.get("make_model") or ""
                            if not name or not self.match_target(name):
                                continue

                            # Get dealer name - try to fetch from dealer ID if not found
                            dealer_name = item.get("dealer_name") or "–"
                            dealer_id = item.get("dealer_id")

                            # If dealer name not found but we have dealer ID, try to fetch it
                            if (dealer_name == "–" or len(dealer_name) < 3) and dealer_id:
                                try:
                                    print(f"Fetching dealer info for ID: {dealer_id}")

                                    # Random delay before fetching dealer page (natural behavior)
                                    time.sleep(random.uniform(1.2, 2.8))

                                    dealer_url = f"https://www.sgcarmart.com/dealers/dlrprofile.php?DL={dealer_id}"

                                    # Set referer to simulate clicking from listing page
                                    context.set_extra_http_headers({
                                        **context._options.get("extra_http_headers", {}),
                                        "Referer": url
                                    })

                                    page.goto(dealer_url, wait_until="domcontentloaded", timeout=10000)

                                    # Slightly longer wait for dealer page
                                    time.sleep(random.uniform(1.5, 3.0))

                                    # Extract dealer name from dealer profile page
                                    fetched_dealer = page.evaluate("""
                                        () => {
                                            // Try multiple selectors for dealer name
                                            let name = '';

                                            // Method 1: Look for dealer name in title or h1/h2
                                            const title = document.querySelector('h1, h2, .dealer-name, [class*="dealer"] h1, [class*="dealer"] h2');
                                            if (title) name = (title.textContent || '').trim();

                                            // Method 2: Look in page title
                                            if (!name || name.length < 3) {
                                                const pageTitle = document.title || '';
                                                const match = pageTitle.match(/^([^-|]+)/);
                                                if (match) name = match[1].trim();
                                            }

                                            // Method 3: Look for strong/b tags that might contain dealer name
                                            if (!name || name.length < 3) {
                                                const strongs = document.querySelectorAll('strong, b');
                                                for (const s of strongs) {
                                                    const text = (s.textContent || '').trim();
                                                    if (text.length > 5 && text.length < 60 && !text.includes('$')) {
                                                        name = text;
                                                        break;
                                                    }
                                                }
                                            }

                                            return name;
                                        }
                                    """)

                                    if fetched_dealer and len(fetched_dealer) > 2 and len(fetched_dealer) < 80:
                                        dealer_name = fetched_dealer.strip()
                                        print(f"  → Found dealer: {dealer_name}")
                                    else:
                                        print(f"  → Dealer name not found on profile page")
                                except Exception as e:
                                    print(f"  → Error fetching dealer: {e}")

                            # Create unique item
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
                            # Color-coded logging
                            if dealer_name and dealer_name != "–":
                                print(f"[OK] Scraped: {name} - ${item.get('price')} - Dealer: [{dealer_name}]")
                            else:
                                print(f"[!] Scraped: {name} - ${item.get('price')} - Dealer: [NOT FOUND]")

                    except Exception as e:
                        print(f"Error loading URL {url}: {e}")
                        continue

                # Dedupe by URL
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

                if len(scraped_data) == 0:
                    print("WARNING: 0 listings found!")
                    print("Possible reasons:")
                    print("1. Website structure has changed")
                    print("2. Anti-bot protection is blocking the scraper")
                    print("3. Need to run from Singapore IP")
                    print("Try running with --headed flag to debug: python js_scraper.py --headed")

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
