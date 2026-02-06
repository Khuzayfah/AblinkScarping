"""Verify final alignment with unique combinations"""
from main import _build_daily_table
from database import SessionLocal, VehicleListing
from datetime import datetime, timedelta

db = SessionLocal()

try:
    latest = db.query(VehicleListing).order_by(VehicleListing.scrape_date.desc()).first()
    if not latest:
        print("No data found")
        exit()

    report_date = latest.scrape_date.date()
    start = datetime.combine(report_date, datetime.min.time())
    end = start + timedelta(days=1)
    listings = db.query(VehicleListing).filter(
        VehicleListing.scrape_date >= start,
        VehicleListing.scrape_date < end
    ).all()

    rows = _build_daily_table(listings, report_date.strftime("%Y-%m-%d"))

    # Show models with multiple values
    print("Models with Aligned Comma-Separated Values:")
    print("="*120)

    for row in rows:
        dealer = row['dealer_name']
        year = row['year_registered']
        depreciation = row['depreciation']

        # Check if has comma (multiple values)
        if ',' in dealer:
            print(f"\n{row['name_model']}:")

            # Split and count
            dealers = [d.strip() for d in dealer.split(',')]
            years = [y.strip() for y in year.split(',')]
            depreciations = [d.strip() for d in depreciation.split(',')]

            print(f"  Count: {len(dealers)} dealers, {len(years)} years, {len(depreciations)} depreciations")

            # Show alignment
            print(f"\n  {'#':<3} | {'Dealer':<30} | {'Year':<6} | {'Depreciation':<15}")
            print(f"  {'-'*3}-+-{'-'*30}-+-{'-'*6}-+-{'-'*15}")

            for i in range(len(dealers)):
                d_name = dealers[i] if i < len(dealers) else "–"
                y_val = years[i] if i < len(years) else "–"
                dep_val = depreciations[i] if i < len(depreciations) else "–"
                print(f"  {i+1:<3} | {d_name:<30} | {y_val:<6} | {dep_val:<15}")

            # Check if aligned
            if len(dealers) == len(years) == len(depreciations):
                print(f"\n  ✓ ALIGNED: All lists have same length ({len(dealers)} items)")
            else:
                print(f"\n  ✗ NOT ALIGNED: dealers={len(dealers)}, years={len(years)}, depreciations={len(depreciations)}")

    print("\n" + "="*120)
    print("VERIFICATION COMPLETE")

finally:
    db.close()
