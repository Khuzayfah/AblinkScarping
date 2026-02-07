"""Detect sold units (listings that disappeared) and push to Daily Sold Log"""
import logging
import re
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from database import SessionLocal, VehicleListing, SoldLog
from config import TARGET_VEHICLES

logger = logging.getLogger("sold_log")


def _normalize_model(name):
    """Match listing make_model to TARGET_VEHICLES (case-insensitive)."""
    if not name:
        return None
    n = (name or "").upper().strip()
    # Remove "Used " prefix
    if n.startswith("USED "):
        n = n[5:]
    # Remove everything after "REG DATE" or "$"
    for cutoff in ["REG DATE", "REG.DATE", "REGDATE", "$"]:
        idx = n.find(cutoff)
        if idx > 0:
            n = n[:idx]
    # Remove COE suffix
    n = re.sub(r'\s*\((?:COE|NEW|5-YR).*\)', '', n, flags=re.IGNORECASE).strip()
    n = re.sub(r'(\bDYNA)\s+\d+\s+', r'\1 ', n)
    n_clean = re.sub(r'\bCOMMUTER\b', '', n).strip()
    n_clean = re.sub(r'\s+', ' ', n_clean)
    n_clean = re.sub(r'\s+(DX|GL|HIGH ROOF).*$', '', n_clean).strip()
    n_no_trans = re.sub(r'(\d\.\d)[AM]\b', r'\1', n_clean)

    for v in TARGET_VEHICLES:
        vu = v.upper()
        vu_no_trans = re.sub(r'(\d\.\d)[AM]\b', r'\1', vu)
        if vu in n or n in vu:
            return v
        if vu in n_clean or n_clean in vu:
            return v
        if vu_no_trans and (vu_no_trans in n_no_trans or n_no_trans in vu_no_trans):
            return v
        if "ISUZU" in n and ("NHR" in vu and "NHR" in n):
            return v
        if "ISUZU" in n and ("NJR" in vu and "NJR" in n):
            return v
    return None


def detect_and_log_sold():
    """
    Compare previous scrape's listings with today's. Any listing URL that was
    in previous and is not in current = considered sold. Push to SoldLog.
    Only logs vehicles that match TARGET_VEHICLES.
    """
    db = SessionLocal()
    try:
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = today_start + timedelta(days=1)

        # Check if we already have sold log entries for today (avoid duplicates)
        existing = db.query(SoldLog).filter(
            and_(SoldLog.sold_date >= today_start, SoldLog.sold_date < today_end)
        ).count()
        if existing > 0:
            logger.info(f"Sold log already has {existing} entries for {today}, skipping detection")
            return existing

        # Previous scrape date = latest date in DB that is strictly before today
        prev_date_row = db.query(func.date(VehicleListing.scrape_date).label("d")).filter(
            func.date(VehicleListing.scrape_date) < today
        ).order_by(func.date(VehicleListing.scrape_date).desc()).first()
        if not prev_date_row:
            logger.warning("No previous scrape data found - cannot detect sold vehicles")
            return 0

        prev_date = prev_date_row[0]
        prev_start = datetime.combine(datetime.strptime(str(prev_date), '%Y-%m-%d').date(), datetime.min.time())
        prev_end = prev_start + timedelta(days=1)

        logger.info(f"Comparing listings: {prev_date} vs {today}")

        previous_listings = db.query(VehicleListing).filter(
            VehicleListing.scrape_date >= prev_start,
            VehicleListing.scrape_date < prev_end,
        ).all()

        current_listings = db.query(VehicleListing).filter(
            VehicleListing.scrape_date >= today_start,
            VehicleListing.scrape_date < today_end,
        ).all()

        if not previous_listings:
            logger.warning(f"No previous listings found for {prev_date}")
            return 0
        if not current_listings:
            logger.warning(f"No current listings found for {today}")
            return 0

        logger.info(f"  Previous ({prev_date}): {len(previous_listings)} listings")
        logger.info(f"  Current  ({today}): {len(current_listings)} listings")

        previous_urls = {l.listing_url for l in previous_listings if l.listing_url}
        current_urls = {l.listing_url for l in current_listings if l.listing_url}
        sold_urls = previous_urls - current_urls

        if not sold_urls:
            logger.info("No sold vehicles detected (0 listings disappeared)")
            return 0

        logger.info(f"  Disappeared URLs: {len(sold_urls)}")

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
            if not dep or dep == "–":
                if row.price is not None:
                    dep = f"${row.price:,.0f}"
                else:
                    dep = "–"

            db.add(SoldLog(
                sold_date=today_start,
                make_model=row.make_model or "",
                year_registered=row.registered_year,
                depreciation=dep,
                dealer_name=row.dealer_name or "–",
                price=row.price,
                listing_url=row.listing_url or "",
            ))
            logged += 1
            logger.info(f"  [SOLD] {row.make_model} | Year: {row.registered_year} | Dep: {dep} | Dealer: {row.dealer_name} | Price: {row.price}")

        if logged:
            db.commit()
            logger.info(f"[OK] Daily Sold Log: pushed {logged} sold unit(s) for {today}")
        else:
            logger.info("No target vehicles sold today")

        return logged
    except Exception as e:
        logger.error(f"Error in detect_and_log_sold: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 0
    finally:
        db.close()
