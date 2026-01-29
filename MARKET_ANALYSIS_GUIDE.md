# Ablink SGCarmart Scraper - Market Analysis Dashboard
## By Oneiros Indonesia

---

## Features

### 1. Upload Pricelist
- Upload your pricelist file (Excel or CSV)
- Supported formats: `.xlsx`, `.xls`, `.csv`
- Template file available: `pricelist/PRICELIST_TEMPLATE.csv`
- Clear and replace data anytime

### 2. Two Data Charts

#### Chart 1: DEPRECIATION / UNITS (Lowest + Average)
- Shows depreciation data for each vehicle
- **Lowest**: The lowest depreciation price found on SGCarmart
- **Average**: The average depreciation price on SGCarmart
- Years: 2025 down to 2014 & Older
- TOTAL UNITS, Previous (Date), and DIFF columns

#### Chart 2: NUMBER OF UNITS SOLD LAST 60 DAYS
- Shows how many units were sold for each vehicle model
- Organized by year
- TOTAL UNITS and Last 120 Days columns

### 3. Price Comparison
When you upload your pricelist, the system will show:
- **Our Depreciation**: Your price
- **X vehicles cheaper than us**: How many vehicles on SGCarmart are cheaper
- **X vehicles more expensive**: How many vehicles are more expensive
- SGCarmart data: Lowest, Average, and Units count

### 4. Export Options
- **CSV**: Download data as CSV file
- **Excel**: Download data as Excel file (.xlsx)
- **PDF**: Open printable HTML (save as PDF via browser)

---

## How to Run

### Option 1: Double-click the batch file
```
RUN_MARKET_ANALYSIS.bat
```

### Option 2: Run from command line
```
python market_analysis_app.py
```

The server will start at: **http://localhost:5555**

---

## Pricelist Format

Your pricelist file must have these columns:

| Column | Description | Example |
|--------|-------------|---------|
| Category | Vehicle category | 10FT DIESEL |
| Description | Vehicle model/name | Toyota Dyna 150MT |
| Registered Date | Registration date | 30/12/2025 |
| Asking $ | Your asking price | $123800 |
| COE Expiry | COE expiry date | 29/12/2035 |

**Template file**: `pricelist/PRICELIST_TEMPLATE.csv`

---

## Category Colors

| Category | Color |
|----------|-------|
| 10FT DIESEL | Light Green #E8F4E8 |
| 14FT DIESEL | Light Blue #E8F0F8 |
| VAN DIESEL (GOODS VAN) | Light Orange #FFF8E8 |
| VAN PETROL (GOODS VAN) | Light Pink #F8E8F0 |

---

## Technical Details

- **Framework**: Flask
- **Port**: 5555 (configurable via PORT environment variable)
- **Data storage**: JSON files in `data/` folder
- **Export files**: Saved to `daily_reports/` folder

---

## File Structure

```
Scraping test/
├── market_analysis_app.py      # Main application
├── market_analysis_generator.py # HTML report generator
├── templates/
│   └── market_analysis.html    # Dashboard template
├── pricelist/
│   └── PRICELIST_TEMPLATE.csv  # Template for upload
├── data/                       # Data storage
├── daily_reports/              # Export files
├── uploads/                    # Uploaded files
├── RUN_MARKET_ANALYSIS.bat     # Quick start
└── MARKET_ANALYSIS_GUIDE.md    # This guide
```

---

## Keyboard Shortcuts

No keyboard shortcuts in this version. All actions via button clicks.

---

## Troubleshooting

### Server won't start
- Check if port 5555 is already in use
- Run: `python market_analysis_app.py` to see error messages

### Upload failed
- Check file format (must be .xlsx, .xls, or .csv)
- Check file size (max 16MB)
- Check column names match the template

### Data not showing
- Refresh the page (F5)
- Check browser console for errors (F12)

---

**Developed by Oneiros Indonesia**
