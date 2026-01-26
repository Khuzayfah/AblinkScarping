"""Show sample data - Ablink SGCarmart Scraper"""
import pandas as pd

print("="*80)
print("ABLINK SGCARMART SCRAPER - DATA OUTPUT")
print("By Oneiros Indonesia")
print("="*80)

# Read Excel file
df = pd.read_excel('daily_reports/depreciation_sample_20260125_100514.xlsx')

print(f"\nTotal Vehicles: {len(df)}")
print(f"Categories: {df['Category'].nunique()}")
print(f"Total Units: {int(df['TOTAL UNITS'].sum())}")

print("\n" + "="*80)
print("DATA PREVIEW:")
print("="*80)
print(df.to_string())

print("\n" + "="*80)
print("COLUMNS:")
print("="*80)
for col in df.columns:
    print(f"  - {col}")

print("\n" + "="*80)
print("CATEGORIES:")
print("="*80)
for cat in df['Category'].unique():
    count = len(df[df['Category'] == cat])
    print(f"  - {cat}: {count} vehicles")

print("\n" + "="*80)
