@echo off
title SGCarMart Scraper - Test Mode
color 0B

echo ========================================
echo  SGCarMart Scraper - TEST MODE
echo ========================================
echo.
echo Mode: Browser TERLIHAT (untuk debugging)
echo.
echo [INFO] Test scraper akan dijalankan...
echo [INFO] Browser Chrome akan terbuka
echo [INFO] Anda bisa lihat proses scraping
echo.
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    pause
    exit /b 1
)

REM Run test scraper in headed mode
python test_safe_scraper.py --headed

echo.
echo ========================================
echo Test selesai!
echo ========================================
echo.
pause
