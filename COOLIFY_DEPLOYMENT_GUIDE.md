# 🚀 Panduan Deploy ke Coolify

## 📋 Prerequisites

1. **Coolify Server** sudah setup dan running
2. **GitHub Repository** sudah di-push: `https://github.com/Khuzayfah/AblinkScarping.git`
3. **Domain** (optional) untuk akses aplikasi

---

## 🔧 Step-by-Step Deployment

### **STEP 1: Login ke Coolify Dashboard**

1. Buka browser dan akses Coolify dashboard Anda
2. Login dengan credentials Anda

---

### **STEP 2: Buat Resource Baru**

1. Klik **"New Resource"** atau **"+"** button
2. Pilih **"Application"** atau **"New Application"**

---

### **STEP 3: Connect GitHub Repository**

1. Pilih **"GitHub"** sebagai source
2. Jika belum connect GitHub:
   - Klik **"Connect GitHub"** atau **"Authorize GitHub"**
   - Login ke GitHub dan authorize Coolify
   - Pilih repository yang diizinkan
3. Pilih repository: **`Khuzayfah/AblinkScarping`**
4. Pilih branch: **`main`**

---

### **STEP 4: Configure Application**

#### **4.1 Basic Settings**

- **Name**: `ablink-scraper` (atau nama lain yang Anda inginkan)
- **Description**: `Ablink SGCarmart Market Analysis Dashboard`

#### **4.2 Build Settings**

**Build Pack**: `Python` atau `Dockerfile` (auto-detect)

**Build Command** (jika perlu):
```bash
pip install -r requirements.txt
```

**Start Command** (jika perlu):
```bash
python market_analysis_app.py
```

**Note**: Coolify biasanya auto-detect dari `Procfile`, jadi mungkin tidak perlu diisi manual.

#### **4.3 Port Configuration**

- **Port**: `5555` (atau biarkan auto-detect)
- Coolify akan otomatis set `PORT` environment variable

#### **4.4 Environment Variables** (Optional)

Tambahkan jika perlu:
```
PORT=5555
PYTHONUNBUFFERED=1
```

---

### **STEP 5: Persistent Storage**

**PENTING**: Tambahkan persistent storage untuk data history!

1. Klik **"Storage"** atau **"Volumes"**
2. Tambah volume:
   - **Path di container**: `/app/data`
   - **Path di host**: (auto-generate atau pilih folder)
   - **Mount point**: `/app/data`

**Folder yang perlu persistent:**
- `data/history/` - History data scraping
- `uploads/` - Uploaded pricelist files

---

### **STEP 6: Resource Requirements**

**Minimum Recommended:**
- **CPU**: 1 core (0.5 core minimum)
- **RAM**: 512 MB (256 MB minimum)
- **Storage**: 1 GB

**Recommended:**
- **CPU**: 1-2 cores
- **RAM**: 1 GB
- **Storage**: 2 GB

---

### **STEP 7: Health Check** (Optional)

- **Path**: `/api/status`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds

---

### **STEP 8: Deploy**

1. Klik **"Deploy"** atau **"Save & Deploy"**
2. Tunggu proses build dan deploy selesai
3. Monitor logs untuk melihat progress

---

## 🔍 Troubleshooting

### **Problem: Build Failed**

**Solution:**
- Check logs di Coolify dashboard
- Pastikan `requirements.txt` lengkap
- Pastikan Python version compatible (Python 3.9+)

### **Problem: App Tidak Bisa Start**

**Solution:**
- Check logs untuk error message
- Pastikan PORT environment variable sudah set
- Pastikan semua dependencies terinstall

### **Problem: Chrome/WebDriver Error**

**Solution:**
- Ini NORMAL! App akan otomatis fallback ke sample data
- Sample data sudah include data real dari SGCarmart
- App tetap berfungsi dengan baik tanpa Chrome

### **Problem: Data Tidak Tersimpan**

**Solution:**
- Pastikan persistent storage sudah di-setup
- Check folder permissions
- Pastikan path `/app/data` sudah di-mount

---

## 📝 Post-Deployment Checklist

- [ ] App berhasil deploy dan running
- [ ] Bisa akses dashboard di URL yang diberikan Coolify
- [ ] Button "REFRESH DATA" berfungsi
- [ ] Upload pricelist berfungsi
- [ ] Export (CSV, Excel, PDF) berfungsi
- [ ] History navigation berfungsi
- [ ] Data tersimpan di persistent storage

---

## 🌐 Access Application

Setelah deploy berhasil, Coolify akan memberikan URL:
- **Format**: `https://your-app-name.your-coolify-domain.com`
- Atau: `http://your-server-ip:port`

---

## 🔄 Update Application

Untuk update aplikasi:

1. Push perubahan ke GitHub (`git push origin main`)
2. Di Coolify dashboard, klik **"Redeploy"** atau **"Deploy"**
3. Coolify akan otomatis pull latest code dan rebuild

---

## 📞 Support

Jika ada masalah:
1. Check logs di Coolify dashboard
2. Check GitHub repository untuk latest updates
3. Pastikan semua requirements terpenuhi

---

## ✅ Success Indicators

Jika semua berjalan dengan baik, Anda akan melihat:
- ✅ Dashboard loading dengan data
- ✅ Status "Ready" di scraping panel
- ✅ Tabel depreciation dan units sold terisi
- ✅ History navigation berfungsi
- ✅ Export buttons berfungsi

---

**Selamat! Aplikasi Anda sudah ter-deploy di Coolify! 🎉**
