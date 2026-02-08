"""Main FastAPI application - Ablink SGCarmart Scraper"""
import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Body
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict
import os
from contextlib import asynccontextmanager

from database import init_db, get_db, VehicleListing, DailyReport, ScrapeLog, AppSetting, SoldLog
from js_scraper import SGCarMartJSScraper
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

            # Step 2: Detect sold by comparison
            comparison_sold = 0
            if results:
                logger.info("[MANUAL] Step 2/3: Detecting sold vehicles (comparison)...")
                comparison_sold = detect_and_log_sold()
                logger.info(f"[MANUAL] Comparison sold: {comparison_sold} vehicles")
            else:
                logger.warning("[MANUAL] Skipping comparison - no active listings scraped")

            # Step 3: Scrape sold listings directly via avl=s
            logger.info("[MANUAL] Step 3/3: Scraping sold listings (avl=s)...")
            sold_results = scraper.scrape_sold_listings()
            avl_sold = len(sold_results) if sold_results else 0
            logger.info(f"[MANUAL] Direct sold (avl=s): {avl_sold} vehicles")

            logger.info(f"[MANUAL] Complete: Active={active_count} | Comparison sold={comparison_sold} | Direct sold={avl_sold}")
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
    body: Dict[str, int] = Body(..., embed=True),
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
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get vehicle listings with optional filters"""
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
    
    listings = query.order_by(VehicleListing.scrape_date.desc()).limit(limit).all()
    return [listing.to_dict() for listing in listings]

def _normalize_model(name: str) -> Optional[str]:
    """Match listing make_model to TARGET_VEHICLES (case-insensitive).
    Handles names like 'Toyota Dyna 150 3.0M (COE till 01/2031)' -> 'TOYOTA DYNA 3.0'
    Also handles dirty names like 'Used Toyota Dyna 150 3.0MReg Date: ...$99,988'
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
    # "COMMUTER" suffix removal for Hiace matching
    n_no_commuter = re.sub(r'\bCOMMUTER\b', '', n).strip()
    n_no_commuter = re.sub(r'\s+', ' ', n_no_commuter)
    # "DX" / "GL" / "HIGH ROOF" suffix removal for matching
    n_clean = re.sub(r'\s+(DX|GL|HIGH ROOF).*$', '', n_no_commuter).strip()

    # Also create version without transmission suffix (A/M) for flexible matching
    # e.g., "NISSAN NV350 2.5A" should match "NISSAN NV350 2.5M"
    n_no_trans = re.sub(r'(\d\.\d)[AM]\b', r'\1', n_clean)

    for v in config.TARGET_VEHICLES:
        vu = v.upper()
        vu_no_trans = re.sub(r'(\d\.\d)[AM]\b', r'\1', vu)
        # Check various cleaned versions
        if vu in n or n in vu:
            return v
        if vu in n_no_commuter or n_no_commuter in vu:
            return v
        if vu in n_clean or n_clean in vu:
            return v
        # Match ignoring A/M transmission difference
        if vu_no_trans and (vu_no_trans in n_no_trans or n_no_trans in vu_no_trans):
            return v
        # Special: match "ISUZU NHR87A" to "ISUZU NHR / NJR"
        if "ISUZU" in n and ("NHR" in vu and "NHR" in n):
            return v
        if "ISUZU" in n and ("NJR" in vu and "NJR" in n):
            return v
    return None


def _build_daily_table(sold_rows: list, report_date: str) -> Dict[str, Any]:
    """Build daily table grouped by vehicle category from SOLD data only."""
    # Aggregate by normalized model
    agg = defaultdict(lambda: {"items": []})
    for row in sold_rows:
        model = _normalize_model(row.make_model)
        if not model:
            continue

        dealer = (row.dealer_name or "–").strip()
        year = row.year_registered if row.year_registered else None
        dep = (row.depreciation or "–").strip()
        price = getattr(row, 'price', None)
        raw_name = row.make_model or ''
        agg[model]["items"].append((dealer, year, dep, price, raw_name))

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


# Mount static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
