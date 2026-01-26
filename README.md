# 🚗 Ablink SGCarmart Scraper
## By Oneiros Indonesia

Professional depreciation & units tracker with web dashboard, history, and auto-scheduling.

---

## ✨ **Features**

### 🌐 **Web Dashboard**
- Beautiful interface with soft natural colors
- Easy on the eyes - professional design
- Responsive and fast

### 📅 **History Slider**
- Navigate through previous dates
- Use ◀ ▶ buttons or arrow keys
- See trends over time

### 🔄 **Dual Scraping Mode**
- **Manual**: Click button anytime
- **Auto**: Daily at 9:00 AM

### 📥 **Export Options**
- CSV - Universal format
- Excel - Analysis ready  
- PDF - Print-friendly

### 🎨 **Soft Natural Colors**
- Warm beige, sky blue, mint green, peach
- Easy to read for hours
- Bold text for clarity

---

## 🚀 **Quick Start**

### **1. Launch Dashboard:**
```bash
Double-click: START_DASHBOARD.bat
```

Browser opens to: **http://localhost:5555**

### **2. First Scraping:**
```
Click "Scrape Now (Manual)" button
Wait 2 seconds
Data appears automatically
```

### **3. View History:**
```
Use ◀ ▶ buttons to navigate
Or use keyboard arrow keys
See data from previous dates
```

### **4. Export Data:**
```
Click CSV / Excel / PDF button
File downloads/opens immediately
```

---

## 📊 **Dashboard Features**

### **Top Controls:**
- 🔄 **Scrape Now** - Manual scraping
- 📄 **CSV** - Export as CSV
- 📊 **Excel** - Export as Excel  
- 📕 **PDF** - Export as PDF (opens in new tab)

### **History Slider:**
- ◀ **Previous** - Go to older date
- ▶ **Next** - Go to newer date
- 📅 **Current Date** - Shows selected date
- ⌨️ **Arrow Keys** - Keyboard shortcuts

### **Report View:**
- **Summary** - Date, vehicles, units, categories
- **Full Table** - All data with soft colors
- **Categories** - Color-coded for easy reading

---

## 🎨 **Color Scheme**

### **Natural & Professional:**
```
Categories:
  10FT DIESEL       → Warm beige
  14FT DIESEL       → Soft sky blue
  VAN DIESEL        → Mint green
  VAN PETROL        → Peach

Data Cells:
  Price             → Light blue
  Units             → White
  Total             → Light orange
  DIFF Positive     → Soft green
  DIFF Negative     → Soft red
```

**All colors are soft, natural, and easy on the eyes!**

---

## ⏰ **Auto Scheduling**

### **Daily at 9:00 AM:**
- Scraping runs automatically
- Data saved to history
- No action needed

### **How it works:**
1. Dashboard runs in background
2. Checks time every minute
3. At 9:00 AM → Scrapes automatically
4. Saves to `daily_reports/history/`
5. Available immediately in dashboard

---

## 📁 **File Structure**

```
Scraping test/
├── START_DASHBOARD.bat        ← Launch dashboard
├── GENERATE_REPORT.bat        ← Generate standalone report
├── DASHBOARD_GUIDE.md         ← Complete guide
├── README.md                  ← This file
│
├── dashboard_web.py           ← Dashboard server
├── soft_generator.py          ← HTML generator (soft colors)
├── history_manager.py         ← History management
├── simple_report.py           ← Standalone report generator
│
├── templates/
│   └── dashboard_slider.html ← Dashboard UI
│
└── daily_reports/
    ├── history/               ← History data
    │   ├── index.json         ← History index
    │   ├── 2026-01-26/        ← Date folder
    │   │   ├── data_*.csv     ← CSV data
    │   │   └── data_*.xlsx    ← Excel data
    │   └── ...
    └── report_*.html          ← Standalone reports
```

---

## 🎯 **Usage Examples**

### **Daily Workflow:**

**Morning:**
```
9:00 AM - Auto scraping runs
9:05 AM - Check dashboard for new data
         Navigate history to see changes
```

**Anytime:**
```
Open dashboard
Click "Scrape Now" for latest data
Use ◀ ▶ to compare dates
Export for reports
```

### **Weekly Report:**
```
1. Open dashboard
2. Navigate to Monday's data
3. Click "Export Excel"
4. Open in Excel
5. Create pivot tables
6. Share with team
```

---

## ⌨️ **Keyboard Shortcuts**

```
Left Arrow (←)    Previous date
Right Arrow (→)   Next date
```

**Fast navigation without clicking!**

---

## 📥 **Export Formats**

### **CSV:**
- Universal format
- Open in any spreadsheet
- Good for data transfer
- UTF-8 encoded

### **Excel:**
- Native .xlsx format
- Ready for pivot tables
- Formulas supported
- Professional format

### **PDF:**
- Print-friendly
- Opens in new tab
- Press Ctrl+P to print
- Enable "Background graphics"

---

## 🛠️ **Technical Info**

### **Requirements:**
- Python 3.7+
- Flask
- Pandas
- Schedule
- openpyxl

### **Ports:**
- Dashboard: 5555
- Access: http://localhost:5555

### **Storage:**
- Location: `daily_reports/history/`
- Format: CSV + Excel per date
- Index: JSON file

---

## 💡 **Tips**

1. **Keep dashboard open** - Leave browser tab open for quick access
2. **Use arrow keys** - Faster than clicking buttons
3. **Export daily** - Backup important data
4. **Check history** - Compare trends over time
5. **Bold text** - All important data is bold for easy reading

---

## 🎨 **Design Features**

### **Soft Natural Colors:**
- Reduce eye strain
- Easy to read for hours
- Professional appearance
- Accessible design

### **Bold Typography:**
- Important data stands out
- Clear hierarchy
- Easy to scan
- Professional look

### **Smooth Navigation:**
- Intuitive slider
- Keyboard shortcuts
- Fast loading
- Responsive design

---

## 🔧 **Troubleshooting**

### **Dashboard won't start:**
```
Check if port 5555 is free
Restart: START_DASHBOARD.bat
```

### **No data showing:**
```
Click "Scrape Now" button
Wait for confirmation
Refresh page (F5)
```

### **Export not working:**
```
Select a date first
Check browser popup blocker
Check daily_reports/ folder
```

---

## 📋 **What You Get**

✅ **Web Dashboard** - Modern interface  
✅ **History Slider** - Navigate dates easily  
✅ **Manual Scraping** - Anytime, one click  
✅ **Auto Scraping** - Daily at 9 AM  
✅ **Export Options** - CSV, Excel, PDF  
✅ **Soft Colors** - Easy on eyes  
✅ **Bold Text** - Clear & readable  
✅ **Keyboard Shortcuts** - Fast navigation  

---

## 🎯 **Summary**

**Launch:**
```
Double-click: START_DASHBOARD.bat
```

**Access:**
```
http://localhost:5555
```

**Features:**
- Manual & Auto scraping
- History with slider
- Export CSV/Excel/PDF
- Soft natural colors
- Easy to read

**Perfect for:**
- Daily tracking
- Trend analysis
- Report generation
- Data backup

---

*Ablink SGCarmart Scraper*  
*By Oneiros Indonesia*  
*Professional Depreciation & Units Tracker*  
*Version 2.0*  
*Status: READY! ✓*
