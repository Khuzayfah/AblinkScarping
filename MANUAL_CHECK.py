"""
MANUAL INSPECTION - User lihat sendiri browser
Untuk debug kenapa scraper tidak dapat data
"""
from playwright.sync_api import sync_playwright
import time

print("="*70)
print("MANUAL INSPECTION MODE")
print("="*70)
print("\nBrowser akan terbuka. Tolong CEK:")
print("1. Apakah ada Cloudflare 'Just a moment...'?")
print("2. Apakah listings muncul?")
print("3. Apakah ada CAPTCHA?")
print("4. Berapa banyak listings yang terlihat?")
print("\n" + "="*70)

input("\nPress Enter untuk mulai...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, channel="chrome")
    page = browser.new_page()

    # Step 1: Homepage
    print("\nStep 1: Loading HOMEPAGE...")
    page.goto("https://www.sgcarmart.com")
    time.sleep(3)

    title1 = page.title()
    print(f"  Title: {title1}")

    input("  --> Apakah homepage terlihat OK? Press Enter to continue...")

    # Step 2: Used cars listing
    print("\nStep 2: Loading USED CARS LISTING...")
    page.goto("https://www.sgcarmart.com/used-cars/listing?veh=1&limit=100")
    time.sleep(8)

    title2 = page.title()
    print(f"  Title: {title2}")

    if "just a moment" in title2.lower():
        print("  ⚠️  CLOUDFLARE DETECTED!")
        input("  --> Tunggu sampai Cloudflare selesai, terus Press Enter...")
        time.sleep(3)
        title2 = page.title()
        print(f"  New title: {title2}")

    # Count elements
    counts = page.evaluate("""
        () => {
            return {
                articles: document.querySelectorAll('article').length,
                info_links: document.querySelectorAll('a[href*="info"]').length,
                cards: document.querySelectorAll('[class*="card"]').length,
                all_links: document.querySelectorAll('a').length,
                body_text: document.body.textContent.substring(0, 200)
            }
        }
    """)

    print(f"\n  📊 Element counts:")
    print(f"     Articles: {counts['articles']}")
    print(f"     Info links: {counts['info_links']}")
    print(f"     Cards: {counts['cards']}")
    print(f"     All links: {counts['all_links']}")
    print(f"\n  📄 Sample text:")
    print(f"     {counts['body_text'][:150]}...")

    if counts['info_links'] == 0:
        print("\n  ❌ NO INFO LINKS FOUND!")
        print("     Possible reasons:")
        print("     - Cloudflare still blocking")
        print("     - Website structure changed")
        print("     - Need Singapore IP")
    else:
        print(f"\n  ✅ Found {counts['info_links']} info links - SHOULD WORK!")

    print("\n" + "="*70)
    print("INSPECT BROWSER WINDOW NOW")
    print("="*70)
    print("\nTolong check di browser:")
    print("1. Apakah ada tulisan 'Just a moment...' (Cloudflare)?")
    print("2. Apakah ada listings kendaraan?")
    print("3. Kalau ada listings, coba klik salah satu - apakah buka?")
    print("4. Apakah ada error message?")
    print("\nBrowser akan tetap terbuka...")
    input("\nPress Enter untuk close browser...")

    browser.close()

print("\n" + "="*70)
print("DONE")
print("="*70)
print("\nApa yang Anda lihat di browser?")
print("Tolong kasih tahu hasilnya!")
