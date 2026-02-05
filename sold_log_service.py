"""Detect sold units (listings that disappeared) and push to Daily Sold Log"""
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import SessionLocal, VehicleListing, SoldLog
from config import TARGET_VEHICLES


def _normalize_model(name):
    if not name:
        return None
    n = (name or "").upper().strip()
    for v in TARGET_VEHICLES:
        if v.upper() in n or n in v.upper():
            return v
    return None


def detect_and_log_sold():
    """
    Compare previous scrape's listings with today's. Any listing URL that was
    in previous and is not in current = considered sold. Push to SoldLog.
    """
    db = SessionLocal()
    try:
        today = datetime.now().date()
        # Previous scrape date = latest date in DB that is strictly before today
        prev_date_row = db.query(func.date(VehicleListing.scrape_date).label("d")).filter(
            func.date(VehicleListing.scrape_date) < today
        ).order_by(func.date(VehicleListing.scrape_date).desc()).first()
        if not prev_date_row:
            return

        prev_date = prev_date_row[0]
        prev_start = datetime.combine(prev_date, datetime.min.time())
        prev_end = prev_start + timedelta(days=1)
        today_start = datetime.combine(today, datetime.min.time())
        today_end = today_start + timedelta(days=1)

        previous_listings = db.query(VehicleListing).filter(
            VehicleListing.scrape_date >= prev_start,
            VehicleListing.scrape_date < prev_end,
        ).all()

        current_listings = db.query(VehicleListing).filter(
            VehicleListing.scrape_date >= today_start,
            VehicleListing.scrape_date < today_end,
        ).all()

        previous_urls = {l.listing_url for l in previous_listings if l.listing_url}
        current_urls = {l.listing_url for l in current_listings if l.listing_url}
        sold_urls = previous_urls - current_urls
        if not sold_urls:
            return

        prev_by_url = {l.listing_url: l for l in previous_listings if l.listing_url}
        logged = 0
        for url in sold_urls:
            row = prev_by_url.get(url)
            if not row:
                continue
            # Only log if it's one of our target vehicles
            if _normalize_model(row.make_model) is None:
                continue
            dep = (row.depreciation or "").strip()
            if not dep and row.price is not None:
                dep = f"${row.price:,.0f}"
            if not dep:
                dep = "–"
            log = SoldLog(
                sold_date=datetime.combine(today, datetime.min.time()),
                make_model=row.make_model or "",
                year_registered=row.registered_year,
                depreciation=dep or "–",
                dealer_name=row.dealer_name or "–",
            )
            db.add(log)
            logged += 1
        if logged:
            db.commit()
            print(f"Daily Sold Log: pushed {logged} sold unit(s)")
    except Exception as e:
        print(f"Error in detect_and_log_sold: {e}")
        db.rollback()
    finally:
        db.close()
