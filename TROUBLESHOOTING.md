# Troubleshooting Bad Gateway & Common Issues

## 🚨 Bad Gateway Error (502)

### Penyebab Umum

1. **Aplikasi belum ready** - Container baru start, app masih loading
2. **Health check gagal** - Endpoint `/api/health` tidak respond
3. **Port tidak match** - Config port tidak sesuai
4. **Aplikasi crash** - Error saat startup
5. **Database issue** - Tidak bisa buat/akses database

### Solusi Step-by-Step

#### 1. Check Logs di Coolify

```
Coolify Dashboard > Your App > Logs
```

**Cari error ini:**
```
✓ GOOD: "Application startup complete"
✓ GOOD: "Uvicorn running on http://0.0.0.0:8000"
✓ GOOD: "Scheduler started"

✗ BAD: "Error"
✗ BAD: "Exception"
✗ BAD: "Failed"
✗ BAD: "Permission denied"
```

#### 2. Verify Health Check

Health check harus return response:

**Check di logs:**
```
INFO:     127.0.0.1:XXXX - "GET /api/health HTTP/1.1" 200 OK
```

**Jika 404 atau 500:**
- Health endpoint tidak ada/error
- Fix: Check main.py line 84-92

#### 3. Check Port Configuration

**Pastikan match:**
```yaml
# docker-compose.yml
ports:
  - "8000:8000"  ← Host:Container must match

# Environment
PORT=8000

# main.py startup
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### 4. Check Container Status

**Di Coolify:**
```
Deployments > Latest > Status
```

**Should be:**
- ✅ Status: Running
- ✅ Health: Healthy
- ✅ Restarts: 0 (or low number)

**If restarting frequently:**
- Container crash loop
- Check logs for error

#### 5. Database Permissions

**Common issue:**
```
Error: unable to open database file
```

**Solution:**
```bash
# In Coolify, check volume permissions
# Volume should be writable

# Or in Dockerfile, ensure directory exists:
RUN mkdir -p /app/data && chmod 777 /app/data
```

### Quick Fixes

#### Fix 1: Wait for Startup (Most Common)

**Waktu startup normal: 30-60 detik**

Playwright install chromium butuh waktu. Tunggu sampai logs show:
```
Application startup complete
```

Refresh browser setelah 1-2 menit.

#### Fix 2: Increase Health Check Timeout

**Di docker-compose.yml:**
```yaml
healthcheck:
  start_period: 60s  # ← Increase dari 40s ke 60s
  timeout: 20s       # ← Increase dari 10s ke 20s
```

#### Fix 3: Add Health Endpoint Logging

**Temporary debug - edit main.py:**

```python
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    print("Health check called!")  # ← Add this
    next_run = scheduler.get_next_run_time()
    result = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "next_scheduled_scrape": next_run.isoformat() if next_run else None
    }
    print(f"Returning: {result}")  # ← Add this
    return result
```

Check logs untuk "Health check called!"

#### Fix 4: Bypass Health Check (Temporary)

**Comment out health check di docker-compose.yml:**
```yaml
# healthcheck:
#   test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
#   ...
```

Redeploy. Jika app works tanpa health check, berarti health check config yang issue.

#### Fix 5: Check Coolify Proxy

**In Coolify:**
1. Go to Settings
2. Check Proxy settings
3. Verify port mapping correct

### Debugging Commands

**Jika ada SSH access ke server:**

```bash
# List containers
docker ps

# Check specific container logs
docker logs [container-name] --tail 100

# Enter container
docker exec -it [container-name] bash

# Inside container, test health endpoint
curl http://localhost:8000/api/health

# Check if app is running
ps aux | grep python

# Check port listening
netstat -tlnp | grep 8000

# Test database
ls -la /app/data
sqlite3 /app/data/scraping.db ".tables"
```

## 🔥 Common Errors & Solutions

### Error: "Module not found"

**Log shows:**
```
ModuleNotFoundError: No module named 'undetected_playwright'
```

**Fix:**
```bash
# Check requirements.txt has all modules
# Rebuild container
```

### Error: "Permission denied: /app/data"

**Fix in Dockerfile:**
```dockerfile
RUN mkdir -p /app/data && chmod 777 /app/data
```

### Error: "Playwright browser not found"

**Fix in Dockerfile:**
```dockerfile
RUN playwright install chromium
RUN playwright install-deps chromium
```

### Error: "Port 8000 already in use"

**Fix:**
1. Change port in docker-compose.yml
2. Change PORT in environment
3. Restart container

### Error: "Database locked"

**Fix:**
1. Stop all connections to database
2. Restart container
3. Check only one instance running

## 📊 Diagnostic Checklist

Use ini untuk debug systematic:

```
□ 1. Logs menunjukkan "Application startup complete"?
□ 2. Health check endpoint accessible? (curl http://localhost:8000/api/health)
□ 3. Container status = Running?
□ 4. Port 8000 mapped correctly?
□ 5. Volume mounted? (ls /app/data works?)
□ 6. Environment variables set?
□ 7. Playwright installed? (playwright --version)
□ 8. Database file exists? (ls /app/data/scraping.db)
□ 9. No errors in logs?
□ 10. Health check timeout sufficient?
```

## 🆘 Still Not Working?

### Step 1: Simplify Health Check

**Replace health check in docker-compose.yml:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 90s  # ← Give more time
```

### Step 2: Check Root Endpoint

**Add simple root endpoint di main.py:**
```python
@app.get("/")
async def root():
    return {"status": "ok", "message": "SGCarMart Scraper is running"}
```

### Step 3: Disable Scheduler Temporarily

**Comment out scheduler di main.py:**
```python
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Handle startup and shutdown events"""
#     ... comment all this
```

**Then:**
```python
app = FastAPI(
    title="Ablink SGCarmart Scraper",
    description="...",
    version="1.0.0",
    # lifespan=lifespan  ← Comment this
)
```

If app works tanpa scheduler, berarti scheduler yang causing issue.

### Step 4: Minimal Dockerfile

**Test dengan minimal Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

If ini works, add dependencies satu-satu.

## 📞 Get Help

If masih stuck, provide ini:

1. **Full logs** dari Coolify (last 100 lines)
2. **Container status** (running/restarting/stopped?)
3. **What you tried** (dari troubleshooting guide)
4. **Health check response** (if accessible)

**Post issue di:**
https://github.com/Khuzayfah/AblinkScarping/issues

**Include:**
- Error message
- Logs
- Coolify version
- What troubleshooting steps tried

---

**Tip:** 90% bad gateway issues = app belum ready. Tunggu 1-2 menit setelah deploy! ⏰
