# Quick Start Guide
## Ablink SGCarmart Scraper by Oneiros Indonesia

---

## 🚀 **3 Ways to Use**

### **1. Web Interface** ⭐ (Recommended)

**Start:**
```bash
Double-click: RUN_WEB_APP.bat
```

**Use:**
1. Browser opens at `http://localhost:5000`
2. Click "🔄 Refresh Data" button
3. Wait ~30 seconds
4. View data, download Excel, or print PDF

---

### **2. Command Line**

```bash
python depreciation_scraper.py
```

Files saved to `daily_reports/` folder

---

### **3. Daily Automation**

**Setup once:**
```bash
Right-click SETUP_AUTO_DAILY.bat
→ Run as Administrator
```

Scrapes automatically every day at 09:00 AM

---

## 📊 **What You Get**

**Every scraping creates 3 files:**
- **Excel** (.xlsx) - Full data spreadsheet
- **CSV** (.csv) - Universal format
- **HTML** (.html) - Beautiful report with colors

**Data includes:**
- Vehicle models (HINO, TOYOTA, NISSAN, etc.)
- Categories (10FT DIESEL, 14FT DIESEL, VAN DIESEL, VAN PETROL)
- Prices by year (2025, 2024, 2023, ..., 2014 & Older)
- Total units, Previous, Difference
- All prices in SGD ($)

---

## ⚙️ **Configuration**

Edit `config.json` to customize:

```json
{
  "scraper_settings": {
    "headless": true,
    "timeout": 30
  },
  "automation": {
    "schedule_time": "09:00"
  }
}
```

---

## 🔌 **n8n Integration**

**Start API:**
```bash
python n8n_webhook_api.py
```

**Endpoint:** `POST http://localhost:5001/api/scrape`

**Headers:**
```
X-API-Key: your-secret-api-key-change-this
```

**Body:**
```json
{
  "headless": true,
  "format": ["excel", "csv", "html"]
}
```

---

## 📁 **File Locations**

- **Output:** `daily_reports/` folder
- **Logs:** `daily_reports/scraping_log.txt`
- **Config:** `config.json`

---

## 🛠️ **Troubleshooting**

**No data found:**
- Check internet connection
- Check logs: `daily_reports/scraping_log.txt`

**Port already in use:**
- Edit port in `web_scraper_app.py` line 233

**ChromeDriver error:**
- Reinstall: `pip install --upgrade webdriver-manager`

---

**That's it! Start with `RUN_WEB_APP.bat`** 🎉

---

*By Oneiros Indonesia for Ablink*
