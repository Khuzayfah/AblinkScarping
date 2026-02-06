"""
SGCarMart scraper - Uses curl_cffi for Cloudflare bypass
Extracts vehicle data from Next.js RSC payload (no browser needed)
Falls back to Playwright if curl_cffi fails
"""
import re
import logging
import math
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import config
from database import SessionLocal, VehicleListing, SoldLog

logger = logging.getLogger("scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Escaped quote used in Next.js RSC payload
BQ = '\\"'

# Search keywords for commercial vehicles
SEARCH_KEYWORDS = [
    "Toyota Hiace",
    "Hino Dutro",
    "Hino XZU",
    "Toyota Dyna",
    "Nissan NV350",
    "Nissan NV200",
    "Nissan Cabstar",
    "Isuzu NPR",
    "Isuzu NMR",
    "Isuzu NNR",
    "Isuzu NHR",
    "Honda N-VAN",
    "Mitsubishi Fuso",
    "Mitsubishi FEA",
    "Kia K2500",
]


def extract_year(reg_date: Optional[str]) -> Optional[int]:
    """Extract year from registration date string like '08-Dec-2017'."""
    if not reg_date:
        return None
    m = re.search(r'(\d{4})', reg_date)
    if m:
        return int(m.group(1))
    m = re.search(r'\d{1,2}-\w{3}-(\d{2})', reg_date)
    if m:
        y = int(m.group(1))
        return 2000 + y if y < 50 else 1900 + y
    return None


def _extract_rsc_str(text: str, field: str, start: int, end: int) -> Optional[str]:
    """Extract a string field value from RSC payload text."""
    prefix = BQ + field + BQ + ':' + BQ
    idx = text.find(prefix, start, end)
    if idx < 0:
        return None
    val_start = idx + len(prefix)
    val_end = text.find(BQ, val_start)
    if val_end < 0 or val_end > end:
        return None
    return text[val_start:val_end]


def _extract_rsc_num(text: str, field: str, start: int, end: int) -> Optional[int]:
    """Extract a numeric field value from RSC payload text."""
    prefix = BQ + field + BQ + ':'
    idx = text.find(prefix, start, end)
    if idx < 0:
        return None
    val_start = idx + len(prefix)
    digits = ''
    for c in text[val_start:val_start + 20]:
        if c.isdigit():
            digits += c
        else:
            break
    return int(digits) if digits else None


def _extract_rsc_nullable(text: str, field: str, start: int, end: int) -> Optional[str]:
    """Extract a field that might be null."""
    prefix = BQ + field + BQ + ':'
    idx = text.find(prefix, start, end)
    if idx < 0:
        return None
    val_start = idx + len(prefix)
    # Check if null
    if text[val_start:val_start + 4] == 'null':
        return None
    # Check if string
    if text[val_start:val_start + 1] == BQ[0] and text[val_start + 1:val_start + 2] == BQ[1]:
        actual_start = val_start + 2
        val_end = text.find(BQ, actual_start)
        if val_end >= 0 and val_end <= end:
            return text[actual_start:val_end]
    return None


def _build_dealer_map(text: str) -> Dict[int, str]:
    """Build dealer code -> dealer name mapping from RSC payload.

    The RSC payload contains dealer data in format:
    \\"value\\":CODE,\\"text\\":\\"NAME\\"

    We filter out non-dealer entries (price ranges etc).
    """
    dealer_map = {}
    pos = 0
    prefix = BQ + 'value' + BQ + ':'
    text_prefix = BQ + 'text' + BQ + ':' + BQ

    while True:
        idx = text.find(prefix, pos)
        if idx < 0:
            break

        # Extract the numeric value
        val_start = idx + len(prefix)
        digits = ''
        for c in text[val_start:val_start + 10]:
            if c.isdigit():
                digits += c
            else:
                break

        if not digits:
            pos = idx + 10
            continue

        code = int(digits)

        # Extract the text value
        text_idx = text.find(text_prefix, val_start, val_start + 100)
        if text_idx >= 0:
            name_start = text_idx + len(text_prefix)
            name_end = text.find(BQ, name_start)
            if name_end >= 0:
                name = text[name_start:name_end]
                # Filter: real dealers have names without $ and with letters
                if name and not name.startswith('$') and any(c.isalpha() for c in name) and code > 0:
                    dealer_map[code] = name

        pos = idx + 10

    return dealer_map


def _extract_listings_from_rsc(text: str) -> Tuple[List[Dict[str, Any]], Dict[int, str]]:
    """Extract all vehicle listings from Next.js RSC payload.

    Returns (listings, dealer_map)
    """
    # Build dealer name mapping
    dealer_map = _build_dealer_map(text)

    # Find each listing by looking for link field with sgcarmart info URL
    link_prefix = BQ + 'link' + BQ + ':' + BQ + 'https://www.sgcarmart.com/used-cars/info/'

    listings = []
    seen_urls = set()
    pos = 0

    while True:
        idx = text.find(link_prefix, pos)
        if idx < 0:
            break

        # Define block boundaries for this listing (look back and forward)
        block_start = max(0, idx - 100)
        block_end = min(len(text), idx + 2000)

        # Extract all fields
        link = _extract_rsc_str(text, 'link', block_start, block_end)
        car_model = _extract_rsc_str(text, 'car_model', block_start, block_end)
        reg_date = _extract_rsc_str(text, 'registration_date', block_start, block_end)
        price = _extract_rsc_num(text, 'price', block_start, block_end)
        depreciation = _extract_rsc_num(text, 'depreciation', block_start, block_end)
        dealer_code = _extract_rsc_num(text, 'dealer_code', block_start, block_end)
        listing_id = _extract_rsc_num(text, 'id', block_start, block_end)

        # Skip invalid entries (script tags, broken data)
        if car_model and not any(s in car_model for s in ['</', 'script', 'self.', '__next']):
            # Dedup by URL
            clean_url = (link or '').split('?')[0]
            if clean_url and clean_url not in seen_urls:
                seen_urls.add(clean_url)

                # Get dealer name from map
                dealer_name = ''
                if dealer_code:
                    dealer_name = dealer_map.get(dealer_code, '')

                listings.append({
                    'id': listing_id,
                    'car_model': car_model,
                    'price': price,
                    'depreciation': depreciation,
                    'registration_date': reg_date,
                    'dealer_code': dealer_code,
                    'dealer_name': dealer_name,
                    'link': link,
                })

        pos = idx + 100

    return listings, dealer_map


def _extract_total_from_rsc(text: str) -> int:
    """Extract total result count from RSC payload."""
    # Look for \"total\":NUMBER pattern
    prefix = BQ + 'total' + BQ + ':'
    idx = text.find(prefix)
    if idx >= 0:
        val_start = idx + len(prefix)
        digits = ''
        for c in text[val_start:val_start + 10]:
            if c.isdigit():
                digits += c
            else:
                break
        if digits:
            return int(digits)
    return 0


class SGCarMartJSScraper:
    """SGCarMart scraper using curl_cffi for Cloudflare bypass."""

    def __init__(self, headless=True):
        self.url = config.COMMERCIAL_LISTING_URL
        self.target_vehicles = config.TARGET_VEHICLES
        self.headless = headless

    def normalize(self, s: str) -> str:
        return re.sub(r'\s+', ' ', (s or '').upper().strip())

    def match_target(self, name: str) -> bool:
        """Check if a vehicle name matches our target commercial vehicles.

        Only matches vehicles from the target list:
        HINO DUTRO, HINO XZU710, TOYOTA DYNA, TOYOTA HIACE,
        NISSAN CABSTAR, NISSAN NV350, NISSAN NV200,
        ISUZU NHR/NJR/NPR/NMR/NNR, MITSUBISHI FEA, KIA 2500,
        HONDA N-VAN
        """
        n = self.normalize(name)
        if not n:
            return False

        # Check exact target vehicles
        if any(self.normalize(t) in n or n in self.normalize(t) for t in self.target_vehicles):
            return True

        # Check brand+model commercial vehicle keywords
        # Each keyword requires BOTH the brand AND model to be present
        brand_model_rules = [
            # (brand, model_keywords) - brand AND at least one model keyword must match
            ('TOYOTA', ['HIACE', 'DYNA']),
            ('HINO', ['DUTRO', 'XZU']),
            ('NISSAN', ['CABSTAR', 'NV350', 'NV200']),
            ('ISUZU', ['NPR', 'NMR', 'NNR', 'NHR', 'NJR']),
            ('MITSUBISHI', ['FEA']),
            ('KIA', ['2500', 'K2500']),
            ('HONDA', ['N-VAN']),
        ]

        for brand, models in brand_model_rules:
            if brand in n:
                for model in models:
                    if model in n:
                        return True

        return False

    def _fetch_page(self, session, url: str, description: str = '') -> Optional[str]:
        """Fetch a page with curl_cffi, handling errors."""
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                # Check for Cloudflare challenge
                if 'Just a moment' in r.text[:500] or 'Verifying you are human' in r.text[:500]:
                    logger.warning(f"  Cloudflare challenge on {description}")
                    return None
                return r.text
            else:
                logger.warning(f"  HTTP {r.status_code} on {description}")
                return None
        except Exception as e:
            logger.error(f"  Fetch error on {description}: {e}")
            return None

    def _scrape_search_keyword(self, session, keyword: str, dealer_map: Dict[int, str]) -> List[Dict[str, Any]]:
        """Search for a specific keyword and extract all pages of results."""
        all_listings = []
        query = keyword.replace(' ', '+')

        # First page with limit=100
        url = f"https://www.sgcarmart.com/used-cars/listing?q={query}&limit=100"
        logger.info(f"  Searching: {keyword}")

        text = self._fetch_page(session, url, f"search '{keyword}' page 1")
        if not text:
            return []

        # Extract listings
        listings, page_dealer_map = _extract_listings_from_rsc(text)
        dealer_map.update(page_dealer_map)

        # Update dealer names for listings
        for l in listings:
            if l['dealer_code'] and not l['dealer_name']:
                l['dealer_name'] = dealer_map.get(l['dealer_code'], '')

        all_listings.extend(listings)

        # Check total and paginate if needed
        total = _extract_total_from_rsc(text)
        if total > 0 and len(listings) > 0:
            total_pages = math.ceil(total / max(len(listings), 1))
            total_pages = min(total_pages, 10)  # Max 10 pages per keyword

            target_in_page = sum(1 for l in listings if self.match_target(l['car_model']))
            logger.info(f"    Page 1: {len(listings)} listings ({target_in_page} targets), total: {total}")

            for page_num in range(2, total_pages + 1):
                time.sleep(2)  # Be polite
                page_url = f"https://www.sgcarmart.com/used-cars/listing?q={query}&limit=100&page={page_num}"
                page_text = self._fetch_page(session, page_url, f"search '{keyword}' page {page_num}")
                if not page_text:
                    break

                page_listings, pg_dm = _extract_listings_from_rsc(page_text)
                dealer_map.update(pg_dm)
                for l in page_listings:
                    if l['dealer_code'] and not l['dealer_name']:
                        l['dealer_name'] = dealer_map.get(l['dealer_code'], '')

                target_count = sum(1 for l in page_listings if self.match_target(l['car_model']))
                logger.info(f"    Page {page_num}: {len(page_listings)} listings ({target_count} targets)")
                all_listings.extend(page_listings)

                if len(page_listings) == 0:
                    break
        else:
            target_in_page = sum(1 for l in listings if self.match_target(l['car_model']))
            logger.info(f"    Got {len(listings)} listings ({target_in_page} targets)")

        return all_listings

    def _fetch_detail_page_dealer(self, session, url: str, dealer_map: Dict[int, str]) -> Tuple[str, str]:
        """Fetch detail page to get dealer name and depreciation if missing."""
        try:
            text = self._fetch_page(session, url, "detail page")
            if not text:
                return '', ''

            # Extract dealer from page title: "Used 2019 Toyota Hiace for Sale | DEALER - Sgcarmart"
            title_match = re.search(r'<title>([^<]+)</title>', text)
            dealer = ''
            if title_match:
                title = title_match.group(1)
                m = re.search(r'\|\s*(.+?)\s*-\s*Sgcarmart', title, re.IGNORECASE)
                if m:
                    dealer = m.group(1).strip()

            # Extract depreciation
            dep = ''
            dep_match = re.search(r'\$\s*([\d,]+)\s*/\s*yr', text)
            if dep_match:
                dep = '$' + dep_match.group(1) + '/yr'

            return dealer, dep
        except Exception as e:
            logger.error(f"    Detail page error: {e}")
            return '', ''

    def scrape_vehicle_listings(self) -> List[Dict[str, Any]]:
        """Main scraping method using curl_cffi for Cloudflare bypass."""
        logger.info(f"Starting scrape at {datetime.now()}")
        logger.info("Using curl_cffi with Chrome impersonation for Cloudflare bypass...")

        try:
            from curl_cffi import requests as curl_requests
        except ImportError:
            logger.error("curl_cffi not installed! Run: pip install curl_cffi")
            logger.info("Falling back to Playwright...")
            return self._fallback_playwright_scrape()

        scraped_data = []
        global_dealer_map = {}

        try:
            session = curl_requests.Session(impersonate='chrome')

            # Step 1: Establish session via homepage
            logger.info("[1/4] Loading homepage (establish session)...")
            homepage_text = self._fetch_page(session, "https://www.sgcarmart.com", "homepage")
            if not homepage_text:
                logger.error("  FAILED: Cannot access homepage")
                logger.info("  Falling back to Playwright...")
                return self._fallback_playwright_scrape()

            logger.info("  OK Homepage loaded")
            time.sleep(1)

            # Step 2: Try commercial vehicle listing page first
            logger.info("[2/4] Loading commercial vehicle listings...")
            listing_url = "https://www.sgcarmart.com/used-cars/listing?veh=1&limit=100"
            listing_text = self._fetch_page(session, listing_url, "commercial listing")

            all_raw_items = []

            if listing_text:
                listings, dealer_map = _extract_listings_from_rsc(listing_text)
                global_dealer_map.update(dealer_map)
                total = _extract_total_from_rsc(listing_text)
                target_count = sum(1 for l in listings if self.match_target(l['car_model']))
                logger.info(f"  Listing page: {len(listings)} items ({target_count} targets), total on site: {total}")
                all_raw_items.extend(listings)

                # Paginate if there are more
                if total > len(listings):
                    pages_needed = min(math.ceil(total / max(len(listings), 1)), 20)
                    for page_num in range(2, pages_needed + 1):
                        time.sleep(2)
                        page_url = f"https://www.sgcarmart.com/used-cars/listing?veh=1&limit=100&page={page_num}"
                        page_text = self._fetch_page(session, page_url, f"listing page {page_num}")
                        if not page_text:
                            break
                        page_listings, pg_dm = _extract_listings_from_rsc(page_text)
                        global_dealer_map.update(pg_dm)
                        new_targets = sum(1 for l in page_listings if self.match_target(l['car_model']))
                        logger.info(f"  Page {page_num}: {len(page_listings)} items ({new_targets} targets)")
                        all_raw_items.extend(page_listings)
                        if len(page_listings) == 0:
                            break

            # Step 3: Search by keyword for each vehicle type
            logger.info("[3/4] Searching by keyword for commercial vehicles...")
            seen_urls = {(l.get('link', '').split('?')[0]) for l in all_raw_items if l.get('link')}

            for keyword in SEARCH_KEYWORDS:
                time.sleep(1.5)  # Rate limiting
                keyword_items = self._scrape_search_keyword(session, keyword, global_dealer_map)

                # Add only new items
                new_count = 0
                for item in keyword_items:
                    clean_url = (item.get('link', '').split('?')[0])
                    if clean_url and clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        all_raw_items.append(item)
                        new_count += 1

                if new_count > 0:
                    logger.info(f"    +{new_count} new items from '{keyword}'")

            # Step 4: Process and filter target vehicles
            logger.info(f"[4/4] Processing {len(all_raw_items)} total items...")

            for item in all_raw_items:
                name = item.get('car_model', '')
                if not name or not self.match_target(name):
                    continue

                link = item.get('link', '')
                dealer_name = item.get('dealer_name', '')
                dealer_code = item.get('dealer_code')
                depreciation = item.get('depreciation')
                reg_date = item.get('registration_date', '')

                # Format depreciation
                dep_str = ''
                if depreciation is not None:
                    dep_str = f"${depreciation:,}/yr"

                # If dealer name is missing, try to get from dealer map or detail page
                if not dealer_name and dealer_code:
                    dealer_name = global_dealer_map.get(dealer_code, '')

                if not dealer_name and link:
                    # Fetch detail page for dealer name (with rate limiting)
                    time.sleep(1)
                    detail_dealer, detail_dep = self._fetch_detail_page_dealer(session, link, global_dealer_map)
                    if detail_dealer:
                        dealer_name = detail_dealer
                        logger.info(f"    Detail: {name[:40]} -> Dealer: {dealer_name}")
                    if detail_dep and not dep_str:
                        dep_str = detail_dep

                # Skip rental listings
                if '/car_rental/' in link:
                    continue

                if not dealer_name:
                    dealer_name = '–'

                scraped_data.append({
                    'make_model': name,
                    'registered_year': extract_year(reg_date),
                    'depreciation': dep_str,
                    'dealer_name': dealer_name,
                    'price': item.get('price'),
                    'listing_url': link,
                    'additional_info': reg_date or '',
                })

                status = "OK" if dealer_name != '–' else "!"
                logger.info(f"  [{status}] {name} - ${item.get('price')} - {dep_str} - {dealer_name}")

            # Deduplicate by listing URL
            seen = set()
            unique = []
            for item in scraped_data:
                key = (item.get('listing_url', '').split('?')[0])
                if not key:
                    key = f"{item.get('make_model', '')}_{item.get('price', 0)}"
                if key and key not in seen:
                    seen.add(key)
                    unique.append(item)
            scraped_data = unique

            logger.info("=" * 60)
            logger.info(f"[SUCCESS] Total target vehicles found: {len(scraped_data)}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()

        if scraped_data:
            self._save_to_db(scraped_data)

        return scraped_data

    def scrape_sold_listings(self) -> List[Dict[str, Any]]:
        """Scrape SOLD vehicle listings from SGCarMart (avl=s parameter)."""
        logger.info(f"Starting SOLD scrape at {datetime.now()}")

        try:
            from curl_cffi import requests as curl_requests
        except ImportError:
            logger.error("curl_cffi not installed!")
            return []

        sold_data = []
        global_dealer_map = {}

        try:
            session = curl_requests.Session(impersonate='chrome')

            # Establish session
            logger.info("[1/3] Loading homepage (establish session)...")
            homepage_text = self._fetch_page(session, "https://www.sgcarmart.com", "homepage")
            if not homepage_text:
                logger.error("  FAILED: Cannot access homepage")
                return []
            logger.info("  OK Homepage loaded")
            time.sleep(1)

            # Search sold listings per keyword
            logger.info("[2/3] Searching SOLD listings by keyword...")
            seen_urls = set()

            for keyword in SEARCH_KEYWORDS:
                time.sleep(1.5)
                query = keyword.replace(' ', '+')
                url = f"https://www.sgcarmart.com/used-cars/listing?q={query}&avl=s&limit=100"
                logger.info(f"  Searching SOLD: {keyword}")

                text = self._fetch_page(session, url, f"sold '{keyword}' page 1")
                if not text:
                    continue

                listings, dealer_map = _extract_listings_from_rsc(text)
                global_dealer_map.update(dealer_map)

                # Update dealer names
                for l in listings:
                    if l['dealer_code'] and not l['dealer_name']:
                        l['dealer_name'] = global_dealer_map.get(l['dealer_code'], '')

                target_count = sum(1 for l in listings if self.match_target(l.get('car_model', '')))
                total = _extract_total_from_rsc(text)
                logger.info(f"    Found {len(listings)} sold ({target_count} targets), total: {total}")

                # Add only new target items
                for item in listings:
                    clean_url = (item.get('link', '').split('?')[0])
                    if clean_url and clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        name = item.get('car_model', '')
                        if name and self.match_target(name):
                            # Paginate if more results
                            sold_data.append(item)

                # Paginate if needed
                if total > len(listings) and len(listings) > 0:
                    total_pages = min(math.ceil(total / max(len(listings), 1)), 5)
                    for page_num in range(2, total_pages + 1):
                        time.sleep(2)
                        page_url = f"https://www.sgcarmart.com/used-cars/listing?q={query}&avl=s&limit=100&page={page_num}"
                        page_text = self._fetch_page(session, page_url, f"sold '{keyword}' page {page_num}")
                        if not page_text:
                            break
                        page_listings, pg_dm = _extract_listings_from_rsc(page_text)
                        global_dealer_map.update(pg_dm)
                        for l in page_listings:
                            if l['dealer_code'] and not l['dealer_name']:
                                l['dealer_name'] = global_dealer_map.get(l['dealer_code'], '')
                        for item in page_listings:
                            clean_url = (item.get('link', '').split('?')[0])
                            if clean_url and clean_url not in seen_urls:
                                seen_urls.add(clean_url)
                                name = item.get('car_model', '')
                                if name and self.match_target(name):
                                    sold_data.append(item)
                        if len(page_listings) == 0:
                            break

            # Step 3: Process and save
            logger.info(f"[3/3] Processing {len(sold_data)} sold target vehicles...")

            processed = []
            for item in sold_data:
                name = item.get('car_model', '')
                link = item.get('link', '')
                dealer_name = item.get('dealer_name', '')
                dealer_code = item.get('dealer_code')
                depreciation = item.get('depreciation')
                reg_date = item.get('registration_date', '')

                dep_str = ''
                if depreciation is not None:
                    dep_str = f"${depreciation:,}/yr"

                if not dealer_name and dealer_code:
                    dealer_name = global_dealer_map.get(dealer_code, '')

                # Fetch detail page for missing dealer/depreciation
                if (not dealer_name or not dep_str) and link:
                    time.sleep(1)
                    detail_dealer, detail_dep = self._fetch_detail_page_dealer(session, link, global_dealer_map)
                    if detail_dealer and not dealer_name:
                        dealer_name = detail_dealer
                    if detail_dep and not dep_str:
                        dep_str = detail_dep

                if not dealer_name:
                    dealer_name = '–'

                processed.append({
                    'make_model': name,
                    'registered_year': extract_year(reg_date),
                    'depreciation': dep_str,
                    'dealer_name': dealer_name,
                    'price': item.get('price'),
                    'listing_url': link,
                })
                logger.info(f"  [SOLD] {name} | ${item.get('price', '?')} | {dep_str} | {dealer_name}")

            logger.info("=" * 60)
            logger.info(f"[SUCCESS] Total SOLD target vehicles: {len(processed)}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during sold scraping: {e}")
            import traceback
            traceback.print_exc()
            processed = []

        if processed:
            self._save_sold_to_db(processed)

        return processed

    def _save_sold_to_db(self, data: List[Dict[str, Any]]):
        """Save sold listings to SoldLog table."""
        db = SessionLocal()
        try:
            now = datetime.now()
            for item in data:
                dep = item.get('depreciation', '') or '–'
                if not dep and item.get('price') is not None:
                    dep = f"${item['price']:,.0f}"
                db.add(SoldLog(
                    sold_date=now,
                    make_model=item.get('make_model', ''),
                    year_registered=item.get('registered_year'),
                    depreciation=dep,
                    dealer_name=item.get('dealer_name', '–'),
                ))
            db.commit()
            logger.info(f"[OK] Saved {len(data)} sold listings to SoldLog")
        except Exception as e:
            logger.error(f"Error saving sold data: {e}")
            db.rollback()
        finally:
            db.close()

    def _fallback_playwright_scrape(self) -> List[Dict[str, Any]]:
        """Fallback to Playwright-based scraping if curl_cffi fails."""
        logger.info("Attempting Playwright fallback...")
        try:
            from playwright.sync_api import sync_playwright
            from undetected_playwright import stealth_sync
        except ImportError:
            logger.error("Playwright not available for fallback")
            return []

        scraped_data = []

        with sync_playwright() as p:
            logger.info("  Launching Chromium...")
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                ]
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="en-SG"
            )
            page = context.new_page()
            stealth_sync(page)

            try:
                # Visit homepage first
                page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)

                # Search each keyword
                for keyword in SEARCH_KEYWORDS:
                    query = keyword.replace(' ', '+')
                    url = f"https://www.sgcarmart.com/used-cars/listing?q={query}&limit=100"
                    logger.info(f"  Playwright search: {keyword}")

                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        time.sleep(5)

                        # Wait for content to render
                        page.wait_for_selector('a[href*="used-cars/info"]', timeout=10000)

                        # Get page source after JS rendering
                        content = page.content()
                        listings, _ = _extract_listings_from_rsc(content)

                        if not listings:
                            # Try evaluating JS
                            listings_js = page.evaluate("""
                                () => {
                                    const results = [];
                                    const links = document.querySelectorAll('a[href*="used-cars/info"]');
                                    for (const a of links) {
                                        const href = a.getAttribute('href') || '';
                                        const text = (a.textContent || '').trim();
                                        if (text && text.length > 3 && !text.includes('$')) {
                                            results.push({
                                                car_model: text,
                                                link: href.startsWith('http') ? href : 'https://www.sgcarmart.com' + href,
                                                price: null,
                                                depreciation: null,
                                                registration_date: null,
                                                dealer_code: null,
                                                dealer_name: ''
                                            });
                                        }
                                    }
                                    return results;
                                }
                            """)
                            listings = listings_js or []

                        target_count = sum(1 for l in listings if self.match_target(l.get('car_model', '')))
                        logger.info(f"    Found {len(listings)} items ({target_count} targets)")

                        for item in listings:
                            name = item.get('car_model', '')
                            if name and self.match_target(name):
                                dep = item.get('depreciation')
                                dep_str = f"${dep:,}/yr" if dep else ''
                                scraped_data.append({
                                    'make_model': name,
                                    'registered_year': extract_year(item.get('registration_date')),
                                    'depreciation': dep_str,
                                    'dealer_name': item.get('dealer_name', '–'),
                                    'price': item.get('price'),
                                    'listing_url': item.get('link', ''),
                                    'additional_info': item.get('registration_date', ''),
                                })
                    except Exception as e:
                        logger.error(f"    Playwright search error: {e}")
                        continue

            except Exception as e:
                logger.error(f"Playwright error: {e}")
            finally:
                browser.close()

        if scraped_data:
            self._save_to_db(scraped_data)

        return scraped_data

    def _save_to_db(self, data: List[Dict[str, Any]]):
        """Save scraped data to database."""
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
    results = scraper.scrape_vehicle_listings()
    print(f"\nTotal results: {len(results)}")
    for r in results:
        print(f"  {r['make_model']} | ${r.get('price', '?')} | {r.get('depreciation', '?')} | {r.get('dealer_name', '?')}")
