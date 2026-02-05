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
    value = Column(String(200))


class SoldLog(Base):
    """Daily Sold Log: when a unit from Chart 1 disappears (sold), log it"""
    __tablename__ = "sold_log"
    
    id = Column(Integer, primary_key=True, index=True)
    sold_date = Column(DateTime, index=True)  # date we detected as sold
    make_model = Column(String(200), index=True)
    year_registered = Column(Integer)
    depreciation = Column(String(100))  # e.g. $16,890 or COE info
    dealer_name = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            "id": self.id,
            "sold_date": self.sold_date.strftime("%Y-%m-%d") if self.sold_date else None,
            "make_model": self.make_model,
            "year_registered": self.year_registered,
            "depreciation": self.depreciation,
            "dealer_name": self.dealer_name,
        }

# Create engine and session
engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
