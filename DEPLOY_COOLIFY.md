# Deploy to Coolify - Step by Step Guide

## Prerequisites

1. Coolify instance running (self-hosted or cloud)
2. GitHub repository access: https://github.com/Khuzayfah/AblinkScarping
3. Domain (optional, but recommended)

## Deployment Steps

### Method 1: Deploy via GitHub (Recommended)

1. **Login to Coolify Dashboard**
   - Access your Coolify instance
   - Login with your credentials

2. **Create New Resource**
   - Click "New Resource"
   - Select "Public Repository"
   - Choose "Docker Compose"

3. **Configure Repository**
   ```
   Repository URL: https://github.com/Khuzayfah/AblinkScarping
   Branch: main
   Docker Compose Location: docker-compose.yml
   ```

4. **Configure Environment Variables**

   Go to Environment tab and add:
   ```
   DATABASE_URL=sqlite:///./data/scraping.db
   SCRAPE_SCHEDULE_TIME=08:00
   TZ=Asia/Singapore
   PORT=8000
   ```

5. **Configure Volumes**

   Add persistent volume:
   ```
   Source: /data
   Destination: /app/data
   ```

   This ensures your database persists across deployments.

6. **Configure Port**
   ```
   Port: 8000
   Public: Yes (if you want external access)
   ```

7. **Configure Domain (Optional)**
   ```
   Domain: scraper.yourdomain.com
   SSL: Enable (Let's Encrypt)
   ```

8. **Deploy**
   - Click "Deploy"
   - Wait for build to complete (3-5 minutes first time)
   - Check logs for any errors

### Method 2: Deploy via Git Push

1. **Connect Your Repository**
   - In Coolify, add your GitHub repository
   - Set up webhook for auto-deploy on push

2. **Push Changes**
   ```bash
   git add .
   git commit -m "Deploy to Coolify"
   git push origin main
   ```

3. **Auto Deploy**
   - Coolify will automatically detect changes
   - Build and deploy new version

## Configuration Details

### Docker Compose Structure

The app uses Docker Compose with these services:

```yaml
sgcarmart-scraper:
  - Port: 8000
  - Volume: ./data (for database persistence)
  - Health Check: /api/health endpoint
  - Auto-restart: unless-stopped
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite:///./data/scraping.db | Database connection string |
| SCRAPE_SCHEDULE_TIME | 08:00 | Daily scrape time (HH:MM) |
| TZ | Asia/Singapore | Timezone |
| PORT | 8000 | Application port |

### Health Check

Coolify monitors app health via:
```
Endpoint: GET /api/health
Interval: 30s
Timeout: 10s
Retries: 3
```

Response example:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-05T16:30:00",
  "next_scheduled_scrape": "2026-02-06T08:00:00"
}
```

## Volume Persistence

**Critical:** Database must persist across deployments.

Coolify will mount `./data` directory to container:
```
Host: /var/lib/coolify/applications/[app-id]/data
Container: /app/data
```

Database file location:
```
/app/data/scraping.db
```

## Post-Deployment

### 1. Verify Deployment

Check these endpoints:

```bash
# Health check
curl https://your-domain.com/api/health

# Web interface
open https://your-domain.com
```

### 2. Initial Scrape

Trigger first scrape manually:

1. Open web interface
2. Click "Refresh Data" button
3. Wait for scrape to complete (2-5 minutes)

Or via API:
```bash
curl -X POST https://your-domain.com/api/scrape
```

### 3. Verify Schedule

Check logs to confirm scheduler is running:
```
Scheduler started, next run at: 2026-02-06 08:00:00
```

### 4. Monitor Logs

In Coolify:
- Go to your application
- Click "Logs" tab
- Monitor for errors

## Troubleshooting

### Problem: Build Fails

**Solution:**
1. Check Dockerfile syntax
2. Verify all files are committed to GitHub
3. Check Coolify build logs for specific errors

### Problem: Health Check Fails

**Solution:**
1. Check if port 8000 is exposed
2. Verify app is running: `docker ps`
3. Check app logs: `docker logs [container-id]`
4. Test health endpoint inside container:
   ```bash
   docker exec [container-id] curl http://localhost:8000/api/health
   ```

### Problem: Database Not Persisting

**Solution:**
1. Verify volume is mounted correctly in Coolify
2. Check permissions on host volume directory
3. Ensure DATABASE_URL points to `/app/data/scraping.db`

### Problem: Scraper Not Running

**Solution:**
1. Check scheduler logs
2. Verify timezone is correct (TZ environment variable)
3. Check SCRAPE_SCHEDULE_TIME format (HH:MM)
4. Manually trigger scrape to test

### Problem: Playwright/Chrome Errors

**Solution:**
1. Ensure Dockerfile installs all Chrome dependencies
2. Check if running in headless mode
3. Verify system has enough memory (min 1GB recommended)

## Updating the App

### Auto-Update (Recommended)

With webhook configured:
```bash
git add .
git commit -m "Update: [description]"
git push origin main
```

Coolify auto-detects and deploys.

### Manual Update

In Coolify:
1. Go to your application
2. Click "Redeploy"
3. Select "Force rebuild" if needed

## Backup

### Database Backup

Automated backup (recommended):

1. In Coolify, enable "Backup" for volume
2. Schedule: Daily at 00:00
3. Retention: 7 days

Manual backup:
```bash
# From host
cp /var/lib/coolify/applications/[app-id]/data/scraping.db ./backup/

# Download via Coolify UI
# Applications > [Your App] > Volumes > Download
```

## Performance

### Recommended Resources

- **CPU**: 1 core (2 cores for faster scraping)
- **RAM**: 1GB minimum, 2GB recommended
- **Storage**: 1GB (database grows ~10MB/month)
- **Network**: Stable internet required

### Scaling

For high-traffic deployments:
1. Increase CPU/RAM in Coolify
2. Consider external database (PostgreSQL)
3. Use Redis for caching (future enhancement)

## Security

### Best Practices

1. **Enable SSL/HTTPS**
   - Use Coolify's built-in Let's Encrypt
   - Force HTTPS redirect

2. **Environment Variables**
   - Never commit `.env` to git
   - Use Coolify's environment management

3. **Network**
   - Use Coolify's private network for inter-container communication
   - Limit public access to port 8000 only

4. **Updates**
   - Keep dependencies updated
   - Monitor security advisories

## Monitoring

### Coolify Built-in

- Resource usage (CPU, RAM, Disk)
- Deployment history
- Logs (real-time and historical)
- Health check status

### Custom Monitoring

Add endpoints for monitoring:
- `/api/health` - App health
- `/api/latest-data` - Last scrape info
- Logs - Error tracking

## Support

### Resources

- Coolify Docs: https://coolify.io/docs
- Repository: https://github.com/Khuzayfah/AblinkScarping
- Issues: https://github.com/Khuzayfah/AblinkScarping/issues

### Common Commands

```bash
# View logs
docker logs -f [container-name]

# Enter container
docker exec -it [container-name] bash

# Check database
docker exec [container-name] ls -la /app/data

# Manual scrape
docker exec [container-name] python js_scraper.py

# Restart container
docker restart [container-name]
```

## Success Checklist

After deployment, verify:

- [ ] Health check returns "healthy"
- [ ] Web interface loads
- [ ] Can trigger manual scrape
- [ ] Data appears in dashboard
- [ ] Scheduler shows next run time
- [ ] Database persists after restart
- [ ] SSL certificate works (if configured)
- [ ] Logs show no errors

## Next Steps

1. Configure custom domain
2. Set up monitoring alerts
3. Configure backup schedule
4. Test scraping schedule
5. Monitor first few scrapes
6. Optimize resources based on usage

---

**Deployment Complete! Your SGCarMart scraper is now running on Coolify.** 🚀
