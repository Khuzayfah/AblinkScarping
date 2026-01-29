# SGCarmart Real-time Scraping Guide
## Ablink SGCarmart Scraper by Oneiros Indonesia

---

## Real Scraping from SGCarmart ✓

### What Gets Scraped

The system connects to **SGCarmart.com** and scrapes:

| Data | Source |
|------|--------|
| Vehicle Categories | 10FT DIESEL, 14FT DIESEL, VAN DIESEL, VAN PETROL |
| Vehicle Models | HINO, TOYOTA, NISSAN, MITSUBISHI, ISUZU, KIA, HONDA |
| Years | 2025 down to 2014 & Older |
| Prices | Lowest & Average depreciation per year |
| Units | Number of vehicles available |

### URLs Scraped

```
10FT DIESEL:
https://www.sgcarmart.com/used_cars/listing.php?VT=30

14FT DIESEL:
https://www.sgcarmart.com/used_cars/listing.php?VT=31

VAN DIESEL:
https://www.sgcarmart.com/used_cars/listing.php?VT=34&FUE=1

VAN PETROL:
https://www.sgcarmart.com/used_cars/listing.php?VT=34&FUE=2
```

---

## How to Scrape

### Method 1: Manual Scraping

1. Open dashboard: http://localhost:5555
2. Look for large button at top: **"🔄 SCRAPE NOW FROM SGCARMART"**
3. Click button
4. Confirm dialog (will take 2-3 minutes)
5. Wait for completion message
6. Data automatically saved to history

### Method 2: Auto Scraping

- **Automatic daily at 09:00 AM**
- No action needed
- Data saved automatically
- Check history to see results

---

## How It Works

### Step-by-Step Process

1. **Connect to SGCarmart**
   - Opens Chrome browser (headless mode)
   - Navigates to each vehicle category

2. **Extract Data**
   - Finds all vehicle listings
   - Extracts: name, year, price, units
   - Calculates depreciation

3. **Aggregate Data**
   - Groups by category and vehicle
   - Calculates lowest price
   - Calculates average price
   - Counts units

4. **Save to History**
   - Creates folder for today: `data/history/2026-01-29/`
   - Saves JSON file: `latest.json`
   - Saves CSV file: `data_HHMMSS.csv`
   - Saves Excel file: `data_HHMMSS.xlsx`
   - Updates index: `data/history/index.json`

5. **Calculate Differences**
   - Compares with previous day
   - Shows +/- difference in units

---

## Data Storage

### File Structure

```
data/
├── history/
│   ├── 2026-01-29/           ← Today's data
│   │   ├── latest.json       ← Latest scrape
│   │   ├── data_090000.json  ← 9:00 AM scrape
│   │   ├── data_090000.csv
│   │   ├── data_090000.xlsx
│   │   ├── data_140530.json  ← Manual scrape at 2:05 PM
│   │   ├── data_140530.csv
│   │   └── data_140530.xlsx
│   ├── 2026-01-28/           ← Yesterday
│   ├── 2026-01-27/           ← Day before
│   └── index.json            ← Index of all dates
└── pricelist.json            ← Your uploaded pricelist
```

### JSON Format

```json
{
  "date": "2026-01-29",
  "time": "09:00:00",
  "vehicles": [
    {
      "category": "10FT DIESEL",
      "vehicle": "HINO DUTRO 2.8",
      "years": {
        "2025": {
          "lowest": 11510,
          "average": 11480,
          "units": 49
        },
        "2024": {
          "lowest": 11450,
          "average": 11450,
          "units": 8
        }
      },
      "total_units": 57,
      "previous": 55,
      "diff": 2
    }
  ],
  "total_scraped": 450
}
```

---

## History Navigation

### View Past Data

1. **Use arrow buttons**: ← Previous Day | Next Day →
2. **Keyboard shortcuts**: 
   - ← (Left Arrow) = Previous day
   - → (Right Arrow) = Next day
3. **Unlimited history**: All past scrapes saved forever
4. **Date display**: Shows which day you're viewing

### Features

| Feature | Description |
|---------|-------------|
| Latest Data | Always shows most recent scrape first |
| Previous Button | Disabled when on oldest data |
| Next Button | Disabled when on latest data |
| Date Label | Shows "Latest Data" or "Historical Data" |
| Keyboard Nav | Use arrow keys to navigate |

---

## Scraping Status

### Status Indicators

| Status | Meaning | Color |
|--------|---------|-------|
| Ready | System ready to scrape | Green |
| Scraping... | Currently scraping | Orange (pulsing) |
| Error | Scraping failed | Red |

### What to Check

- **Last scrape**: Shows date & time of last successful scrape
- **Next auto**: Always 09:00 AM daily
- **History days**: Number of days with saved data
- **Data source**: Always SGCarmart.com

---

## Troubleshooting

### Scraping Takes Too Long

**Cause**: SGCarmart website slow or many listings

**Solution**: 
- Be patient (can take 3-5 minutes)
- Check terminal for progress logs
- Don't close browser

### No Data Scraped

**Cause**: Website blocked or changed structure

**Solution**:
- Check internet connection
- Try again later
- System will use sample data as fallback

### Button Not Working

**Cause**: JavaScript not loaded

**Solution**:
- Refresh page (F5)
- Clear browser cache (Ctrl+Shift+R)
- Check browser console (F12)

---

## Requirements

### Software

- Python 3.8+
- Chrome browser (for Selenium)
- Internet connection

### Python Packages

```
selenium>=4.0.0
beautifulsoup4>=4.11.0
pandas>=2.0.0
openpyxl>=3.0.0
webdriver-manager>=3.8.0
flask>=3.0.0
schedule>=1.2.0
```

### Install

```bash
pip install -r requirements.txt
```

---

## Technical Details

### Scraper Module

**File**: `sgcarmart_scraper.py`

**Class**: `SGCarmartScraper`

**Methods**:
- `scrape_all_categories()` - Main scraping function
- `scrape_listing_page()` - Scrape one category
- `_parse_listing()` - Parse vehicle details
- `_aggregate_data()` - Calculate stats

### History Manager

**File**: `data_history_manager.py`

**Class**: `DataHistoryManager`

**Methods**:
- `save_data()` - Save scraped data
- `get_dates()` - Get all history dates
- `get_data()` - Get data for specific date
- `get_latest()` - Get most recent data
- `calculate_diff()` - Calculate differences

### Scheduler

**Auto-scraping**:
- Uses `schedule` library
- Runs in background thread
- Daily at 09:00 AM
- Saves to history automatically

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scrape` | POST | Start manual scraping |
| `/api/status` | GET | Get scraping status |
| `/api/history` | GET | Get all history dates |
| `/api/data/latest` | GET | Get latest data |
| `/api/data/<date>` | GET | Get data for specific date |
| `/api/export/<date>/<format>` | GET | Export data (csv/excel/pdf) |

---

## Validation

### Data Quality Checks

✓ Price must be > $0
✓ Year must be 2014-2026
✓ Units must be > 0
✓ Vehicle name not empty
✓ Category matches predefined list

### Real-time Verification

To verify data is real:

1. Open SGCarmart.com manually
2. Browse vehicles in same category
3. Compare prices with scraped data
4. Prices should match ±5%

---

**Developed by Oneiros Indonesia**
**For Ablink Singapore**
