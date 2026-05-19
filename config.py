"""Configuration settings for the SGCarMart scraper"""
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()


# === Singapore Time helpers ===
# SGCarMart is a Singapore site and all user-facing dates are SGT (UTC+8).
# But Coolify Docker containers default to UTC, so datetime.now() returns
# UTC-based timestamps — leading to scrapes at 06:15 SGT being stored as
# May 18 22:15 (UTC date = May 18), confusing sold detection that thinks
# "today" is May 19. Always use now_sgt() / today_sgt() for DB writes and
# date arithmetic to keep everything in SGT regardless of container TZ.
_SGT = pytz.timezone('Asia/Singapore')


def now_sgt() -> datetime:
    """Naive SGT datetime — drops tzinfo so SQLAlchemy stores the wall-clock
    value as-is without re-interpreting it."""
    return datetime.now(_SGT).replace(tzinfo=None)


def today_sgt():
    """Today's date in SGT (date object)."""
    return now_sgt().date()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sgcarmart_data.db")

# Scraping schedule
SCRAPING_SCHEDULE_HOUR = int(os.getenv("SCRAPING_SCHEDULE_HOUR", "6"))
SCRAPING_SCHEDULE_MINUTE = int(os.getenv("SCRAPING_SCHEDULE_MINUTE", "0"))

# Google OAuth2 settings (for Gmail API email sending)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
APP_PORT = int(os.getenv("PORT", "3000"))
GMAIL_TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gmail_token.json")

# Target vehicles to scrape (order and categories for table display)
VEHICLE_CATEGORIES = {
    "10FT DIESEL": [
        "HINO DUTRO 2.8", "TOYOTA DYNA 2.8", "TOYOTA DYNA 150 3.0",
        "NISSAN CABSTAR", "CANTER FEA01", "ISUZU NHR / ISUZU NJR", "KIA K2500"
    ],
    "14FT DIESEL": [
        "HINO XZU710", "ISUZU NPR85", "ISUZU NMR85", "ISUZU NNR85",
        "CANTER FEB21"
    ],
    "VAN DIESEL (FILTER: GOODS VAN)": [
        "TOYOTA HIACE 3.0M", "TOYOTA HIACE 3.0A", "TOYOTA HIACE 2.8A",
        "NISSAN NV350 2.5", "NISSAN NV200 1.5M"
    ],
    "VAN PETROL (FILTER: GOODS VAN)": [
        "HONDA N-VAN", "TOYOTA HIACE 2.0", "NISSAN NV350 2.0",
        "NISSAN NV200 1.6A", "NISSAN NV200 VANETTE 1.6"
    ],
    "BUS DIESEL (FILTER: BUS/MINI BUS , FUEL: DIESEL)": [
        "TOYOTA HIACE COMMUTER 2.8A GL", "TOYOTA HIACE COMMUTER 3.0A GL",
        "TOYOTA HIACE COMMUTER 2.8A GL HIGH ROOF", "TOYOTA HIACE COMMUTER 3.0A GL HIGH ROOF",
        "TOYOTA COASTER", "MITSUBISHI ROSA"
    ]
}

# TARGET_VEHICLES list for matching scraped data
# "ISUZU NHR" and "ISUZU NJR" are separate targets but combined in one display row
# NOTE: More-specific COMMUTER targets must appear BEFORE their base variants
# so they match first (before goods-van passenger exclusion can reject them)
TARGET_VEHICLES = [
    "HINO DUTRO 2.8",
    "HINO XZU710",
    "TOYOTA DYNA 2.8",
    "TOYOTA DYNA 3.0",
    "TOYOTA HIACE 3.0M",
    "TOYOTA HIACE COMMUTER 3.0A GL HIGH ROOF",  # before non-HIGH ROOF variant
    "TOYOTA HIACE COMMUTER 3.0A GL",  # before TOYOTA HIACE 3.0A
    "TOYOTA HIACE 3.0A",
    "TOYOTA HIACE COMMUTER 2.8A GL HIGH ROOF",  # before non-HIGH ROOF variant
    "TOYOTA HIACE COMMUTER 2.8A GL",  # before TOYOTA HIACE 2.8A
    "TOYOTA HIACE 2.8A",
    "TOYOTA HIACE 2.0",
    "TOYOTA COASTER",
    "NISSAN CABSTAR",
    "NISSAN NV350 2.5",
    "NISSAN NV350 2.0",
    "NISSAN NV200 1.5M",
    "NISSAN NV200 1.6A",
    "NISSAN NV200 VANETTE 1.6",
    "ISUZU NHR",
    "ISUZU NJR",
    "ISUZU NPR85",
    "ISUZU NMR85",
    "ISUZU NNR85",
    "CANTER FEA01",
    "CANTER FEB21",
    "KIA K2500",
    "HONDA N-VAN",
    "MITSUBISHI ROSA",
]

# Display name mapping: TARGET_VEHICLES name -> VEHICLE_CATEGORIES display name
# Used when the normalized matching name differs from the display name
TARGET_DISPLAY_NAMES = {
    "TOYOTA DYNA 3.0": "TOYOTA DYNA 150 3.0",
}

# SGCarMart URLs (site migrated to Next.js - new format)
BASE_URL = "https://www.sgcarmart.com"
# New site uses hyphens; veh=1 = commercial (Van, Truck)
USED_CARS_URL = f"{BASE_URL}/used-cars/listing"
COMMERCIAL_LISTING_URL = f"{BASE_URL}/used-cars/listing?veh=1&limit=100"

# Human-like behavior settings (random delays in seconds)
HUMAN_DELAYS = {
    "page_load_min": 4.5,
    "page_load_max": 8.3,
    "scroll_pause_min": 1.8,
    "scroll_pause_max": 4.5,
    "between_pages_min": 3.5,
    "between_pages_max": 7.2,
    "dealer_fetch_min": 1.2,
    "dealer_fetch_max": 2.8
}
