"""
Test PDF-Style HTML Generator
Ablink SGCarmart Scraper by Oneiros Indonesia
"""

import pandas as pd
from datetime import datetime
from pdf_style_generator import PDFStyleHTMLGenerator
import webbrowser
import os

print("="*80)
print("ABLINK SGCARMART SCRAPER - PDF-STYLE REPORT TEST")
print("By Oneiros Indonesia")
print("="*80)

# Read existing data
df = pd.read_excel('daily_reports/demo_depreciation_20260126_165304.xlsx')

print(f"\nData loaded:")
print(f"  Vehicles: {len(df)}")
print(f"  Categories: {df['Category'].nunique()}")
print(f"  Total Units: {df['TOTAL UNITS'].sum()}")

print("\nGenerating PDF-style HTML report...")

# Generate report
generator = PDFStyleHTMLGenerator()
html_file = generator.generate_report(df)

print(f"\n[OK] Report generated: {html_file}")

# Open in browser
print("\nOpening in browser...")
abs_path = os.path.abspath(html_file)
webbrowser.open('file://' + abs_path)

print("\n" + "="*80)
print("CHECK YOUR BROWSER!")
print("="*80)
print("\nReport should look like PDF format:")
print("  - DATE header at top")
print("  - Each year: 2 columns (Price + Units)")
print("  - Category section headers")
print("  - Color-coded DIFF (green/red)")
print("  - Compact table layout")
print("  - Print-ready (Ctrl+P -> PDF)")

print("\n" + "="*80)
