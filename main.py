"""Main FastAPI application - Ablink SGCarmart Scraper"""
import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Body, UploadFile, File, Request
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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
            # Cleanup sold_log rows with NULL or invalid sold_date (julianday 0).
            # Legacy production data had ~1394 rows with no usable date — these
            # pollute the History dropdown and provide no analytic value.
            from sqlalchemy import text as _txt
            bad = _db.execute(_txt(
                "SELECT COUNT(*) FROM sold_log "
                "WHERE sold_date IS NULL OR sold_date = '' "
                "OR CAST(strftime('%Y', sold_date) AS INTEGER) < 2000 "
                "OR strftime('%Y', sold_date) IS NULL"
            )).scalar()
            if bad and bad > 0:
                logger.info(f"[STARTUP] Removing {bad} sold_log rows with invalid sold_date...")
                _db.execute(_txt(
                    "DELETE FROM sold_log "
                    "WHERE sold_date IS NULL OR sold_date = '' "
                    "OR CAST(strftime('%Y', sold_date) AS INTEGER) < 2000 "
                    "OR strftime('%Y', sold_date) IS NULL"
                ))
                _db.commit()
                logger.info("[STARTUP] Invalid sold_date rows removed.")

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

# CORS middleware - required for reverse proxy deployments (Cloud Run, sslip.io, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler - prevents unhandled errors from killing the response
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
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
        from scheduler import _set_app_setting
        scraper = SGCarMartJSScraper(headless=True)
        scrape_error = None
        active_count = 0
        avl_count = 0
        comparison_sold = 0
        try:
            # Step 1: Scrape active listings
            logger.info("[MANUAL] Step 1/3: Scraping active listings...")
            results = scraper.scrape_vehicle_listings()
            active_count = len(results) if results else 0
            logger.info(f"[MANUAL] Active listings: {active_count} vehicles found")

            # Step 2: Detect sold by comparison (previous vs current) → sold_log
            if results:
                logger.info("[MANUAL] Step 2/3: Detecting sold vehicles (comparison)...")
                comparison_sold = detect_and_log_sold()
                logger.info(f"[MANUAL] Sold today: {comparison_sold} vehicles disappeared since last scrape")
            else:
                logger.warning("[MANUAL] Skipping sold detection - no active listings scraped")
                scrape_error = "Active listings scrape returned 0 results (likely blocked / Cloudflare)"

            # Step 3: Scrape accumulated sold from SGCarMart (avl=s) → sgcarmart_sold
            logger.info("[MANUAL] Step 3/3: Scraping SGCarMart sold listings (avl=s)...")
            sold_results = scraper.scrape_sold_listings()
            avl_count = len(sold_results) if sold_results else 0
            logger.info(f"[MANUAL] SGCarMart sold (accumulated): {avl_count} vehicles")

            if active_count == 0 and avl_count == 0:
                scrape_error = scrape_error or "Both active and sold scrapes returned 0 results"

            logger.info(f"[MANUAL] Complete: Active={active_count} | Sold today={comparison_sold} | SGCarMart sold={avl_count}")
        except Exception as e:
            logger.error(f"Scrape failed with error: {e}")
            import traceback
            traceback.print_exc()
            scrape_error = f"{type(e).__name__}: {e}"
        finally:
            d = SessionLocal()
            try:
                lg = d.query(ScrapeLog).first()
                if lg:
                    lg.status = "Ready"
                    lg.last_scrape_at = datetime.now()
                    d.commit()
                # Update health fields so /api/status reflects real outcome
                if scrape_error:
                    _set_app_setting(d, 'last_scrape_error', scrape_error)
                else:
                    _set_app_setting(d, 'last_scrape_error', '')
                    # SGT-aware so scheduler's startup catch-up check compares
                    # apples-to-apples regardless of container TZ.
                    import pytz as _tz
                    _set_app_setting(d, 'last_successful_scrape_at',
                                     datetime.now(_tz.timezone('Asia/Singapore')).isoformat())
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

    # Surface scrape health so the UI can show when the last run actually
    # succeeded vs. silently failed (e.g. blocked by Cloudflare).
    err_row = db.query(AppSetting).filter(AppSetting.key == "last_scrape_error").first()
    succ_row = db.query(AppSetting).filter(AppSetting.key == "last_successful_scrape_at").first()
    last_error = err_row.value if err_row and err_row.value else None
    last_success_at = succ_row.value if succ_row and succ_row.value else None

    return {
        "status": log.status,
        "last_scrape_at": log.last_scrape_at.strftime("%Y-%m-%d %H:%M:%S") if log.last_scrape_at else None,
        "last_successful_scrape_at": last_success_at,
        "last_scrape_error": last_error,
        "scrape_healthy": last_error is None,
        "schedule": {"hour": hour, "minute": minute, "interval_days": interval_days},
        "schedule_display": (
            f"3x/day at {hour % 24:02d}:{minute:02d}, {(hour + 8) % 24:02d}:{minute:02d}, {(hour + 16) % 24:02d}:{minute:02d} SGT"
            if interval_days == 1
            else f"{hour:02d}:{minute:02d} SGT (every {interval_days} days)"
        ),
        "next_scheduled_scrape": next_run.isoformat() if next_run else None,
        "next_run_display": next_run_display,
        "timezone": "Asia/Singapore (SGT)"
    }


@app.post("/api/sold-log/catchup")
async def catchup_sold_log():
    """Force-run sold detection bypassing the MAX_GAP_DAYS check.

    Use this once after the scheduler has been broken for several days:
    all accumulated sold units (units that disappeared while scraping was
    down) get logged onto today's date. Past day-level granularity is
    permanently lost — there's no way to know which exact day each unit
    actually sold on. This is a one-shot recovery tool, not for daily use.
    """
    count = detect_and_log_sold(force=True)
    return {
        "logged": count,
        "message": (
            f"Catch-up complete: {count} sold unit(s) logged onto today."
            if count > 0
            else "No sold units detected. Either no listings disappeared, "
                 "or there is no previous active-listing snapshot to compare against."
        )
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
        "schedule_display": (
            f"3x/day at {hour % 24:02d}:{minute:02d}, {(hour + 8) % 24:02d}:{minute:02d}, {(hour + 16) % 24:02d}:{minute:02d} SGT"
            if interval_days == 1
            else f"{hour:02d}:{minute:02d} (every {interval_days} days)"
        )
    }

@app.get("/api/listings")
async def get_listings(
    date: Optional[str] = None,
    make_model: Optional[str] = None,
    limit: int = 5000,
    db: Session = Depends(get_db)
):
    """Get vehicle listings — target vehicles only, deduped, enriched from cache.
    Uses raw sqlite3 to avoid SQLAlchemy 2.0 DateTime processor errors on prod."""
    import sqlite3 as _s3
    sqlite_path = config.DATABASE_URL.replace("sqlite:///", "").lstrip("./").lstrip("/")
    conn = _s3.connect(sqlite_path)
    try:
        sql = ("SELECT id, scrape_date, make_model, registered_year, depreciation, "
               "dealer_name, price, listing_url, additional_info FROM vehicle_listings ")
        clauses, params = [], []
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
                next_date = target_date + timedelta(days=1)
                clauses.append("scrape_date >= ? AND scrape_date < ?")
                params += [
                    target_date.strftime("%Y-%m-%d 00:00:00"),
                    next_date.strftime("%Y-%m-%d 00:00:00"),
                ]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        if make_model:
            clauses.append("UPPER(make_model) LIKE ?")
            params.append("%" + make_model.upper() + "%")
        if clauses:
            sql += "WHERE " + " AND ".join(clauses) + " "
        sql += "ORDER BY scrape_date DESC"
        all_rows = conn.execute(sql, params).fetchall()

        # Build ListingCache lookup
        cache_rows = conn.execute(
            "SELECT listing_url_clean, depreciation, dealer_name, year_registered, price "
            "FROM listing_cache"
        ).fetchall()
    finally:
        conn.close()

    cache_map = {}
    for url_clean, dep, dealer, yr, price in cache_rows:
        if url_clean:
            cache_map[url_clean] = {"depreciation": dep, "dealer_name": dealer,
                                    "year_registered": yr, "price": price}

    seen_urls = set()
    filtered = []
    for row in all_rows:
        rid, sdate, mm, ryear, dep, dealer, price, url, addl = row
        raw_url = url or ''
        clean_url = _url_dedup_key(raw_url)
        if clean_url:
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
        model = _normalize_model(mm)
        if not model:
            continue
        model = config.TARGET_DISPLAY_NAMES.get(model, model)
        d = {
            "id": rid,
            "scrape_date": str(sdate) if sdate else None,
            "date": str(sdate)[:10] if sdate else None,
            "make_model": mm,
            "registered_year": ryear,
            "depreciation": dep,
            "dealer_name": dealer,
            "price": price,
            "listing_url": url,
            "additional_info": addl,
            "matched_model": model,
        }
        cached = cache_map.get(clean_url) if clean_url else None
        if cached:
            if not d.get('depreciation') or d['depreciation'] in ('', '–', '$0/yr', None):
                if cached["depreciation"] and cached["depreciation"] not in ('', '–', '$0/yr'):
                    d['depreciation'] = cached["depreciation"]
            if not d.get('dealer_name') or d['dealer_name'] in ('', '–', None):
                if cached["dealer_name"] and cached["dealer_name"] not in ('', '–'):
                    d['dealer_name'] = cached["dealer_name"]
        year_val = d.get('registered_year')
        if not year_val or year_val in (0, None):
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
    """Get daily report: sold units grouped by category for a specific date or today.
    Uses raw sqlite3 to avoid intermittent SQLAlchemy 2.0 DateTime column-processor
    failures on production (the ORM path sometimes returns 0 rows silently)."""
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()

    next_date = target_date + timedelta(days=1)

    import sqlite3 as _s3
    sqlite_path = config.DATABASE_URL.replace("sqlite:///", "").lstrip("./").lstrip("/")
    conn = _s3.connect(sqlite_path)
    try:
        rows = conn.execute(
            "SELECT make_model, year_registered, depreciation, dealer_name, price "
            "FROM sold_log WHERE sold_date >= ? AND sold_date < ?",
            (
                datetime.combine(target_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
                datetime.combine(next_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
            )
        ).fetchall()
    finally:
        conn.close()

    # Wrap tuples in a simple object so _build_daily_table can use attribute access
    class _Row:
        __slots__ = ("make_model", "year_registered", "depreciation", "dealer_name", "price")
        def __init__(self, mm, yr, dep, dealer, price):
            self.make_model = mm
            self.year_registered = yr
            self.depreciation = dep
            self.dealer_name = dealer
            self.price = price

    sold_rows = [_Row(*r) for r in rows]
    daily_rows = _build_daily_table(sold_rows, target_date.isoformat())

    return {
        "date": target_date.isoformat(),
        "summary": {"total_sold": len(sold_rows), "date": target_date.isoformat()},
        "daily_table": daily_rows,
    }

@app.get("/api/history")
async def get_history(db: Session = Depends(get_db)):
    """Get list of dates that have sold data. Invalid/NULL/julianday-0 dates
    are filtered out so the History dropdown only shows real days."""
    # Use raw SQL to bypass SQLAlchemy DateTime type processor issues
    import sqlite3 as _s3
    sqlite_path = config.DATABASE_URL.replace("sqlite:///", "").lstrip("./").lstrip("/")
    conn = _s3.connect(sqlite_path)
    try:
        rows = conn.execute(
            "SELECT date(sold_date) AS d, COUNT(id) AS c FROM sold_log "
            "WHERE sold_date IS NOT NULL AND sold_date <> '' "
            "AND CAST(strftime('%Y', sold_date) AS INTEGER) >= 2000 "
            "GROUP BY date(sold_date) "
            "ORDER BY date(sold_date) DESC"
        ).fetchall()
    finally:
        conn.close()
    return [{"date": str(d), "count": c} for d, c in rows if d]


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
    """Chart 3: Daily Sold Log - entries when a unit from Chart 1 was detected as sold.
    Uses raw sqlite3 to avoid SQLAlchemy 2.0 DateTime processor issues on prod."""
    import sqlite3 as _s3
    sqlite_path = config.DATABASE_URL.replace("sqlite:///", "").lstrip("./").lstrip("/")
    conn = _s3.connect(sqlite_path)
    try:
        sql = ("SELECT id, sold_date, make_model, year_registered, depreciation, "
               "dealer_name, price, listing_url FROM sold_log ")
        params = []
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
                next_date = target_date + timedelta(days=1)
                sql += "WHERE sold_date >= ? AND sold_date < ? "
                params = [
                    datetime.combine(target_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.combine(next_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
                ]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        sql += "ORDER BY sold_date DESC, id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        sd = r[1]
        try:
            sd_iso = datetime.fromisoformat(str(sd).replace(' ', 'T')).strftime("%Y-%m-%d") if sd else None
        except Exception:
            sd_iso = str(sd)[:10] if sd else None
        out.append({
            "id": r[0],
            "sold_date": sd_iso,
            "make_model": r[2],
            "year_registered": r[3],
            "depreciation": r[4],
            "dealer_name": r[5],
            "price": r[6],
            "listing_url": r[7],
        })
    return out


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
        # Skip items without year
        if not d.get('year_registered') or d['year_registered'] in (0, None):
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
    """Get daily sold table for a given date. Uses raw sqlite3 (see /api/daily-report)."""
    next_date = target_date + timedelta(days=1)
    import sqlite3 as _s3
    sqlite_path = config.DATABASE_URL.replace("sqlite:///", "").lstrip("./").lstrip("/")
    conn = _s3.connect(sqlite_path)
    try:
        rows = conn.execute(
            "SELECT make_model, year_registered, depreciation, dealer_name, price "
            "FROM sold_log WHERE sold_date >= ? AND sold_date < ?",
            (
                datetime.combine(target_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
                datetime.combine(next_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
            )
        ).fetchall()
    finally:
        conn.close()

    class _Row:
        __slots__ = ("make_model", "year_registered", "depreciation", "dealer_name", "price")
        def __init__(self, mm, yr, dep, dealer, price):
            self.make_model = mm; self.year_registered = yr; self.depreciation = dep
            self.dealer_name = dealer; self.price = price

    sold_rows = [_Row(*r) for r in rows]
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
    """Get overall statistics. Uses raw sqlite3 to avoid SQLAlchemy 2.0
    DateTime column-processor issues that appear on production Python 3.11."""
    import sqlite3 as _s3
    sqlite_path = config.DATABASE_URL.replace("sqlite:///", "").lstrip("./").lstrip("/")
    conn = _s3.connect(sqlite_path)
    try:
        total_listings = conn.execute("SELECT COUNT(*) FROM vehicle_listings").fetchone()[0] or 0
        dr = conn.execute(
            "SELECT MIN(scrape_date), MAX(scrape_date) FROM vehicle_listings"
        ).fetchone()
        first_raw, last_raw = (dr or (None, None))
        unique_models = conn.execute(
            "SELECT COUNT(DISTINCT make_model) FROM vehicle_listings"
        ).fetchone()[0] or 0
        ps = conn.execute(
            "SELECT AVG(price), MIN(price), MAX(price) FROM vehicle_listings WHERE price IS NOT NULL"
        ).fetchone()
    finally:
        conn.close()

    def _to_iso(v):
        if not v:
            return None
        try:
            return datetime.fromisoformat(str(v).replace(' ', 'T')).isoformat()
        except Exception:
            return str(v)

    return {
        "total_listings": total_listings,
        "unique_models": unique_models,
        "date_range": {"first": _to_iso(first_raw), "last": _to_iso(last_raw)},
        "price_statistics": {
            "average": float(ps[0]) if ps and ps[0] else 0,
            "minimum": float(ps[1]) if ps and ps[1] else 0,
            "maximum": float(ps[2]) if ps and ps[2] else 0,
        },
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

    # Use raw sqlite3 to avoid the SQLAlchemy 2.0 DateTime processor bug that
    # intermittently returns 0 rows on production for queries with date filters.
    import sqlite3 as _s3
    sqlite_path = config.DATABASE_URL.replace("sqlite:///", "").lstrip("./").lstrip("/")
    conn = _s3.connect(sqlite_path)

    class _DRow:
        __slots__ = ("make_model", "depreciation", "listing_url", "year_registered",
                     "registered_year", "price", "dealer_name")
        def __init__(self, mm, dep, url, yr, price, dealer):
            self.make_model = mm
            self.depreciation = dep
            self.listing_url = url
            self.year_registered = yr
            self.registered_year = yr
            self.price = price
            self.dealer_name = dealer

    try:
        if source == "sold":
            if days:
                cutoff_str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
                raw_rows = conn.execute(
                    "SELECT make_model, depreciation, listing_url, year_registered, price, dealer_name "
                    "FROM sgcarmart_sold WHERE scrape_date >= ?",
                    (cutoff_str,)
                ).fetchall()
            else:
                raw_rows = conn.execute(
                    "SELECT make_model, depreciation, listing_url, year_registered, price, dealer_name "
                    "FROM sgcarmart_sold"
                ).fetchall()
            year_field = 'year_registered'
            cache_rows = conn.execute(
                "SELECT listing_url_clean, depreciation, dealer_name, year_registered, price, make_model "
                "FROM listing_cache"
            ).fetchall()
            class _CacheEntry:
                __slots__ = ("listing_url_clean", "depreciation", "dealer_name",
                             "year_registered", "price", "make_model")
                def __init__(self, url_c, dep, dealer, yr, price, mm):
                    self.listing_url_clean = url_c; self.depreciation = dep
                    self.dealer_name = dealer; self.year_registered = yr
                    self.price = price; self.make_model = mm
            cache_map = {c.listing_url_clean: c for c in [_CacheEntry(*r) for r in cache_rows] if c.listing_url_clean}
        else:
            raw_rows = conn.execute(
                "SELECT make_model, depreciation, listing_url, registered_year, price, dealer_name "
                "FROM vehicle_listings WHERE scrape_date >= ? AND scrape_date < ?",
                (
                    target_date.strftime("%Y-%m-%d 00:00:00"),
                    next_date.strftime("%Y-%m-%d 00:00:00"),
                )
            ).fetchall()
            year_field = 'registered_year'
            cache_map = None
    finally:
        conn.close()

    rows = [_DRow(*r) for r in raw_rows]

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
# DASHBOARD SUMMARY ENDPOINT
# ============================================================

_DASHBOARD_CONFIG_KEY = "dashboard_config"

# Default dashboard config (used when no saved config exists in DB).
# Each category has a name + list of target model names from config.TARGET_VEHICLES
# (or TARGET_DISPLAY_NAMES mapped names like "TOYOTA DYNA 150 3.0").
_DEFAULT_DASHBOARD_CONFIG = {
    "compare_days": 7,
    "year_min": None,
    "year_max": None,
    "categories": [
        {"name": "10FT DIESEL", "models": list(config.VEHICLE_CATEGORIES["10FT DIESEL"])},
        {"name": "14FT DIESEL", "models": list(config.VEHICLE_CATEGORIES["14FT DIESEL"])},
        {"name": "VAN DIESEL", "models": list(config.VEHICLE_CATEGORIES["VAN DIESEL (FILTER: GOODS VAN)"])},
        {"name": "BUS DIESEL", "models": list(config.VEHICLE_CATEGORIES["BUS DIESEL (FILTER: BUS/MINI BUS , FUEL: DIESEL)"])},
    ],
    "watchlist": [
        "TOYOTA DYNA 150 3.0",
        "CANTER FEB21",
        "TOYOTA HIACE 3.0M",
        "NISSAN NV200 1.6A",
    ],
}


def _load_dashboard_config(db: Session) -> dict:
    """Load the dashboard config from DB, falling back to defaults."""
    import json as _json
    row = db.query(AppSetting).filter(AppSetting.key == _DASHBOARD_CONFIG_KEY).first()
    if not row or not row.value:
        return _DEFAULT_DASHBOARD_CONFIG
    try:
        cfg = _json.loads(row.value)
        # Sanity check structure
        if not isinstance(cfg, dict) or "categories" not in cfg or "watchlist" not in cfg:
            return _DEFAULT_DASHBOARD_CONFIG
        cfg.setdefault("compare_days", 7)
        cfg.setdefault("year_min", None)
        cfg.setdefault("year_max", None)
        return cfg
    except Exception:
        return _DEFAULT_DASHBOARD_CONFIG


def _save_dashboard_config(db: Session, cfg: dict):
    """Persist dashboard config to AppSetting."""
    import json as _json
    row = db.query(AppSetting).filter(AppSetting.key == _DASHBOARD_CONFIG_KEY).first()
    serialized = _json.dumps(cfg)
    if row:
        row.value = serialized
    else:
        db.add(AppSetting(key=_DASHBOARD_CONFIG_KEY, value=serialized))
    db.commit()


def _parse_dep_value(dep_str):
    """Parse '$16,890/yr' -> 16890. Returns None for invalid/placeholder values."""
    if not dep_str:
        return None
    if dep_str in ("$5,001/yr", "$0/yr", "–"):
        return None
    import re as _re
    m = _re.search(r'[\d,]+', str(dep_str))
    if not m:
        return None
    try:
        v = int(m.group(0).replace(',', ''))
        return v if v not in (0, 5001) else None
    except ValueError:
        return None


def _aggregate_active_snapshot(db: Session, snapshot_date, year_min=None, year_max=None):
    """Return dict model->{'units': int, 'deps': [int]} for the active listings
    on (or closest before) snapshot_date. Uses VehicleListing scrape_date date-bucket.

    If year_min/year_max provided, only includes listings whose registered_year
    falls inside the inclusive range. Rows with NULL registered_year are excluded
    when any year bound is set."""
    # Bypass SQLAlchemy entirely — its DateTime/Date processor on SQLite chokes
    # on Python 3.14 fromisoformat when called from cyextension on certain rows.
    # We use a fresh sqlite3 connection and pull rows as plain tuples.
    import sqlite3
    sqlite_path = config.DATABASE_URL.replace("sqlite:///", "").lstrip("./").lstrip("/")
    conn = sqlite3.connect(sqlite_path)
    try:
        end_of_day_str = datetime.combine(snapshot_date, datetime.max.time()).strftime("%Y-%m-%d %H:%M:%S")
        max_row = conn.execute(
            "SELECT MAX(scrape_date) FROM vehicle_listings "
            "WHERE scrape_date IS NOT NULL AND scrape_date <= ?",
            (end_of_day_str,)
        ).fetchone()
        max_raw = max_row[0] if max_row else None
        if not max_raw:
            return {}, None
        try:
            actual = datetime.fromisoformat(str(max_raw).replace(' ', 'T')).date()
        except Exception:
            actual = datetime.strptime(str(max_raw)[:10], "%Y-%m-%d").date()
        next_day = actual + timedelta(days=1)
        start_str = datetime.combine(actual, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
        end_str = datetime.combine(next_day, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.execute(
            "SELECT make_model, depreciation, listing_url, registered_year FROM vehicle_listings "
            "WHERE scrape_date >= ? AND scrape_date < ?",
            (start_str, end_str)
        )
        rows = cursor.fetchall()
    finally:
        conn.close()
    has_year_filter = (year_min is not None) or (year_max is not None)
    seen = set()
    agg = {}
    for make_model, dep_str, listing_url, reg_year in rows:
        if has_year_filter:
            if reg_year is None:
                continue
            if year_min is not None and reg_year < year_min:
                continue
            if year_max is not None and reg_year > year_max:
                continue
        url_key = _url_dedup_key(listing_url or '')
        if url_key:
            if url_key in seen:
                continue
            seen.add(url_key)
        model = _normalize_model(make_model)
        if not model:
            continue
        model = config.TARGET_DISPLAY_NAMES.get(model, model)
        slot = agg.setdefault(model, {"units": 0, "deps": []})
        slot["units"] += 1
        dv = _parse_dep_value(dep_str)
        if dv is not None:
            slot["deps"].append(dv)
    return agg, actual


def _category_metrics(model_agg: dict, models: list):
    """Aggregate per-model stats into a category total."""
    units = 0
    deps = []
    for m in models:
        s = model_agg.get(m)
        if not s:
            continue
        units += s["units"]
        deps.extend(s["deps"])
    avg = int(sum(deps) / len(deps)) if deps else None
    return {"units": units, "avg_dep": avg}


def _delta(cur, prev):
    """Return delta direction + amount given current/previous numeric values (or None)."""
    if cur is None or prev is None:
        return {"delta": None, "direction": "flat"}
    diff = cur - prev
    direction = "up" if diff > 0 else ("down" if diff < 0 else "flat")
    return {"delta": abs(diff), "direction": direction}


@app.get("/api/dashboard-summary")
async def dashboard_summary(db: Session = Depends(get_db)):
    """Aggregated dashboard: per-category metrics with 7d trend, sold counts, watchlist."""
    cfg = _load_dashboard_config(db)
    compare_days = int(cfg.get("compare_days", 7) or 7)
    year_min = cfg.get("year_min")
    year_max = cfg.get("year_max")
    today = datetime.now().date()
    compare_date = today - timedelta(days=compare_days)

    cur_agg, cur_date = _aggregate_active_snapshot(db, today, year_min, year_max)
    prev_agg, prev_date = _aggregate_active_snapshot(db, compare_date, year_min, year_max)

    # Categories: from saved config (or defaults)
    categories_out = []
    for cat in cfg.get("categories", []):
        models = cat.get("models", []) or []
        cur = _category_metrics(cur_agg, models)
        prev = _category_metrics(prev_agg, models)
        categories_out.append({
            "name": cat.get("name", ""),
            "avg_dep": cur["avg_dep"],
            "avg_dep_trend": _delta(cur["avg_dep"], prev["avg_dep"]),
            "units": cur["units"],
            "units_trend": _delta(cur["units"], prev["units"]),
        })

    # Watchlist
    watchlist_out = []
    for m in cfg.get("watchlist", []):
        cur_s = cur_agg.get(m, {"units": 0, "deps": []})
        prev_s = prev_agg.get(m, {"units": 0, "deps": []})
        cur_avg = int(sum(cur_s["deps"]) / len(cur_s["deps"])) if cur_s["deps"] else None
        prev_avg = int(sum(prev_s["deps"]) / len(prev_s["deps"])) if prev_s["deps"] else None
        watchlist_out.append({
            "model": m,
            "units": cur_s["units"],
            "avg_dep": cur_avg,
            "avg_dep_trend": _delta(cur_avg, prev_avg),
            "units_trend": _delta(cur_s["units"], prev_s["units"]),
        })

    # Sold counts from sold_log (target vehicles only — already filtered there)
    yesterday = today - timedelta(days=1)
    last_7_start = today - timedelta(days=7)
    last_30_start = today - timedelta(days=30)

    import sqlite3 as _s3
    _sqlite_path = config.DATABASE_URL.replace("sqlite:///", "").lstrip("./").lstrip("/")
    _conn = _s3.connect(_sqlite_path)
    try:
        # Source A: sold_log (units detected as disappeared from active listings)
        def _count_sold_log(start_date, end_date):
            s = datetime.combine(start_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
            e = datetime.combine(end_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
            r = _conn.execute(
                "SELECT COUNT(*) FROM sold_log WHERE sold_date >= ? AND sold_date < ?",
                (s, e)
            ).fetchone()
            return r[0] if r else 0

        # Source B: sgcarmart_sold (avl=s accumulated). Count UNIQUE listings whose
        # first observed scrape_date falls within the window — that's the day they
        # first appeared as sold on SGCarMart.
        def _count_sgcarmart_sold(start_date, end_date):
            s = datetime.combine(start_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
            e = datetime.combine(end_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
            r = _conn.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT listing_url, MIN(scrape_date) AS first_seen
                    FROM sgcarmart_sold
                    WHERE listing_url IS NOT NULL AND listing_url <> ''
                    GROUP BY listing_url
                ) AS firsts
                WHERE firsts.first_seen >= ? AND firsts.first_seen < ?
                """,
                (s, e)
            ).fetchone()
            return r[0] if r else 0

        sold_log_summary = {
            "yesterday": _count_sold_log(yesterday, today),
            "last_7_days": _count_sold_log(last_7_start, today),
            "last_30_days": _count_sold_log(last_30_start, today),
        }
        sgcarmart_sold_summary = {
            "yesterday": _count_sgcarmart_sold(yesterday, today),
            "last_7_days": _count_sgcarmart_sold(last_7_start, today),
            "last_30_days": _count_sgcarmart_sold(last_30_start, today),
        }
    finally:
        _conn.close()

    return {
        "snapshot_date": cur_date.isoformat() if cur_date else None,
        "compare_date": prev_date.isoformat() if prev_date else None,
        "compare_days": compare_days,
        "year_min": year_min,
        "year_max": year_max,
        "categories": categories_out,
        "sold_log_summary": sold_log_summary,
        "sgcarmart_sold_summary": sgcarmart_sold_summary,
        "watchlist": watchlist_out,
    }


@app.get("/api/dashboard-config")
async def get_dashboard_config(db: Session = Depends(get_db)):
    """Return current dashboard config + list of all available target models."""
    cfg = _load_dashboard_config(db)
    # Build full list of available models (TARGET_VEHICLES + display-name mapped)
    available = set()
    for m in config.TARGET_VEHICLES:
        available.add(config.TARGET_DISPLAY_NAMES.get(m, m))
    # Also include combined display names from VEHICLE_CATEGORIES (e.g. "ISUZU NHR / ISUZU NJR")
    for cat_models in config.VEHICLE_CATEGORIES.values():
        for m in cat_models:
            available.add(m)
    return {
        "config": cfg,
        "available_models": sorted(available),
        "default_config": _DEFAULT_DASHBOARD_CONFIG,
    }


@app.post("/api/dashboard-config")
async def set_dashboard_config(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Save a new dashboard config. Expected shape:
    { compare_days: int, categories: [{name, models: [str]}], watchlist: [str] }
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")
    cats = payload.get("categories")
    wl = payload.get("watchlist")
    if not isinstance(cats, list) or not isinstance(wl, list):
        raise HTTPException(status_code=400, detail="categories and watchlist must be arrays")
    # Sanitize
    clean_cats = []
    for c in cats:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", "")).strip()
        models = [str(m).strip() for m in (c.get("models") or []) if str(m).strip()]
        if name:
            clean_cats.append({"name": name, "models": models})
    clean_wl = [str(m).strip() for m in wl if str(m).strip()]
    try:
        compare_days = int(payload.get("compare_days", 7) or 7)
        if compare_days < 1:
            compare_days = 7
    except (TypeError, ValueError):
        compare_days = 7

    def _parse_year(v):
        if v in (None, "", "null"):
            return None
        try:
            y = int(v)
        except (TypeError, ValueError):
            return None
        if y < 1980 or y > 2100:
            return None
        return y

    year_min = _parse_year(payload.get("year_min"))
    year_max = _parse_year(payload.get("year_max"))
    if year_min is not None and year_max is not None and year_min > year_max:
        year_min, year_max = year_max, year_min

    new_cfg = {
        "compare_days": compare_days,
        "year_min": year_min,
        "year_max": year_max,
        "categories": clean_cats,
        "watchlist": clean_wl,
    }
    _save_dashboard_config(db, new_cfg)
    return {"success": True, "config": new_cfg}


@app.post("/api/dashboard-config/reset")
async def reset_dashboard_config(db: Session = Depends(get_db)):
    """Reset dashboard config to defaults."""
    _save_dashboard_config(db, _DEFAULT_DASHBOARD_CONFIG)
    return {"success": True, "config": _DEFAULT_DASHBOARD_CONFIG}


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
    """Download the SQLite database as a self-contained backup file.

    Uses SQLite's online backup API (via VACUUM INTO) to produce a
    consistent snapshot — this works even while the live DB is being
    written to, and produces a single .db file with no -wal/-shm
    sidecars needed to read it back.
    """
    import os
    import sqlite3
    import tempfile

    db_url = config.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url[len("sqlite:///"):]
    else:
        db_path = "sgcarmart_data.db"

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")

    # Stage the snapshot in a temp file next to the live DB (same FS) so
    # SQLite can write to it and we can serve it. We do NOT touch the live
    # file. VACUUM INTO produces a clean, defragged, self-contained copy.
    db_dir = os.path.dirname(os.path.abspath(db_path)) or "."
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="backup_", suffix=".db", dir=db_dir)
    os.close(tmp_fd)
    try:
        os.remove(tmp_path)  # VACUUM INTO requires the destination not to exist
    except OSError:
        pass

    try:
        src = sqlite3.connect(db_path)
        try:
            # Make sure any pending WAL pages are folded into the main file
            # logically before we snapshot. (VACUUM INTO ignores WAL on the
            # destination, but checkpointing makes the source state cleaner.)
            try:
                src.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.OperationalError:
                pass  # Not in WAL mode — that's fine.

            # Quote the path for SQL safely (escape single quotes).
            quoted = tmp_path.replace("'", "''")
            src.execute(f"VACUUM INTO '{quoted}'")
        finally:
            src.close()
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to snapshot DB: {e}")

    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    # FileResponse will stream the file; we delete the temp file via a
    # BackgroundTask after the response is sent so we don't ship a phantom
    # file on disk.
    from starlette.background import BackgroundTask

    def _cleanup():
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return FileResponse(
        path=tmp_path,
        media_type="application/octet-stream",
        filename=filename,
        background=BackgroundTask(_cleanup),
    )


@app.post("/api/backup/restore")
async def restore_backup(file: UploadFile = File(...)):
    """Restore database from an uploaded backup file.

    Simple, same as original — just write the file. The previous version
    had three bugs that made it silently 'succeed' without the new data
    becoming visible; we keep ONLY the minimal fixes for those:

      a) engine.dispose() before overwrite — otherwise SQLAlchemy's pool
         keeps serving from connections pinned to the OLD file.
      b) Delete .db-wal / .db-shm / -journal sidecars — leaving them
         behind makes SQLite layer the OLD database's WAL pages on top
         of the new file (the 'data tidak ganti' bug).
      c) scheduler.stop() before the write, scheduler.start() after —
         so a concurrent scrape can't corrupt the swap.

    No file validation, no schema migration, no temp file — exactly the
    same shape as the original endpoint.
    """
    import os
    import shutil

    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="File harus berformat .db (SQLite backup)")

    db_url = config.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url[len("sqlite:///"):]
    else:
        db_path = "sgcarmart_data.db"

    # Backup current db before overwrite (same as original)
    if os.path.exists(db_path):
        try:
            shutil.copy2(db_path, db_path + ".before_restore")
        except Exception as e:
            logger.warning(f"[RESTORE] Could not snapshot old DB: {e}")

    # Close all SQLAlchemy connections to the OLD file — otherwise the pool
    # keeps serving cached pages from the pre-restore state.
    try:
        from database import engine as _engine
        _engine.dispose()
    except Exception as e:
        logger.warning(f"[RESTORE] engine.dispose() warning: {e}")

    # Wipe sidecar files belonging to the OLD database — leaving WAL/SHM
    # behind makes SQLite splice old WAL pages onto the new file.
    for ext in ("-wal", "-shm", "-journal"):
        sidecar = db_path + ext
        if os.path.exists(sidecar):
            try:
                os.remove(sidecar)
            except Exception as e:
                logger.warning(f"[RESTORE] Could not remove {sidecar}: {e}")

    # Write uploaded file (same as original — direct write)
    contents = await file.read()
    with open(db_path, "wb") as f:
        f.write(contents)

    # Restart scheduler with wait=False so we don't block on any in-flight
    # scrape (used to make this endpoint hang for 5-10 minutes).
    try:
        scheduler.restart()
    except Exception as e:
        logger.warning(f"[RESTORE] Scheduler restart warning: {e}")

    return {
        "success": True,
        "message": f"Database berhasil di-restore ({len(contents):,} bytes). Refresh halaman."
    }


# ============================================================
# PUBLIC REST API v1
# Clean, versioned endpoints for external integrations
# Base: /api/v1/
# Docs: /api/v1/docs
# ============================================================

@app.get("/api/v1/openapi.json", include_in_schema=False)
async def v1_openapi_spec(request: Request):
    """OpenAPI 3.0 spec for API v1 — compatible with ChatGPT Actions, Claude Projects, and any AI agent"""
    base = str(request.base_url).rstrip("/")
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Ablink SGCarMart Market Intelligence API",
            "version": "1.0.0",
            "description": (
                "Real-time Singapore commercial vehicle market data scraped from SGCarMart.com. "
                "Provides active listings, sold vehicle history, depreciation analytics, and daily reports. "
                "All dates in Singapore Time (SGT / UTC+8). No authentication required."
            ),
            "contact": {"name": "SingRank.com", "url": "https://singrank.com"}
        },
        "servers": [{"url": f"{base}/api/v1", "description": "Production"}],
        "paths": {
            "/status": {
                "get": {
                    "operationId": "getStatus",
                    "summary": "Scraper status",
                    "description": "Returns current scraper status, timestamp of last scrape, and next scheduled scrape.",
                    "responses": {"200": {"description": "Status object", "content": {"application/json": {"schema": {"type": "object", "properties": {"status": {"type": "string"}, "last_scrape_at": {"type": "string"}, "next_scrape": {"type": "string"}, "timezone": {"type": "string"}}}}}}}
                }
            },
            "/active-listings": {
                "get": {
                    "operationId": "getActiveListings",
                    "summary": "Active vehicle listings",
                    "description": "Returns active commercial vehicle listings scraped from SGCarMart for a given date. Includes price, depreciation, dealer, and listing URL.",
                    "parameters": [
                        {"name": "date", "in": "query", "schema": {"type": "string", "example": "2026-04-06"}, "description": "Scrape date (YYYY-MM-DD). Defaults to today."},
                        {"name": "category", "in": "query", "schema": {"type": "string"}, "description": "Filter by vehicle category (partial match)"},
                        {"name": "make_model", "in": "query", "schema": {"type": "string"}, "description": "Filter by make/model (partial match)"},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 500, "maximum": 5000}}
                    ],
                    "responses": {"200": {"description": "List of active listings"}}
                }
            },
            "/sold-listings": {
                "get": {
                    "operationId": "getSoldListings",
                    "summary": "Sold vehicle history",
                    "description": "Returns vehicles detected as sold (listing disappeared from SGCarMart). Includes depreciation, price, and dealer captured while the vehicle was still active.",
                    "parameters": [
                        {"name": "from_date", "in": "query", "schema": {"type": "string", "example": "2026-03-01"}},
                        {"name": "to_date", "in": "query", "schema": {"type": "string", "example": "2026-04-06"}},
                        {"name": "category", "in": "query", "schema": {"type": "string"}},
                        {"name": "make_model", "in": "query", "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 200, "maximum": 1000}}
                    ],
                    "responses": {"200": {"description": "List of sold vehicles with full data"}}
                }
            },
            "/daily-report": {
                "get": {
                    "operationId": "getDailyReport",
                    "summary": "Daily sold report by category",
                    "description": "Returns the daily sold vehicle summary grouped by vehicle category and model. Includes unit count, average price, and average depreciation per model.",
                    "parameters": [
                        {"name": "date", "in": "query", "schema": {"type": "string", "example": "2026-04-06"}, "description": "Report date. Defaults to today."}
                    ],
                    "responses": {"200": {"description": "Daily report grouped by category"}}
                }
            },
            "/depreciation": {
                "get": {
                    "operationId": "getDepreciation",
                    "summary": "Depreciation analytics by model and year",
                    "description": "Returns lowest and average depreciation (SGD/year) and unit count, aggregated by vehicle model and registration year. Use source=active for current market or source=sold for historical sold data.",
                    "parameters": [
                        {"name": "source", "in": "query", "schema": {"type": "string", "enum": ["active", "sold"], "default": "active"}, "description": "active = today's listings, sold = sold history"},
                        {"name": "date", "in": "query", "schema": {"type": "string"}, "description": "Date for active source (YYYY-MM-DD)"},
                        {"name": "days", "in": "query", "schema": {"type": "integer", "default": 60}, "description": "Lookback window in days for sold source"}
                    ],
                    "responses": {"200": {"description": "Depreciation table keyed by model and year"}}
                }
            },
            "/categories": {
                "get": {
                    "operationId": "getCategories",
                    "summary": "Vehicle categories and target models",
                    "description": "Returns all tracked vehicle categories (e.g. VAN DIESEL, 10FT DIESEL, BUS DIESEL) and their target model lists.",
                    "responses": {"200": {"description": "List of categories with models"}}
                }
            },
            "/history": {
                "get": {
                    "operationId": "getHistory",
                    "summary": "Available report dates",
                    "description": "Returns all dates that have sold vehicle data, with unit counts. Use to discover which dates have data before calling /daily-report.",
                    "responses": {"200": {"description": "List of dates with unit counts"}}
                }
            },
            "/scrape": {
                "post": {
                    "operationId": "triggerScrape",
                    "summary": "Trigger a full scrape",
                    "description": "Starts a background scrape of SGCarMart (~3-5 minutes). Returns 409 if scrape already running. Poll /status to track completion.",
                    "responses": {
                        "200": {"description": "Scrape started"},
                        "409": {"description": "Scrape already in progress"}
                    }
                }
            }
        }
    }


@app.get("/api/v1/docs", response_class=HTMLResponse, include_in_schema=False)
async def api_v1_docs():
    """Human-readable API reference page"""
    return HTMLResponse(content="""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ablink API v1 — Reference</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
:root{--navy:#0d1b2a;--orange:#f26522}
body{background:#f5f6fa;font-family:'Segoe UI',sans-serif}
.sidebar{background:var(--navy);min-height:100vh;padding:24px 0;position:sticky;top:0}
.sidebar .brand{color:white;font-size:1.5rem;font-weight:900;padding:0 24px 24px;letter-spacing:-1px;border-bottom:1px solid rgba(255,255,255,.1);margin-bottom:16px}
.sidebar .brand span{color:var(--orange)}
.sidebar a{display:block;color:rgba(255,255,255,.7);padding:8px 24px;text-decoration:none;font-size:.88rem;transition:.15s}
.sidebar a:hover,.sidebar a.active{color:white;background:rgba(255,255,255,.08)}
.sidebar .nav-section{color:rgba(255,255,255,.35);font-size:.72rem;font-weight:700;letter-spacing:1px;padding:16px 24px 4px;text-transform:uppercase}
.main{padding:40px}
.endpoint-card{background:white;border-radius:12px;margin-bottom:20px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.endpoint-header{display:flex;align-items:center;gap:12px;padding:16px 20px;border-bottom:1px solid #f0f2f5}
.method{font-size:.78rem;font-weight:700;padding:4px 10px;border-radius:6px;letter-spacing:.5px}
.method.get{background:#dcfce7;color:#166534}
.method.post{background:#dbeafe;color:#1e40af}
.endpoint-path{font-family:monospace;font-size:1rem;font-weight:600;color:var(--navy)}
.endpoint-body{padding:16px 20px}
.endpoint-desc{color:#374151;font-size:.9rem;margin-bottom:14px}
.params-table{width:100%;font-size:.83rem;border-collapse:collapse}
.params-table th{background:#f8fafc;padding:8px 12px;text-align:left;font-weight:600;color:#6b7280;font-size:.78rem;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #e5e7eb}
.params-table td{padding:8px 12px;border-bottom:1px solid #f0f2f5;vertical-align:top}
.params-table td:first-child{font-family:monospace;color:var(--orange);font-weight:600}
.params-table td.required{color:#dc2626;font-size:.75rem;font-weight:600}
.example{background:#0d1b2a;border-radius:8px;padding:14px 16px;margin-top:12px;font-family:monospace;font-size:.82rem;color:#e2e8f0;overflow-x:auto}
.example .comment{color:#6b7280}
.try-btn{font-size:.78rem;padding:4px 12px;background:var(--orange);color:white;border:none;border-radius:6px;cursor:pointer;text-decoration:none;display:inline-block;margin-top:8px}
.page-title{color:var(--navy);font-size:2rem;font-weight:900;letter-spacing:-1px;margin-bottom:4px}
.page-title span{color:var(--orange)}
.badge-v{background:var(--orange);color:white;font-size:.72rem;font-weight:700;padding:3px 8px;border-radius:20px;vertical-align:middle;margin-left:8px}
.base-url{background:#0d1b2a;color:#e2e8f0;font-family:monospace;padding:12px 16px;border-radius:8px;margin:16px 0;font-size:.9rem}
.base-url span{color:var(--orange)}
.tag{background:#f0fdf4;color:#166534;font-size:.72rem;font-weight:600;padding:2px 8px;border-radius:20px;border:1px solid #bbf7d0}
</style>
</head>
<body>
<div class="container-fluid p-0">
<div class="row g-0">
  <div class="col-auto sidebar d-none d-md-block" style="width:220px">
    <div class="brand">ABLINK<span>.</span></div>
    <div class="nav-section">Reference</div>
    <a href="#overview">Overview</a>
    <a href="#status">Status</a>
    <div class="nav-section">Data</div>
    <a href="#active-listings">Active Listings</a>
    <a href="#sold-listings">Sold Listings</a>
    <a href="#daily-report">Daily Report</a>
    <a href="#depreciation">Depreciation</a>
    <div class="nav-section">Meta</div>
    <a href="#categories">Categories</a>
    <a href="#history">History</a>
    <a href="#scrape">Trigger Scrape</a>
  </div>
  <div class="col main">
    <div class="page-title">API Reference <span class="badge-v">v1</span></div>
    <p class="text-muted mb-0">Ablink SGCarMart Market Intelligence · REST API</p>
    <div class="base-url"><span>Base URL:</span> https://your-domain.com<span>/api/v1</span></div>
    <p style="font-size:.88rem;color:#6b7280">All responses are JSON. Dates use <code>YYYY-MM-DD</code> format (Singapore Time). No authentication required.</p>

    <hr id="overview">

    <!-- STATUS -->
    <h5 class="fw-bold mt-4 mb-3" id="status" style="color:#0d1b2a">System</h5>
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method get">GET</span>
        <span class="endpoint-path">/api/v1/status</span>
        <span class="tag ms-auto">no params</span>
      </div>
      <div class="endpoint-body">
        <div class="endpoint-desc">Returns scraper status, last scrape timestamp, next scheduled scrape, and system health.</div>
        <div class="example"><span class="comment">// Response</span>
{"status": "Ready", "last_scrape_at": "2026-04-06 08:00:00", "next_scrape": "2026-04-07 08:00:00", "timezone": "Asia/Singapore"}</div>
        <a href="/api/v1/status" target="_blank" class="try-btn">Try it →</a>
      </div>
    </div>

    <!-- ACTIVE LISTINGS -->
    <h5 class="fw-bold mt-4 mb-3" id="active-listings" style="color:#0d1b2a">Data Endpoints</h5>
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method get">GET</span>
        <span class="endpoint-path">/api/v1/active-listings</span>
      </div>
      <div class="endpoint-body">
        <div class="endpoint-desc">Returns active vehicle listings scraped from SGCarMart. Filtered to tracked commercial vehicles only.</div>
        <table class="params-table"><thead><tr><th>Parameter</th><th>Type</th><th>Default</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>date</td><td>string</td><td>today</td><td>Scrape date — <code>YYYY-MM-DD</code></td></tr>
          <tr><td>category</td><td>string</td><td>—</td><td>Filter by vehicle category (partial match)</td></tr>
          <tr><td>make_model</td><td>string</td><td>—</td><td>Filter by make/model (partial match)</td></tr>
          <tr><td>limit</td><td>int</td><td>500</td><td>Max records returned (max 5000)</td></tr>
        </tbody></table>
        <div class="example"><span class="comment">// GET /api/v1/active-listings?date=2026-04-06&category=VAN+DIESEL&limit=50</span>
{"date": "2026-04-06", "total": 42, "listings": [{"make_model": "Toyota Hiace", "year": 2019, "price": 85000, "depreciation": "$8,200/yr", "dealer": "ABC Motors", "url": "https://..."}]}</div>
        <a href="/api/v1/active-listings?limit=10" target="_blank" class="try-btn">Try it →</a>
      </div>
    </div>

    <!-- SOLD LISTINGS -->
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method get">GET</span>
        <span class="endpoint-path">/api/v1/sold-listings</span>
      </div>
      <div class="endpoint-body">
        <div class="endpoint-desc">Returns sold vehicle listings detected by comparing consecutive daily scrapes. Includes depreciation, price, and dealer info captured while the vehicle was still active.</div>
        <table class="params-table"><thead><tr><th>Parameter</th><th>Type</th><th>Default</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>from_date</td><td>string</td><td>30 days ago</td><td>Start of date range</td></tr>
          <tr><td>to_date</td><td>string</td><td>today</td><td>End of date range</td></tr>
          <tr><td>category</td><td>string</td><td>—</td><td>Filter by category</td></tr>
          <tr><td>make_model</td><td>string</td><td>—</td><td>Filter by make/model</td></tr>
          <tr><td>limit</td><td>int</td><td>200</td><td>Max records (max 1000)</td></tr>
        </tbody></table>
        <div class="example"><span class="comment">// GET /api/v1/sold-listings?from_date=2026-04-01&to_date=2026-04-06</span>
{"from_date": "2026-04-01", "to_date": "2026-04-06", "total": 18, "sold": [{"make_model": "Isuzu NLR", "year": 2018, "sold_date": "2026-04-05", "price": 72000, "depreciation": "$9,100/yr", "dealer": "XYZ Trucks"}]}</div>
        <a href="/api/v1/sold-listings?limit=10" target="_blank" class="try-btn">Try it →</a>
      </div>
    </div>

    <!-- DAILY REPORT -->
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method get">GET</span>
        <span class="endpoint-path">/api/v1/daily-report</span>
      </div>
      <div class="endpoint-body">
        <div class="endpoint-desc">Returns the daily sold vehicle summary grouped by category and model — same data shown in the main dashboard table.</div>
        <table class="params-table"><thead><tr><th>Parameter</th><th>Type</th><th>Default</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>date</td><td>string</td><td>today</td><td>Report date — <code>YYYY-MM-DD</code></td></tr>
        </tbody></table>
        <div class="example"><span class="comment">// GET /api/v1/daily-report?date=2026-04-06</span>
{"date": "2026-04-06", "total_sold": 7, "categories": [{"category": "VAN DIESEL (FILTER: GOODS VAN)", "models": [{"make_model": "Isuzu NLR", "units_sold": 2, "avg_price": 75000, "avg_depreciation": 8500}]}]}</div>
        <a href="/api/v1/daily-report" target="_blank" class="try-btn">Try it →</a>
      </div>
    </div>

    <!-- DEPRECIATION -->
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method get">GET</span>
        <span class="endpoint-path">/api/v1/depreciation</span>
      </div>
      <div class="endpoint-body">
        <div class="endpoint-desc">Returns depreciation and unit count aggregated by vehicle model and registration year. Useful for market benchmarking.</div>
        <table class="params-table"><thead><tr><th>Parameter</th><th>Type</th><th>Default</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>source</td><td>string</td><td><code>active</code></td><td><code>active</code> = current listings · <code>sold</code> = sold history</td></tr>
          <tr><td>date</td><td>string</td><td>today</td><td>Date for active source</td></tr>
          <tr><td>days</td><td>int</td><td>60</td><td>Lookback window for sold source (e.g. 30, 60, 90)</td></tr>
        </tbody></table>
        <div class="example"><span class="comment">// GET /api/v1/depreciation?source=sold&days=30</span>
{"source": "sold", "days": 30, "total_rows": 85, "data": {"Toyota Hiace 2.5M": {"2019": {"lowest": 7800, "average": 8500, "units": 4}}}}</div>
        <a href="/api/v1/depreciation?source=active" target="_blank" class="try-btn">Try it →</a>
      </div>
    </div>

    <!-- CATEGORIES -->
    <h5 class="fw-bold mt-4 mb-3" id="categories" style="color:#0d1b2a">Meta Endpoints</h5>
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method get">GET</span>
        <span class="endpoint-path">/api/v1/categories</span>
        <span class="tag ms-auto">no params</span>
      </div>
      <div class="endpoint-body">
        <div class="endpoint-desc">Returns all tracked vehicle categories and their target models.</div>
        <a href="/api/v1/categories" target="_blank" class="try-btn">Try it →</a>
      </div>
    </div>

    <!-- HISTORY -->
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method get">GET</span>
        <span class="endpoint-path">/api/v1/history</span>
        <span class="tag ms-auto">no params</span>
      </div>
      <div class="endpoint-body">
        <div class="endpoint-desc">Returns all dates that have sold vehicle data, along with unit counts per day. Use to discover available report dates.</div>
        <a href="/api/v1/history" target="_blank" class="try-btn">Try it →</a>
      </div>
    </div>

    <!-- TRIGGER SCRAPE -->
    <div class="endpoint-card" id="scrape">
      <div class="endpoint-header">
        <span class="method post">POST</span>
        <span class="endpoint-path">/api/v1/scrape</span>
        <span class="tag ms-auto">no body</span>
      </div>
      <div class="endpoint-body">
        <div class="endpoint-desc">Triggers a full scrape of SGCarMart. Runs in background (~3–5 min). Returns 409 if scrape already in progress. Poll <code>/api/v1/status</code> to track completion.</div>
        <div class="example"><span class="comment">// POST /api/v1/scrape</span>
{"success": true, "message": "Scrape started. Poll /api/v1/status for completion."}</div>
      </div>
    </div>

    <!-- AI Integration -->
    <h5 class="fw-bold mt-4 mb-3" style="color:#0d1b2a">Use with AI Tools</h5>
    <p style="font-size:.88rem;color:#6b7280;margin-bottom:12px">The API is fully OpenAPI 3.0 compatible. Plug it directly into ChatGPT, Claude, or any AI agent.</p>
    <div class="endpoint-card">
      <div class="endpoint-body" style="padding:16px 20px;">
        <div style="display:grid;gap:14px;">
          <div>
            <div style="font-weight:700;font-size:.88rem;color:#0d1b2a;margin-bottom:4px;"><i class="bi bi-robot me-2" style="color:#f26522;"></i>ChatGPT — GPT Actions</div>
            <div style="font-size:.83rem;color:#6b7280;">In your GPT configuration → <b>Actions</b> → <b>Import from URL</b> → paste:<br>
            <code style="background:#f8fafc;padding:3px 8px;border-radius:4px;font-size:.82rem;">https://your-domain.com/api/v1/openapi.json</code></div>
          </div>
          <div>
            <div style="font-weight:700;font-size:.88rem;color:#0d1b2a;margin-bottom:4px;"><i class="bi bi-cpu me-2" style="color:#f26522;"></i>Claude — Projects / MCP</div>
            <div style="font-size:.83rem;color:#6b7280;">Add the OpenAPI spec URL as a tool source in your Claude Project, or use the endpoints directly in prompts with the URL:<br>
            <code style="background:#f8fafc;padding:3px 8px;border-radius:4px;font-size:.82rem;">https://your-domain.com/api/v1/openapi.json</code></div>
          </div>
          <div>
            <div style="font-weight:700;font-size:.88rem;color:#0d1b2a;margin-bottom:4px;"><i class="bi bi-lightning me-2" style="color:#f26522;"></i>Any AI Agent / LangChain / n8n</div>
            <div style="font-size:.83rem;color:#6b7280;">Use the OpenAPI JSON spec to auto-generate tool definitions. All endpoints return clean JSON — no auth needed.</div>
          </div>
        </div>
        <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;">
          <a href="/api/v1/openapi.json" target="_blank" class="try-btn"><i class="bi bi-braces me-1"></i>Download OpenAPI JSON</a>
          <a href="/docs" target="_blank" class="try-btn" style="background:#0d1b2a;">Swagger UI →</a>
        </div>
      </div>
    </div>

    <hr>
    <p class="text-muted" style="font-size:.8rem">Developed by <a href="https://singrank.com" style="color:#f26522;font-weight:600">SingRank.com</a> · Ablink SGCarMart Intelligence</p>
  </div>
</div>
</div>
</body>
</html>""")


@app.get("/api/v1/status")
async def v1_status(db: Session = Depends(get_db)):
    """v1: Scraper status, last scrape time, next scheduled scrape"""
    log = _ensure_scrape_log(db)
    next_run = scheduler.get_next_run_time()
    return {
        "status": log.status,
        "last_scrape_at": log.last_scrape_at.strftime("%Y-%m-%d %H:%M:%S") if log.last_scrape_at else None,
        "next_scrape": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None,
        "timezone": "Asia/Singapore (SGT)"
    }


@app.get("/api/v1/active-listings")
async def v1_active_listings(
    date: Optional[str] = None,
    category: Optional[str] = None,
    make_model: Optional[str] = None,
    limit: int = 500,
    db: Session = Depends(get_db)
):
    """v1: Active vehicle listings scraped from SGCarMart for a given date"""
    limit = min(limit, 5000)
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()
    next_date = target_date + timedelta(days=1)

    query = db.query(VehicleListing).filter(
        and_(
            VehicleListing.scrape_date >= target_date,
            VehicleListing.scrape_date < next_date
        )
    )
    if make_model:
        query = query.filter(VehicleListing.make_model.ilike(f"%{make_model}%"))
    if category:
        query = query.filter(VehicleListing.additional_info.ilike(f"%{category}%"))

    rows = query.limit(limit).all()
    listings = [
        {
            "make_model": r.make_model,
            "year": r.registered_year,
            "price": r.price,
            "depreciation": r.depreciation,
            "dealer": r.dealer_name,
            "url": r.listing_url,
            "scraped_at": r.scrape_date.isoformat() if r.scrape_date else None
        }
        for r in rows
    ]
    return {"date": target_date.isoformat(), "total": len(listings), "listings": listings}


@app.get("/api/v1/sold-listings")
async def v1_sold_listings(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    category: Optional[str] = None,
    make_model: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """v1: Sold vehicles detected by comparing consecutive daily scrapes"""
    limit = min(limit, 1000)
    try:
        fd = datetime.strptime(from_date, "%Y-%m-%d") if from_date else datetime.now() - timedelta(days=30)
        td = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1) if to_date else datetime.now()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    query = db.query(SoldLog).filter(
        and_(SoldLog.sold_date >= fd, SoldLog.sold_date < td)
    )
    if make_model:
        query = query.filter(SoldLog.make_model.ilike(f"%{make_model}%"))
    if category:
        query = query.filter(SoldLog.category.ilike(f"%{category}%"))

    rows = query.order_by(SoldLog.sold_date.desc()).limit(limit).all()
    sold = [
        {
            "make_model": r.make_model,
            "year": r.year_registered,
            "category": r.category,
            "sold_date": r.sold_date.strftime("%Y-%m-%d") if r.sold_date else None,
            "price": r.price,
            "depreciation": r.depreciation,
            "dealer": r.dealer_name,
            "url": r.listing_url
        }
        for r in rows
    ]
    return {
        "from_date": fd.strftime("%Y-%m-%d"),
        "to_date": (td - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total": len(sold),
        "sold": sold
    }


@app.get("/api/v1/daily-report")
async def v1_daily_report(
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """v1: Daily sold summary grouped by category and model"""
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()
    next_date = target_date + timedelta(days=1)

    sold_rows = db.query(SoldLog).filter(
        and_(
            SoldLog.sold_date >= datetime.combine(target_date, datetime.min.time()),
            SoldLog.sold_date < datetime.combine(next_date, datetime.min.time())
        )
    ).all()

    # Group by category → model
    grouped: Dict[str, Dict[str, Any]] = {}
    for r in sold_rows:
        cat = r.category or "Uncategorised"
        if cat not in grouped:
            grouped[cat] = {}
        mm = r.make_model or "Unknown"
        if mm not in grouped[cat]:
            grouped[cat][mm] = {"units_sold": 0, "prices": [], "depreciations": []}
        grouped[cat][mm]["units_sold"] += 1
        if r.price:
            grouped[cat][mm]["prices"].append(r.price)
        if r.depreciation:
            try:
                dep_val = float(r.depreciation.replace("$", "").replace(",", "").replace("/yr", "").strip())
                grouped[cat][mm]["depreciations"].append(dep_val)
            except Exception:
                pass

    categories_out = []
    for cat, models in grouped.items():
        models_out = []
        for mm, d in models.items():
            models_out.append({
                "make_model": mm,
                "units_sold": d["units_sold"],
                "avg_price": round(sum(d["prices"]) / len(d["prices"])) if d["prices"] else None,
                "avg_depreciation": round(sum(d["depreciations"]) / len(d["depreciations"])) if d["depreciations"] else None
            })
        categories_out.append({"category": cat, "models": sorted(models_out, key=lambda x: -x["units_sold"])})

    return {
        "date": target_date.isoformat(),
        "total_sold": len(sold_rows),
        "categories": categories_out
    }


@app.get("/api/v1/depreciation")
async def v1_depreciation(
    source: str = "active",
    date: Optional[str] = None,
    days: Optional[int] = 60,
    db: Session = Depends(get_db)
):
    """v1: Depreciation & unit count aggregated by model and registration year"""
    if source not in ("active", "sold"):
        raise HTTPException(status_code=400, detail="source must be 'active' or 'sold'")
    result = _get_depreciation_data(source, date, db, days=days if source == "sold" else None)
    if source == "sold":
        result["days"] = days
    return result


@app.get("/api/v1/categories")
async def v1_categories():
    """v1: All tracked vehicle categories and their target models"""
    return {
        "categories": [
            {
                "name": cat,
                "targets": list(targets)
            }
            for cat, targets in config.VEHICLE_CATEGORIES.items()
        ]
    }


@app.get("/api/v1/history")
async def v1_history(db: Session = Depends(get_db)):
    """v1: Dates with sold data and unit counts"""
    dates = db.query(
        func.date(SoldLog.sold_date).label("date"),
        func.count(SoldLog.id).label("units_sold")
    ).group_by(func.date(SoldLog.sold_date)).order_by(func.date(SoldLog.sold_date).desc()).all()
    return {"total_dates": len(dates), "history": [{"date": str(d[0]), "units_sold": d[1]} for d in dates]}


@app.post("/api/v1/scrape")
async def v1_trigger_scrape(db: Session = Depends(get_db)):
    """v1: Trigger a full SGCarMart scrape (background). Poll /api/v1/status for completion."""
    log = _ensure_scrape_log(db)
    if log.status == "Scraping":
        raise HTTPException(status_code=409, detail="Scrape already in progress")
    # Delegate to the existing /api/scrape endpoint logic via redirect
    from fastapi.responses import RedirectResponse
    # Reuse manual_scrape by calling POST /api/scrape internally via same handler
    log.status = "Scraping"
    db.commit()

    def run_scrape_v1():
        from database import SessionLocal
        scraper = SGCarMartJSScraper(headless=True)
        try:
            results = scraper.scrape_vehicle_listings()
            with SessionLocal() as s:
                for r in results:
                    s.add(VehicleListing(**{k: v for k, v in r.items() if k in VehicleListing.__table__.columns.keys()}))
                s.commit()
            with SessionLocal() as s:
                detect_and_log_sold(s)
            with SessionLocal() as s:
                l = _ensure_scrape_log(s)
                l.status = "Ready"
                l.last_scrape_at = datetime.now()
                s.commit()
        except Exception as e:
            logger.error(f"[v1/scrape] Error: {e}")
            from database import SessionLocal as SL
            with SL() as s:
                l = _ensure_scrape_log(s)
                l.status = "Ready"
                s.commit()

    import threading
    threading.Thread(target=run_scrape_v1, daemon=True).start()
    return {"success": True, "message": "Scrape started. Poll /api/v1/status for completion."}


# Mount static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
