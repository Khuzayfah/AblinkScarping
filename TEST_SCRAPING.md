# Test Scraping in Coolify

## 🚀 Setelah Redeploy

### 1. Trigger Manual Scrape

**Via Web Interface:**
```
1. Open: http://xoccsg84ogkc40sk4swkgw4w.76.13.22.221.sslip.io
2. Click tombol "Refresh Data" atau "Scrape Now"
3. Tunggu 2-5 menit (scraping butuh waktu)
4. Data akan muncul di dashboard
```

**Via API:**
```bash
curl -X POST http://xoccsg84ogkc40sk4swkgw4w.76.13.22.221.sslip.io/api/scrape
```

### 2. Check Logs di Coolify

Setelah trigger scrape, **monitor logs:**

```
✓ GOOD logs:
[1/4] Launching undetected browser...
OK Applying stealth mode...
OK Homepage: ...
Searching: Toyota Hiace
Found X info links
Extracted X items
[SUCCESS] Total target vehicles found: X

✗ BAD logs (errors):
Error launching browser
Playwright error
Executable doesn't exist
Permission denied
```

### 3. Verify Data

**Check if data scraped:**
```bash
# API endpoint
curl http://xoccsg84ogkc40sk4swkgw4w.76.13.22.221.sslip.io/api/latest-data

# Should return JSON with vehicle data
```

**Web interface should show:**
- Vehicle listings
- Prices
- Dealer names
- Years registered

---

## 🔧 Troubleshooting

### Scraping Fails - Playwright Error

**Error:**
```
playwright._impl._api_types.Error: Executable doesn't exist
```

**Fix:**
Already fixed with latest Dockerfile (added dependencies & chromium install)

### Scraping Fails - Sandbox Error

**Error:**
```
Failed to launch browser: Running as root without --no-sandbox
```

**Fix:**
Already fixed with `--no-sandbox` arg in js_scraper.py

### Scraping Slow or Timeout

**Issue:**
Scraping takes too long (>5 minutes)

**Solution:**
1. Check Coolify resource limits (RAM, CPU)
2. Increase timeout in config.py if needed
3. Check internet connection from container

### No Data After Scrape

**Issue:**
Scrape completes but no data shows

**Check:**
1. Database volume mounted? (Storage: data → /app/data)
2. Check logs for "Saved X listings to database"
3. Database permissions OK? (chmod 777 already set)

---

## 🎯 Expected Results

**After successful scrape:**

```
Dashboard should show:
- 30-60+ vehicle listings
- Toyota Hiace, Hino Dutro, Nissan NV350, etc.
- Prices ranging $20k-$130k
- Various dealer names
- Year registered (2015-2026)
- Depreciation values

Daily Report shows:
- Aligned data (year, depreciation, dealer)
- Comma-separated values for multiple entries
- No "Various" or "–" for existing listings
```

---

## 🐛 Debug Commands

**If scraping fails, SSH to server and run:**

```bash
# Enter container
docker exec -it [container-name] bash

# Test Playwright
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print('OK')"

# Test Chromium
playwright install chromium

# Check Chromium
which chromium
chromium --version

# Test scraper manually
python js_scraper.py

# Check database
ls -la /app/data/
sqlite3 /app/data/scraping.db ".tables"
```

---

## 📊 Performance

**Normal scraping time:**
- First scrape: 3-5 minutes
- Subsequent: 2-3 minutes
- Per search keyword: 20-30 seconds

**Resource usage:**
- RAM: 500MB-1GB during scrape
- CPU: 50-80% during scrape
- Storage: Database grows ~1MB per 100 listings

---

## ✅ Success Checklist

After redeploy and scrape:

- [ ] Container running (not exited)
- [ ] Logs show "Launching undetected browser"
- [ ] No Playwright errors in logs
- [ ] Scrape completes (shows "Total target vehicles found")
- [ ] Dashboard shows vehicle data
- [ ] Data persists after container restart
- [ ] Can trigger scrape again without errors

---

**If all checks pass: SCRAPING IS WORKING!** 🎉
