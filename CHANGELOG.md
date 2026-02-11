# Changelog

All notable changes to the Ablink SGCarMart Scraper project will be documented in this file.

## [1.1.0] - 2026-02-11

### ✨ Added
- **Depreciation/Units Table by Year** - Major new feature!
  - Active Listings - Depreciation / Units by Year section
  - Sold Listings - Depreciation / Units by Year section
  - Table format: [DATE] [VEHICLE NAME] [YEAR COLUMNS: LOWEST/AVERAGE/UNIT] [TOTAL UNITS]
  - Category grouping: VAN DIESEL, VAN PETROL, 10FT DIESEL, 14FT DIESEL
  - Collapsible sections with date picker

- **New API Endpoints**:
  - `GET /api/depreciation-by-year?date=YYYY-MM-DD&source=active|sold`
    - Calculates LOWEST, AVERAGE, UNIT for each year registration
    - Parses depreciation from string ($16,890/yr) to integer
    - Groups by vehicle model and year
  - `GET /api/vehicle-categories`
    - Returns vehicle category grouping from config
    - Used for table display ordering

### 🔧 Changed
- Frontend: Added 2 new collapsible sections before Active Listings Data
- JavaScript: Enhanced date formatting ("9 DEC" style)
- Table styling: Matches screenshot format with proper borders and colors

### 📦 Deployment
- Added `DEPLOYMENT.md` with complete Coolify deployment guide
- Added `.coolify/config.yaml` for auto-configuration
- Volume mount configuration for database persistence
- Health check, resource limits, environment variables documented

---

## [1.0.0] - 2026-02-06

### ✨ Initial Release
- Real-time scraping from SGCarMart.com
- Daily sold vehicle detection (comparison method)
- Three-layer architecture:
  - Chart 1: Active Listings (VehicleListing table)
  - Chart 2: SGCarMart Sold (SgcarmartSold table - avl=s parameter)
  - Chart 3: Daily Sold Log (SoldLog table - comparison detection)

### 🛠️ Features
- **Scraping Engine**:
  - curl_cffi with Chrome impersonation for Cloudflare bypass
  - Next.js RSC payload extraction (no JS rendering needed)
  - Dealer mapping from RSC payload
  - MAX_DETAIL_FETCHES = 80 for depreciation lookup

- **Sold Detection**:
  - Comparison method: yesterday's active vs today's active
  - Layer 0: ListingCache for depreciation/price (SGCarMart removes this when sold)
  - Automatic sold logging with full data

- **Database**:
  - SQLite with 6 tables:
    - vehicle_listings (active scrapes)
    - sold_log (daily sold detection)
    - sgcarmart_sold (accumulated sold from SGCarMart avl=s)
    - listing_cache (cache active data for sold lookup)
    - scrape_log (scraper status)
    - app_settings (schedule config)
    - daily_reports (unused, reserved for future)

- **Frontend**:
  - Bootstrap 5 UI with Ablink green theme
  - Calendar navigation for daily reports
  - Export: CSV, Excel, PDF
  - Collapsible sections: Active Log, Sold Log, How It Works
  - History dropdown for quick date navigation

- **Scheduling**:
  - APScheduler with cron jobs
  - Default: 06:00 AM SGT daily
  - Configurable via UI
  - Timezone: Asia/Singapore (SGT)

- **Export Service**:
  - CSV: Daily sold report
  - Excel: Formatted with openpyxl
  - PDF: ReportLab with tables
  - SGCarMart Sold CSV (all-time export)

### 🔒 Important Lessons Learned
- **Sold pages are useless**: SGCarMart removes depreciation AND price from both listing RSC and detail pages once sold
- **ListingCache solution**: Cache depreciation/price/dealer from active scrapes for later sold lookup
- **DB migrations**: SQLite requires ALTER TABLE for new columns
- **Frontend colspan**: Update ALL colspan values when adding table columns

### 🐛 Known Issues
- First scrape only saves active listings (no comparison yet)
- Both days must complete successfully for sold detection
- Server must stay running for scheduler to work

### 📋 Tech Stack
- Backend: FastAPI + SQLAlchemy + APScheduler
- Scraper: curl_cffi + BeautifulSoup4 + Playwright (backup)
- Database: SQLite
- Frontend: Vanilla JS + Bootstrap 5
- Export: pandas, openpyxl, reportlab
- Deployment: Docker + Coolify

---

## Release Notes Format

- ✨ Added: New features
- 🔧 Changed: Changes in existing functionality
- 🐛 Fixed: Bug fixes
- 🗑️ Removed: Removed features
- 📦 Deployment: Deployment-related changes
- 🔒 Security: Security fixes
- 📝 Documentation: Documentation changes

---

**Repository**: https://github.com/Khuzayfah/AblinkScarping
**Maintained by**: Oneiros Indonesia
