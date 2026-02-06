# VPN Setup Guide (NOT RECOMMENDED!)

## ⚠️ WARNING: High Risk Approach

**Using VPN in container is:**
- ❌ Complex to setup
- ❌ Prone to failures
- ❌ Slow performance
- ❌ Hard to debug
- ❌ Maintenance nightmare

**Consider alternatives:**
- ✅ HTTP/SOCKS Proxy (simple & reliable)
- ✅ Rotating Proxy Service (professional)
- ✅ Deploy in different region (clean)

---

## 🔧 If You Still Want VPN (Against Advice)

### Prerequisites

1. **VPN Provider that supports OpenVPN**
   - NordVPN
   - ExpressVPN
   - ProtonVPN
   - Your own VPN server

2. **OpenVPN config file (.ovpn)**
   - Download from your VPN provider
   - Includes: server, certificates, keys

3. **VPN credentials**
   - Username & password (if required)

---

## 📝 Setup Steps

### Step 1: Get VPN Config

Download `.ovpn` file from your VPN provider:

```bash
# Example for NordVPN
# Go to: https://nordvpn.com/ovpn/
# Download: Singapore.ovpn (or desired location)

# Save as: vpn-config.ovpn
```

### Step 2: Modify Dockerfile

```bash
# Use Dockerfile.vpn instead of Dockerfile
mv Dockerfile Dockerfile.original
mv Dockerfile.vpn Dockerfile
```

### Step 3: Add VPN Config to Repo

```bash
# Create vpn directory
mkdir vpn

# Copy your VPN config
cp /path/to/your/config.ovpn vpn/config.ovpn

# Add credentials if needed
echo "your-username" > vpn/auth.txt
echo "your-password" >> vpn/auth.txt
```

**IMPORTANT: Add to .gitignore!**
```bash
echo "vpn/*.ovpn" >> .gitignore
echo "vpn/auth.txt" >> .gitignore
```

### Step 4: Update docker-compose.yml

```yaml
services:
  sgcarmart-scraper:
    build: .
    container_name: sgcarmart-scraper
    restart: unless-stopped
    cap_add:           # ← Add these
      - NET_ADMIN      # ← For VPN
    devices:           # ← Add these
      - /dev/net/tun   # ← For VPN tunnel
    ports:
      - "3000:3000"
    volumes:
      - ./data:/app/data
      - ./vpn:/app/vpn:ro  # ← Add VPN config volume
    environment:
      - DATABASE_URL=sqlite:///./data/scraping.db
      - TZ=Asia/Singapore
      - PORT=3000
```

### Step 5: Deploy

```bash
git add Dockerfile start-with-vpn.sh docker-compose.yml
git commit -m "Add VPN support (experimental)"
git push origin main
```

In Coolify:
1. Redeploy
2. Wait 5-10 minutes (VPN takes longer)
3. Check logs for "VPN connected"

---

## 🐛 Common Errors & Fixes

### Error: "Permission denied: /dev/net/tun"

**Fix:**
```yaml
# In docker-compose.yml
cap_add:
  - NET_ADMIN
devices:
  - /dev/net/tun
```

### Error: "VPN config not found"

**Fix:**
```bash
# Ensure vpn/config.ovpn exists
ls -la vpn/

# Check volume mount in docker-compose
volumes:
  - ./vpn:/app/vpn:ro
```

### Error: "VPN not connecting"

**Check logs:**
```bash
docker logs [container-name]
```

**Common issues:**
- Invalid credentials
- Wrong server
- Firewall blocking
- Missing certificates

### Error: "Container keeps restarting"

VPN failed to start, app won't start.

**Temporary fix:**
```bash
# Disable VPN, use fallback
# Edit start-with-vpn.sh to skip VPN
```

---

## 🔍 Verify VPN is Working

### Check 1: Container logs
```bash
docker logs [container-name] | grep VPN
```

Should show:
```
VPN connected successfully!
tun0: <POINTOPOINT,UP,RUNNING>
```

### Check 2: IP Address
```bash
# From inside container
docker exec [container-name] curl ifconfig.me
```

Should show VPN IP, not server IP.

### Check 3: Scraping works
```
Access app → Click "REFRESH DATA"
Check if scraping completes
```

---

## 📊 Performance Comparison

| Method | Speed | Reliability | Complexity |
|--------|-------|-------------|------------|
| No VPN | ⚡⚡⚡ | ⭐⭐⭐ | ✅ Simple |
| Proxy  | ⚡⚡ | ⭐⭐⭐ | ✅ Simple |
| VPN    | ⚡ | ⭐ | ❌ Complex |

---

## 💡 Better Alternative: HTTP Proxy

Instead of VPN, use this simple proxy setup:

```python
# js_scraper.py
context = browser.new_context(
    proxy={
        "server": "http://proxy-server:port",
        "username": "your-username",
        "password": "your-password"
    }
)
```

**Advantages:**
- ✅ 5 lines of code (vs VPN 100+ lines)
- ✅ No container network magic
- ✅ Easy to change proxy
- ✅ Works reliably
- ✅ No special permissions needed

---

## 🎯 Recommendation

**DON'T use VPN approach unless absolutely necessary!**

**Use instead:**
1. **HTTP/SOCKS Proxy** - Simple & reliable
2. **Rotating Proxy Service** - Professional solution
3. **Deploy in target region** - Clean architecture

**Only use VPN if:**
- You already have VPN infrastructure
- You're familiar with OpenVPN
- You accept the risk of failures
- You have time for debugging

---

**Still want to proceed with VPN? Reply "YES VPN" and provide:**
1. VPN provider name
2. Are you using OpenVPN config?
3. Do you need help with specific setup?

**Want proxy solution instead? Reply "PROXY" and I'll help setup!**
