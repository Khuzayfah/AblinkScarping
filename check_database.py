"""Check what's in database"""
from database import SessionLocal, VehicleListing
from datetime import datetime, timedelta

db = SessionLocal()

# Get latest scrape
latest_scrape = db.query(VehicleListing).order_by(VehicleListing.scrape_date.desc()).first()

if latest_scrape:
    print(f"Latest scrape time: {latest_scrape.scrape_date}")

    # Get all from latest scrape
    today = latest_scrape.scrape_date.date()
    tomorrow = today + timedelta(days=1)

    items = db.query(VehicleListing).filter(
        VehicleListing.scrape_date >= datetime.combine(today, datetime.min.time()),
        VehicleListing.scrape_date < datetime.combine(tomorrow, datetime.min.time())
    ).all()

    print(f"\nTotal items from latest scrape: {len(items)}")

    # Check dealer names
    with_dealer = sum(1 for x in items if x.dealer_name and x.dealer_name != "–")
    print(f"Items WITH dealer name: {with_dealer} ({with_dealer/len(items)*100:.1f}%)")
    print(f"Items WITHOUT dealer name: {len(items) - with_dealer} ({(len(items)-with_dealer)/len(items)*100:.1f}%)")

    # Check depreciation
    with_deprec = sum(1 for x in items if x.depreciation and x.depreciation.strip())
    print(f"\nItems WITH depreciation: {with_deprec} ({with_deprec/len(items)*100:.1f}%)")
    print(f"Items WITHOUT depreciation: {len(items) - with_deprec}")

    # Sample data
    print(f"\n{'='*80}")
    print("SAMPLE DATA (first 5):")
    print(f"{'='*80}")
    for i, item in enumerate(items[:5], 1):
        print(f"\n{i}. {item.make_model}")
        print(f"   Year: {item.registered_year or 'N/A'}")
        print(f"   Price: ${item.price:,.0f}" if item.price else "   Price: N/A")
        print(f"   Depreciation: {item.depreciation or 'NOT FOUND'}")
        print(f"   Dealer: {item.dealer_name or 'NOT FOUND'}")
        print(f"   URL: {item.listing_url[:60]}..." if item.listing_url else "   URL: N/A")

    print(f"\n{'='*80}")
    print("ITEMS WITHOUT DEALER NAME (sample 5):")
    print(f"{'='*80}")
    no_dealer = [x for x in items if not x.dealer_name or x.dealer_name == "–"]
    for i, item in enumerate(no_dealer[:5], 1):
        print(f"\n{i}. {item.make_model}")
        print(f"   URL: {item.listing_url}")
        print(f"   Additional info: {item.additional_info[:100] if item.additional_info else 'N/A'}")

else:
    print("No data in database yet!")

db.close()
