# Ablink SGCarmart Scraper - Complete Dashboard Guide
## By Oneiros Indonesia

---

## 🚀 **Quick Start**

### **Launch Dashboard:**
```bash
Double-click: START_DASHBOARD.bat
```

Browser will open automatically at: **http://localhost:5555**

---

## ✨ **Features**

### **1. Manual Scraping** 🔄
- Click "Scrape Now" button
- Data scraped immediately
- Saved to history automatically

### **2. Auto Daily Scraping** ⏰
- Runs automatically at **9:00 AM** every day
- No need to do anything
- Check history to see updates

### **3. History Slider** 📅
- Use **◀ ▶** buttons to navigate
- Or use **Arrow Keys** on keyboard
- See data from previous dates
- Smooth navigation

### **4. Export Options** 📥
- **CSV**: Universal format
- **Excel**: Analysis ready
- **PDF**: Print-friendly (opens in new tab)

### **5. Soft Natural Colors** 🎨
- Easy on the eyes
- Professional look
- Clear text (bold & readable)
- Natural color palette

---

## 🎨 **Color Scheme**

### **Natural & Comfortable:**
```
Header:       Soft blue gradient (#8B9DC3 → #6B7FA8)
Background:   Light grey (#fafaf8)

Categories:
  10FT DIESEL:       Warm beige (#F5E6D3)
  14FT DIESEL:       Soft sky blue (#D3E4F5)
  VAN DIESEL:        Mint green (#D8F3DC)
  VAN PETROL:        Peach (#FFE5D9)

Data Cells:
  Price:            Light blue (#F8F9FB)
  Units:            White
  Total:            Light orange (#FFF5E6)
  DIFF Positive:    Soft green (#DFF0D8)
  DIFF Negative:    Soft red (#F8DEDC)
```

**All colors are soft, natural, and easy on the eyes!** ✅

---

## 📊 **Dashboard Layout**

### **Top Section:**
```
┌─────────────────────────────────────┐
│  Ablink SGCarmart Scraper           │
│  by Oneiros Indonesia               │
└─────────────────────────────────────┘

[🔄 Scrape Now]  Auto: Daily at 9:00 AM
                 [📄 CSV] [📊 Excel] [📕 PDF]
```

### **History Slider:**
```
┌─────────────────────────────────────┐
│  📅 History        (X dates available)│
│                                       │
│     [◀]   26 January 2026   [▶]     │
│                                       │
│  Use ◀ ▶ buttons to navigate        │
└─────────────────────────────────────┘
```

### **Report View:**
```
┌─────────────────────────────────────┐
│  Summary:                             │
│  Date: 26 Jan 2026 17:58:12          │
│  Vehicles: 21 | Units: 799           │
│                                       │
│  [Full Data Table]                   │
└─────────────────────────────────────┘
```

---

## 🎯 **How to Use**

### **Daily Workflow:**

**Morning (Automatic):**
```
1. 9:00 AM - Auto scraping runs
2. Data saved to history
3. Check dashboard anytime
```

**Manual Anytime:**
```
1. Open dashboard: http://localhost:5555
2. Click "Scrape Now" button
3. Wait ~2 seconds
4. Data appears automatically
```

**View History:**
```
1. Click ◀ button (or Left Arrow key)
2. See previous day's data
3. Click ▶ button (or Right Arrow key)
4. Navigate back to recent data
```

**Export Data:**
```
1. Navigate to desired date
2. Click CSV / Excel / PDF button
3. File downloads/opens automatically
```

---

## ⌨️ **Keyboard Shortcuts**

```
Left Arrow (←)   : Previous date
Right Arrow (→)  : Next date
```

**Quick navigation without clicking!** ⚡

---

## 📁 **File Structure**

### **Generated Files:**
```
daily_reports/
├── history/
│   ├── index.json              ← History index
│   ├── 2026-01-26/
│   │   ├── data_175812.csv     ← CSV data
│   │   └── data_175812.xlsx    ← Excel data
│   ├── 2026-01-25/
│   │   └── ...
│   └── ...
└── report_*.html               ← HTML reports
```

**Organized by date - never overwrites!** ✅

---

## 🔧 **Technical Details**

### **Scraping Schedule:**
- **Time**: 9:00 AM daily
- **Runs**: Automatically in background
- **Saves**: To history folder

### **History Storage:**
- **Format**: CSV + Excel
- **Index**: JSON file
- **Per date**: Separate folder

### **Web Server:**
- **Port**: 5555
- **Host**: localhost
- **Access**: http://localhost:5555

---

## 💡 **Tips & Tricks**

### **Tip 1: Keep Dashboard Open**
```
Leave browser tab open
Auto-refresh when data changes
Always see latest
```

### **Tip 2: Use Keyboard**
```
Arrow keys for quick navigation
Faster than clicking buttons
```

### **Tip 3: Export Multiple**
```
Navigate to date
Export CSV (for data)
Export PDF (for printing)
Export Excel (for analysis)
```

### **Tip 4: Check Daily**
```
9:05 AM - Check if auto scraping worked
History slider shows new date
Compare with previous days
```

---

## 🛠️ **Troubleshooting**

### **Dashboard won't open:**
```
1. Check if port 5555 is free
2. Close other programs using the port
3. Restart: START_DASHBOARD.bat
```

### **No data showing:**
```
1. Click "Scrape Now" button
2. Wait for confirmation message
3. Data appears automatically
```

### **Export not working:**
```
1. Make sure date is selected
2. Check daily_reports/ folder exists
3. Browser might block popup (allow it)
```

### **History not loading:**
```
1. Check daily_reports/history/ folder
2. Run scraping at least once
3. Refresh page (F5)
```

---

## 📋 **API Endpoints**

For developers/integration:

```
POST   /api/scrape              - Manual scraping
GET    /api/history             - Get all history dates
GET    /api/data/<date>         - Get data for date
GET    /api/export/<date>/<format>  - Export (csv/excel/pdf)
```

---

## ⏰ **Auto Scheduling**

### **How it works:**
```
1. Dashboard starts → Scheduler starts
2. Every minute, checks if time is 9:00 AM
3. At 9:00 AM → Runs scraping
4. Saves to history automatically
5. Next day → Repeats
```

### **To change schedule time:**
```python
# Edit dashboard_web.py, line:
schedule.every().day.at("09:00").do(daily_scrape)

# Change "09:00" to your preferred time (24h format)
# Example: "14:30" for 2:30 PM
```

---

## 🎨 **Design Philosophy**

### **Soft Natural Colors:**
- Reduce eye strain
- Professional appearance
- Easy to read for hours
- Accessible for all users

### **Bold Text:**
- Important data stands out
- Easy to scan quickly
- Clear hierarchy
- Professional typography

### **Smooth Navigation:**
- History slider intuitive
- Keyboard shortcuts
- Fast loading
- Responsive design

---

## ✅ **Checklist: Daily Use**

**Morning:**
- [ ] Check if auto scraping ran (9:05 AM)
- [ ] Verify new date in history
- [ ] Review DIFF column for changes

**Anytime:**
- [ ] Manual scrape if needed
- [ ] Export data for reports
- [ ] Compare with previous dates
- [ ] Share exports with team

---

## 📊 **Data Summary**

### **What's Tracked:**
- **Date & Time**: When scraped
- **Vehicles**: All models
- **Categories**: 4 types
- **Price**: Per year (2014-2025)
- **Units**: Per year
- **Total Units**: Sum
- **DIFF**: Change from previous

### **How to Analyze:**
```
1. Use history slider
2. Compare same vehicle across dates
3. Check DIFF column (green = up, red = down)
4. Export to Excel for deeper analysis
5. Create pivot tables / charts
```

---

## 🚀 **Advanced Usage**

### **Run without browser:**
```bash
python dashboard_web.py
# Access from any device on network:
# http://[your-ip]:5555
```

### **Schedule additional times:**
```python
# In dashboard_web.py, add:
schedule.every().day.at("14:00").do(daily_scrape)  # 2 PM
schedule.every().day.at("18:00").do(daily_scrape)  # 6 PM
```

### **Backup history:**
```bash
# Copy entire history folder:
cp -r daily_reports/history backup/
```

---

## 📖 **Summary**

**What You Have:**
- ✅ Web dashboard with history slider
- ✅ Manual scraping button
- ✅ Auto daily scraping (9 AM)
- ✅ History navigation (◀ ▶)
- ✅ Export CSV, Excel, PDF
- ✅ Soft natural colors
- ✅ Bold readable text
- ✅ Keyboard shortcuts

**How to Use:**
```
1. Double-click: START_DASHBOARD.bat
2. Browser opens to dashboard
3. Click "Scrape Now" or wait for 9 AM
4. Use ◀ ▶ to view history
5. Export data as needed
```

**Files Location:**
```
daily_reports/history/  ← All history data
```

---

## 🎯 **Final Tips**

### **Best Practices:**
1. **Keep dashboard running** - Leave it open in browser
2. **Check daily** - Verify auto scraping worked
3. **Export regularly** - Backup to CSV/Excel
4. **Use history** - Compare trends over time
5. **Keyboard shortcuts** - Faster navigation

### **Maintenance:**
- **Weekly**: Check history folder size
- **Monthly**: Backup history folder
- **Quarterly**: Review auto schedule

---

*Ablink SGCarmart Scraper*  
*By Oneiros Indonesia*  
*Complete Dashboard with History & Auto Scraping*  
*Version 2.0*  
*Status: READY TO USE! ✓*

---

## 📞 **Support**

Need help?
- Check this guide
- Review troubleshooting section
- Verify file structure
- Test manual scraping first

---

**Enjoy your new dashboard!** 🎉
