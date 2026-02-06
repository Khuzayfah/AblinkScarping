@echo off
title SGCarMart Scraper - Installation
color 0E

echo ========================================
echo  SGCarMart Scraper - INSTALLATION
echo ========================================
echo.

REM Check if Python is installed
echo [1/3] Checking Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo.
    echo Silakan install Python dari: https://python.org
    echo Versi minimum: Python 3.9
    echo PENTING: Centang "Add Python to PATH" saat install
    echo.
    pause
    exit /b 1
)
echo [OK] Python terdeteksi!
echo.

REM Install Python dependencies
echo [2/3] Installing Python dependencies...
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal install dependencies!
    echo.
    pause
    exit /b 1
)
echo.
echo [OK] Python dependencies berhasil diinstall!
echo.

REM Install Playwright browser
echo [3/3] Installing Playwright Chromium browser...
echo.
playwright install chromium
if errorlevel 1 (
    echo [ERROR] Gagal install Playwright!
    echo.
    pause
    exit /b 1
)
echo.
echo [OK] Playwright browser berhasil diinstall!
echo.

echo ========================================
echo  INSTALLATION COMPLETE!
echo ========================================
echo.
echo Instalasi selesai! Sekarang Anda bisa:
echo.
echo 1. Double-click "go.bat" untuk run aplikasi
echo 2. Double-click "test.bat" untuk test scraper
echo.
echo ========================================
echo.
pause
