"""Check alignment of year, depreciation, and dealer per listing"""
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

    # Get sample: HINO DUTRO 2.8
    listings = db.query(VehicleListing).filter(
        VehicleListing.scrape_date >= start,
        VehicleListing.scrape_date < end,
        VehicleListing.make_model.like('%HINO%DUTRO%')
    ).all()

    print(f"HINO DUTRO listings ({len(listings)} total):")
    print("="*100)

    # Show raw data
    for i, L in enumerate(listings, 1):
        print(f"{i}. {L.make_model[:40]}")
        print(f"   Dealer: {L.dealer_name}")
        print(f"   Year:   {L.registered_year}")
        print(f"   Deprec: {L.depreciation}")
        print()

    print("\n" + "="*100)
    print("What user wants (unique combinations aligned):")
    print("="*100)

    # Get unique combinations
    unique_items = []
    seen = set()

    for L in sorted(listings, key=lambda x: (x.dealer_name or "", x.registered_year or 0)):
        key = (L.dealer_name, L.registered_year, L.depreciation)
        if key not in seen:
            seen.add(key)
            unique_items.append({
                "dealer": L.dealer_name or "–",
                "year": L.registered_year or "–",
                "depreciation": L.depreciation or "–"
            })

    print(f"\nUnique combinations: {len(unique_items)}")

    # Show aligned
    dealers = [item["dealer"] for item in unique_items]
    years = [str(item["year"]) for item in unique_items]
    depreciations = [item["depreciation"] for item in unique_items]

    print("\nAligned format:")
    print(f"Dealers:      {', '.join(dealers)}")
    print(f"Years:        {', '.join(years)}")
    print(f"Depreciation: {', '.join(depreciations)}")

    print("\n\nPer item breakdown:")
    for i, item in enumerate(unique_items, 1):
        print(f"{i}. {item['dealer']:30} | {item['year']:6} | {item['depreciation']}")

finally:
    db.close()
