"""Check sold log data"""
from database import SessionLocal, SoldLog
from sqlalchemy import func

db = SessionLocal()

try:
    # Get all sold items
    sold_items = db.query(SoldLog).order_by(SoldLog.sold_date.desc()).all()

    print(f"Total sold items: {len(sold_items)}\n")

    # Group by dealer name
    dealer_counts = db.query(
        SoldLog.dealer_name,
        func.count(SoldLog.id).label('count')
    ).group_by(SoldLog.dealer_name).order_by(func.count(SoldLog.id).desc()).all()

    print("Sold items by dealer:")
    print("="*60)
    for dealer, count in dealer_counts:
        print(f"{dealer}: {count} items")

    # Show "Various" items
    print("\n" + "="*60)
    print("Items with 'Various' dealer name:")
    print("="*60)
    various_items = db.query(SoldLog).filter(
        SoldLog.dealer_name == 'Various'
    ).all()

    for item in various_items[:10]:  # Show first 10
        print(f"\n- {item.make_model[:60]}")
        print(f"  Dealer: {item.dealer_name}")
        print(f"  Year: {item.year_registered}")
        print(f"  Depreciation: {item.depreciation}")
        print(f"  Sold date: {item.sold_date}")

    # Show items with "–" dealer name
    print("\n" + "="*60)
    print("Items with '–' dealer name:")
    print("="*60)
    dash_items = db.query(SoldLog).filter(
        SoldLog.dealer_name == '–'
    ).all()

    for item in dash_items[:10]:  # Show first 10
        print(f"\n- {item.make_model[:60]}")
        print(f"  Dealer: {item.dealer_name}")
        print(f"  Year: {item.year_registered}")
        print(f"  Depreciation: {item.depreciation}")
        print(f"  Sold date: {item.sold_date}")

finally:
    db.close()
