"""
Remove duplicate entries from database (keep the most recent one)
"""
from database import SessionLocal, VehicleListing
from sqlalchemy import func

db = SessionLocal()

try:
    # Find duplicates based on listing_url
    print("Finding duplicates...")

    # Get all URLs with counts
    url_counts = db.query(
        VehicleListing.listing_url,
        func.count(VehicleListing.id).label('count')
    ).group_by(VehicleListing.listing_url).having(func.count(VehicleListing.id) > 1).all()

    print(f"Found {len(url_counts)} URLs with duplicates\n")

    total_removed = 0

    for url, count in url_counts:
        print(f"Processing: {url}")
        print(f"  Count: {count}")

        # Get all entries for this URL, ordered by scrape_date (newest first)
        items = db.query(VehicleListing).filter(
            VehicleListing.listing_url == url
        ).order_by(VehicleListing.scrape_date.desc()).all()

        if len(items) > 1:
            # Keep the first (newest), delete the rest
            keep = items[0]
            to_delete = items[1:]

            print(f"  Keeping: ID={keep.id}, scraped at {keep.scrape_date}")
            print(f"  Removing {len(to_delete)} duplicates...")

            for item in to_delete:
                print(f"    - ID={item.id}, scraped at {item.scrape_date}")
                db.delete(item)
                total_removed += 1

            db.commit()
            print()

    print(f"{'='*60}")
    print(f"Removed {total_removed} duplicate entries")
    print(f"{'='*60}")

except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
