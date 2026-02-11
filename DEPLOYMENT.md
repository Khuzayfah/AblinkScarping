# Deployment Guide - Coolify

## 🚀 Quick Deploy to Coolify

### Prerequisites
- Coolify instance running
- GitHub repository: https://github.com/Khuzayfah/AblinkScarping

### Deployment Steps

1. **Create New Service in Coolify**
   - Go to your Coolify dashboard
   - Click "New Service" → "Docker Image" or "GitHub Repository"
   - Select: **Application (Docker)**

2. **Configure Repository**
   - Repository URL: `https://github.com/Khuzayfah/AblinkScarping.git`
   - Branch: `main`
   - Build Pack: **Dockerfile**
   - Dockerfile Path: `./Dockerfile`

3. **Environment Variables** (Optional - defaults are set in Dockerfile)
   ```bash
   # Database (optional - default uses SQLite in /app/data)
   DATABASE_URL=sqlite:///./data/scraping.db

   # Scheduling (optional - defaults: 6:00 AM SGT)
   SCRAPING_SCHEDULE_HOUR=6
   SCRAPING_SCHEDULE_MINUTE=0

   # Timezone (optional - default: Asia/Singapore)
   TZ=Asia/Singapore
   ```

4. **Port Configuration**
   - **Container Port**: `3000`
   - **Public Port**: Auto-assigned by Coolify or custom (e.g., `3000`)
   - The app listens on port 3000 internally

5. **Volume Mounts** (Important for Data Persistence!)
   ```
   Host Path: /var/lib/coolify/volumes/ablink-scraper/data
   Container Path: /app/data
   ```
   This ensures database persists across container restarts.

6. **Health Check** (Already configured in Dockerfile)
   - Endpoint: `http://localhost:3000/api/health`
   - Interval: 30s
   - Timeout: 10s
   - Start Period: 90s (allows time for Playwright installation)

7. **Deploy!**
   - Click "Deploy"
   - Wait for build to complete (takes ~3-5 minutes first time due to Playwright)
   - Access your app at the assigned URL

---

## 📊 Features Available After Deployment

### Main Features
1. **Real-time Scraping** - Click "REFRESH DATA" button
2. **Daily Reports** - View sold vehicles by date
3. **Depreciation Tables** - NEW! View depreciation/units by year
   - Active Listings - Depreciation / Units by Year
   - Sold Listings - Depreciation / Units by Year
4. **Auto-scheduling** - Set daily auto-scrape time
5. **Export** - Download reports as CSV, Excel, or PDF

### API Endpoints
- `GET /api/health` - Health check
- `GET /api/status` - Scraper status
- `POST /api/scrape` - Trigger manual scrape
- `GET /api/daily-report?date=YYYY-MM-DD` - Daily sold report
- `GET /api/depreciation-by-year?date=YYYY-MM-DD&source=active` - NEW! Depreciation table
- `GET /api/vehicle-categories` - NEW! Vehicle categories config
- `GET /api/listings?date=YYYY-MM-DD` - Active listings
- `GET /api/sgcarmart-sold` - All-time sold from SGCarMart

---

## 🔧 Troubleshooting

### Container won't start
- Check logs in Coolify: Look for Playwright installation errors
- Ensure volume is mounted correctly for database persistence
- Verify port 3000 is not already in use

### Scraping fails with Cloudflare errors
- The app uses `curl_cffi` with Chrome impersonation to bypass Cloudflare
- If still blocked, SGCarMart may have updated their protection
- Check scraper logs: `docker logs <container-name>`

### Database resets after restart
- **CRITICAL**: Ensure volume is mounted to `/app/data`
- Without volume mount, database is lost on container restart
- Check Coolify volume configuration

### Scheduler not running
- Check timezone is set correctly: `TZ=Asia/Singapore`
- View next scheduled run: Visit `/api/status` endpoint
- Verify scheduler logs in container

---

## 📝 Database Location

- **Development**: `./sgcarmart_data.db` (local)
- **Production (Docker)**: `/app/data/scraping.db` (inside container)
- **Persistent Storage**: Mount volume to `/app/data` for data persistence

---

## 🔄 Update Deployment

When new changes are pushed to GitHub:

1. Coolify **Auto-deploy** (if enabled):
   - Coolify will automatically pull and rebuild

2. **Manual deploy**:
   - Go to your service in Coolify
   - Click "Redeploy"
   - Coolify will pull latest changes and rebuild

---

## 📦 Resource Requirements

- **RAM**: Minimum 1GB (2GB recommended for Playwright)
- **CPU**: 1 core minimum (2 cores recommended)
- **Storage**: 2GB minimum (for database + Docker layers)
- **Network**: Outbound HTTPS access to sgcarmart.com required

---

## 🌐 Default Access

After deployment, access the app at:
- **Coolify URL**: `https://your-app.coolify.domain`
- **Direct IP**: `http://your-server-ip:3000` (if exposed)

Default interface shows:
- Scraping controls
- Daily sold reports with calendar navigation
- **NEW**: Depreciation/Units tables by year
- Active listings data (expandable)
- SGCarMart sold listings (expandable)
- How It Works guide

---

## 🛡️ Security Notes

- No authentication required (internal tool)
- Consider adding basic auth if exposing publicly
- Database is SQLite (local file) - backup regularly
- No sensitive data stored in environment variables

---

## 📞 Support

- Repository: https://github.com/Khuzayfah/AblinkScarping
- Issues: Open GitHub issue for bugs/features
- Built with: FastAPI + Playwright + curl_cffi + SQLite

---

**Last Updated**: 2026-02-11
**Version**: 1.1.0 (Added Depreciation/Units tables)
