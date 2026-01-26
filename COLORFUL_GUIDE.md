# Colorful Report Guide
## Ablink SGCarmart Scraper
### By Oneiros Indonesia

---

## 🚀 **Quick Start**

### **Generate Report:**
```bash
Double-click: GENERATE_REPORT.bat
```

**Or:**
```bash
python simple_report.py
```

---

## 📊 **What You Get**

### **3 Files Automatically Created:**

**1. CSV File** 📄
- `report_YYYYMMDD_HHMMSS.csv`
- Universal format
- Open in Excel, Google Sheets
- Good for data analysis

**2. Excel File** 📊
- `report_YYYYMMDD_HHMMSS.xlsx`
- Native Excel format
- All formulas preserved
- Ready for pivot tables

**3. HTML File** 🌈
- `colorful_report_YYYYMMDD_HHMMSS.html`
- Opens in browser automatically
- Press `Ctrl+P` → "Save as PDF"
- **COLORFUL design - easy to distinguish!**

---

## 🎨 **Design - COLORFUL!**

### **Category Colors:**
- **10FT DIESEL**: Light Red (#FFE6E6)
- **14FT DIESEL**: Light Blue (#E6F3FF)
- **VAN DIESEL**: Light Green (#E6FFE6)
- **VAN PETROL**: Light Orange (#FFF4E6)

### **Cell Colors:**
- **Header**: Purple gradient
- **Price cells**: Light blue background
- **Units cells**: White background
- **Total Units**: Orange background
- **Previous**: Grey background
- **DIFF Positive**: Green background
- **DIFF Negative**: Red background

**Colorful & easy to read - perfect for quick analysis!**

---

## 📥 **How to Get PDF**

### **From HTML:**
1. HTML opens in browser automatically
2. Press `Ctrl+P`
3. Select "Save as PDF"
4. Enable "Background graphics"
5. Click "Save"
6. Done!

---

## 📁 **File Locations**

**All files saved to:**
```
daily_reports/
├── report_*.csv        ← CSV
├── report_*.xlsx       ← Excel
└── depreciation_report_*.html  ← HTML (for PDF)
```

**Timestamped filenames** - never overwrites!

---

## 🎯 **Usage**

### **Daily Workflow:**
```
1. Double-click: GENERATE_REPORT.bat
2. Wait ~2 seconds
3. Browser opens with report
4. Files saved to daily_reports/
5. Done!
```

### **For PDF:**
```
1. Browser shows report
2. Ctrl+P
3. Save as PDF
4. Done!
```

### **For Analysis:**
```
1. Open report_*.xlsx in Excel
2. Create pivot tables
3. Add your own analysis
4. Done!
```

---

## ✨ **Features**

✅ **Simple & Fast** - No complicated setup  
✅ **Grey Design** - Like your PDF  
✅ **3 Formats** - CSV, Excel, HTML  
✅ **Auto-Open** - Browser opens automatically  
✅ **Print-Ready** - Ctrl+P for PDF  
✅ **Timestamped** - Never overwrites files  

---

## 📋 **Data Structure**

**Table Format:**
```
Vehicle | Category | 2025 | 2024 | ... | TOTAL UNITS | Previous | DIFF
        | Price/Units per year...
```

**Exactly like your PDF upload!**

---

## 💡 **Tips**

### **Tip 1: Quick PDF**
```
Ctrl+P → Save as PDF → Done!
```

### **Tip 2: Excel Analysis**
```
Open .xlsx → Create pivot table → Analyze
```

### **Tip 3: Share Data**
```
Send .csv file → Opens anywhere
```

### **Tip 4: Archive**
```
Files are timestamped - keep all for history
```

---

## 🛠️ **Troubleshooting**

### **Browser doesn't open:**
- Check: `daily_reports/depreciation_report_*.html`
- Double-click HTML file manually

### **No files created:**
- Check: `daily_reports/` folder exists
- Run script again

### **PDF colors missing:**
- In print dialog: Enable "Background graphics"

---

## ✅ **Summary**

**What You Have:**
- ✅ Simple report generator
- ✅ Grey design (like PDF)
- ✅ 3 formats: CSV, Excel, HTML
- ✅ One-click operation
- ✅ No charts, no colors - clean & simple

**How to Use:**
```
Double-click: GENERATE_REPORT.bat
→ Browser opens with report
→ Ctrl+P for PDF
→ Done!
```

**Files Location:**
```
daily_reports/ folder
```

---

*Ablink SGCarmart Scraper*  
*By Oneiros Indonesia*  
*Simple Report Generator v1.0*
