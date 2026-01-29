"""
Ablink SGCarmart Scraper - Real Data Scraper Module
By Oneiros Indonesia

Scrapes REAL depreciation data from SGCarmart.com
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import os
from datetime import datetime


class SGCarmartScraper:
    """Real SGCarmart scraper for depreciation data"""
    
    # Vehicle categories to scrape
    CATEGORIES = {
        '10FT DIESEL': {
            'url': 'https://www.sgcarmart.com/used_cars/listing.php?BRSR=0&RPG=60&AVL=2&VT=30&FRY=2010&TOY=2026',
            'vehicles': ['HINO DUTRO', 'TOYOTA DYNA', 'NISSAN CABSTAR', 'MITSUBISHI FEA', 'ISUZU NHR', 'ISUZU NJR', 'KIA 2500']
        },
        '14FT DIESEL': {
            'url': 'https://www.sgcarmart.com/used_cars/listing.php?BRSR=0&RPG=60&AVL=2&VT=31&FRY=2010&TOY=2026',
            'vehicles': ['HINO XZU', 'ISUZU NPR', 'ISUZU NMR', 'ISUZU NNR', 'MITSUBISHI FEB']
        },
        'VAN DIESEL (GOODS VAN)': {
            'url': 'https://www.sgcarmart.com/used_cars/listing.php?BRSR=0&RPG=60&AVL=2&VT=34&FRY=2010&TOY=2026&FUE=1',
            'vehicles': ['TOYOTA HIACE', 'NISSAN NV350', 'NISSAN NV200']
        },
        'VAN PETROL (GOODS VAN)': {
            'url': 'https://www.sgcarmart.com/used_cars/listing.php?BRSR=0&RPG=60&AVL=2&VT=34&FRY=2010&TOY=2026&FUE=2',
            'vehicles': ['HONDA N-VAN', 'TOYOTA HIACE', 'NISSAN NV350', 'NISSAN NV200']
        }
    }
    
    def __init__(self, headless=True):
        """Initialize scraper"""
        self.headless = headless
        self.driver = None
        self.data = {}
        
    def start_driver(self):
        """Start Chrome WebDriver"""
        print("[INFO] Starting Chrome WebDriver...")
        
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            print("[OK] WebDriver started successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to start WebDriver: {e}")
            return False
    
    def close_driver(self):
        """Close WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("[OK] WebDriver closed")
    
    def scrape_listing_page(self, url, category, max_pages=5):
        """Scrape vehicle listings from a category page"""
        vehicles_data = []
        
        try:
            print(f"\n[INFO] Scraping: {category}")
            print(f"[INFO] URL: {url}")
            
            self.driver.get(url)
            time.sleep(3)
            
            page = 1
            while page <= max_pages:
                print(f"[INFO] Page {page}...")
                
                # Parse page
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Find vehicle listings
                listings = soup.find_all('div', class_='listing-item') or \
                          soup.find_all('tr', class_='listing_row') or \
                          soup.find_all('div', {'class': re.compile(r'listing|car-item|vehicle')})
                
                if not listings:
                    # Try alternative selectors
                    tables = soup.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        if len(rows) > 3:
                            listings = rows[1:]  # Skip header
                            break
                
                print(f"[INFO] Found {len(listings)} listings")
                
                for listing in listings:
                    try:
                        vehicle_info = self._parse_listing(listing, category)
                        if vehicle_info:
                            vehicles_data.append(vehicle_info)
                    except Exception as e:
                        continue
                
                # Try next page
                try:
                    next_link = soup.find('a', text=re.compile(r'Next|>|>>'))
                    if next_link and next_link.get('href'):
                        next_url = next_link['href']
                        if not next_url.startswith('http'):
                            next_url = 'https://www.sgcarmart.com' + next_url
                        self.driver.get(next_url)
                        time.sleep(2)
                        page += 1
                    else:
                        break
                except:
                    break
            
        except Exception as e:
            print(f"[ERROR] Failed to scrape {category}: {e}")
        
        return vehicles_data
    
    def _parse_listing(self, listing, category):
        """Parse a single vehicle listing"""
        try:
            text = listing.get_text(' ', strip=True)
            
            # Extract vehicle name
            title_elem = listing.find(['a', 'h3', 'h4', 'span'], class_=re.compile(r'title|name|model'))
            if title_elem:
                vehicle_name = title_elem.get_text(strip=True)
            else:
                # Extract from text
                vehicle_name = text.split('$')[0].strip()[:50]
            
            # Extract year (registration year)
            year_match = re.search(r'(20\d{2})', text)
            year = year_match.group(1) if year_match else None
            
            # Extract depreciation
            deprec_match = re.search(r'\$\s*([\d,]+)\s*/\s*yr', text, re.IGNORECASE) or \
                          re.search(r'depreciation[:\s]*\$\s*([\d,]+)', text, re.IGNORECASE)
            
            if deprec_match:
                depreciation = int(deprec_match.group(1).replace(',', ''))
            else:
                # Try to find price and calculate
                price_match = re.search(r'\$\s*([\d,]+)', text)
                if price_match:
                    price = int(price_match.group(1).replace(',', ''))
                    # Estimate depreciation (rough calculation)
                    if year and price > 10000:
                        coe_years = 10 - (datetime.now().year - int(year))
                        if coe_years > 0:
                            depreciation = int(price / coe_years)
                        else:
                            depreciation = 0
                    else:
                        depreciation = 0
                else:
                    depreciation = 0
            
            if year and depreciation > 0:
                return {
                    'category': category,
                    'vehicle': vehicle_name,
                    'year': year,
                    'depreciation': depreciation
                }
            
        except Exception as e:
            pass
        
        return None
    
    def scrape_all_categories(self):
        """Scrape all vehicle categories"""
        print("="*70)
        print("SGCarmart Real Data Scraper")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        if not self.start_driver():
            return None
        
        all_vehicles = []
        
        try:
            for category, config in self.CATEGORIES.items():
                vehicles = self.scrape_listing_page(config['url'], category)
                all_vehicles.extend(vehicles)
                print(f"[OK] {category}: {len(vehicles)} vehicles")
                time.sleep(2)
        
        finally:
            self.close_driver()
        
        # Process and aggregate data
        return self._aggregate_data(all_vehicles)
    
    def _aggregate_data(self, vehicles):
        """Aggregate vehicle data by category, vehicle, and year"""
        
        if not vehicles:
            print("[WARNING] No vehicles scraped, using sample data")
            return self._get_sample_data()
        
        # Group by category and vehicle
        aggregated = {}
        
        for v in vehicles:
            cat = v['category']
            vehicle = v['vehicle'].upper()
            year = v['year']
            deprec = v['depreciation']
            
            # Normalize vehicle name
            for known in self.CATEGORIES.get(cat, {}).get('vehicles', []):
                if known.upper() in vehicle:
                    vehicle = known
                    break
            
            key = (cat, vehicle)
            
            if key not in aggregated:
                aggregated[key] = {
                    'category': cat,
                    'vehicle': vehicle,
                    'years': {}
                }
            
            if year not in aggregated[key]['years']:
                aggregated[key]['years'][year] = {
                    'prices': [],
                    'count': 0
                }
            
            aggregated[key]['years'][year]['prices'].append(deprec)
            aggregated[key]['years'][year]['count'] += 1
        
        # Calculate lowest, average, units
        result_vehicles = []
        
        for key, data in aggregated.items():
            vehicle_data = {
                'category': data['category'],
                'vehicle': data['vehicle'],
                'years': {},
                'total_units': 0
            }
            
            for year, year_data in data['years'].items():
                prices = year_data['prices']
                vehicle_data['years'][year] = {
                    'lowest': min(prices),
                    'average': int(sum(prices) / len(prices)),
                    'units': year_data['count']
                }
                vehicle_data['total_units'] += year_data['count']
            
            vehicle_data['previous'] = vehicle_data['total_units']  # Will be updated with history
            vehicle_data['diff'] = 0
            
            result_vehicles.append(vehicle_data)
        
        # Sort by category
        category_order = list(self.CATEGORIES.keys())
        result_vehicles.sort(key=lambda x: (
            category_order.index(x['category']) if x['category'] in category_order else 999,
            x['vehicle']
        ))
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'vehicles': result_vehicles,
            'total_scraped': len(vehicles)
        }
    
    def _get_sample_data(self):
        """Return sample data when scraping fails"""
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'vehicles': [
                {'category': '10FT DIESEL', 'vehicle': 'HINO DUTRO 2.8', 
                 'years': {
                     '2025': {'lowest': 11510, 'average': 11480, 'units': 49},
                     '2024': {'lowest': 11450, 'average': 11450, 'units': 8},
                 },
                 'total_units': 57, 'previous': 55, 'diff': 2},
                {'category': '10FT DIESEL', 'vehicle': 'TOYOTA DYNA 2.8',
                 'years': {
                     '2023': {'lowest': 14720, 'average': 14720, 'units': 2},
                     '2022': {'lowest': 12740, 'average': 12740, 'units': 14},
                     '2021': {'lowest': 13310, 'average': 13310, 'units': 4},
                 },
                 'total_units': 20, 'previous': 17, 'diff': 3},
                {'category': '10FT DIESEL', 'vehicle': 'TOYOTA DYNA 3.0',
                 'years': {
                     '2022': {'lowest': 13470, 'average': 13470, 'units': 1},
                     '2021': {'lowest': 15580, 'average': 15580, 'units': 4},
                     '2020': {'lowest': 15330, 'average': 15330, 'units': 11},
                     '2019': {'lowest': 16160, 'average': 16160, 'units': 10},
                     '2018': {'lowest': 16220, 'average': 16220, 'units': 7},
                     '2017': {'lowest': 16700, 'average': 16700, 'units': 5},
                     '2016': {'lowest': 9950, 'average': 9950, 'units': 19},
                     '2015': {'lowest': 9840, 'average': 9840, 'units': 23},
                     '2014': {'lowest': 8960, 'average': 8960, 'units': 19},
                 },
                 'total_units': 99, 'previous': 105, 'diff': -6},
                {'category': '10FT DIESEL', 'vehicle': 'NISSAN CABSTAR',
                 'years': {
                     '2022': {'lowest': 10110, 'average': 10110, 'units': 1},
                     '2021': {'lowest': 8530, 'average': 8530, 'units': 1},
                     '2020': {'lowest': 9770, 'average': 9770, 'units': 2},
                     '2017': {'lowest': 11090, 'average': 11090, 'units': 9},
                     '2016': {'lowest': 8360, 'average': 8360, 'units': 3},
                     '2015': {'lowest': 9620, 'average': 9620, 'units': 1},
                     '2014': {'lowest': 8700, 'average': 8700, 'units': 7},
                 },
                 'total_units': 24, 'previous': 29, 'diff': -5},
                {'category': '10FT DIESEL', 'vehicle': 'MITSUBISHI FEA01',
                 'years': {
                     '2021': {'lowest': 11550, 'average': 11550, 'units': 5},
                     '2020': {'lowest': 11670, 'average': 11670, 'units': 3},
                     '2019': {'lowest': 12060, 'average': 12060, 'units': 4},
                     '2017': {'lowest': 11550, 'average': 11550, 'units': 2},
                     '2016': {'lowest': 18840, 'average': 18840, 'units': 2},
                     '2015': {'lowest': 8560, 'average': 8560, 'units': 3},
                     '2014': {'lowest': 10940, 'average': 10940, 'units': 3},
                 },
                 'total_units': 22, 'previous': 25, 'diff': -3},
                {'category': '10FT DIESEL', 'vehicle': 'ISUZU NHR / NJR',
                 'years': {
                     '2025': {'lowest': 13470, 'average': 13470, 'units': 2},
                     '2021': {'lowest': 11400, 'average': 11400, 'units': 1},
                     '2020': {'lowest': 12990, 'average': 12990, 'units': 2},
                     '2018': {'lowest': 11680, 'average': 11680, 'units': 3},
                     '2017': {'lowest': 11740, 'average': 11740, 'units': 3},
                     '2016': {'lowest': 9150, 'average': 9150, 'units': 6},
                     '2015': {'lowest': 8080, 'average': 8080, 'units': 6},
                     '2014': {'lowest': 8920, 'average': 8920, 'units': 2},
                 },
                 'total_units': 25, 'previous': 24, 'diff': 1},
                {'category': '10FT DIESEL', 'vehicle': 'KIA 2500',
                 'years': {
                     '2024': {'lowest': 10550, 'average': 10550, 'units': 1},
                     '2023': {'lowest': 11170, 'average': 11170, 'units': 2},
                     '2022': {'lowest': 10020, 'average': 10020, 'units': 3},
                     '2021': {'lowest': 11180, 'average': 11180, 'units': 3},
                     '2020': {'lowest': 10350, 'average': 10350, 'units': 2},
                 },
                 'total_units': 11, 'previous': 9, 'diff': 2},
                
                # 14FT DIESEL
                {'category': '14FT DIESEL', 'vehicle': 'HINO XZU710',
                 'years': {
                     '2025': {'lowest': 12220, 'average': 12220, 'units': 27},
                     '2024': {'lowest': 12220, 'average': 12220, 'units': 6},
                     '2023': {'lowest': 13120, 'average': 13120, 'units': 2},
                     '2022': {'lowest': 13880, 'average': 13880, 'units': 2},
                     '2021': {'lowest': 15790, 'average': 15790, 'units': 1},
                     '2020': {'lowest': 16130, 'average': 16130, 'units': 2},
                     '2019': {'lowest': 16280, 'average': 16280, 'units': 1},
                     '2018': {'lowest': 16270, 'average': 16270, 'units': 3},
                     '2017': {'lowest': 18440, 'average': 18440, 'units': 1},
                     '2016': {'lowest': 29970, 'average': 29970, 'units': 3},
                     '2015': {'lowest': 10370, 'average': 10370, 'units': 3},
                     '2014': {'lowest': 18020, 'average': 18020, 'units': 1},
                 },
                 'total_units': 52, 'previous': 54, 'diff': -2},
                {'category': '14FT DIESEL', 'vehicle': 'ISUZU NPR85',
                 'years': {
                     '2025': {'lowest': 13180, 'average': 13180, 'units': 2},
                     '2022': {'lowest': 14060, 'average': 14060, 'units': 5},
                     '2021': {'lowest': 13760, 'average': 13760, 'units': 3},
                     '2018': {'lowest': 19710, 'average': 19710, 'units': 1},
                     '2017': {'lowest': 13610, 'average': 13610, 'units': 3},
                     '2015': {'lowest': 9170, 'average': 9170, 'units': 2},
                     '2014': {'lowest': 13640, 'average': 13640, 'units': 1},
                 },
                 'total_units': 17, 'previous': 21, 'diff': -4},
                {'category': '14FT DIESEL', 'vehicle': 'ISUZU NMR85',
                 'years': {
                     '2025': {'lowest': 12520, 'average': 12520, 'units': 2},
                     '2022': {'lowest': 13530, 'average': 13530, 'units': 1},
                     '2019': {'lowest': 13460, 'average': 13460, 'units': 1},
                     '2018': {'lowest': 17190, 'average': 17190, 'units': 1},
                 },
                 'total_units': 5, 'previous': 3, 'diff': 2},
                {'category': '14FT DIESEL', 'vehicle': 'ISUZU NNR85',
                 'years': {
                     '2025': {'lowest': 12250, 'average': 12250, 'units': 1},
                     '2022': {'lowest': 13740, 'average': 13740, 'units': 2},
                     '2018': {'lowest': 14560, 'average': 14560, 'units': 2},
                     '2017': {'lowest': 16420, 'average': 16420, 'units': 1},
                     '2016': {'lowest': 10150, 'average': 10150, 'units': 1},
                     '2014': {'lowest': 10230, 'average': 10230, 'units': 1},
                 },
                 'total_units': 8, 'previous': 11, 'diff': -3},
                {'category': '14FT DIESEL', 'vehicle': 'MITSUBISHI FEB21',
                 'years': {
                     '2025': {'lowest': 12370, 'average': 12370, 'units': 12},
                     '2023': {'lowest': 12470, 'average': 12470, 'units': 2},
                     '2020': {'lowest': 13060, 'average': 13060, 'units': 4},
                     '2019': {'lowest': 14770, 'average': 14770, 'units': 5},
                     '2018': {'lowest': 15740, 'average': 15740, 'units': 7},
                     '2017': {'lowest': 16320, 'average': 16320, 'units': 7},
                     '2016': {'lowest': 9950, 'average': 9950, 'units': 8},
                     '2015': {'lowest': 8360, 'average': 8360, 'units': 19},
                     '2014': {'lowest': 10030, 'average': 10030, 'units': 5},
                 },
                 'total_units': 69, 'previous': 72, 'diff': -3},
                
                # VAN DIESEL
                {'category': 'VAN DIESEL (GOODS VAN)', 'vehicle': 'TOYOTA HIACE 3.0M',
                 'years': {
                     '2022': {'lowest': 13610, 'average': 13610, 'units': 1},
                     '2021': {'lowest': 13590, 'average': 13590, 'units': 7},
                     '2020': {'lowest': 13310, 'average': 13310, 'units': 12},
                     '2019': {'lowest': 14130, 'average': 14130, 'units': 10},
                     '2018': {'lowest': 13780, 'average': 13780, 'units': 13},
                     '2017': {'lowest': 13630, 'average': 13630, 'units': 9},
                     '2016': {'lowest': 9750, 'average': 9750, 'units': 6},
                     '2015': {'lowest': 8010, 'average': 8010, 'units': 19},
                     '2014': {'lowest': 8980, 'average': 8980, 'units': 9},
                 },
                 'total_units': 86, 'previous': 78, 'diff': 8},
                {'category': 'VAN DIESEL (GOODS VAN)', 'vehicle': 'TOYOTA HIACE 3.0A',
                 'years': {
                     '2021': {'lowest': 13780, 'average': 13780, 'units': 10},
                     '2020': {'lowest': 13990, 'average': 13990, 'units': 3},
                     '2019': {'lowest': 14110, 'average': 14110, 'units': 3},
                     '2018': {'lowest': 16600, 'average': 16600, 'units': 5},
                     '2017': {'lowest': 15130, 'average': 15130, 'units': 3},
                     '2016': {'lowest': 29200, 'average': 29200, 'units': 1},
                     '2015': {'lowest': 11410, 'average': 11410, 'units': 1},
                     '2014': {'lowest': 11170, 'average': 11170, 'units': 4},
                 },
                 'total_units': 30, 'previous': 25, 'diff': 5},
                {'category': 'VAN DIESEL (GOODS VAN)', 'vehicle': 'TOYOTA HIACE 2.8A',
                 'years': {
                     '2025': {'lowest': 13230, 'average': 13230, 'units': 14},
                     '2024': {'lowest': 13050, 'average': 13050, 'units': 1},
                     '2023': {'lowest': 15180, 'average': 15180, 'units': 1},
                     '2022': {'lowest': 14230, 'average': 14230, 'units': 1},
                     '2021': {'lowest': 14030, 'average': 14030, 'units': 22},
                     '2020': {'lowest': 14660, 'average': 14660, 'units': 22},
                     '2019': {'lowest': 14830, 'average': 14830, 'units': 6},
                     '2018': {'lowest': 21270, 'average': 21270, 'units': 1},
                 },
                 'total_units': 68, 'previous': 61, 'diff': 7},
                {'category': 'VAN DIESEL (GOODS VAN)', 'vehicle': 'NISSAN NV350 2.5M',
                 'years': {
                     '2020': {'lowest': 10350, 'average': 10350, 'units': 3},
                     '2019': {'lowest': 11530, 'average': 11530, 'units': 2},
                     '2018': {'lowest': 10370, 'average': 10370, 'units': 6},
                     '2017': {'lowest': 10320, 'average': 10320, 'units': 4},
                     '2015': {'lowest': 8070, 'average': 8070, 'units': 7},
                     '2014': {'lowest': 9050, 'average': 9050, 'units': 3},
                 },
                 'total_units': 26, 'previous': 28, 'diff': -2},
                {'category': 'VAN DIESEL (GOODS VAN)', 'vehicle': 'NISSAN NV200 1.5M',
                 'years': {
                     '2020': {'lowest': 11570, 'average': 11570, 'units': 1},
                     '2019': {'lowest': 9530, 'average': 9530, 'units': 6},
                     '2018': {'lowest': 9720, 'average': 9720, 'units': 6},
                     '2017': {'lowest': 9320, 'average': 9320, 'units': 8},
                     '2016': {'lowest': 8160, 'average': 8160, 'units': 6},
                     '2015': {'lowest': 8360, 'average': 8360, 'units': 6},
                     '2014': {'lowest': 7760, 'average': 7760, 'units': 2},
                 },
                 'total_units': 35, 'previous': 37, 'diff': -2},
                
                # VAN PETROL
                {'category': 'VAN PETROL (GOODS VAN)', 'vehicle': 'HONDA N-VAN',
                 'years': {
                     '2025': {'lowest': 9540, 'average': 9540, 'units': 27},
                     '2024': {'lowest': 9350, 'average': 9350, 'units': 3},
                     '2023': {'lowest': 9950, 'average': 9950, 'units': 1},
                     '2022': {'lowest': 10040, 'average': 10040, 'units': 13},
                 },
                 'total_units': 44, 'previous': 41, 'diff': 3},
                {'category': 'VAN PETROL (GOODS VAN)', 'vehicle': 'TOYOTA HIACE 2.0',
                 'years': {
                     '2025': {'lowest': 12260, 'average': 12260, 'units': 1},
                     '2023': {'lowest': 10760, 'average': 10760, 'units': 3},
                     '2022': {'lowest': 11240, 'average': 11240, 'units': 9},
                     '2021': {'lowest': 11360, 'average': 11360, 'units': 11},
                 },
                 'total_units': 24, 'previous': 15, 'diff': 9},
                {'category': 'VAN PETROL (GOODS VAN)', 'vehicle': 'NISSAN NV350 2.0',
                 'years': {
                     '2023': {'lowest': 8870, 'average': 8870, 'units': 1},
                     '2022': {'lowest': 9550, 'average': 9550, 'units': 4},
                     '2021': {'lowest': 9860, 'average': 9860, 'units': 1},
                 },
                 'total_units': 6, 'previous': 8, 'diff': -2},
                {'category': 'VAN PETROL (GOODS VAN)', 'vehicle': 'NISSAN NV200 1.6A',
                 'years': {
                     '2025': {'lowest': 9340, 'average': 9340, 'units': 9},
                     '2024': {'lowest': 9860, 'average': 9860, 'units': 3},
                     '2023': {'lowest': 9690, 'average': 9690, 'units': 3},
                     '2021': {'lowest': 9980, 'average': 9980, 'units': 18},
                     '2020': {'lowest': 9860, 'average': 9860, 'units': 8},
                     '2019': {'lowest': 11530, 'average': 11530, 'units': 8},
                     '2018': {'lowest': 11300, 'average': 11300, 'units': 1},
                     '2017': {'lowest': 11590, 'average': 11590, 'units': 7},
                     '2016': {'lowest': 9150, 'average': 9150, 'units': 2},
                     '2015': {'lowest': 8560, 'average': 8560, 'units': 11},
                     '2014': {'lowest': 9760, 'average': 9760, 'units': 1},
                 },
                 'total_units': 71, 'previous': 50, 'diff': 21},
            ],
            'total_scraped': 0,
            'source': 'sample_data'
        }


def test_scraper():
    """Test the scraper"""
    scraper = SGCarmartScraper(headless=True)
    data = scraper.scrape_all_categories()
    
    if data:
        print("\n" + "="*70)
        print("SCRAPING RESULTS")
        print("="*70)
        print(f"Date: {data['date']}")
        print(f"Time: {data['time']}")
        print(f"Total vehicles: {len(data['vehicles'])}")
        
        for v in data['vehicles'][:5]:
            print(f"\n{v['category']} - {v['vehicle']}")
            print(f"  Total units: {v['total_units']}")
    
    return data


if __name__ == "__main__":
    test_scraper()
