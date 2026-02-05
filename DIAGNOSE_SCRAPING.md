# 🔍 Diagnose Scraping Issue

## Situasi Sekarang

✅ **Yang Sudah Jalan:**
- Container deploy berhasil
- Web interface bisa diakses
- Health check OK
- Button "REFRESH DATA" bisa diklik

❌ **Yang Belum Jalan:**
- Scraping tidak menghasilkan data
- Semua kolom menampilkan "–"
- Daily report kosong

---

## 🚀 Quick Test (Pilih Salah Satu)

### Opsi 1: Test via Web (PALING MUDAH)

1. **Klik "REFRESH DATA"** di web interface
2. **Tunggu 2-3 menit**
3. **Buka Coolify → Logs**
4. **Screenshot logs** dan kirim ke saya

**Yang saya cari di logs:**

```
✓ GOOD (scraping working):
[1/4] Launching undetected browser...
OK Applying stealth mode...
OK Homepage: SGCarMart - Singapore's No.1 Car Portal
[3/4] Searching for commercial vehicles...
Searching: Toyota Hiace
Found 15 info links
Extracted 12 items
[SUCCESS] Total target vehicles found: 45

✗ BAD (error):
Error launching browser
playwright._impl._errors.Error
Permission denied
Chromium executable not found
TimeoutError
Connection refused
```

---

### Opsi 2: Run Quick Test Script

**Jika bisa SSH ke server:**

```bash
# 1. Masuk ke container
docker exec -it [container-name] bash

# 2. Run quick test
python quick_test.py

# 3. Screenshot output dan kirim
```

Script ini akan test:
- ✓ Imports OK?
- ✓ Network connectivity?
- ✓ Chromium launch?
- ✓ Page load?
- ✓ Stealth mode?
- ✓ Extract data?

---

## 🔧 Possible Root Causes

### 1. Chromium Launch Failure

**Symptoms:**
```
Error launching browser
Executable doesn't exist at /root/.cache/ms-playwright/chromium
```

**Fix:**
```dockerfile
# Already added to Dockerfile, redeploy:
RUN playwright install chromium
RUN playwright install-deps chromium
```

**Action:** Redeploy di Coolify

---

### 2. Network/Firewall Block

**Symptoms:**
```
TimeoutError
Connection refused
Network error
```

**Test dari dalam container:**
```bash
curl -I https://www.sgcarmart.com
# Should return: HTTP/2 200
```

**Possible causes:**
- Server firewall blocking outgoing HTTPS
- SGCarmart blocking server IP
- DNS issue

**Fix (if IP blocked):**
- Need proxy/VPN (which we postponed)
- OR deploy to different server/region

---

### 3. SGCarmart Blocking/Detection

**Symptoms:**
```
Found 0 info links
Page loaded but no data extracted
Cloudflare challenge page
```

**Fix:**
Already using `undetected-playwright` with stealth mode, should bypass most blocks.

If still blocked:
- Add more realistic browser args
- Add random delays
- Rotate user agents

---

### 4. Page Structure Changed

**Symptoms:**
```
Found 0 info links
Extracted 0 items
```

**Test:**
Visit https://www.sgcarmart.com/search?q=Toyota+Hiace manually - does it show listings?

**Fix:**
- Update selectors in `js_scraper.py`
- Update `EXTRACT_JS` JavaScript

---

### 5. Database Write Permission

**Symptoms:**
```
Scrape completes but data not saved
Permission denied writing to /app/data
```

**Fix:**
Already set `chmod 777 /app/data` in Dockerfile

**Verify:**
```bash
docker exec [container] ls -la /app/data
# Should show: drwxrwxrwx
```

---

## 📋 What I Need From You

**Pilih salah satu:**

### A) Screenshot Coolify Logs ⭐ RECOMMENDED
1. Klik "REFRESH DATA" di web
2. Buka Coolify → Service → Logs
3. Screenshot dari awal sampai selesai (atau copy text)
4. Kirim ke saya

### B) Run Quick Test
1. SSH ke server
2. Run: `docker exec -it [container] python quick_test.py`
3. Screenshot output
4. Kirim ke saya

### C) Manual Debug Commands
```bash
# Enter container
docker exec -it [container] bash

# Test 1: Chromium exists?
which chromium-browser
playwright --version

# Test 2: Network OK?
curl -I https://www.sgcarmart.com

# Test 3: Run mini scrape
python -c "from js_scraper import SGCarMartJSScraper; s = SGCarMartJSScraper(); s.scrape_vehicle_listings()"
```

---

## ⚡ Quick Fixes to Try

### Fix 1: Redeploy (if not done yet)

Latest Dockerfile already has all fixes. Redeploy di Coolify:
```bash
git pull origin main  # Pull latest changes
# Then redeploy in Coolify
```

### Fix 2: Increase Timeouts

If getting timeout errors, increase in `js_scraper.py`:
```python
# Line 218, 247, 302
timeout=30000  # Change to 60000 (60 seconds)
```

### Fix 3: Check Database

```bash
docker exec [container] sqlite3 /app/data/scraping.db "SELECT COUNT(*) FROM vehicle_listings;"
# Should return: 0 (if no data scraped yet)
```

---

## 🎯 Expected Behavior When Working

**Logs should show:**
```
[1/4] Launching undetected browser...
  OK Applying stealth mode...

[2/4] Loading homepage (establish session)...
  OK Homepage: SGCarMart - Singapore's No.1 Car Portal

[3/4] Searching for commercial vehicles...

  Searching: Toyota Hiace
    Found 15 info links
    Extracted 12 items

  Searching: Hino Dutro
    Found 8 info links
    Extracted 6 items

  ... (more keywords) ...

[4/4] Processing 45 total items...
  Processing 45 items...
  [OK] Toyota Hiace 2.8A - $98000 - ABS Bus Pte Ltd
  [OK] Hino Dutro 2.8 - $78000 - Mega Bus Pte Ltd
  ... (more items) ...

============================================================
[SUCCESS] Total target vehicles found: 45
============================================================

[OK] Saved 45 listings to database
```

**Web interface should show:**
- Vehicle models
- Prices ($50,000 - $130,000)
- Dealer names (not "–")
- Years (2015-2026)
- Depreciation ($3,000/yr - $12,000/yr)

---

## 🚦 Next Steps

**After you send logs/test results, I will:**

1. ✅ **Identify exact error** from logs
2. ✅ **Provide specific fix** (not generic)
3. ✅ **Update code if needed**
4. ✅ **Test fix works**

**Estimated time to fix:** 10-30 minutes after receiving logs

---

## 💬 Response Template

**Copy this and fill in:**

```
## My Test Results

**Option chosen:** [ ] A (Coolify Logs) / [ ] B (Quick Test) / [ ] C (Manual Debug)

**What I see:**
[Paste logs or screenshot here]

**Error messages (if any):**
[Copy specific error]

**Container name:**
[Your container name in Coolify]

**Can access manually?**
Can I open https://www.sgcarmart.com/search?q=Toyota+Hiace in browser? [ ] Yes / [ ] No
(Test if website blocks me)
```

---

**Kirim hasil test, nanti saya kasih exact fix!** 🚀
