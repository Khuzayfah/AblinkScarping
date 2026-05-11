"""Database models and setup"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

Base = declarative_base()

class VehicleListing(Base):
    """Model for storing vehicle listing data"""
    __tablename__ = "vehicle_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    scrape_date = Column(DateTime, default=datetime.now, index=True)
    make_model = Column(String(200), index=True)
    registered_year = Column(Integer)
    depreciation = Column(String(100))
    dealer_name = Column(String(200))
    price = Column(Float)
    listing_url = Column(Text)
    additional_info = Column(Text)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "scrape_date": self.scrape_date.strftime("%Y-%m-%d %H:%M:%S"),
            "date": self.scrape_date.strftime("%Y-%m-%d"),
            "make_model": self.make_model,
            "registered_year": self.registered_year,
            "depreciation": self.depreciation,
            "dealer_name": self.dealer_name,
            "price": self.price,
            "listing_url": self.listing_url,
            "additional_info": self.additional_info
        }

class DailyReport(Base):
    """Model for storing daily report summaries"""
    __tablename__ = "daily_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(DateTime, default=datetime.now, index=True)
    total_listings = Column(Integer)
    vehicles_tracked = Column(String(500))
    highest_price = Column(Float)
    lowest_price = Column(Float)
    avg_price = Column(Float)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "report_date": self.report_date.strftime("%Y-%m-%d %H:%M:%S"),
            "total_listings": self.total_listings,
            "vehicles_tracked": self.vehicles_tracked,
            "highest_price": self.highest_price,
            "lowest_price": self.lowest_price,
            "avg_price": self.avg_price
        }


class ScrapeLog(Base):
    """Model for last scrape time and status"""
    __tablename__ = "scrape_log"
    
    id = Column(Integer, primary_key=True, index=True)
    last_scrape_at = Column(DateTime)
    status = Column(String(20), default="Ready")  # Ready, Scraping
    created_at = Column(DateTime, default=datetime.now)


class AppSetting(Base):
    """Key-value store for app settings (schedule etc.)"""
    __tablename__ = "app_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, index=True)
    value = Column(Text)


class SoldLog(Base):
    """Daily Sold Log: when a unit from Chart 1 disappears (sold), log it"""
    __tablename__ = "sold_log"

    id = Column(Integer, primary_key=True, index=True)
    sold_date = Column(DateTime, index=True)  # date we detected as sold
    make_model = Column(String(200), index=True)
    year_registered = Column(Integer)
    depreciation = Column(String(100))  # e.g. $16,890/yr
    dealer_name = Column(String(200))
    price = Column(Float)
    listing_url = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "sold_date": self.sold_date.strftime("%Y-%m-%d") if self.sold_date else None,
            "make_model": self.make_model,
            "year_registered": self.year_registered,
            "depreciation": self.depreciation,
            "dealer_name": self.dealer_name,
            "price": self.price,
            "listing_url": self.listing_url,
        }


class SgcarmartSold(Base):
    """Accumulated sold listings from SGCarMart (avl=s) - all-time sold vehicles"""
    __tablename__ = "sgcarmart_sold"

    id = Column(Integer, primary_key=True, index=True)
    scrape_date = Column(DateTime, default=datetime.now, index=True)
    make_model = Column(String(200), index=True)
    year_registered = Column(Integer)
    depreciation = Column(String(100))
    dealer_name = Column(String(200))
    price = Column(Float)
    listing_url = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "scrape_date": self.scrape_date.strftime("%Y-%m-%d") if self.scrape_date else None,
            "make_model": self.make_model,
            "year_registered": self.year_registered,
            "depreciation": self.depreciation,
            "dealer_name": self.dealer_name,
            "price": self.price,
            "listing_url": self.listing_url,
        }


class ListingCache(Base):
    """Cache of listing data captured while active.
    SGCarMart removes depreciation/price from detail pages once sold,
    so we store this data while the listing is still active.
    Keyed by listing URL (without query params).
    """
    __tablename__ = "listing_cache"

    id = Column(Integer, primary_key=True, index=True)
    listing_url_clean = Column(String(500), unique=True, index=True)  # URL without ?params
    make_model = Column(String(200))
    year_registered = Column(Integer)
    depreciation = Column(String(100))
    dealer_name = Column(String(200))
    price = Column(Float)
    last_seen = Column(DateTime, default=datetime.now)  # last time seen as active


# Create engine and session
engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

    # Migrate: populate listing_cache from existing vehicle_listings data
    _migrate_listing_cache()

    # Clean up invalid $0/yr entries in listing_cache (SGCarMart uses 0 as N/A placeholder)
    _clean_invalid_cache_dep()


def _migrate_listing_cache():
    """One-time migration: populate listing_cache from existing vehicle_listings.
    This ensures we have cached depreciation/price data for listings
    that were previously scraped while active.
    """
    from sqlalchemy import text, inspect
    db = SessionLocal()
    try:
        # Check if listing_cache already has data (skip if already migrated)
        count = db.query(ListingCache).count()
        if count > 0:
            return

        # Check if vehicle_listings has any data to migrate
        inspector = inspect(engine)
        if 'vehicle_listings' not in inspector.get_table_names():
            return

        vl_count = db.query(VehicleListing).count()
        if vl_count == 0:
            return

        # Populate cache from vehicle_listings (latest data per URL)
        from sqlalchemy import func
        # Get the latest listing per URL with valid depreciation
        subq = db.query(
            VehicleListing.listing_url,
            func.max(VehicleListing.id).label('max_id')
        ).filter(
            VehicleListing.listing_url.isnot(None),
            VehicleListing.listing_url != ''
        ).group_by(VehicleListing.listing_url).subquery()

        rows = db.query(VehicleListing).join(
            subq, VehicleListing.id == subq.c.max_id
        ).all()

        seen_urls = set()
        inserted = 0
        for row in rows:
            url = row.listing_url
            if not url:
                continue
            clean_url = url.split('?')[0]

            # Skip duplicates (different query params, same base URL)
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)

            dep = (row.depreciation or '').strip()
            dealer = (row.dealer_name or '').strip()
            price = row.price

            # Skip invalid depreciation values ($0/yr means N/A, not real data)
            _bad_dep = {'', '–', '$0/yr'}
            if dep in _bad_dep:
                if not price and (not dealer or dealer == '–'):
                    continue

            db.add(ListingCache(
                listing_url_clean=clean_url,
                make_model=row.make_model or '',
                year_registered=row.registered_year,
                depreciation=dep if dep not in _bad_dep else None,
                dealer_name=dealer if dealer and dealer != '–' else None,
                price=price,
                last_seen=row.scrape_date,
            ))
            inserted += 1

        if inserted:
            db.commit()
            import logging
            logging.getLogger("database").info(f"[MIGRATE] Populated listing_cache with {inserted} entries from vehicle_listings")
    except Exception as e:
        import logging
        logging.getLogger("database").warning(f"[MIGRATE] listing_cache migration note: {e}")
        db.rollback()
    finally:
        db.close()

def _clean_invalid_cache_dep():
    """Clean up listing_cache entries where depreciation='$0/yr' (SGCarMart N/A placeholder)."""
    db = SessionLocal()
    try:
        updated = db.query(ListingCache).filter(
            ListingCache.depreciation == '$0/yr'
        ).update({ListingCache.depreciation: None})
        if updated:
            db.commit()
            import logging
            logging.getLogger("database").info(f"[CLEANUP] Cleared $0/yr depreciation from {updated} cache entries")
    except Exception as e:
        import logging
        logging.getLogger("database").warning(f"[CLEANUP] Cache cleanup note: {e}")
        db.rollback()
    finally:
        db.close()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
