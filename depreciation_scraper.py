"""
Ablink SGCarmart Scraper - Depreciation Data Module
By Oneiros Indonesia

Automated scraper for vehicle depreciation prices from SGCarmart.com
Extracts data for all vehicle categories with year-wise pricing
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
from datetime import datetime
import os


class DepreciationScraper:
    """
    Scraper for SGCarmart vehicle depreciation data
    Configurable parameters for flexible scraping
    """
    
    def __init__(self, config=None):
        """
        Initialize scraper with configuration
        
        Args:
            config (dict): Configuration parameters
                - headless (bool): Run browser in background
                - timeout (int): Page load timeout in seconds
                - delay (int): Delay between requests in seconds
                - output_folder (str): Folder for saving reports
        """
        # Default configuration
        self.config = {
            'headless': False,
            'timeout': 30,
            'delay': 3,
            'output_folder': 'daily_reports',
            'save_excel': True,
            'save_csv': True,
            'save_html': True
        }
        
        # Update with user config
        if config:
            self.config.update(config)
        
        # Setup Chrome options
        self.options = Options()
        if self.config['headless']:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = None
        self.data = None
    
    def start_driver(self):
        """Initialize Chrome WebDriver"""
        print("Starting Chrome WebDriver...")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=self.options)
        self.driver.maximize_window()
        print("[OK] WebDriver started successfully!")
    
    def scrape_depreciation_page(self, url=None):
        """
        Scrape depreciation data from SGCarmart
        
        Args:
            url (str): Target URL. If None, will search for depreciation page
        
        Returns:
            pd.DataFrame: Depreciation data
        """
        if not self.driver:
            self.start_driver()
        
        # URLs to try for depreciation data
        depreciation_urls = [
            "https://www.sgcarmart.com/new_cars/newcars_depreciation.php",
            "https://www.sgcarmart.com/depreciation.php",
            "https://www.sgcarmart.com/new_cars/overview.php?page=depreciation",
        ]
        
        if url:
            depreciation_urls.insert(0, url)
        
        print("\nSearching for depreciation data...")
        
        for test_url in depreciation_urls:
            print(f"\nTrying: {test_url}")
            
            try:
                self.driver.get(test_url)
                time.sleep(self.config['delay'])
                
                # Wait for page load
                try:
                    WebDriverWait(self.driver, self.config['timeout']).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except:
                    print("[WARNING] Timeout waiting for page")
                    continue
                
                # Parse page
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Look for depreciation table
                tables = soup.find_all('table')
                print(f"Found {len(tables)} tables on page")
                
                if tables:
                    # Try to find the depreciation table
                    # Look for table with year columns (2025, 2024, etc.)
                    for idx, table in enumerate(tables):
                        # Check headers for year patterns
                        headers = table.find_all(['th', 'td'])
                        header_text = ' '.join([h.get_text() for h in headers[:10]])
                        
                        # Check if this looks like depreciation table
                        if any(year in header_text for year in ['2025', '2024', '2023', 'UNITS', 'DEPRECIATION']):
                            print(f"[OK] Found depreciation table (table {idx + 1})")
                            df = self._parse_depreciation_table(table)
                            
                            if df is not None and not df.empty:
                                self.data = df
                                print(f"[OK] Successfully scraped {len(df)} rows of data")
                                return df
            
            except Exception as e:
                print(f"[ERROR] Failed to scrape {test_url}: {e}")
                continue
        
        print("\n[WARNING] Could not find depreciation table")
        print("Attempting to scrape all tables for manual inspection...")
        
        # Last resort: get all tables
        return self._scrape_all_tables()
    
    def _scrape_all_tables(self):
        """Scrape all tables from current page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        tables = soup.find_all('table')
        
        all_data = []
        
        for idx, table in enumerate(tables):
            print(f"\nParsing table {idx + 1}...")
            df = self._parse_depreciation_table(table)
            
            if df is not None and not df.empty and len(df) > 2:
                all_data.append({
                    'table_index': idx + 1,
                    'data': df
                })
                print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
        
        if all_data:
            # Return the largest table (likely the main depreciation table)
            largest = max(all_data, key=lambda x: len(x['data']))
            self.data = largest['data']
            return self.data
        
        return None
    
    def _parse_depreciation_table(self, table):
        """
        Parse HTML table into DataFrame
        
        Args:
            table: BeautifulSoup table element
        
        Returns:
            pd.DataFrame: Parsed data
        """
        rows = table.find_all('tr')
        
        if not rows:
            return None
        
        data = []
        headers = []
        
        for idx, row in enumerate(rows):
            # Try to get headers
            if idx == 0:
                ths = row.find_all('th')
                if ths:
                    headers = [th.get_text(strip=True) for th in ths]
                    continue
                else:
                    # If no th, check if first row has td that look like headers
                    tds = row.find_all('td')
                    row_text = [td.get_text(strip=True) for td in tds]
                    # Check if it looks like header row
                    if any(keyword in ' '.join(row_text).upper() for keyword in ['YEAR', 'UNITS', 'DIFF', 'DATE']):
                        headers = row_text
                        continue
            
            # Get data cells
            cells = row.find_all('td')
            if cells:
                row_data = []
                for cell in cells:
                    text = cell.get_text(strip=True)
                    # Clean data
                    text = text.replace('$', '').replace(',', '')
                    row_data.append(text)
                
                if any(row_data):  # Skip empty rows
                    data.append(row_data)
        
        if not data:
            return None
        
        # Create DataFrame
        try:
            if headers and len(headers) == len(data[0]):
                df = pd.DataFrame(data, columns=headers)
            else:
                # Generate column names
                num_cols = len(data[0])
                headers = [f"Column_{i+1}" for i in range(num_cols)]
                df = pd.DataFrame(data, columns=headers)
            
            return df
        
        except Exception as e:
            print(f"[ERROR] Failed to parse table: {e}")
            return None
    
    def save_data(self, df=None, filename_prefix="depreciation"):
        """
        Save scraped data to various formats
        
        Args:
            df (pd.DataFrame): Data to save. If None, uses self.data
            filename_prefix (str): Prefix for output files
        
        Returns:
            dict: Paths to saved files
        """
        if df is None:
            df = self.data
        
        if df is None or df.empty:
            print("[ERROR] No data to save")
            return None
        
        # Create output folder
        output_folder = self.config['output_folder']
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"[OK] Created folder: {output_folder}")
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Add metadata columns
        df['Scraped_Date'] = date_str
        df['Scraped_Time'] = datetime.now().strftime("%H:%M:%S")
        
        saved_files = {}
        
        # Save Excel
        if self.config['save_excel']:
            excel_file = f"{output_folder}/{filename_prefix}_{timestamp}.xlsx"
            df.to_excel(excel_file, index=False)
            saved_files['excel'] = excel_file
            print(f"[OK] Excel saved: {excel_file}")
        
        # Save CSV
        if self.config['save_csv']:
            csv_file = f"{output_folder}/{filename_prefix}_{timestamp}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            saved_files['csv'] = csv_file
            print(f"[OK] CSV saved: {csv_file}")
        
        # Save HTML report
        if self.config['save_html']:
            try:
                from html_report_generator import HTMLReportGenerator
                
                # First save to Excel, then generate HTML
                temp_excel = f"{output_folder}/temp_{timestamp}.xlsx"
                df.to_excel(temp_excel, index=False)
                
                generator = HTMLReportGenerator()
                html_file = generator.generate_html_report(
                    temp_excel, 
                    f"{output_folder}/{filename_prefix}_{timestamp}.html"
                )
                saved_files['html'] = html_file
                
                # Clean up temp file
                if os.path.exists(temp_excel):
                    os.remove(temp_excel)
            
            except Exception as e:
                print(f"[WARNING] Could not generate HTML report: {e}")
        
        # Save latest version (overwrite)
        latest_excel = f"{output_folder}/{filename_prefix}_latest.xlsx"
        latest_csv = f"{output_folder}/{filename_prefix}_latest.csv"
        
        df.to_excel(latest_excel, index=False)
        df.to_csv(latest_csv, index=False, encoding='utf-8-sig')
        
        saved_files['latest_excel'] = latest_excel
        saved_files['latest_csv'] = latest_csv
        
        print(f"\n[OK] Latest files also updated")
        
        return saved_files
    
    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            print("\n[OK] Browser closed")
    
    def run(self, url=None):
        """
        Complete scraping workflow
        
        Args:
            url (str): Target URL (optional)
        
        Returns:
            dict: Information about saved files
        """
        print("="*70)
        print("SGCarmart Depreciation Scraper")
        print("="*70)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Configuration: {self.config}")
        
        try:
            # Start driver
            self.start_driver()
            
            # Scrape data
            df = self.scrape_depreciation_page(url)
            
            if df is not None and not df.empty:
                # Display preview
                print("\n" + "="*70)
                print("DATA PREVIEW")
                print("="*70)
                print(df.head(10).to_string())
                print(f"\nTotal rows: {len(df)}")
                print(f"Total columns: {len(df.columns)}")
                
                # Save data
                print("\n" + "="*70)
                print("SAVING DATA")
                print("="*70)
                saved_files = self.save_data(df)
                
                return saved_files
            
            else:
                print("\n[ERROR] No data scraped")
                return None
        
        except Exception as e:
            print(f"\n[ERROR] Scraping failed: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        finally:
            self.close()


def main():
    """Main execution function"""
    
    print("\n")
    print("="*70)
    print("  SGCarmart Depreciation Data Scraper")
    print("="*70)
    print()
    
    # Configuration options
    print("Configuration Options:")
    print("1. Default (Recommended)")
    print("2. Custom configuration")
    print()
    
    choice = input("Select option (1-2) [default: 1]: ").strip() or "1"
    
    config = {}
    
    if choice == "2":
        print("\nCustom Configuration:")
        
        # Headless mode
        headless = input("  Run in headless mode? (y/n) [default: n]: ").strip().lower()
        config['headless'] = headless == 'y'
        
        # Timeout
        timeout = input("  Page load timeout (seconds) [default: 30]: ").strip()
        config['timeout'] = int(timeout) if timeout.isdigit() else 30
        
        # Delay
        delay = input("  Delay between requests (seconds) [default: 3]: ").strip()
        config['delay'] = int(delay) if delay.isdigit() else 3
        
        # Output formats
        save_excel = input("  Save as Excel? (y/n) [default: y]: ").strip().lower() or 'y'
        config['save_excel'] = save_excel == 'y'
        
        save_csv = input("  Save as CSV? (y/n) [default: y]: ").strip().lower() or 'y'
        config['save_csv'] = save_csv == 'y'
        
        save_html = input("  Save as HTML? (y/n) [default: y]: ").strip().lower() or 'y'
        config['save_html'] = save_html == 'y'
    
    # Custom URL (optional)
    print()
    custom_url = input("Custom URL (leave empty for auto-search): ").strip()
    
    # Create scraper
    scraper = DepreciationScraper(config)
    
    # Run scraping
    result = scraper.run(custom_url if custom_url else None)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if result:
        print("\n[SUCCESS] Scraping completed successfully!")
        print("\nSaved files:")
        for file_type, file_path in result.items():
            if file_path:
                print(f"  {file_type}: {file_path}")
    else:
        print("\n[FAILED] Scraping did not complete successfully")
    
    print("\n" + "="*70)
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
