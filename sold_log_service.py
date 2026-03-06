"""Detect sold units (listings that disappeared) and push to Daily Sold Log"""
import logging
import re
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from database import SessionLocal, VehicleListing, SoldLog
from config import TARGET_VEHICLES, VEHICLE_CATEGORIES

logger = logging.getLogger("sold_log")

# Targets in GOODS VAN categories — require passenger variant exclusion
_GOODS_VAN_TARGETS = frozenset(
    m for cat, models in VEHICLE_CATEGORIES.items()
    if 'GOODS VAN' in cat
    for m in models
)
_PASSENGER_VAN_KEYWORDS = frozenset({'COMMUTER', 'CARAVAN', 'MICROBUS', 'URVAN'})


def _normalize_model(name):
    """Match listing make_model to TARGET_VEHICLES (case-insensitive).
    Goods Van passenger variants (Commuter, Caravan, Microbus, Urvan) are excluded.
    """
    if not name:
        return None
    n = (name or "").upper().strip()
    if n.startswith("USED "):
        n = n[5:]
    for cutoff in ["REG DATE", "REG.DATE", "REGDATE", "$"]:
        idx = n.find(cutoff)
        if idx > 0:
            n = n[:idx]
    n = re.sub(r'\s*\((?:COE|NEW|5-YR).*\)', '', n, flags=re.IGNORECASE).strip()
    n = re.sub(r'(\bDYNA)\s+\d+\s+', r'\1 ', n)
    n_clean = re.sub(r'\bCOMMUTER\b', '', n).strip()
    n_clean = re.sub(r'\s+', ' ', n_clean)
    n_clean = re.sub(r'\s+(DX|GL|HIGH ROOF).*$', '', n_clean).strip()
    n_no_trans = re.sub(r'(\d\.\d)[AM]\b', r'\1', n_clean)

    matched = None
    for v in TARGET_VEHICLES:
        vu = v.upper()
        vu_no_trans = re.sub(r'(\d\.\d)[AM]\b', r'\1', vu)
        if vu in n or n in vu:
            matched = v; break
        if vu in n_clean or n_clean in vu:
            matched = v; break
        if vu_no_trans and (vu_no_trans in n_no_trans or n_no_trans in vu_no_trans):
            matched = v; break
        if "ISUZU" in n and ("NHR" in vu and "NHR" in n):
            matched = v; break
        if "ISUZU" in n and ("NJR" in vu and "NJR" in n):
            matched = v; break

    if matched is None:
        return None

    # Goods Van passenger exclusion
    if matched in _GOODS_VAN_TARGETS:
        n_upper = name.upper()
        for kw in _PASSENGER_VAN_KEYWORDS:
            if kw in n_upper:
                return None
    return matched


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

        # Get existing sold URLs for today to skip duplicates (allows re-detect after clear)
        existing_sold_urls = set()
        existing_rows = db.query(SoldLog.listing_url).filter(
            and_(SoldLog.sold_date >= today_start, SoldLog.sold_date < today_end)
        ).all()
        for row in existing_rows:
            if row[0]:
                existing_sold_urls.add(row[0].split('?')[0])
        if existing_sold_urls:
            logger.info(f"Already have {len(existing_sold_urls)} sold entries for {today}, will skip duplicates")

        # Previous scrape date = latest date in DB that is strictly before today
        prev_date_row = db.query(func.date(VehicleListing.scrape_date).label("d")).filter(
            func.date(VehicleListing.scrape_date) < today
        ).order_by(func.date(VehicleListing.scrape_date).desc()).first()
        if not prev_date_row:
            logger.warning("No previous scrape data found - cannot detect sold vehicles")
            return 0

        prev_date_obj = datetime.strptime(str(prev_date_row[0]), '%Y-%m-%d').date()
        gap_days = (today - prev_date_obj).days
        MAX_GAP_DAYS = 2  # Only compare consecutive scrapes (max 2-day gap)
        if gap_days > MAX_GAP_DAYS:
            logger.warning(
                f"Skipping sold detection: gap is {gap_days} days (prev={prev_date_obj}, today={today}). "
                f"Gap too large — cannot reliably attribute sold units to a single day. "
                f"Run daily scrapes to enable per-day sold tracking."
            )
            return 0

        prev_date = prev_date_obj
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
        skipped = 0
        for url in sold_urls:
            # Skip if already logged today
            clean_url = url.split('?')[0] if url else ''
            if clean_url and clean_url in existing_sold_urls:
                skipped += 1
                continue

            row = prev_by_url.get(url)
            if not row:
                continue
            # Only log if it's one of our target vehicles
            if _normalize_model(row.make_model) is None:
                continue

            dep = (row.depreciation or "").strip()
            if not dep or dep == "–":
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
            logger.info(f"  [SOLD] {row.make_model} | Year: {row.registered_year} | Dep: {dep} | Dealer: {row.dealer_name}")

        if logged:
            db.commit()
            logger.info(f"[OK] Daily Sold Log: pushed {logged} sold unit(s) for {today} (skipped {skipped} duplicates)")
        else:
            logger.info(f"No new target vehicles sold today (skipped {skipped} duplicates)")

        return logged
    except Exception as e:
        logger.error(f"Error in detect_and_log_sold: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 0
    finally:
        db.close()
