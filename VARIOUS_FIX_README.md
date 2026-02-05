# Fix "Various" Dealer Name Display

## Problem
Di daily report table (Chart 2), ketika ada lebih dari satu dealer untuk model yang sama, sistem menampilkan "Various" alih-alih menampilkan semua dealer names.

**Screenshot masalah:**
```
| Dealer Name |
|-------------|
| Various     |  ← Tidak informatif
| Various     |
| –           |
```

## Root Cause
Di file `main.py` line 233, ada logika yang mengecek jumlah dealer:
```python
dealer = "Various" if len(d["dealers"]) > 1 else (list(d["dealers"])[0] if d["dealers"] else "–")
```

Ketika ada lebih dari 1 dealer, sistem hanya menampilkan "Various" yang tidak informatif.

## Solution
Mengubah logika untuk menampilkan semua dealer names dengan comma separator:

**Before:**
```python
dealer = "Various" if len(d["dealers"]) > 1 else (list(d["dealers"])[0] if d["dealers"] else "–")
```

**After:**
```python
# Join multiple dealers with comma instead of showing "Various"
dealer = ", ".join(sorted(d["dealers"])) if d["dealers"] else "–"
```

### Changes Made:
1. **File:** `main.py` (line 233-234)
2. **Benefit:** Sekarang menampilkan semua dealer names, diurutkan alfabetis, dipisahkan dengan comma

## Results

### Before Fix:
```
HINO DUTRO 2.8    | Various
TOYOTA HIACE 3.0M | Various
NISSAN NV350 2.5M | Various
```

### After Fix:
```
HINO DUTRO 2.8    | ABS Bus Pte Ltd, Lek Auto Pte Ltd, Pioneer Auto, SG Motor Link Pte Ltd
TOYOTA HIACE 3.0M | Ezy-1 Pte Ltd, Titans Auto Pte Ltd, Zenith Automobile
NISSAN NV350 2.5M | Net Link Partners Pte Ltd, Wonderland Car Hub Pte Ltd
```

## Verification

Test dilakukan dengan `test_daily_report_api.py`:

```
Total rows: 25
Rows with 'Various': 0
Rows with multiple dealers (comma-separated): 9

[SUCCESS] No 'Various' found - all dealer names are properly displayed!
```

✅ **0 rows dengan "Various"**
✅ **9 rows dengan multiple dealers (comma-separated)**

## Examples from Real Data

### Toyota Hiace (8 units)
- **Dealers:** ABS Bus Pte Ltd, Ezy-1 Pte Ltd, Titans Auto Pte Ltd, Wonderland Car Hub Pte Ltd, Zenith Automobile
- **Years:** 2017, 2019, 2020, 2021

### Hino Dutro (8 units)
- **Dealers:** ABS Bus Pte Ltd, Lek Auto Pte Ltd, Pioneer Auto, SG Motor Link Pte Ltd
- **Years:** 2024, 2025, 2026

### Nissan NV350 (8 units)
- **Dealers:** ABS Bus Pte Ltd, Net Link Partners Pte Ltd, SG Motor Link Pte Ltd, Wonderland Car Hub Pte Ltd
- **Years:** 2016, 2020

## Notes

- Dealer names diurutkan alfabetis untuk konsistensi
- Spacing tetap rapi dengan comma separator
- Jika hanya 1 dealer, tidak ada comma (ditampilkan as-is)
- Jika tidak ada dealer, tetap menampilkan "–"

## Testing

Untuk test perubahan:

```bash
# Test API endpoint
python test_daily_report_api.py

# Check models with multiple dealers
python check_multiple_dealers.py

# Start web server dan lihat daily report
uvicorn main:app --reload
# Buka: http://localhost:8000
```

## Impact

**Sebelumnya:**
- User tidak tahu dealer mana saja yang punya unit tersebut
- Harus manual check satu-satu listing

**Sekarang:**
- Semua dealer names langsung terlihat di daily report
- Lebih informatif dan berguna untuk user
- User bisa langsung contact semua dealer yang relevan

## Conclusion

✅ **Masalah "Various" sudah diperbaiki**
✅ **Semua dealer names sekarang ditampilkan dengan jelas**
✅ **User mendapat informasi lengkap di daily report**
