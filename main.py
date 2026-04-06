"""Main FastAPI application - Ablink SGCarmart Scraper"""
import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Body, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict
import os
from contextlib import asynccontextmanager

from database import init_db, get_db, VehicleListing, DailyReport, ScrapeLog, AppSetting, SoldLog, SgcarmartSold, ListingCache
from js_scraper import SGCarMartJSScraper, calculate_depreciation
from export_service import ExportService
from scheduler import ScraperScheduler
from sold_log_service import detect_and_log_sold
import config

logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Initialize database
init_db()

# Initialize scheduler
scheduler = ScraperScheduler()


def _ensure_scrape_log(db: Session):
    """Ensure one ScrapeLog row exists"""
    log = db.query(ScrapeLog).first()
    if not log:
        log = ScrapeLog(last_scrape_at=None, status="Ready")
        db.add(log)
        db.commit()
        db.refresh(log)
    return log


def _get_schedule_from_db(db: Session) -> tuple:
    """Get schedule hour, minute, interval_days from DB or config"""
    h = db.query(AppSetting).filter(AppSetting.key == "schedule_hour").first()
    m = db.query(AppSetting).filter(AppSetting.key == "schedule_minute").first()
    i = db.query(AppSetting).filter(AppSetting.key == "schedule_interval_days").first()
    hour = int(h.value) if h else config.SCRAPING_SCHEDULE_HOUR
    minute = int(m.value) if m else config.SCRAPING_SCHEDULE_MINUTE
    interval_days = int(i.value) if i else 1
    return hour, minute, interval_days


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    from database import SessionLocal
    try:
        db = SessionLocal()
        try:
            hour, minute, interval_days = _get_schedule_from_db(db)
            scheduler.set_initial_schedule(hour, minute, interval_days)
            logger.info(f"Loaded schedule from DB: {hour:02d}:{minute:02d} SGT, every {interval_days} day(s)")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not load schedule from DB, using defaults: {e}")
    scheduler.start()
    logger.info("Application started. Scheduler is running.")

    # Run backfill + integrity check on startup
    try:
        from database import SessionLocal as _SL
        _db = _SL()
        try:
            # Backfill missing data from cache
            logger.info("[STARTUP] Running sold data backfill...")
            SGCarMartJSScraper._backfill_sold_depreciation(_db)
            logger.info("[STARTUP] Backfill complete.")

            # SoldLog integrity scan: flag dates with suspiciously high sold counts
            from sqlalchemy import func as _fn
            sus = _db.query(
                _fn.date(SoldLog.sold_date).label('d'),
                _fn.count(SoldLog.id).label('cnt')
            ).group_by(_fn.date(SoldLog.sold_date)).having(_fn.count(SoldLog.id) > 200).all()
            if sus:
                for s in sus:
                    logger.warning(f"[INTEGRITY] SoldLog date {s.d} has {s.cnt} entries — possible accumulated data (>200 threshold)")
            else:
                logger.info("[STARTUP] SoldLog integrity OK — no suspicious dates found")
        finally:
            _db.close()
    except Exception as e:
        logger.warning(f"[STARTUP] Backfill/integrity check failed: {e}")

    yield
    scheduler.stop()
    logger.info("Application shutting down.")

# Initialize FastAPI app
app = FastAPI(
    title="Ablink SGCarmart Scraper",
    description="Real-time Market Data from SGCarmart.com | By Oneiros Indonesia",
    version="1.0.0",
    lifespan=lifespan
)

# API Endpoints

@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    next_run = scheduler.get_next_run_time()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "next_scheduled_scrape": next_run.isoformat() if next_run else None
    }


@app.get("/api/vehicle-categories")
async def get_vehicle_categories():
    """Get vehicle categories and models from config"""
    return {
        "categories": config.VEHICLE_CATEGORIES,
        "target_vehicles": config.TARGET_VEHICLES
    }

@app.post("/api/scrape")
async def manual_scrape(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger manual scraping (Refresh Data)"""
    log = _ensure_scrape_log(db)
    if log.status == "Scraping":
        raise HTTPException(status_code=409, detail="Scrape already in progress")
    log.status = "Scraping"
    db.commit()

    def run_scrape():
        from database import SessionLocal
        scraper = SGCarMartJSScraper(headless=True)
        try:
            # Step 1: Scrape active listings
            logger.info("[MANUAL] Step 1/3: Scraping active listings...")
            results = scraper.scrape_vehicle_listings()
            active_count = len(results) if results else 0
            logger.info(f"[MANUAL] Active listings: {active_count} vehicles found")

            # Step 2: Detect sold by comparison (previous vs current) → sold_log
            comparison_sold = 0
            if results:
                logger.info("[MANUAL] Step 2/3: Detecting sold vehicles (comparison)...")
                comparison_sold = detect_and_log_sold()
                logger.info(f"[MANUAL] Sold today: {comparison_sold} vehicles disappeared since last scrape")
            else:
                logger.warning("[MANUAL] Skipping sold detection - no active listings scraped")

            # Step 3: Scrape accumulated sold from SGCarMart (avl=s) → sgcarmart_sold
            logger.info("[MANUAL] Step 3/3: Scraping SGCarMart sold listings (avl=s)...")
            sold_results = scraper.scrape_sold_listings()
            avl_count = len(sold_results) if sold_results else 0
            logger.info(f"[MANUAL] SGCarMart sold (accumulated): {avl_count} vehicles")

            logger.info(f"[MANUAL] Complete: Active={active_count} | Sold today={comparison_sold} | SGCarMart sold={avl_count}")
        except Exception as e:
            logger.error(f"Scrape failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            d = SessionLocal()
            try:
                lg = d.query(ScrapeLog).first()
                if lg:
                    lg.status = "Ready"
                    lg.last_scrape_at = datetime.now()
                    d.commit()
                    logger.info("Scrape status set to Ready")
            finally:
                d.close()

    background_tasks.add_task(run_scrape)
    return {
        "message": "Scraping started in background",
        "status": "Scraping",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/status")
async def get_status(db: Session = Depends(get_db)):
    """Get scraper status: last scrape time, current status, schedule"""
    log = _ensure_scrape_log(db)
    hour, minute, interval_days = _get_schedule_from_db(db)
    next_run = scheduler.get_next_run_time()
    next_run_display = None
    if next_run:
        next_run_display = next_run.strftime("%Y-%m-%d %H:%M SGT")
    return {
        "status": log.status,
        "last_scrape_at": log.last_scrape_at.strftime("%Y-%m-%d %H:%M:%S") if log.last_scrape_at else None,
        "schedule": {"hour": hour, "minute": minute, "interval_days": interval_days},
        "schedule_display": f"{hour:02d}:{minute:02d} SGT (every {interval_days} day{'s' if interval_days > 1 else ''})",
        "next_scheduled_scrape": next_run.isoformat() if next_run else None,
        "next_run_display": next_run_display,
        "timezone": "Asia/Singapore (SGT)"
    }


@app.post("/api/schedule")
async def update_schedule(
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Update auto scrape schedule (e.g. { \"hour\": 9, \"minute\": 0, \"interval_days\": 1 })"""
    hour = body.get("hour", 9)
    minute = body.get("minute", 0)
    interval_days = body.get("interval_days", 1)

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise HTTPException(status_code=400, detail="Invalid hour or minute")
    if interval_days not in [1, 2]:
        raise HTTPException(status_code=400, detail="Interval must be 1 or 2 days")

    for key, val in [("schedule_hour", str(hour)), ("schedule_minute", str(minute)), ("schedule_interval_days", str(interval_days))]:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = val
        else:
            db.add(AppSetting(key=key, value=val))
    db.commit()
    scheduler.update_schedule(hour, minute, interval_days)

    return {
        "schedule": {"hour": hour, "minute": minute, "interval_days": interval_days},
        "schedule_display": f"{hour:02d}:{minute:02d} (every {interval_days} day{'s' if interval_days > 1 else ''})"
    }

@app.get("/api/listings")
async def get_listings(
    date: Optional[str] = None,
    make_model: Optional[str] = None,
    limit: int = 5000,
    db: Session = Depends(get_db)
):
    """Get vehicle listings — target vehicles only, deduped, enriched from cache"""
    query = db.query(VehicleListing)

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            next_date = target_date + timedelta(days=1)
            query = query.filter(
                and_(
                    VehicleListing.scrape_date >= target_date,
                    VehicleListing.scrape_date < next_date
                )
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if make_model:
        query = query.filter(VehicleListing.make_model.ilike(f"%{make_model}%"))

    all_rows = query.order_by(VehicleListing.scrape_date.desc()).all()

    # Build ListingCache lookup for enrichment
    cache_map = {}
    for c in db.query(ListingCache).all():
        if c.listing_url_clean:
            cache_map[c.listing_url_clean] = c

    # Filter to target vehicles + dedup by URL (same as dep table)
    seen_urls = set()
    filtered = []
    for r in all_rows:
        raw_url = getattr(r, 'listing_url', '') or ''
        clean_url = _url_dedup_key(raw_url)
        if clean_url:
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
        model = _normalize_model(r.make_model)
        if not model:
            continue
        model = config.TARGET_DISPLAY_NAMES.get(model, model)
        d = r.to_dict()
        d['matched_model'] = model
        # Enrich from ListingCache for empty fields
        cached = cache_map.get(clean_url) if clean_url else None
        if cached:
            if not d.get('depreciation') or d['depreciation'] in ('', '–', '$0/yr', None):
                if cached.depreciation and cached.depreciation not in ('', '–', '$0/yr'):
                    d['depreciation'] = cached.depreciation
            if not d.get('dealer_name') or d['dealer_name'] in ('', '–', None):
                if cached.dealer_name and cached.dealer_name not in ('', '–'):
                    d['dealer_name'] = cached.dealer_name
        # Skip items without year or year < 2014 (same as dep table — ensures count consistency)
        year_val = d.get('registered_year') or d.get('year_registered')
        if not year_val or year_val in (0, None):
            continue
        try:
            if int(year_val) < 2014:
                continue
        except (ValueError, TypeError):
            continue
        filtered.append(d)

    return filtered[:limit]

# Targets in GOODS VAN categories — require passenger variant exclusion
_GOODS_VAN_TARGETS = frozenset(
    m for cat, models in config.VEHICLE_CATEGORIES.items()
    if 'GOODS VAN' in cat
    for m in models
)
# Passenger/commuter keywords: if found in the raw model name AND the matched target
# is a GOODS VAN model, reject the match (it's a people carrier, not a cargo van)
_PASSENGER_VAN_KEYWORDS = frozenset({'COMMUTER', 'CARAVAN', 'MICROBUS', 'URVAN'})


def _normalize_model(name: str) -> Optional[str]:
    """Match listing make_model to TARGET_VEHICLES (case-insensitive).
    Handles names like 'Toyota Dyna 150 3.0M (COE till 01/2031)' -> 'TOYOTA DYNA 150 3.0'
    Also handles dirty names like 'Used Toyota Dyna 150 3.0MReg Date: ...$99,988'
    Goods Van passenger variants (Commuter, Caravan, Microbus, Urvan) are excluded.
    """
    if not name:
        return None
    # Clean the name
    n = name.upper().strip()
    # Remove "Used " prefix
    if n.startswith("USED "):
        n = n[5:]
    # Remove everything after "REG DATE" or "$" (price)
    for cutoff in ["REG DATE", "REG.DATE", "REGDATE", "$"]:
        idx = n.find(cutoff)
        if idx > 0:
            n = n[:idx]
    # Remove COE suffix
    import re
    n = re.sub(r'\s*\((?:COE|NEW|5-YR).*\)', '', n, flags=re.IGNORECASE).strip()
    # Remove intermediate model numbers like "150" in "DYNA 150 3.0M"
    n = re.sub(r'(\bDYNA)\s+\d+\s+', r'\1 ', n)
    # Detect HIGH ROOF before stripping (needed for separate HIGH ROOF targets)
    has_high_roof = 'HIGH ROOF' in n
    # "COMMUTER" suffix removal for Hiace matching (still match, but will be rejected for GOODS VAN below)
    n_no_commuter = re.sub(r'\bCOMMUTER\b', '', n).strip()
    n_no_commuter = re.sub(r'\s+', ' ', n_no_commuter)
    # "DX" / "GL" / "HIGH ROOF" suffix removal for matching
    n_clean = re.sub(r'\s+(DX|GL|HIGH ROOF).*$', '', n_no_commuter).strip()

    # Two-pass matching: first try exact (with A/M), then try transmission-agnostic
    n_no_trans = re.sub(r'(\d\.\d)[AM]\b', r'\1', n_clean)

    matched = None

    # PASS 0: HIGH ROOF specific match (check before general matching)
    # Any COMMUTER + HIGH ROOF listing matches the HIGH ROOF target by engine size
    if has_high_roof and 'COMMUTER' in n:
        for v in config.TARGET_VEHICLES:
            vu = v.upper()
            if 'HIGH ROOF' not in vu:
                continue
            # Match by engine size (e.g., 2.8A or 3.0A)
            engine = re.search(r'(\d\.\d[AM]?)', vu)
            if engine and engine.group(1) in n:
                matched = v; break

    # PASS 0.5: COMMUTER (non-HIGH ROOF) specific match
    # "Commuter 3.0A DX" must match "COMMUTER 3.0A GL" target, not "HIACE 3.0A" goods van.
    # Without this, n_no_commuter strips COMMUTER and mis-matches the goods van target,
    # which then gets rejected by passenger exclusion → data silently lost.
    # Uses base engine size (e.g., "3.0") so 3.0M also matches 3.0A target.
    if matched is None and 'COMMUTER' in n and not has_high_roof:
        for v in config.TARGET_VEHICLES:
            vu = v.upper()
            if 'HIGH ROOF' in vu or 'COMMUTER' not in vu:
                continue
            engine = re.search(r'(\d\.\d)', vu)
            if engine and engine.group(1) in n:
                matched = v; break

    # PASS 1: Exact match (preserves A/M distinction like 3.0A vs 3.0M)
    if matched is None:
        for v in config.TARGET_VEHICLES:
            vu = v.upper()
            if 'HIGH ROOF' in vu:
                continue  # Skip HIGH ROOF targets in general matching (handled in PASS 0)
            if vu in n or n in vu:
                matched = v; break
            if vu in n_no_commuter or n_no_commuter in vu:
                matched = v; break
            if vu in n_clean or n_clean in vu:
                matched = v; break
            # Special: match "ISUZU NHR87A" to "ISUZU NHR"
            if "ISUZU" in n and vu == "ISUZU NHR" and "NHR" in n:
                matched = v; break
            if "ISUZU" in n and vu == "ISUZU NJR" and "NJR" in n:
                matched = v; break

    # PASS 2: Transmission-agnostic fallback (A/M stripped)
    if matched is None:
        for v in config.TARGET_VEHICLES:
            vu = v.upper()
            if 'HIGH ROOF' in vu:
                continue
            vu_no_trans = re.sub(r'(\d\.\d)[AM]\b', r'\1', vu)
            if vu_no_trans and (vu_no_trans in n_no_trans or n_no_trans in vu_no_trans):
                matched = v; break

    if matched is None:
        return None

    # Goods Van passenger exclusion: if the matched target is in a GOODS VAN category,
    # reject the match when the original name contains a passenger variant keyword
    if matched in _GOODS_VAN_TARGETS:
        n_upper = name.upper()
        for kw in _PASSENGER_VAN_KEYWORDS:
            if kw in n_upper:
                return None  # Passenger/commuter variant — not a cargo goods van
    return matched


def _url_dedup_key(url):
    """Return a unique key for URL deduplication.
    Old-format URLs (info.php?ID=xxx): keep full URL — stripping query would collapse all to same path.
    New-format URLs (used-cars/info/name-id/): strip query params (safe, path is unique).
    """
    if not url:
        return ''
    if 'info.php' in url and '?ID=' in url:
        return url  # Old format: ID is in query string, keep it
    return url.split('?')[0]  # New format: path is unique


def _build_daily_table(sold_rows: list, report_date: str) -> Dict[str, Any]:
    """Build daily table grouped by vehicle category from SOLD data only."""
    # Aggregate by normalized model
    agg = defaultdict(lambda: {"items": []})
    for row in sold_rows:
        model = _normalize_model(row.make_model)
        if not model:
            continue
        model = config.TARGET_DISPLAY_NAMES.get(model, model)

        dealer = (row.dealer_name or "–").strip()
        year = row.year_registered if row.year_registered else None
        dep = (row.depreciation or "–").strip()
        price = getattr(row, 'price', None)
        raw_name = row.make_model or ''
        agg[model]["items"].append((dealer, year, dep, price, raw_name))

    # Merge combined models (e.g., "ISUZU NHR" + "ISUZU NJR" -> "ISUZU NHR / ISUZU NJR")
    for cat_name, cat_models in config.VEHICLE_CATEGORIES.items():
        for cm in cat_models:
            if " / " in cm:
                parts = [p.strip() for p in cm.split(" / ")]
                combined_items = []
                for part in parts:
                    if part in agg:
                        combined_items.extend(agg[part]["items"])
                        del agg[part]
                if combined_items:
                    agg[cm] = {"items": combined_items}

    # Build grouped structure using VEHICLE_CATEGORIES from config
    groups = []
    for category, models in config.VEHICLE_CATEGORIES.items():
        category_items = []
        for model in models:
            d = agg.get(model, {"items": []})
            items = d["items"]

            if not items:
                category_items.append({
                    "name_model": model,
                    "entries": []
                })
                continue

            items_list = sorted(items, key=lambda x: (x[0], x[1] if x[1] else 0))
            entries = []
            for item in items_list:
                entries.append({
                    "year_registered": str(item[1]) if item[1] else "–",
                    "depreciation": item[2],
                    "dealer_name": item[0],
                    "price": item[3],
                    "raw_name": item[4]
                })

            category_items.append({
                "name_model": model,
                "entries": entries
            })

        groups.append({
            "category": category,
            "models": category_items
        })

    return {
        "date": report_date,
        "groups": groups
    }


@app.get("/api/daily-report")
async def get_daily_report(
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get daily report: sold units grouped by category for a specific date or today."""
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()

    next_date = target_date + timedelta(days=1)

    # Get SOLD data from SoldLog
    sold_rows = db.query(SoldLog).filter(
        and_(
            SoldLog.sold_date >= datetime.combine(target_date, datetime.min.time()),
            SoldLog.sold_date < datetime.combine(next_date, datetime.min.time())
        )
    ).all()

    daily_rows = _build_daily_table(sold_rows, target_date.isoformat())

    # Summary from sold data
    summary = {
        "total_sold": len(sold_rows),
        "date": target_date.isoformat()
    }

    return {
        "date": target_date.isoformat(),
        "summary": summary,
        "daily_table": daily_rows
    }

@app.get("/api/history")
async def get_history(db: Session = Depends(get_db)):
    """Get list of dates that have sold data"""
    dates = db.query(
        func.date(SoldLog.sold_date).label('sold_date'),
        func.count(SoldLog.id).label('count')
    ).group_by(
        func.date(SoldLog.sold_date)
    ).order_by(func.date(SoldLog.sold_date).desc()).all()

    return [{"date": str(d[0]), "count": d[1]} for d in dates]


@app.delete("/api/sold-log/clear")
async def clear_sold_log(
    date: str,
    db: Session = Depends(get_db)
):
    """Clear (delete) sold data for a specific date so it can be re-scraped."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    next_date = target_date + timedelta(days=1)
    deleted = db.query(SoldLog).filter(
        and_(
            SoldLog.sold_date >= datetime.combine(target_date, datetime.min.time()),
            SoldLog.sold_date < datetime.combine(next_date, datetime.min.time())
        )
    ).delete()
    db.commit()

    return {"message": f"Cleared {deleted} sold entries for {date}", "deleted": deleted}


@app.get("/api/sold-log")
async def get_sold_log(
    date: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """Chart 3: Daily Sold Log - entries when a unit from Chart 1 was detected as sold"""
    query = db.query(SoldLog).order_by(SoldLog.sold_date.desc(), SoldLog.id.desc())
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            next_date = target_date + timedelta(days=1)
            query = query.filter(
                and_(
                    SoldLog.sold_date >= datetime.combine(target_date, datetime.min.time()),
                    SoldLog.sold_date < datetime.combine(next_date, datetime.min.time())
                )
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    rows = query.limit(limit).all()
    return [r.to_dict() for r in rows]


@app.get("/api/sgcarmart-sold")
async def get_sgcarmart_sold(
    limit: int = 5000,
    db: Session = Depends(get_db)
):
    """Get accumulated sold listings from SGCarMart (avl=s) - target vehicles only, enriched from cache"""
    rows = db.query(SgcarmartSold).order_by(SgcarmartSold.id.desc()).all()

    # Build ListingCache lookup for enrichment
    cache_map = {}
    for c in db.query(ListingCache).all():
        if c.listing_url_clean:
            cache_map[c.listing_url_clean] = c

    # Filter to target vehicles + dedup by URL (same logic as dep table)
    seen_urls = set()
    filtered = []
    for r in rows:
        raw_url = r.listing_url or ''
        clean_url = _url_dedup_key(raw_url)
        if clean_url:
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
        model = _normalize_model(r.make_model)
        if not model:
            continue
        model = config.TARGET_DISPLAY_NAMES.get(model, model)
        # Enrich from ListingCache for empty fields
        d = r.to_dict()
        d['matched_model'] = model
        cached = cache_map.get(clean_url) if clean_url else None
        if cached:
            if not d.get('depreciation') or d['depreciation'] in ('', '–', '$0/yr', None):
                if cached.depreciation and cached.depreciation not in ('', '–', '$0/yr'):
                    d['depreciation'] = cached.depreciation
            if not d.get('dealer_name') or d['dealer_name'] in ('', '–', None):
                if cached.dealer_name and cached.dealer_name not in ('', '–'):
                    d['dealer_name'] = cached.dealer_name
            if not d.get('price') or d['price'] in (0, None):
                if cached.price and cached.price > 0:
                    d['price'] = cached.price
            if not d.get('year_registered') or d['year_registered'] in (0, None):
                if cached.year_registered and cached.year_registered > 0:
                    d['year_registered'] = cached.year_registered
        # Calculate depreciation from price + year if still missing
        if not d.get('depreciation') or d['depreciation'] in ('', '–', '$0/yr', '$5,001/yr', None):
            price_val = d.get('price')
            yr = d.get('year_registered')
            if price_val and price_val > 0 and yr:
                calc = calculate_depreciation(price_val, f"01-Jul-{yr}", car_name=d.get('make_model'))
                if calc:
                    d['depreciation'] = f"${calc:,}/yr"
        # Skip items without year or year < 2014 (same as dep table — ensures count consistency)
        if not d.get('year_registered') or d['year_registered'] in (0, None):
            continue
        try:
            if int(d['year_registered']) < 2014:
                continue
        except (ValueError, TypeError):
            continue
        filtered.append(d)

    total = len(filtered)
    items = filtered[:limit]
    return {
        "total": total,
        "items": items
    }


@app.get("/api/export/sgcarmart-sold-csv")
async def export_sgcarmart_sold_csv(db: Session = Depends(get_db)):
    """Export all SGCarMart sold listings (avl=s) to CSV"""
    import csv
    from io import StringIO
    rows = db.query(SgcarmartSold).order_by(SgcarmartSold.id.desc()).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['No', 'Date Found Sold', 'Name & Model', 'Year', 'Depreciation', 'Dealer'])
    for idx, r in enumerate(rows, 1):
        scrape_dt = r.scrape_date.strftime("%Y-%m-%d") if r.scrape_date else ''
        writer.writerow([
            idx,
            scrape_dt,
            r.make_model or '',
            r.year_registered if r.year_registered is not None else '',
            r.depreciation or '',
            r.dealer_name or '',
        ])
    csv_bytes = output.getvalue().encode('utf-8')
    from io import BytesIO
    bio = BytesIO(csv_bytes)
    filename = f"sgcarmart_sold_all_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        bio,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _get_daily_table_for_date(target_date, db: Session) -> Dict[str, Any]:
    """Get daily sold table for a given date."""
    next_date = target_date + timedelta(days=1)
    sold_rows = db.query(SoldLog).filter(
        and_(
            SoldLog.sold_date >= datetime.combine(target_date, datetime.min.time()),
            SoldLog.sold_date < datetime.combine(next_date, datetime.min.time())
        )
    ).all()
    return _build_daily_table(sold_rows, target_date.isoformat())


@app.get("/api/export/csv")
async def export_csv(date: Optional[str] = None, db: Session = Depends(get_db)):
    """Export daily table to CSV"""
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = datetime.now().date()
    
    daily_rows = _get_daily_table_for_date(target_date, db)
    csv_file = ExportService.export_daily_table_csv(daily_rows)
    
    filename = f"sgcarmart_daily_{target_date}.csv"
    return StreamingResponse(
        csv_file,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/export/excel")
async def export_excel(date: Optional[str] = None, db: Session = Depends(get_db)):
    """Export daily table to Excel"""
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = datetime.now().date()
    
    daily_rows = _get_daily_table_for_date(target_date, db)
    excel_file = ExportService.export_daily_table_excel(daily_rows)
    
    filename = f"sgcarmart_daily_{target_date}.xlsx"
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/export/pdf")
async def export_pdf(date: Optional[str] = None, db: Session = Depends(get_db)):
    """Export daily table to PDF"""
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = datetime.now().date()
    
    daily_rows = _get_daily_table_for_date(target_date, db)
    pdf_file = ExportService.export_daily_table_pdf(daily_rows, f"SGCarMart Daily Report - {target_date}")
    
    filename = f"sgcarmart_daily_{target_date}.pdf"
    return StreamingResponse(
        pdf_file,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/export/depreciation-csv")
async def export_depreciation_csv(source: str = "active", date: Optional[str] = None, db: Session = Depends(get_db)):
    """Export depreciation table to CSV"""
    dep_result = _get_depreciation_data(source, date, db)
    cats = config.VEHICLE_CATEGORIES
    date_str = dep_result.get("date", "")
    csv_file = ExportService.export_depreciation_csv(dep_result["data"], cats, date_str)
    filename = f"depreciation_{source}_{date_str}.csv"
    return StreamingResponse(csv_file, media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.get("/api/export/depreciation-excel")
async def export_depreciation_excel(source: str = "active", date: Optional[str] = None, db: Session = Depends(get_db)):
    """Export depreciation table to Excel"""
    dep_result = _get_depreciation_data(source, date, db)
    cats = config.VEHICLE_CATEGORIES
    date_str = dep_result.get("date", "")
    excel_file = ExportService.export_depreciation_excel(dep_result["data"], cats, date_str)
    filename = f"depreciation_{source}_{date_str}.xlsx"
    return StreamingResponse(excel_file,
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.get("/api/export/depreciation-pdf")
async def export_depreciation_pdf(source: str = "active", date: Optional[str] = None, db: Session = Depends(get_db)):
    """Export depreciation table to PDF"""
    dep_result = _get_depreciation_data(source, date, db)
    cats = config.VEHICLE_CATEGORIES
    date_str = dep_result.get("date", "")
    title = f"{'Active' if source == 'active' else 'Sold'} Listings - Depreciation / Units"
    pdf_file = ExportService.export_depreciation_pdf(dep_result["data"], cats, date_str, title)
    filename = f"depreciation_{source}_{date_str}.pdf"
    return StreamingResponse(pdf_file, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.post("/api/send-email")
async def send_email_report(date: Optional[str] = None, db: Session = Depends(get_db)):
    """Manually trigger sending the daily report email with Excel + PDF attachments."""
    from email_service import send_daily_report
    import pytz
    if not date:
        date = datetime.now(pytz.timezone('Asia/Singapore')).strftime("%Y-%m-%d")
    ok, msg = send_daily_report(db, date)
    if ok:
        return {"success": True, "message": msg}
    raise HTTPException(status_code=500, detail=msg)


@app.get("/api/gmail-status")
async def gmail_status(db: Session = Depends(get_db)):
    """Return Gmail OAuth2 connection status and email settings."""
    from email_service import get_gmail_status, get_db_setting
    status = get_gmail_status()
    status['recipient'] = get_db_setting(db, 'gmail_recipient', '')
    status['enabled'] = get_db_setting(db, 'gmail_enabled', 'false') == 'true'
    status['has_client_id'] = bool(config.GOOGLE_CLIENT_ID)
    return status


@app.get("/api/gmail-auth-url")
async def gmail_auth_url():
    """Return Google OAuth2 authorization URL for the Gmail sign-in flow."""
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        raise HTTPException(400, "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not set in .env")
    from google_auth_oauthlib.flow import Flow
    from email_service import GMAIL_SCOPES
    flow = Flow.from_client_config(
        {"web": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }},
        scopes=GMAIL_SCOPES,
        redirect_uri=f"http://localhost:{config.APP_PORT}/api/gmail-callback",
    )
    auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
    return {"url": auth_url}


@app.get("/api/gmail-callback")
async def gmail_callback(code: str):
    """Handle Google OAuth2 callback, exchange code for tokens, save to file."""
    from google_auth_oauthlib.flow import Flow
    from email_service import GMAIL_SCOPES, _save_token
    from fastapi.responses import RedirectResponse as RR
    import requests as req_lib

    flow = Flow.from_client_config(
        {"web": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }},
        scopes=GMAIL_SCOPES,
        redirect_uri=f"http://localhost:{config.APP_PORT}/api/gmail-callback",
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Get sender email from Google userinfo
    try:
        resp = req_lib.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=10,
        )
        sender_email = resp.json().get('email', '')
    except Exception:
        sender_email = ''

    _save_token({
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'sender_email': sender_email,
    })
    return RR(url="/?gmail_connected=1")


@app.post("/api/gmail-logout")
async def gmail_logout():
    """Disconnect Gmail by deleting the stored token."""
    import json
    from email_service import _save_token
    _save_token({})
    return {"success": True}


@app.post("/api/gmail-settings")
async def update_gmail_settings(
    recipient: Optional[str] = Body(None),
    enabled: Optional[bool] = Body(None),
    db: Session = Depends(get_db),
):
    """Update recipient email and enable/disable daily email sending."""
    from email_service import set_db_setting
    if recipient is not None:
        set_db_setting(db, 'gmail_recipient', recipient.strip())
    if enabled is not None:
        set_db_setting(db, 'gmail_enabled', 'true' if enabled else 'false')
    return {"success": True}


@app.get("/api/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """Get overall statistics"""
    total_listings = db.query(VehicleListing).count()

    # Get date range
    date_range = db.query(
        func.min(VehicleListing.scrape_date).label('first_date'),
        func.max(VehicleListing.scrape_date).label('last_date')
    ).first()

    # Get unique models count
    unique_models = db.query(VehicleListing.make_model).distinct().count()

    # Get price statistics
    price_stats = db.query(
        func.avg(VehicleListing.price).label('avg_price'),
        func.min(VehicleListing.price).label('min_price'),
        func.max(VehicleListing.price).label('max_price')
    ).first()

    return {
        "total_listings": total_listings,
        "unique_models": unique_models,
        "date_range": {
            "first": date_range.first_date.isoformat() if date_range.first_date else None,
            "last": date_range.last_date.isoformat() if date_range.last_date else None
        },
        "price_statistics": {
            "average": float(price_stats.avg_price) if price_stats.avg_price else 0,
            "minimum": float(price_stats.min_price) if price_stats.min_price else 0,
            "maximum": float(price_stats.max_price) if price_stats.max_price else 0
        }
    }


def _get_depreciation_data(source: str, date: Optional[str], db, days: Optional[int] = None):
    """Shared logic for depreciation-by-year API and export endpoints.
    Returns dict: {date, source, total_rows, data: {model: {year: {lowest, average, unit}}}}
    days: if provided, filter sold data to only include items from last N days
    """
    import re

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            next_date = target_date + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()
        next_date = target_date + timedelta(days=1)

    if source == "sold":
        query = db.query(SgcarmartSold)
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = query.filter(SgcarmartSold.scrape_date >= cutoff_date)
        rows = query.all()
        year_field = 'year_registered'
        # Cache map keyed by listing_url_clean → full ListingCache object
        # (used for depreciation, year, dealer, price enrichment)
        cache_map = {}
        for cache_entry in db.query(ListingCache).all():
            if cache_entry.listing_url_clean:
                cache_map[cache_entry.listing_url_clean] = cache_entry
    else:
        rows = db.query(VehicleListing).filter(
            and_(
                VehicleListing.scrape_date >= target_date,
                VehicleListing.scrape_date < next_date
            )
        ).all()
        year_field = 'registered_year'
        cache_map = None

    def parse_depreciation(dep_str):
        if not dep_str:
            return None
        if dep_str == "$5,001/yr":
            return None
        match = re.search(r'[\d,]+', str(dep_str))
        if match:
            num_str = match.group(0).replace(',', '')
            try:
                val = int(num_str)
                if val == 0 or val == 5001:
                    return None
                return val
            except:
                return None
        return None

    result = {}
    skipped_no_dep = 0
    seen_urls = set()  # Deduplicate by listing_url to prevent inflated counts

    for row in rows:
        # Deduplicate: skip if we already processed this listing URL
        url_field = 'listing_url'
        raw_url = getattr(row, url_field, None) or ''
        clean_url = _url_dedup_key(raw_url)
        if clean_url:
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)

        model = _normalize_model(row.make_model)
        if not model:
            continue
        # Apply display name mapping (e.g., "TOYOTA DYNA 3.0" -> "TOYOTA DYNA 150 3.0")
        model = config.TARGET_DISPLAY_NAMES.get(model, model)
        year = getattr(row, year_field)
        # Try to fill year from ListingCache if missing
        if not year and source == "sold" and clean_url and cache_map:
            cached_obj = cache_map.get(clean_url)
            if cached_obj and cached_obj.year_registered:
                year = cached_obj.year_registered
        if not year:
            continue  # Skip items without year (cannot categorize)
        # Skip items with year < 2014 (not shown in dep table)
        try:
            if int(year) < 2014:
                continue
        except (ValueError, TypeError):
            continue

        dep_value = parse_depreciation(row.depreciation)
        if dep_value is None and source == "sold" and cache_map:
            # Look up by listing URL — cache_map now stores full ListingCache objects
            cached_obj = cache_map.get(clean_url)
            if cached_obj:
                dep_value = parse_depreciation(cached_obj.depreciation)

        # Calculate depreciation from price + registration_date if still missing
        if dep_value is None and source == "sold":
            price_val = getattr(row, 'price', None)
            reg_date_str = None
            # SgcarmartSold doesn't store reg_date string, but we can reconstruct from year
            # Try ListingCache for full data, or use price + year approximation
            if price_val and price_val > 0:
                car_name = row.make_model or ''
                # Try cache for registration_date
                if cache_map and clean_url:
                    cached_obj = cache_map.get(clean_url)
                    if cached_obj and cached_obj.year_registered and price_val:
                        approx_date = f"01-Jul-{cached_obj.year_registered}"
                        dep_value = calculate_depreciation(price_val, approx_date, car_name=car_name)
                # Fallback: use year_registered from the row itself
                if dep_value is None and year and price_val:
                    approx_date = f"01-Jul-{year}"
                    dep_value = calculate_depreciation(price_val, approx_date, car_name=car_name)

        if model not in result:
            result[model] = {}
        if year not in result[model]:
            result[model][year] = {'values': [], 'count': 0}

        # Always count the unit, even if depreciation is unknown
        result[model][year]['count'] += 1
        if dep_value is not None:
            result[model][year]['values'].append(dep_value)
        else:
            skipped_no_dep += 1

    merged = {}
    for model, years_data in result.items():
        merged[model] = {}
        for year, data in years_data.items():
            key = year
            if key not in merged[model]:
                merged[model][key] = {'values': [], 'count': 0}
            merged[model][key]['values'].extend(data['values'])
            merged[model][key]['count'] += data['count']

    # Merge combined models (e.g., "ISUZU NHR" + "ISUZU NJR" -> "ISUZU NHR / ISUZU NJR")
    # Check VEHICLE_CATEGORIES for combined entries (containing " / ")
    combine_map = {}  # individual model -> combined display name
    for cat_name, cat_models in config.VEHICLE_CATEGORIES.items():
        for cm in cat_models:
            if " / " in cm:
                parts = [p.strip() for p in cm.split(" / ")]
                for part in parts:
                    combine_map[part] = cm

    # Merge data from individual models into combined model
    for individual, combined in combine_map.items():
        if individual in merged:
            if combined not in merged:
                merged[combined] = {}
            for year, data in merged[individual].items():
                if year not in merged[combined]:
                    merged[combined][year] = {'values': [], 'count': 0}
                merged[combined][year]['values'].extend(data['values'])
                merged[combined][year]['count'] += data['count']
            del merged[individual]

    # Merge years <= 2015 into "2015 & Older" bucket
    for model in list(merged.keys()):
        older_values = []
        older_count = 0
        years_to_remove = []
        for year in list(merged[model].keys()):
            try:
                if int(year) <= 2015:
                    older_values.extend(merged[model][year]['values'])
                    older_count += merged[model][year]['count']
                    years_to_remove.append(year)
            except (ValueError, TypeError):
                pass
        for y in years_to_remove:
            del merged[model][y]
        if older_count > 0:
            merged[model]["2015 & Older"] = {'values': older_values, 'count': older_count}

    final = {}
    for model, years_data in merged.items():
        final[model] = {}
        for year, data in years_data.items():
            values = data['values']
            final[model][year] = {
                # None = no depreciation data (frontend shows '-')
                # 0 is not used - prevents "$0" being shown
                'lowest': min(values) if values else None,
                'average': int(sum(values) / len(values)) if values else None,
                # unit = ALL units (with or without dep) so count matches sgcarmart-sold total
                'unit': data['count']
            }

    logger.info(f"[DEPRECIATION-BY-YEAR] source={source}, models={len(final)}, skipped_no_dep={skipped_no_dep}")

    date_label = target_date.isoformat() if source == "active" else ("last-" + str(days) + "-days" if days else "all-time")
    return {
        "date": date_label,
        "source": source,
        "total_rows": len(rows),
        "days": days,
        "data": final
    }


@app.get("/api/depreciation-by-year")
async def get_depreciation_by_year(
    date: Optional[str] = None,
    source: str = "active",
    days: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get depreciation aggregated by year and model.
    days: filter sold data to last N days only (e.g., days=60 for last 60 days)
    """
    return _get_depreciation_data(source, date, db, days=days)


# ============================================================
# DEBUG ENDPOINTS - For Debug Console
# ============================================================

@app.post("/api/debug/quick-test")
async def debug_quick_test():
    """Run quick diagnostic test - all components"""
    results = []
    all_passed = True

    # Test 1: Imports
    try:
        from playwright.async_api import async_playwright
        from undetected_playwright import stealth_async
        results.append({
            "test": "Imports",
            "success": True,
            "message": "All imports OK (Playwright, undetected-playwright)"
        })
    except ImportError as e:
        all_passed = False
        results.append({
            "test": "Imports",
            "success": False,
            "message": f"Import failed: {str(e)}",
            "details": "Run: pip install playwright undetected-playwright"
        })
        return {"results": results, "all_passed": False, "summary": "Import test failed"}

    # Test 2: Network
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get("https://www.sgcarmart.com")
        results.append({
            "test": "Network",
            "success": r.status_code == 200,
            "message": f"SGCarMart.com: HTTP {r.status_code}",
            "details": f"Response time: {int(r.elapsed.total_seconds() * 1000)}ms"
        })
        if r.status_code != 200:
            all_passed = False
    except Exception as e:
        all_passed = False
        results.append({
            "test": "Network",
            "success": False,
            "message": f"Network failed: {str(e)}",
            "details": "Check firewall, DNS, or IP blocking"
        })

    # Test 3: Chromium Launch
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            await browser.close()
        results.append({
            "test": "Chromium Launch",
            "success": True,
            "message": "Chromium launched successfully"
        })
    except Exception as e:
        all_passed = False
        results.append({
            "test": "Chromium Launch",
            "success": False,
            "message": f"Chromium launch failed: {str(e)}",
            "details": "Run: playwright install chromium && playwright install-deps chromium"
        })

    # Test 4: Page Load
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://www.sgcarmart.com", timeout=30000)
            title = await page.title()
            await browser.close()

        results.append({
            "test": "Page Load",
            "success": True,
            "message": f"Page loaded: {title[:50]}",
            "details": "No blocking detected"
        })
    except Exception as e:
        all_passed = False
        results.append({
            "test": "Page Load",
            "success": False,
            "message": f"Page load failed: {str(e)}",
            "details": "Possible timeout or blocking"
        })

    # Test 5: Stealth Mode
    try:
        from playwright.async_api import async_playwright
        from undetected_playwright import stealth_async

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            context = await browser.new_context()
            page = await context.new_page()
            await stealth_async(page)
            await page.goto("https://www.sgcarmart.com", timeout=30000)
            title = await page.title()
            await browser.close()

        results.append({
            "test": "Stealth Mode",
            "success": True,
            "message": "Stealth mode applied successfully",
            "details": f"Page loaded: {title[:40]}"
        })
    except Exception as e:
        all_passed = False
        results.append({
            "test": "Stealth Mode",
            "success": False,
            "message": f"Stealth mode failed: {str(e)}"
        })

    # Test 6: Mini Scrape
    try:
        from playwright.async_api import async_playwright
        from undetected_playwright import stealth_async
        import asyncio

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            context = await browser.new_context()
            page = await context.new_page()
            await stealth_async(page)

            await page.goto("https://www.sgcarmart.com/search?q=Toyota+Hiace", timeout=30000)
            await asyncio.sleep(3)

            link_count = await page.evaluate('() => document.querySelectorAll(\'a[href*="info"]\').length')
            await browser.close()

        if link_count > 0:
            results.append({
                "test": "Mini Scrape",
                "success": True,
                "message": f"Found {link_count} listings on search page",
                "details": "Scraping selectors working correctly"
            })
        else:
            all_passed = False
            results.append({
                "test": "Mini Scrape",
                "success": False,
                "message": "Found 0 listings",
                "details": "Page structure may have changed OR SGCarMart blocking"
            })
    except Exception as e:
        all_passed = False
        results.append({
            "test": "Mini Scrape",
            "success": False,
            "message": f"Scrape test failed: {str(e)}"
        })

    # Summary
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    summary = f"{passed}/{total} tests passed"

    return {
        "results": results,
        "all_passed": all_passed,
        "summary": summary
    }


@app.post("/api/debug/test-network")
async def debug_test_network():
    """Test network connectivity to SGCarMart"""
    try:
        import httpx
        import time

        start = time.time()
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get("https://www.sgcarmart.com")
        elapsed = int((time.time() - start) * 1000)

        return {
            "success": r.status_code == 200,
            "status_code": r.status_code,
            "response_time": elapsed,
            "message": f"HTTP {r.status_code}" if r.status_code == 200 else "Request failed"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Network test failed"
        }


@app.post("/api/debug/test-browser")
async def debug_test_browser():
    """Test Playwright browser and page loading"""
    try:
        from playwright.async_api import async_playwright
        from undetected_playwright import stealth_async
        import asyncio

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            context = await browser.new_context()
            page = await context.new_page()
            await stealth_async(page)

            # Load search page
            await page.goto("https://www.sgcarmart.com/search?q=Toyota+Hiace", timeout=30000)
            await asyncio.sleep(3)

            title = await page.title()
            link_count = await page.evaluate('() => document.querySelectorAll(\'a[href*="info"]\').length')

            await browser.close()

        return {
            "success": True,
            "page_title": title,
            "listings_count": link_count,
            "message": f"Browser test passed. Found {link_count} listings."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Browser test failed"
        }


@app.get("/api/backup/download")
async def download_backup():
    """Download the SQLite database as a backup file"""
    db_url = config.DATABASE_URL
    # Extract file path from sqlite URL (sqlite:///./path/to/db or sqlite:////abs/path)
    if db_url.startswith("sqlite:///"):
        db_path = db_url[len("sqlite:///"):]
    else:
        db_path = "sgcarmart_data.db"

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")

    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return FileResponse(
        path=db_path,
        media_type="application/octet-stream",
        filename=filename
    )


@app.post("/api/backup/restore")
async def restore_backup(file: UploadFile = File(...)):
    """Restore database from an uploaded backup file"""
    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="File harus berformat .db (SQLite backup)")

    db_url = config.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url[len("sqlite:///"):]
    else:
        db_path = "sgcarmart_data.db"

    # Backup current db before overwrite
    if os.path.exists(db_path):
        backup_path = db_path + ".before_restore"
        import shutil
        shutil.copy2(db_path, backup_path)

    # Write uploaded file
    contents = await file.read()
    with open(db_path, "wb") as f:
        f.write(contents)

    # Restart scheduler so it picks up new db connections
    try:
        scheduler.stop()
        scheduler.start()
    except Exception:
        pass

    return {"success": True, "message": f"Database berhasil di-restore ({len(contents):,} bytes). Refresh halaman."}


# Mount static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
