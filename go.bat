@echo off
title SGCarMart Scraper - Starting...
color 0A

echo ========================================
echo  SGCarMart Scraper - Auto Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo Silakan install Python dari https://python.org
    echo.
    pause
    exit /b 1
)

echo [OK] Python terdeteksi
echo.

REM Check if dependencies are installed
echo Checking dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [INSTALLING] Dependencies belum terinstall, installing sekarang...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Gagal install dependencies!
        pause
        exit /b 1
    )
    echo.
    echo [INSTALLING] Installing Playwright browser...
    playwright install chromium
    if errorlevel 1 (
        echo [ERROR] Gagal install Playwright!
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencies berhasil diinstall!
    echo.
) else (
    echo [OK] Dependencies sudah terinstall
    echo.
)

REM Clear Python cache to avoid import errors
if exist __pycache__ (
    echo [CLEANUP] Clearing Python cache...
    rmdir /s /q __pycache__ >nul 2>&1
    echo [OK] Cache cleared
    echo.
)

REM Start the application
echo ========================================
echo  Starting Web Server...
echo ========================================
echo.
echo Server akan berjalan di: http://localhost:8000
echo.
echo Tunggu beberapa detik, browser akan terbuka otomatis...
echo.
echo Tekan CTRL+C untuk stop server
echo ========================================
echo.

REM Wait 3 seconds then open browser
start /b timeout /t 3 /nobreak >nul && start http://localhost:8000

REM Start the server
python main.py

pause
