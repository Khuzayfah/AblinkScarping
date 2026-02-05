# Coolify Quick Start Guide

## 🚀 Deploy in 5 Minutes

### Step 1: Login to Coolify
```
Access your Coolify dashboard
URL: https://your-coolify-instance.com
```

### Step 2: Create New Resource

1. Click **"+ New"** or **"New Resource"**
2. Select **"Public Repository"**
3. Choose **"GitHub"**

### Step 3: Configure Repository

```
Repository URL: https://github.com/Khuzayfah/AblinkScarping
Branch: main
Build Pack: Docker Compose
```

### Step 4: Configure Environment

Add these environment variables in Coolify:

```bash
DATABASE_URL=sqlite:///./data/scraping.db
SCRAPE_SCHEDULE_TIME=08:00
TZ=Asia/Singapore
PORT=8000
```

### Step 5: Configure Storage

**IMPORTANT:** Add persistent volume to save database

```
Source Path: /data
Destination: /app/data
```

### Step 6: Deploy

Click **"Deploy"** button

Wait 3-5 minutes for first build

### Step 7: Access Your App

```
URL: https://your-assigned-domain.coolify.app
or configure custom domain
```

### Step 8: Test

1. Open web interface
2. Click "Refresh Data" to trigger first scrape
3. Wait 2-5 minutes for data to appear
4. Check health: https://your-domain/api/health

## ✅ Done!

Your scraper is now:
- ✅ Running 24/7
- ✅ Scraping daily at 8 AM Singapore time
- ✅ Auto-restarting on failure
- ✅ Health monitored
- ✅ Database persisted

## 🔧 Optional: Custom Domain

1. In Coolify, go to your app
2. Click "Domains"
3. Add your domain: `scraper.yourdomain.com`
4. Enable SSL (Let's Encrypt)
5. Update DNS records as shown by Coolify

## 📊 Monitor

- **Logs:** Coolify Dashboard > Your App > Logs
- **Health:** GET /api/health endpoint
- **Status:** Coolify shows resource usage

## 🆘 Troubleshooting

### Build Failed
- Check Coolify build logs
- Verify all files are in GitHub

### App Not Starting
- Check environment variables
- Verify port 8000 is not used
- Check logs for errors

### Database Lost After Restart
- Verify volume is configured: `/data` → `/app/data`
- Check volume permissions

### Scraper Not Running
- Check TZ environment variable
- Verify SCRAPE_SCHEDULE_TIME format (HH:MM)
- Check logs for scheduler errors

## 📚 Full Documentation

For detailed guide, see: [DEPLOY_COOLIFY.md](DEPLOY_COOLIFY.md)

---

**Need Help?** Open an issue: https://github.com/Khuzayfah/AblinkScarping/issues
