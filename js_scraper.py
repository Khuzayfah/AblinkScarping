"""
SGCarMart scraper - Updated for new Next.js site structure
Uses undetected-playwright for Cloudflare bypass
Navigates homepage first to establish session, then listing pages
"""
import re
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time
import config
from database import SessionLocal, VehicleListing

logger = logging.getLogger("scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# JavaScript extraction for NEW SGCarMart structure (Next.js)
# Listings are in div[id^="listing_"] containers
EXTRACT_JS = r"""
() => {
    const results = [];
    const base = 'https://www.sgcarmart.com';
    const seen = new Set();

    // Strategy 1: New Next.js listing structure
    // Each listing is in div[id="listing_N"]
    const listings = document.querySelectorAll('[id^="listing_"]');

    for (const listing of listings) {
        try {
            // Skip header row
            if (listing.id === 'listing_search_grey_header') continue;

            // Find the vehicle link
            const link = listing.querySelector('a[href*="used-cars/info"]');
            if (!link) continue;

            const href = (link.getAttribute('href') || '').trim();
            const url = href.startsWith('http') ? href : base + href;

            // Remove tracking params for dedup
            const cleanUrl = url.split('?')[0];
            if (seen.has(cleanUrl)) continue;
            seen.add(cleanUrl);

            // Get vehicle name from the model name element
            const nameEl = listing.querySelector('[class*="model_name"] a, [class*="modelName"] a');
            let name = '';
            if (nameEl) {
                name = nameEl.textContent.trim();
            } else {
                // Fallback: get text from any link with used-cars/info that has text
                const textLinks = listing.querySelectorAll('a[href*="used-cars/info"]');
                for (const tl of textLinks) {
                    const t = tl.textContent.trim();
                    if (t && t.length > 3 && !t.includes('$')) {
                        name = t;
                        break;
                    }
                }
            }
            if (!name || name.length < 3) continue;

            // Extract price from price element
            let price = null;
            const priceEl = listing.querySelector('[class*="price__"], [class*="Price"]');
            if (priceEl) {
                const priceMatch = priceEl.textContent.match(/\$([\d,]+)/);
                if (priceMatch) {
                    price = parseFloat(priceMatch[1].replace(/,/g, ''));
                }
            }
            if (!price) {
                const text = listing.innerText || '';
                const pm = text.match(/\$([\d,]+)/);
                if (pm) price = parseFloat(pm[1].replace(/,/g, ''));
            }

            // Extract depreciation
            let depreciation = '';
            const depEl = listing.querySelector('[class*="depreciation_text"], [class*="depreciationText"]');
            if (depEl) {
                depreciation = depEl.textContent.trim();
            }
            if (!depreciation) {
                const text = listing.innerText || '';
                const dm = text.match(/\$([\d,]+)\s*\/\s*yr/i);
                if (dm) depreciation = '$' + dm[1] + '/yr';
            }

            // Extract reg date
            let regDate = '';
            const regEl = listing.querySelector('[class*="reg_date_te"], [class*="regDate"]');
            if (regEl) {
                const rdm = regEl.textContent.match(/(\d{1,2}-[A-Z][a-z]{2}-\d{4})/);
                if (rdm) regDate = rdm[1];
            }
            if (!regDate) {
                const text = listing.innerText || '';
                const rdm = text.match(/(\d{1,2}-[A-Z][a-z]{2}-\d{4})/);
                if (rdm) regDate = rdm[1];
            }

            // Extract dealer from tag element or listing text
            let dealer = '';
            const tagEl = listing.querySelector('[class*="car_tag"], [class*="carTag"]');
            if (tagEl) {
                const tagText = tagEl.textContent.trim();
                if (tagText === 'Direct Owner') {
                    dealer = 'Direct Owner';
                } else if (tagText === 'Premium Ad' || tagText === 'PREMIUM AD') {
                    dealer = '';  // Will be fetched from detail page
                } else if (tagText.length > 2 && tagText.length < 100) {
                    dealer = tagText;
                }
            }

            // Extract dealer ID from URL
            let dealerId = null;
            const dlMatch = href.match(/[?&]dl=(\d+)/i);
            if (dlMatch) dealerId = dlMatch[1];

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

    // Strategy 2: Fallback for old structure or search results
    if (results.length === 0) {
        const links = document.querySelectorAll('a[href*="used-cars/info/"], a[href*="info.php?ID="]');
        for (const a of links) {
            try {
                const href = (a.getAttribute('href') || '').trim();
                const url = href.startsWith('http') ? href : base + href;
                const cleanUrl = url.split('?')[0];
                if (seen.has(cleanUrl)) continue;
                seen.add(cleanUrl);

                const name = (a.textContent || '').trim();
                if (!name || name.length < 3 || name.includes('$')) continue;

                let text = '';
                let container = a.closest('div[class*="listing"]') || a.closest('tr') || a.closest('div');
                for (let i = 0; i < 5 && container; i++) {
                    text += ' ' + (container.textContent || '');
                    container = container.parentElement;
                }

                let price = null;
                const pm = text.match(/\$([\d,]+)/);
                if (pm) price = parseFloat(pm[1].replace(/,/g, ''));

                let depreciation = '';
                const dm = text.match(/\$([\d,]+)\s*\/\s*yr/i);
                if (dm) depreciation = '$' + dm[1] + '/yr';

                let regDate = '';
                const rdm = text.match(/(\d{1,2}-[A-Z][a-z]{2}-\d{4})/);
                if (rdm) regDate = rdm[1];

                let dealerId = null;
                const dlMatch = href.match(/[?&]dl=(\d+)/i);
                if (dlMatch) dealerId = dlMatch[1];

                results.push({
                    make_model: name,
                    price: price,
                    depreciation: depreciation,
                    reg_date: regDate,
                    dealer_name: '',
                    dealer_id: dealerId,
                    listing_url: url
                });
            } catch (e) {}
        }
    }

    return results;
}
"""

# Detail page extraction JS (for dealer name and depreciation)
DETAIL_EXTRACT_JS = r"""
() => {
    const bodyText = document.body.textContent || '';
    const pageTitle = document.title || '';

    // Extract depreciation
    let depreciation = '';
    // Method 1: From depreciation element (new site)
    const depEl = document.querySelector('[class*="depreciation_text"], [class*="depreciationText"], [class*="depreciation"]');
    if (depEl) {
        const dm = depEl.textContent.match(/\$([\d,]+)\s*\/\s*yr/i);
        if (dm) depreciation = '$' + dm[1] + '/yr';
    }
    // Method 2: Near "Depreciation" label
    if (!depreciation) {
        const dm = bodyText.match(/Depreciation[^\$]*\$([\d,]+)\s*\/\s*yr/i);
        if (dm) depreciation = '$' + dm[1] + '/yr';
    }
    // Method 3: First match in body
    if (!depreciation) {
        const dm = bodyText.match(/\$([\d,]+)\s*\/\s*yr/i);
        if (dm) depreciation = '$' + dm[1] + '/yr';
    }

    // Extract dealer name
    let dealer = '';

    // Method 1: From page title - "Used 2019 Toyota Hiace for Sale | Dealer - Sgcarmart"
    const titleMatch = pageTitle.match(/\|\s*(.+?)\s*-\s*Sgcarmart/i);
    if (titleMatch) {
        dealer = titleMatch[1].trim();
    }

    // Method 2: Check for Direct Owner tag
    if (!dealer || dealer.length < 3) {
        const tagEl = document.querySelector('[class*="car_tag"], [class*="carTag"]');
        if (tagEl && tagEl.textContent.trim().toLowerCase().includes('direct owner')) {
            dealer = 'Direct Owner';
        }
    }

    // Method 3: Dealer link
    if (!dealer || dealer.length < 3) {
        const dealerLinks = document.querySelectorAll('a[href*="DL="], a[href*="dl="]');
        for (const link of dealerLinks) {
            const text = (link.textContent || '').trim();
            if (text && text.length > 3 && text.length < 100 &&
                !text.includes('Printable') && !text.includes('Version') &&
                !text.includes('Search') && !text.includes('$')) {
                dealer = text;
                break;
            }
        }
    }

    // Clean dealer name
    if (dealer) {
        dealer = dealer.replace(/\s+/g, ' ').trim();
        dealer = dealer.replace(/\s*Pte\.?\s*Ltd\.?.*$/i, ' Pte Ltd').trim();
        dealer = dealer.replace(/[,;.\s]+$/, '').trim();
        if (dealer.length > 80) dealer = dealer.substring(0, 80).trim();
    }

    return {depreciation, dealer};
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


def wait_for_cloudflare(page, timeout=30):
    """Wait for Cloudflare challenge to resolve."""
    for i in range(timeout // 3):
        title = page.title()
        body_text = page.evaluate("() => (document.body ? document.body.textContent : '').substring(0, 200)")
        if 'moment' not in title.lower() and 'Verifying you are human' not in body_text:
            return True
        logger.info(f"  Cloudflare challenge active, waiting... ({i*3}s)")
        time.sleep(3)
    return False


class SGCarMartJSScraper:
    """SGCarMart scraper with Cloudflare bypass - updated for Next.js site"""

    def __init__(self, headless=True):
        self.url = config.COMMERCIAL_LISTING_URL
        self.target_vehicles = config.TARGET_VEHICLES
        self.headless = headless

    def normalize(self, s):
        return re.sub(r'\s+', ' ', (s or '').upper().strip())

    def match_target(self, name):
        n = self.normalize(name)
        # Check exact target vehicles
        if any(self.normalize(t) in n or n in self.normalize(t) for t in self.target_vehicles):
            return True
        # Also match commercial vehicle brands/models (specific matching)
        # These keywords must appear with their brand context to avoid false positives
        commercial_keywords = [
            'HIACE', 'HINO', 'DYNA', 'DUTRO', 'CABSTAR',
            'NV350', 'NV200', 'N-VAN',
            'ISUZU NPR', 'ISUZU NMR', 'ISUZU NNR', 'ISUZU NHR', 'ISUZU NJR',
            'MITSUBISHI FEA', 'KIA 2500', 'KIA K2500'
        ]
        return any(keyword in n for keyword in commercial_keywords)

    def _navigate_with_cf_bypass(self, page, url, max_retries=2):
        """Navigate to URL with Cloudflare bypass. Returns True if successful."""
        for attempt in range(max_retries):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                title = page.title()
                if 'moment' in title.lower() or title == '':
                    logger.info(f"  Cloudflare challenge detected (attempt {attempt+1})")
                    if wait_for_cloudflare(page, timeout=30):
                        return True
                    # Go back to homepage and try again
                    if attempt < max_retries - 1:
                        logger.info("  Retrying via homepage...")
                        page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded", timeout=30000)
                        time.sleep(5)
                        continue
                    return False
                return True
            except Exception as e:
                logger.error(f"  Navigation error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return False
        return False

    def scrape_vehicle_listings(self):
        logger.info(f"Starting scrape at {datetime.now()}")
        logger.info("Using undetected-playwright for Cloudflare bypass...")
        scraped_data = []

        with sync_playwright() as p:
            logger.info("[1/4] Launching browser...")
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu'
                ]
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="en-SG"
            )
            page = context.new_page()

            logger.info("  Applying stealth mode...")
            stealth_sync(page)

            try:
                # Step 1: Homepage first (CRITICAL for Cloudflare bypass)
                logger.info("[2/4] Loading homepage (establish session)...")
                page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)

                title1 = page.title()
                if 'moment' in title1.lower():
                    logger.warning("  Homepage blocked by Cloudflare - waiting...")
                    if not wait_for_cloudflare(page):
                        logger.error("  FAILED: Cannot bypass Cloudflare on homepage")
                        return []
                    title1 = page.title()

                logger.info(f"  OK Homepage: {title1[:50]}")

                # Step 2: Navigate to listing page with commercial vehicles
                logger.info("[3/4] Loading commercial vehicle listings...")

                # Try the listing page first (all used cars)
                all_raw_items = []

                # Approach: Use listing page with pagination
                # The listing page shows 20 items per page by default
                listing_url = "https://www.sgcarmart.com/used-cars/listing"
                if not self._navigate_with_cf_bypass(page, listing_url):
                    logger.error("  FAILED: Cannot access listing page")
                    # Fallback: try search approach
                    logger.info("  Falling back to search approach...")
                    all_raw_items = self._search_approach(page)
                else:
                    page_title = page.title()
                    logger.info(f"  OK Listing page: {page_title[:60]}")

                    # Extract from listing page - first check total count
                    total_text = page.evaluate("() => document.body.innerText.match(/(\\d[\\d,]*)\\s*Vehicle/)?.[1] || '0'")
                    logger.info(f"  Total vehicles on site: {total_text}")

                    # Extract from current page
                    time.sleep(3)
                    raw = page.evaluate(EXTRACT_JS)
                    logger.info(f"  Page 1: extracted {len(raw)} items")
                    all_raw_items.extend(raw)

                    # Click through pages to find commercial vehicles
                    # Pagination: click "Next" button
                    max_pages = 50  # Limit to avoid infinite loop
                    for page_num in range(2, max_pages + 1):
                        # Check if we have enough target vehicles
                        target_count = sum(1 for item in all_raw_items if self.match_target(item.get("make_model", "")))
                        if target_count >= 100:
                            logger.info(f"  Found {target_count} target vehicles, stopping pagination")
                            break

                        try:
                            # Click "Next" button
                            next_btn = page.query_selector('button:has-text("Next")')
                            if not next_btn:
                                logger.info(f"  No 'Next' button found, stopping at page {page_num - 1}")
                                break

                            next_btn.click()
                            time.sleep(4)

                            # Check if page changed (new listings loaded)
                            raw = page.evaluate(EXTRACT_JS)
                            if not raw:
                                logger.info(f"  Page {page_num}: no items, stopping")
                                break

                            new_count = len(raw)
                            new_targets = sum(1 for item in raw if self.match_target(item.get("make_model", "")))
                            all_raw_items.extend(raw)
                            logger.info(f"  Page {page_num}: {new_count} items ({new_targets} targets)")

                        except Exception as e:
                            logger.error(f"  Page {page_num} error: {e}")
                            break

                    # If not enough targets found via listing, also try search
                    target_count = sum(1 for item in all_raw_items if self.match_target(item.get("make_model", "")))
                    if target_count < 5:
                        logger.info(f"  Only {target_count} targets from listing pages. Trying search approach...")
                        search_items = self._search_approach(page)
                        all_raw_items.extend(search_items)

                # Step 3: Process all extracted items
                logger.info(f"[4/4] Processing {len(all_raw_items)} total items...")

                for idx, item in enumerate(all_raw_items):
                    name = item.get("make_model") or ""
                    if not name:
                        continue

                    if idx < 5:
                        logger.info(f"    Item {idx+1}: {name[:60]}")

                    if not self.match_target(name):
                        continue

                    dealer_name = item.get("dealer_name") or ""
                    dealer_id = item.get("dealer_id")
                    depreciation = item.get("depreciation") or ""
                    listing_url = item.get("listing_url") or ""

                    # Skip rental/lease listings
                    if "/car_rental/" in listing_url:
                        logger.info(f"  [SKIP] Rental: {name[:50]}")
                        continue

                    # If dealer or depreciation missing, fetch from detail page
                    if (not dealer_name or dealer_name == "–" or not depreciation) and listing_url:
                        try:
                            # Remove tracking params
                            clean_url = listing_url.split('?')[0]
                            logger.info(f"    Fetching details: {clean_url[-50:]}...")
                            time.sleep(1)

                            if self._navigate_with_cf_bypass(page, clean_url):
                                time.sleep(2)
                                details = page.evaluate(DETAIL_EXTRACT_JS)

                                if details.get('depreciation'):
                                    depreciation = details['depreciation']
                                if details.get('dealer') and len(details['dealer']) > 2:
                                    dealer_name = details['dealer']
                                    logger.info(f"      OK Dealer: {dealer_name}, Deprec: {depreciation}")
                            else:
                                logger.warning(f"      Cannot access detail page")
                        except Exception as e:
                            logger.error(f"      Detail error: {e}")

                    if not dealer_name:
                        dealer_name = "–"

                    scraped_data.append({
                        "make_model": name,
                        "registered_year": extract_year(item.get("reg_date")),
                        "depreciation": depreciation,
                        "dealer_name": dealer_name,
                        "price": item.get("price"),
                        "listing_url": listing_url,
                        "additional_info": item.get("reg_date") or "",
                    })

                    status = "OK" if dealer_name != "–" else "!"
                    logger.info(f"  [{status}] {name} - ${item.get('price')} - {dealer_name}")

                # Dedupe by listing URL
                seen = set()
                unique = []
                for item in scraped_data:
                    key = (item.get("listing_url") or "").split('?')[0]
                    if not key:
                        key = f"{item.get('make_model', '')}_{item.get('price', 0)}"
                    if key and key not in seen:
                        seen.add(key)
                        unique.append(item)
                scraped_data = unique

                logger.info(f"{'='*60}")
                logger.info(f"[SUCCESS] Total target vehicles found: {len(scraped_data)}")
                logger.info(f"{'='*60}")

            except Exception as e:
                logger.error(f"Error during scraping: {e}")
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
                logger.error(f"Sold log failed: {e}")

        return scraped_data

    def _search_approach(self, page):
        """Fallback: search for each vehicle keyword individually."""
        logger.info("  Using search-by-keyword approach...")
        all_items = []

        search_keywords = [
            "Toyota Hiace",
            "Hino Dutro",
            "Toyota Dyna",
            "Nissan NV350",
            "Nissan NV200",
            "Nissan Cabstar",
            "Isuzu NPR",
            "Isuzu NMR",
            "Honda N-VAN"
        ]

        for keyword in search_keywords:
            try:
                logger.info(f"  Searching: {keyword}")

                # Navigate back to homepage first to maintain session
                page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                # Then go to search/listing
                search_url = f"https://www.sgcarmart.com/search?q={keyword.replace(' ', '+')}"
                if not self._navigate_with_cf_bypass(page, search_url):
                    # Try listing page as fallback
                    logger.info(f"    Search blocked, trying listing page...")
                    listing_url = f"https://www.sgcarmart.com/used-cars/listing"
                    if not self._navigate_with_cf_bypass(page, listing_url):
                        logger.warning(f"    Cannot access any listing page for {keyword}")
                        continue
                    time.sleep(3)

                time.sleep(3)

                # Extract
                raw = page.evaluate(EXTRACT_JS)
                target_count = sum(1 for item in raw if self.match_target(item.get("make_model", "")))
                logger.info(f"    Extracted {len(raw)} items ({target_count} targets)")
                all_items.extend(raw)

            except Exception as e:
                logger.error(f"    Search error for {keyword}: {e}")
                continue

        return all_items

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
            logger.info(f"[OK] Saved {len(data)} listings to database")
        except Exception as e:
            logger.error(f"Error saving: {e}")
            db.rollback()
        finally:
            db.close()


if __name__ == "__main__":
    import sys
    headless = "--headed" not in sys.argv
    scraper = SGCarMartJSScraper(headless=headless)
    scraper.scrape_vehicle_listings()
