"""Scheduler for automated scraping tasks"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import pytz
import config
from js_scraper import SGCarMartJSScraper
from database import SessionLocal, ScrapeLog, AppSetting
from sold_log_service import detect_and_log_sold

logger = logging.getLogger("scheduler")

# Singapore timezone - SGCarMart is a Singapore site
SGT = pytz.timezone('Asia/Singapore')

# If the container was down/sleeping when the scheduled time hit, still run
# the job when it wakes up, as long as we are within this window. 12 hours
# covers overnight sleeps and short restarts.
MISFIRE_GRACE_SECONDS = 12 * 3600


def _set_app_setting(db, key: str, value: str):
    """Upsert a value in the app_settings key-value store."""
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))


class ScraperScheduler:
    """Scheduler for automated scraping"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=SGT)
        self._hour = config.SCRAPING_SCHEDULE_HOUR
        self._minute = config.SCRAPING_SCHEDULE_MINUTE
        self._interval_days = 1

    def _set_status(self, status: str, update_last_scrape: bool = False,
                    last_error: str = None, last_success: bool = None):
        """Update ScrapeLog status and record run outcome in app_settings.

        - status: "Ready" | "Scraping"
        - update_last_scrape: bump last_scrape_at (attempted run timestamp)
        - last_error: if provided, persisted as 'last_scrape_error'; pass ""
          to clear it on a successful run.
        - last_success: if True, also stamp 'last_successful_scrape_at'.
        """
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

            if last_error is not None:
                _set_app_setting(db, 'last_scrape_error', last_error)
            if last_success is True:
                # SGT-aware ISO so the catch-up check on startup compares
                # apples-to-apples regardless of container TZ (Coolify Docker
                # default is UTC, would otherwise be off by 8h).
                _set_app_setting(db, 'last_successful_scrape_at',
                                 datetime.now(SGT).isoformat())
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

        active_count = 0
        comparison_sold = 0
        avl_count = 0
        scrape_error = None

        try:
            scraper = SGCarMartJSScraper(headless=True)

            # Step 1: Scrape active listings
            logger.info("[SCHEDULER] Step 1/3: Scraping active listings...")
            results = scraper.scrape_vehicle_listings()
            active_count = len(results) if results else 0
            logger.info(f"[SCHEDULER] Active listings: {active_count} vehicles found")

            # Step 2: Detect sold by comparison (previous vs current) → sold_log
            if results:
                logger.info("[SCHEDULER] Step 2/3: Detecting sold vehicles (comparison)...")
                comparison_sold = detect_and_log_sold()
                logger.info(f"[SCHEDULER] Sold today: {comparison_sold} vehicles disappeared")
            else:
                logger.warning("[SCHEDULER] Skipping sold detection - no active listings scraped")
                scrape_error = "Active listings scrape returned 0 results (likely blocked / Cloudflare)"

            # Step 3: Scrape accumulated sold from SGCarMart (avl=s) → sgcarmart_sold
            logger.info("[SCHEDULER] Step 3/3: Scraping SGCarMart sold listings (avl=s)...")
            sold_results = scraper.scrape_sold_listings()
            avl_count = len(sold_results) if sold_results else 0
            logger.info(f"[SCHEDULER] SGCarMart sold (accumulated): {avl_count} vehicles")

            # A successful run requires at least one of the two scrapes to
            # have returned data. If both are empty, treat as failure so the
            # dashboard surfaces the problem instead of silently passing.
            if active_count == 0 and avl_count == 0:
                scrape_error = scrape_error or "Both active and sold scrapes returned 0 results"

            if scrape_error:
                # Bump last_scrape_at so we know an attempt happened, but
                # keep last_successful_scrape_at unchanged so the dashboard
                # shows the real last-good time.
                self._set_status("Ready", update_last_scrape=True,
                                 last_error=scrape_error)
                logger.error(f"===== SCHEDULED SCRAPE FINISHED WITH ERROR: {scrape_error} =====")
            else:
                self._set_status("Ready", update_last_scrape=True,
                                 last_error="", last_success=True)
                logger.info(f"===== SCHEDULED SCRAPE COMPLETED =====")

            logger.info(f"  Active: {active_count} | Sold today: {comparison_sold} | SGCarMart sold: {avl_count}")

            # Step 4: Send daily email report (only on success)
            if not scrape_error:
                try:
                    from email_service import send_daily_report, get_db_setting
                    from database import SessionLocal as EmailDBSession
                    email_db = EmailDBSession()
                    try:
                        if get_db_setting(email_db, 'gmail_enabled', 'false') == 'true':
                            date_str = now_sgt.strftime("%Y-%m-%d")
                            ok, msg = send_daily_report(email_db, date_str)
                            if ok:
                                logger.info(f"[SCHEDULER] Email: {msg}")
                            else:
                                logger.warning(f"[SCHEDULER] Email skipped: {msg}")
                    finally:
                        email_db.close()
                except Exception as email_err:
                    logger.error(f"[SCHEDULER] Email error: {email_err}")

        except Exception as e:
            logger.error(f"[SCHEDULER] Scrape failed with error: {e}")
            import traceback
            traceback.print_exc()
            self._set_status("Ready", update_last_scrape=True,
                             last_error=f"{type(e).__name__}: {e}")

    def set_initial_schedule(self, hour: int, minute: int, interval_days: int = 1):
        """Set schedule before start (e.g. from DB)"""
        self._hour = hour
        self._minute = minute
        self._interval_days = interval_days

    def _make_trigger(self, hour: int, minute: int, interval_days: int):
        """Create CronTrigger with SGT timezone.

        Daily mode (interval_days=1): fire 3x per day, every 8h starting from
        the configured base hour. With the default hour=6, this gives
        06:00 / 14:00 / 22:00 SGT — multiple chances per day so a single
        Cloudflare block / outage doesn't lose a whole day of data.

        Every-other-day mode (interval_days=2): single fire per scheduled day
        at the configured hour (legacy behavior preserved).
        """
        if interval_days == 2:
            return CronTrigger(day='*/2', hour=hour, minute=minute, timezone=SGT)
        h1 = hour % 24
        h2 = (hour + 8) % 24
        h3 = (hour + 16) % 24
        hours_csv = f"{h1},{h2},{h3}"
        return CronTrigger(hour=hours_csv, minute=minute, timezone=SGT)

    def _scheduled_hours_csv(self) -> str:
        """Comma-separated hours the scheduler fires at today (SGT). Used by
        the startup catch-up logic to find the most recent slot that should
        have fired."""
        if self._interval_days == 2:
            return str(self._hour % 24)
        h1 = self._hour % 24
        h2 = (self._hour + 8) % 24
        h3 = (self._hour + 16) % 24
        return f"{h1},{h2},{h3}"

    def start(self):
        """Start the scheduler"""
        trigger = self._make_trigger(self._hour, self._minute, self._interval_days)
        if self._interval_days == 1:
            interval_text = f"3x/day at {self._scheduled_hours_csv()}:{self._minute:02d} SGT"
        else:
            interval_text = f"every {self._interval_days} day(s) at {self._hour:02d}:{self._minute:02d} SGT"

        self.scheduler.add_job(
            self.scrape_job,
            trigger=trigger,
            id='daily_scrape',
            name='SGCarMart Scrape',
            replace_existing=True,
            # If the container was sleeping/down when the cron time hit, run
            # the missed job once it comes back up (within the grace window).
            misfire_grace_time=MISFIRE_GRACE_SECONDS,
            # Collapse multiple missed runs into one — we never want to
            # double-scrape if APScheduler thinks several intervals elapsed.
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.start()

        next_run = self.get_next_run_time()
        next_str = next_run.strftime('%Y-%m-%d %H:%M:%S %Z') if next_run else 'unknown'
        logger.info(f"========================================")
        logger.info(f"SCHEDULER STARTED")
        logger.info(f"  Schedule: {interval_text}")
        logger.info(f"  Next run: {next_str}")
        logger.info(f"  Misfire grace: {MISFIRE_GRACE_SECONDS // 3600}h (catches up after restart)")
        logger.info(f"  Timezone: Asia/Singapore (SGT)")
        logger.info(f"========================================")

        # Reset stuck "Scraping" status on startup (e.g. crashed mid-run)
        db = SessionLocal()
        try:
            log = db.query(ScrapeLog).first()
            if log and log.status == "Scraping":
                log.status = "Ready"
                db.commit()
                logger.warning("Reset stuck 'Scraping' status to 'Ready' (previous run crashed?)")
        except Exception as e:
            logger.error(f"Failed to reset stuck status on startup: {e}")
            db.rollback()
        finally:
            db.close()

        # Catch-up: if container restarted AFTER today's scheduled time and
        # we have no successful scrape for today yet, fire one immediately.
        # APScheduler's misfire_grace_time only helps when the scheduler was
        # running at cron-time and had a delay — it does NOT recover missed
        # runs across full container restarts (MemoryJobStore loses history).
        self._schedule_startup_catchup_if_needed()

    def _schedule_startup_catchup_if_needed(self):
        """If we've gone too long without a successful scrape (container down
        across one or more scheduled slots), schedule a one-shot catch-up
        ~45 seconds after startup so the app finishes booting first.

        With 3x/day cadence (every 8h), we consider anything > 9h since the
        last success as 'missed at least one slot' and fire catch-up.
        """
        # Staleness threshold: 1h grace beyond the 8h cadence so we don't
        # fire spuriously right after a normal scheduled run.
        STALE_AFTER_HOURS = 9

        db = SessionLocal()
        try:
            row = db.query(AppSetting).filter(
                AppSetting.key == 'last_successful_scrape_at'
            ).first()
            last_success_str = row.value if row else None
        except Exception as e:
            logger.error(f"[CATCHUP] Could not read last_successful_scrape_at: {e}")
            return
        finally:
            db.close()

        now_sgt = datetime.now(SGT)

        needs_catchup = False
        reason = ""
        if not last_success_str:
            needs_catchup = True
            reason = "no recorded successful scrape ever"
        else:
            try:
                last_success = datetime.fromisoformat(last_success_str)
                if last_success.tzinfo is None:
                    # Legacy values were written naive in container-local TZ.
                    # Coolify Docker default = UTC, so treat naive as UTC and
                    # convert to SGT for the comparison below.
                    last_success = pytz.UTC.localize(last_success).astimezone(SGT)
                else:
                    last_success = last_success.astimezone(SGT)
                age_hours = (now_sgt - last_success).total_seconds() / 3600
                if age_hours >= STALE_AFTER_HOURS:
                    needs_catchup = True
                    reason = (
                        f"last success was {last_success.strftime('%Y-%m-%d %H:%M %Z')} "
                        f"({age_hours:.1f}h ago) — beyond {STALE_AFTER_HOURS}h staleness "
                        f"threshold for 3x/day cadence"
                    )
            except Exception as e:
                needs_catchup = True
                reason = f"could not parse last_successful_scrape_at ({e})"

        if not needs_catchup:
            logger.info(
                f"[CATCHUP] No catch-up needed — last successful scrape "
                f"already covers today's window."
            )
            return

        catchup_at = datetime.now(SGT) + timedelta(seconds=45)
        try:
            self.scheduler.add_job(
                self.scrape_job,
                trigger='date',
                run_date=catchup_at,
                id='startup_catchup',
                name='Startup Catch-up Scrape',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=MISFIRE_GRACE_SECONDS,
                coalesce=True,
            )
            logger.warning(
                f"[CATCHUP] Scheduled one-shot catch-up scrape at "
                f"{catchup_at.strftime('%Y-%m-%d %H:%M:%S %Z')} — reason: {reason}"
            )
        except Exception as e:
            logger.error(f"[CATCHUP] Failed to schedule catch-up: {e}")

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
            if interval_days == 1:
                logger.info(f"Schedule updated: 3x/day at {self._scheduled_hours_csv()}:{minute:02d} SGT | Next: {next_str}")
            else:
                logger.info(f"Schedule updated: every {interval_days} day(s) at {hour:02d}:{minute:02d} SGT | Next: {next_str}")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    def restart(self):
        """Force-restart with a fresh BackgroundScheduler instance.

        APScheduler can't re-start the same instance after shutdown — we have
        to swap in a new one. Uses wait=False so we don't block on any
        in-flight scrape (a scrape can take 5-10 min, which would stall any
        caller that needs the scheduler back up quickly, e.g. /api/backup/restore).
        """
        try:
            self.scheduler.shutdown(wait=False)
        except Exception as e:
            logger.warning(f"Scheduler shutdown during restart: {e}")
        self.scheduler = BackgroundScheduler(timezone=SGT)
        self.start()

    def get_next_run_time(self):
        """Get next scheduled run time"""
        job = self.scheduler.get_job('daily_scrape')
        if job:
            return job.next_run_time
        return None
