from database import SessionLocal, VehicleListing

db = SessionLocal()
items = db.query(VehicleListing).filter(
    VehicleListing.dealer_name.like('%Direct%')
).all()

print(f'Found {len(items)} Direct Owner listings:\n')
for item in items:
    print(f'- {item.make_model[:60]}')
    print(f'  Dealer: {item.dealer_name}')
    print(f'  Price: ${item.price:,}')
    print(f'  Depreciation: {item.depreciation}')
    print(f'  URL: {item.listing_url}')
    print()
