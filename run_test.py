"""
Test run - Ablink SGCarmart Scraper
By Oneiros Indonesia
"""

from depreciation_scraper import DepreciationScraper
from depreciation_html_generator import DepreciationHTMLGenerator
import pandas as pd

print("="*70)
print("Ablink SGCarmart Scraper - Test Run")
print("By Oneiros Indonesia")
print("="*70)

# Configuration
config = {
    'headless': False,
    'timeout': 30,
    'delay': 3,
    'output_folder': 'daily_reports',
    'save_excel': True,
    'save_csv': True,
    'save_html': False
}

print("\n[INFO] Starting scraper...")
print("[INFO] Target: SGCarmart.com")
print("[INFO] Categories: 10FT DIESEL, 14FT DIESEL, VAN DIESEL, VAN PETROL")

# Run scraper
scraper = DepreciationScraper(config)
result = scraper.run()

if result and result.get('excel'):
    print("\n" + "="*70)
    print("SUCCESS! Scraping completed")
    print("="*70)
    
    # Read data
    df = pd.read_excel(result['excel'])
    
    print(f"\n[RESULTS]")
    print(f"Total Vehicles: {len(df)}")
    if 'Category' in df.columns:
        print(f"Categories: {df['Category'].nunique()}")
    if 'TOTAL UNITS' in df.columns:
        print(f"Total Units: {df['TOTAL UNITS'].sum()}")
    
    print(f"\n[FILES CREATED]")
    for key, path in result.items():
        if path:
            print(f"  {key.upper()}: {path}")
    
    # Generate styled HTML
    print(f"\n[INFO] Generating styled HTML report...")
    generator = DepreciationHTMLGenerator()
    html_file = generator.generate_report(df)
    print(f"  HTML: {html_file}")
    
    # Show data preview
    print("\n" + "="*70)
    print("DATA PREVIEW (First 5 rows):")
    print("="*70)
    print(df.head().to_string())
    
    # Open HTML in browser
    print("\n[INFO] Opening HTML report in browser...")
    import webbrowser
    import os
    abs_path = os.path.abspath(html_file)
    webbrowser.open('file://' + abs_path)
    
    print("\n" + "="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print("\nCheck browser for styled HTML report")
    print(f"Files saved to: {config['output_folder']}/")
    
else:
    print("\n[ERROR] Scraping failed")
    print("Check logs for details")

print("\n" + "="*70)
input("Press Enter to exit...")
