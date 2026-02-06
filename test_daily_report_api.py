"""Test daily report API to verify dealer names display"""
import sys
sys.path.insert(0, '.')

from main import _build_daily_table
from database import SessionLocal, VehicleListing
from datetime import datetime, timedelta

db = SessionLocal()

try:
    # Get latest date
    latest = db.query(VehicleListing).order_by(VehicleListing.scrape_date.desc()).first()

    if not latest:
        print("No data found")
        exit()

    report_date = latest.scrape_date.date()
    print(f"Testing daily report for date: {report_date}\n")

    # Get listings for that date
    start = datetime.combine(report_date, datetime.min.time())
    end = start + timedelta(days=1)
    listings = db.query(VehicleListing).filter(
        VehicleListing.scrape_date >= start,
        VehicleListing.scrape_date < end
    ).all()

    # Build daily table rows
    rows = _build_daily_table(listings, report_date.strftime("%Y-%m-%d"))

    print("Daily Report Table:")
    print("="*120)
    print(f"{'Model':<30} | {'Year':<15} | {'Depreciation':<20} | {'Dealer Name':<50}")
    print("="*120)

    for row in rows:
        model = row['name_model']
        year = row['year_registered']
        depreciation = row['depreciation']
        dealer = row['dealer_name']

        print(f"{model:<30} | {year:<15} | {depreciation:<20} | {dealer:<50}")

    print("="*120)
    print(f"\nTotal rows: {len(rows)}")

    # Check for "Various"
    various_count = sum(1 for row in rows if row['dealer_name'] == 'Various')
    print(f"Rows with 'Various': {various_count}")

    # Check for multiple dealers (comma-separated)
    multi_dealer_count = sum(1 for row in rows if ',' in row['dealer_name'])
    print(f"Rows with multiple dealers (comma-separated): {multi_dealer_count}")

    if various_count > 0:
        print("\n[WARNING] Still found 'Various' in dealer names!")
    else:
        print("\n[SUCCESS] No 'Various' found - all dealer names are properly displayed!")

finally:
    db.close()
