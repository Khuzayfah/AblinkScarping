"""Scheduler for automated scraping tasks"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import config
from js_scraper import SGCarMartJSScraper
from database import SessionLocal, ScrapeLog
from sold_log_service import detect_and_log_sold

logger = logging.getLogger("scheduler")

# Singapore timezone - SGCarMart is a Singapore site
SGT = pytz.timezone('Asia/Singapore')


class ScraperScheduler:
    """Scheduler for automated scraping"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=SGT)
        self._hour = config.SCRAPING_SCHEDULE_HOUR
        self._minute = config.SCRAPING_SCHEDULE_MINUTE
        self._interval_days = 1

    def _set_status(self, status: str, update_last_scrape: bool = False):
        """Helper to update ScrapeLog status safely."""
        db = SessionLocal()
        try:
            log = db.query(ScrapeLog).first()
            if not log:
                log = ScrapeLog(status=status)
                db.add(log)
            else:
                log.status = status
            if update_last_scrape:
                log.last_scrape_at = datetime.now()
            db.commit()
        except Exception as e:
            logger.error(f"Failed to set status to '{status}': {e}")
            db.rollback()
        finally:
            db.close()

    def scrape_job(self):
        """Job to execute scraping: active + comparison sold + SGCarMart sold accumulation"""
        now_sgt = datetime.now(SGT)
        logger.info(f"===== SCHEDULED SCRAPE STARTED at {now_sgt.strftime('%Y-%m-%d %H:%M:%S %Z')} =====")

        self._set_status("Scraping")

        try:
            scraper = SGCarMartJSScraper(headless=True)

            # Step 1: Scrape active listings
            logger.info("[SCHEDULER] Step 1/3: Scraping active listings...")
            results = scraper.scrape_vehicle_listings()
            active_count = len(results) if results else 0
            logger.info(f"[SCHEDULER] Active listings: {active_count} vehicles found")

            # Step 2: Detect sold by comparison (previous vs current) → sold_log
            comparison_sold = 0
            if results:
                logger.info("[SCHEDULER] Step 2/3: Detecting sold vehicles (comparison)...")
                comparison_sold = detect_and_log_sold()
                logger.info(f"[SCHEDULER] Sold today: {comparison_sold} vehicles disappeared")
            else:
                logger.warning("[SCHEDULER] Skipping sold detection - no active listings scraped")

            # Step 3: Scrape accumulated sold from SGCarMart (avl=s) → sgcarmart_sold
            logger.info("[SCHEDULER] Step 3/3: Scraping SGCarMart sold listings (avl=s)...")
            sold_results = scraper.scrape_sold_listings()
            avl_count = len(sold_results) if sold_results else 0
            logger.info(f"[SCHEDULER] SGCarMart sold (accumulated): {avl_count} vehicles")

            self._set_status("Ready", update_last_scrape=True)

            logger.info(f"===== SCHEDULED SCRAPE COMPLETED =====")
            logger.info(f"  Active: {active_count} | Sold today: {comparison_sold} | SGCarMart sold: {avl_count}")

        except Exception as e:
            logger.error(f"[SCHEDULER] Scrape failed with error: {e}")
            import traceback
            traceback.print_exc()
            self._set_status("Ready", update_last_scrape=True)

    def set_initial_schedule(self, hour: int, minute: int, interval_days: int = 1):
        """Set schedule before start (e.g. from DB)"""
        self._hour = hour
        self._minute = minute
        self._interval_days = interval_days

    def _make_trigger(self, hour: int, minute: int, interval_days: int):
        """Create CronTrigger with SGT timezone."""
        if interval_days == 2:
            return CronTrigger(day='*/2', hour=hour, minute=minute, timezone=SGT)
        return CronTrigger(hour=hour, minute=minute, timezone=SGT)

    def start(self):
        """Start the scheduler"""
        trigger = self._make_trigger(self._hour, self._minute, self._interval_days)
        interval_text = f"every {self._interval_days} day(s)"

        self.scheduler.add_job(
            self.scrape_job,
            trigger=trigger,
            id='daily_scrape',
            name='SGCarMart Scrape',
            replace_existing=True,
            misfire_grace_time=3600,  # Allow 1 hour grace for missed jobs
        )
        self.scheduler.start()

        next_run = self.get_next_run_time()
        next_str = next_run.strftime('%Y-%m-%d %H:%M:%S %Z') if next_run else 'unknown'
        logger.info(f"========================================")
        logger.info(f"SCHEDULER STARTED")
        logger.info(f"  Schedule: {interval_text} at {self._hour:02d}:{self._minute:02d} SGT")
        logger.info(f"  Next run: {next_str}")
        logger.info(f"  Timezone: Asia/Singapore (SGT)")
        logger.info(f"========================================")

        # Reset stuck "Scraping" status on startup
        self._set_status("Ready")

    def update_schedule(self, hour: int, minute: int, interval_days: int = 1):
        """Update scrape time and interval"""
        self._hour = hour
        self._minute = minute
        self._interval_days = interval_days
        job = self.scheduler.get_job('daily_scrape')
        if job:
            trigger = self._make_trigger(hour, minute, interval_days)
            job.reschedule(trigger=trigger)
            next_run = self.get_next_run_time()
            next_str = next_run.strftime('%Y-%m-%d %H:%M:%S %Z') if next_run else 'unknown'
            logger.info(f"Schedule updated: every {interval_days} day(s) at {hour:02d}:{minute:02d} SGT | Next: {next_str}")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    def get_next_run_time(self):
        """Get next scheduled run time"""
        job = self.scheduler.get_job('daily_scrape')
        if job:
            return job.next_run_time
        return None
