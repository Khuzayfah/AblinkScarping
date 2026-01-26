# Changelog
## Ablink SGCarmart Scraper

---

## Version 1.0.0 - Final Release (January 25, 2026)

### Project Cleanup & Rebranding

**✅ Removed unused files:**
- Deleted old COE scraper modules (sgcarmart_scraper.py, smart_scraper.py)
- Removed test files (test_scraper.py, test_now.py, create_sample_depreciation.py)
- Cleaned up duplicate batch files
- Removed excessive documentation files (kept essential 3)

**✅ Updated branding:**
- Project name: "Ablink SGCarmart Scraper by Oneiros Indonesia"
- Updated all file headers with proper branding
- English comments throughout codebase
- Professional footer in all outputs

**✅ Code improvements:**
- Consistent naming conventions
- Clean, production-ready code
- All comments in English
- Removed debugging code

**✅ Documentation:**
- README.md - Main documentation
- QUICK_START.md - Quick reference guide
- PROJECT_INFO.md - Technical specifications
- CHANGELOG.md - This file

---

## Core Features Implemented

### 1. Web Interface
- Flask-based web application
- One-click refresh button
- Real-time progress tracking
- Auto-save functionality
- Download and print buttons

### 2. Scraping Engine
- Selenium-based scraper for SGCarmart.com
- Extracts all vehicle categories
- Year-wise depreciation data
- Error handling and logging

### 3. Report Generation
- Excel (.xlsx) format
- CSV (.csv) format
- Styled HTML with Excel-like design
- Color-coded values (green/red/yellow)
- Print-optimized for PDF

### 4. API Integration
- RESTful API for n8n/webhooks
- API key authentication
- JSON response format
- Multiple endpoints (scrape, status, latest)

### 5. Automation
- Windows Task Scheduler support
- Configurable schedule time
- Logging and error tracking
- One-click setup

---

## Technical Specifications

**Language:** Python 3.8+  
**Frameworks:** Flask, Selenium, BeautifulSoup4, Pandas  
**Browser:** Chrome (automated via ChromeDriver)  
**Platform:** Windows (primary), Linux/Mac compatible

---

## File Structure (Final)

```
Ablink-SGCarmart-Scraper/
├── depreciation_scraper.py          # Core scraper
├── depreciation_html_generator.py   # HTML report generator
├── web_scraper_app.py               # Web interface
├── n8n_webhook_api.py               # API server
├── config.json                      # Configuration
├── requirements.txt                 # Dependencies
├── RUN_WEB_APP.bat                  # Quick start
├── SETUP_AUTO_DAILY.bat             # Automation setup
├── README.md                        # Main docs
├── QUICK_START.md                   # Quick guide
├── PROJECT_INFO.md                  # Technical info
├── CHANGELOG.md                     # This file
├── templates/
│   └── index.html                   # Web template
└── daily_reports/                   # Output folder
    ├── *.xlsx
    ├── *.csv
    ├── *.html
    └── scraping_log.txt
```

---

## Data Output

**Categories scraped:**
- 10FT DIESEL (7 vehicles)
- 14FT DIESEL (5 vehicles)
- VAN DIESEL - GOODS VAN (5 vehicles)
- VAN PETROL - GOODS VAN (4 vehicles)

**Total:** 21+ vehicle models

**Data columns:**
- Vehicle name
- Category
- Years: 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014 & Older
- TOTAL UNITS
- Previous
- DIFF

**All prices in SGD ($)**

---

## Deployment Status

✅ **Local Development** - Ready  
✅ **Web Interface** - Running on localhost:5000  
✅ **API Server** - Available on localhost:5001  
✅ **Daily Automation** - Setup available  
✅ **n8n Integration** - Compatible  
✅ **Documentation** - Complete  

---

## Known Limitations

1. **Browser requirement:** Needs Chrome installed
2. **Platform:** Automation optimized for Windows
3. **Network:** Requires stable internet connection
4. **Website dependency:** Subject to SGCarmart.com structure changes

---

## Future Enhancements (Optional)

- [ ] Email notifications when scraping completes
- [ ] Data comparison between dates
- [ ] Charts and graphs in HTML reports
- [ ] Direct PDF generation (without print dialog)
- [ ] Multi-user support with authentication
- [ ] Database integration for historical data
- [ ] Mobile app interface
- [ ] Real-time dashboard

---

## Version History

### v1.0.0 (2026-01-25) - Production Release
- Initial release with all core features
- Web interface operational
- API integration ready
- Automation configured
- Documentation complete

---

**Developed by:** Oneiros Indonesia  
**Client:** Ablink Singapore  
**Status:** Production Ready ✓

---

*For support or feature requests, contact Oneiros Indonesia*
