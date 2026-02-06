"""Scheduler for automated scraping tasks"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import config
from js_scraper import SGCarMartJSScraper
from database import SessionLocal, ScrapeLog

class ScraperScheduler:
    """Scheduler for automated scraping"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scraper = SGCarMartJSScraper(headless=True)
        self._hour = config.SCRAPING_SCHEDULE_HOUR
        self._minute = config.SCRAPING_SCHEDULE_MINUTE
        self._interval_days = 1  # Default: every day
        
    def scrape_job(self):
        """Job to execute scraping (active + sold listings)"""
        print(f"Automated scrape triggered at {datetime.now()}")
        try:
            self.scraper.scrape_vehicle_listings()
            self.scraper.scrape_sold_listings()
            db = SessionLocal()
            try:
                log = db.query(ScrapeLog).first()
                if log:
                    log.status = "Ready"
                    log.last_scrape_at = datetime.now()
                    db.commit()
            finally:
                db.close()
            print(f"Automated scrape completed successfully at {datetime.now()}")
        except Exception as e:
            print(f"Error during automated scrape: {e}")
            db = SessionLocal()
            try:
                log = db.query(ScrapeLog).first()
                if log:
                    log.status = "Ready"
                    db.commit()
            finally:
                db.close()
    
    def set_initial_schedule(self, hour: int, minute: int, interval_days: int = 1):
        """Set schedule before start (e.g. from DB)"""
        self._hour = hour
        self._minute = minute
        self._interval_days = interval_days

    def start(self):
        """Start the scheduler"""
        # Create cron trigger based on interval
        if self._interval_days == 1:
            # Every day
            trigger = CronTrigger(hour=self._hour, minute=self._minute)
            interval_text = "every day"
        elif self._interval_days == 2:
            # Every 2 days (even days of month: 2,4,6,8,...)
            trigger = CronTrigger(day='*/2', hour=self._hour, minute=self._minute)
            interval_text = "every 2 days"
        else:
            # Default to daily
            trigger = CronTrigger(hour=self._hour, minute=self._minute)
            interval_text = "every day"

        self.scheduler.add_job(
            self.scrape_job,
            trigger=trigger,
            id='daily_scrape',
            name='SGCarMart Scrape',
            replace_existing=True
        )
        self.scheduler.start()
        print(f"Scheduler started. Scraping {interval_text} at {self._hour:02d}:{self._minute:02d}")

    def update_schedule(self, hour: int, minute: int, interval_days: int = 1):
        """Update scrape time and interval"""
        self._hour = hour
        self._minute = minute
        self._interval_days = interval_days
        job = self.scheduler.get_job('daily_scrape')
        if job:
            # Create new trigger based on interval
            if interval_days == 1:
                trigger = CronTrigger(hour=hour, minute=minute)
                interval_text = "every day"
            elif interval_days == 2:
                trigger = CronTrigger(day='*/2', hour=hour, minute=minute)
                interval_text = "every 2 days"
            else:
                trigger = CronTrigger(hour=hour, minute=minute)
                interval_text = "every day"

            job.reschedule(trigger=trigger)
            print(f"Schedule updated to {interval_text} at {hour:02d}:{minute:02d}")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        print("Scheduler stopped")
    
    def get_next_run_time(self):
        """Get next scheduled run time"""
        job = self.scheduler.get_job('daily_scrape')
        if job:
            return job.next_run_time
        return None
