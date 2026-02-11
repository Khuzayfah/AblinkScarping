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
        "NISSAN CABSTAR", "MITSUBISHI FEA01", "ISUZU NHR / NJR", "KIA 2500"
    ],
    "14FT DIESEL": [
        "HINO XZU710", "ISUZU NPR85", "ISUZU NMR85", "ISUZU NNR85",
        "MITSUBISHI FEA21"
    ],
    "VAN DIESEL (GOODS VAN)": [
        "TOYOTA HIACE 3.0M", "TOYOTA HIACE 3.0A", "TOYOTA HIACE 2.8A",
        "NISSAN NV350 2.5M", "NISSAN NV200 1.5M"
    ],
    "VAN PETROL (GOODS VAN)": [
        "HONDA N-VAN", "TOYOTA HIACE 2.0", "NISSAN NV350 2.0",
        "NISSAN NV200 1.6A"
    ]
}

TARGET_VEHICLES = [
    "HINO DUTRO 2.8",
    "HINO XZU710",
    "TOYOTA DYNA 2.8",
    "TOYOTA DYNA 3.0",
    "TOYOTA HIACE 3.0M",
    "TOYOTA HIACE 3.0A",
    "TOYOTA HIACE 2.8A",
    "TOYOTA HIACE 2.0",
    "NISSAN CABSTAR",
    "NISSAN NV350 2.5M",
    "NISSAN NV350 2.0",
    "NISSAN NV200 1.5M",
    "NISSAN NV200 1.6A",
    "ISUZU NHR / NJR",
    "ISUZU NPR85",
    "ISUZU NMR85",
    "ISUZU NNR85",
    "MITSUBISHI FEA01",
    "MITSUBISHI FEA21",
    "KIA 2500",
    "HONDA N-VAN",
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
