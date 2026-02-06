"""Check if there are models with multiple dealers"""
from database import SessionLocal, VehicleListing
from datetime import datetime
from collections import defaultdict

db = SessionLocal()

try:
    # Get latest scrape date
    latest = db.query(VehicleListing).order_by(VehicleListing.scrape_date.desc()).first()
    if not latest:
        print("No data found")
        exit()

    latest_date = latest.scrape_date.date()
    print(f"Latest scrape date: {latest_date}\n")

    # Get all listings from latest date
    start = datetime.combine(latest_date, datetime.min.time())
    end = datetime.combine(latest_date, datetime.max.time())

    listings = db.query(VehicleListing).filter(
        VehicleListing.scrape_date >= start,
        VehicleListing.scrape_date <= end
    ).all()

    print(f"Total listings on {latest_date}: {len(listings)}\n")

    # Aggregate by model
    agg = defaultdict(lambda: {"dealers": set(), "count": 0})

    for L in listings:
        model = L.make_model
        # Normalize model name to base model (e.g., "Toyota Hiace" -> "Toyota Hiace")
        # Group similar models together
        if "Hiace" in model:
            model = "Toyota Hiace"
        elif "Dyna" in model:
            model = "Toyota Dyna"
        elif "Dutro" in model:
            model = "Hino Dutro"
        elif "NV350" in model or "NV-350" in model:
            model = "Nissan NV350"
        elif "NV200" in model or "NV-200" in model:
            model = "Nissan NV200"
        elif "NPR" in model:
            model = "Isuzu NPR"
        elif "NMR" in model:
            model = "Isuzu NMR"

        agg[model]["count"] += 1
        if L.dealer_name and L.dealer_name != "–":
            agg[model]["dealers"].add(L.dealer_name.strip())

    # Show models with multiple dealers
    print("Models with multiple dealers:")
    print("="*80)

    for model, data in sorted(agg.items(), key=lambda x: len(x[1]["dealers"]), reverse=True):
        if len(data["dealers"]) > 1:
            print(f"\n{model}:")
            print(f"  Total units: {data['count']}")
            print(f"  Dealers ({len(data['dealers'])}):")
            for dealer in sorted(data["dealers"]):
                print(f"    - {dealer}")

    # Show how it would appear in the report
    print("\n" + "="*80)
    print("How it will appear in daily report:")
    print("="*80)

    for model, data in sorted(agg.items()):
        if data["dealers"]:
            dealer_str = ", ".join(sorted(data["dealers"]))
            print(f"{model:30} | {dealer_str}")

finally:
    db.close()
