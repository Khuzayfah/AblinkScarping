"""Configuration settings for the SGCarMart scraper"""
import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sgcarmart_data.db")

# Scraping schedule
SCRAPING_SCHEDULE_HOUR = int(os.getenv("SCRAPING_SCHEDULE_HOUR", "6"))
SCRAPING_SCHEDULE_MINUTE = int(os.getenv("SCRAPING_SCHEDULE_MINUTE", "0"))

# Target vehicles to scrape (order and categories for table display)
VEHICLE_CATEGORIES = {
    "10FT DIESEL": [
        "HINO DUTRO 2.8", "TOYOTA DYNA 2.8", "TOYOTA DYNA 3.0",
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
        "TOYOTA HIACE 3.0A", "TOYOTA COASTER", "MITSUBISHI ROSA"
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
    "TOYOTA HIACE COMMUTER 3.0A GL",  # before TOYOTA HIACE 3.0A
    "TOYOTA HIACE 3.0A",
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
