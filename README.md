# SGCarMart Commercial Vehicle Scraper

A comprehensive web scraping system for tracking commercial vehicle listings on SGCarMart with automated daily reports and sold vehicle detection.

## 🚀 Features

- **Automated Web Scraping**: Scrapes SGCarMart for commercial vehicles (Hiace, Dyna, Hino Dutro, NV350, etc.)
- **Cloudflare Bypass**: Uses undetected-playwright for reliable scraping
- **Daily Reports**: Generates comprehensive daily reports with vehicle listings
- **Sold Vehicle Detection**: Tracks when vehicles are sold and logs them
- **Web Dashboard**: FastAPI-powered web interface for viewing data
- **Data Export**: Export to CSV, Excel, and PDF formats
- **Scheduler**: Automated daily scraping at configured times
- **Private Seller Detection**: Identifies "Direct Owner" listings
- **Aligned Data Display**: Year, depreciation, and dealer names are perfectly aligned with comma separators

## 📊 Tracked Vehicles

- Toyota Hiace (2.8A, 3.0M, 2.0)
- Toyota Dyna (2.8, 3.0)
- Hino Dutro 2.8
- Hino XZU710
- Nissan Cabstar
- Nissan NV350 (2.5M, 2.0)
- Nissan NV200 (1.5M, 1.6A)
- Isuzu NPR85, NMR85, NNR85
- Mitsubishi FEA01, FEA21
- Honda N-VAN
- KIA 2500
- And more commercial vehicles

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Khuzayfah/AblinkScarping.git
cd AblinkScarping
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

4. Configure settings (optional):
```bash
# Edit config.py to customize:
# - Target vehicles
# - Scraping schedule
# - Database location
```

## 🚀 Usage

### Run Web Interface

```bash
python main.py
```

Then open your browser to: `http://localhost:8000`

### Manual Scraping

```bash
# Run scraper once
python js_scraper.py

# Run with browser visible (for debugging)
python js_scraper.py --headed
```

### Check Database

```bash
# View latest scrape data
python check_database.py

# Check sold log
python check_sold_log.py

# Check dealer names
python check_direct_owner.py
```

## 📁 Project Structure

```
Ablink_Scraping/
├── main.py                     # FastAPI web server
├── js_scraper.py               # Main scraper with Cloudflare bypass
├── database.py                 # Database models (SQLAlchemy)
├── config.py                   # Configuration settings
├── sold_log_service.py         # Sold vehicle detection
├── export_service.py           # Data export (CSV, Excel, PDF)
├── scheduler_service.py        # Automated scheduling
├── fix_missing_dealers.py      # Fix missing dealer names
├── clean_duplicates.py         # Remove duplicate entries
├── requirements.txt            # Python dependencies
├── scraping.db                 # SQLite database (auto-created)
├── static/                     # Web UI assets
│   └── index.html             # Dashboard interface
└── README.md                   # This file
```

## 🗄️ Database Schema

### vehicle_listings
- scrape_date: When the listing was scraped
- make_model: Vehicle make and model
- registered_year: Year of registration
- depreciation: Annual depreciation
- dealer_name: Dealer name (or "Direct Owner")
- price: Listing price
- listing_url: SGCarMart URL
- additional_info: Extra details

### sold_log
- sold_date: When vehicle was detected as sold
- make_model: Vehicle make and model
- year_registered: Year of registration
- depreciation: Annual depreciation
- dealer_name: Dealer name

## 🔧 Configuration

Edit `config.py`:

```python
# Target vehicles to track
TARGET_VEHICLES = [
    "10FT DIESEL",
    "14FT DIESEL",
    "HINO DUTRO 2.8",
    # ... add more
]

# Scraping schedule
SCRAPE_SCHEDULE_TIME = "08:00"  # Daily at 8 AM

# Database
DATABASE_URL = "sqlite:///./scraping.db"
```

## 📝 API Endpoints

- `GET /` - Web dashboard
- `GET /api/latest-data` - Get latest scrape data
- `GET /api/daily-report` - Get daily report (aligned format)
- `GET /api/sold-log` - Get sold vehicle log
- `POST /api/scrape-now` - Trigger manual scrape
- `GET /api/export/csv` - Export to CSV
- `GET /api/export/excel` - Export to Excel
- `GET /api/export/pdf` - Export to PDF

## 🎯 Key Features Explained

### Aligned Data Display

Year, depreciation, and dealer names are perfectly aligned:

```
Model: HINO DUTRO 2.8
Dealers:      ABS Bus Pte Ltd, Lek Auto Pte Ltd, Pioneer Auto
Years:        2025, 2025, 2024
Depreciation: $12,670/yr, $11,850/yr, $11,970/yr
              ↓            ↓            ↓
           (aligned)    (aligned)    (aligned)
```

Each dealer has corresponding year and depreciation value.

### Private Seller Detection

Automatically detects "Direct Owner" listings (private sellers) and labels them accordingly.

### Sold Vehicle Detection

Compares daily scrapes to detect when vehicles disappear from listings (sold).

### Cloudflare Bypass

Uses undetected-playwright to bypass Cloudflare protection and scrape reliably.

## 🐛 Troubleshooting

### Scraper Returns No Data

1. Check if SGCarMart website structure changed
2. Run with `--headed` to see browser: `python js_scraper.py --headed`
3. Check internet connection

### Database Locked Error

Close any programs accessing the database (including DB browsers).

### Missing Dealer Names

Run the fix script:
```bash
python fix_missing_dealers.py
```

### Duplicate Entries

Clean up duplicates:
```bash
python clean_duplicates.py
```

## 📚 Documentation

- `DEALER_NAME_FIX_README.md` - Dealer name fixes
- `VARIOUS_FIX_README.md` - "Various" issue fix
- `COMMA_SEPARATOR_FIX.md` - Comma separator implementation
- `ALIGNED_DATA_FINAL.md` - Aligned data structure

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is for educational and personal use only. Please respect SGCarMart's terms of service and robots.txt.

## ⚠️ Disclaimer

This tool is for personal use and educational purposes. Users are responsible for:
- Respecting website terms of service
- Not overloading servers with requests
- Complying with data protection laws
- Using scraped data ethically

## 👨‍💻 Author

Developed for commercial vehicle tracking and market analysis.

## 🔗 Links

- Repository: https://github.com/Khuzayfah/AblinkScarping
- SGCarMart: https://www.sgcarmart.com

## 📊 Stats

- **100% dealer name coverage** (including Direct Owner)
- **Unique combinations** (no duplicates)
- **Aligned data** (year, depreciation, dealer)
- **Automated daily scraping**
- **Export to multiple formats**

---

**Made with ❤️ for commercial vehicle enthusiasts**
