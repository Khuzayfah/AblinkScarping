"""
Test script to verify human-like behavior of the scraper
Checks: delays, randomness, headers, stealth features
"""
import re
import time
from playwright.sync_api import sync_playwright
import random

def test_stealth_features():
    """Test if stealth JavaScript is working"""
    print("=" * 60)
    print("Testing Stealth Features")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-SG",
            timezone_id="Asia/Singapore"
        )
        page = context.new_page()

        # Add stealth script (same as js_scraper.py)
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', description: '', filename: 'internal-nacl-plugin'}
                ]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-SG', 'en', 'id']
            });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        """)

        # Test on bot detection site
        print("\n1. Testing webdriver detection...")
        page.goto("https://bot.sannysoft.com/", wait_until="domcontentloaded")
        time.sleep(3)

        # Check webdriver property
        webdriver_value = page.evaluate("() => navigator.webdriver")
        print(f"   navigator.webdriver: {webdriver_value}")
        print(f"   ✅ PASS" if webdriver_value is None else "   ❌ FAIL")

        # Check chrome object
        has_chrome = page.evaluate("() => typeof window.chrome !== 'undefined'")
        print(f"\n2. Testing chrome object...")
        print(f"   window.chrome exists: {has_chrome}")
        print(f"   ✅ PASS" if has_chrome else "   ❌ FAIL")

        # Check plugins
        plugins_count = page.evaluate("() => navigator.plugins.length")
        print(f"\n3. Testing plugins...")
        print(f"   Plugins count: {plugins_count}")
        print(f"   ✅ PASS" if plugins_count > 0 else "   ❌ FAIL")

        # Check languages
        languages = page.evaluate("() => navigator.languages")
        print(f"\n4. Testing languages...")
        print(f"   Languages: {languages}")
        print(f"   ✅ PASS" if 'en-SG' in languages else "   ❌ FAIL")

        # Check hardware concurrency
        cores = page.evaluate("() => navigator.hardwareConcurrency")
        print(f"\n5. Testing hardware concurrency...")
        print(f"   CPU cores: {cores}")
        print(f"   ✅ PASS" if cores > 0 else "   ❌ FAIL")

        print("\n" + "=" * 60)
        print("Stealth Test Complete")
        print("=" * 60)
        print("Check the browser window - look for RED warnings on bot.sannysoft.com")
        print("GREEN = good, RED = detected as bot")
        input("\nPress Enter to continue to timing test...")

        browser.close()


def test_timing_randomness():
    """Test if delays are random and natural"""
    print("\n" + "=" * 60)
    print("Testing Human-Like Timing")
    print("=" * 60)

    delays = []
    iterations = 10

    print(f"\nGenerating {iterations} random delays (should be between 4.5-8.3s):")
    for i in range(iterations):
        delay = random.uniform(4.5, 8.3)
        delays.append(delay)
        print(f"  Iteration {i+1}: {delay:.2f}s")

    avg_delay = sum(delays) / len(delays)
    min_delay = min(delays)
    max_delay = max(delays)

    print(f"\n📊 Statistics:")
    print(f"   Average: {avg_delay:.2f}s")
    print(f"   Min: {min_delay:.2f}s")
    print(f"   Max: {max_delay:.2f}s")
    print(f"   Range: {max_delay - min_delay:.2f}s")

    # Check if distribution looks random
    print(f"\n🎯 Analysis:")
    if 5.0 < avg_delay < 7.5:
        print(f"   ✅ Average is natural (5-7.5s range)")
    else:
        print(f"   ⚠️  Average might be too predictable")

    if max_delay - min_delay > 2.0:
        print(f"   ✅ Good variance (>{2.0}s spread)")
    else:
        print(f"   ⚠️  Low variance, might look robotic")

    # Check scroll randomness
    print(f"\n📜 Testing scroll steps randomness:")
    scroll_steps = [random.randint(4, 7) for _ in range(10)]
    print(f"   Generated steps: {scroll_steps}")
    print(f"   Unique values: {len(set(scroll_steps))}/4 possible")
    print(f"   ✅ Good randomness" if len(set(scroll_steps)) >= 3 else "   ⚠️  Too predictable")


def test_headers():
    """Test if headers look natural"""
    print("\n" + "=" * 60)
    print("Testing HTTP Headers")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-SG",
            timezone_id="Asia/Singapore",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-SG,en;q=0.9,id;q=0.8",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"'
            }
        )
        page = context.new_page()

        # Test headers on httpbin.org
        print("\n📡 Fetching headers from httpbin.org...")
        page.goto("https://httpbin.org/headers", wait_until="domcontentloaded")
        time.sleep(2)

        headers_text = page.evaluate("() => document.body.textContent")

        # Check critical headers
        checks = {
            "User-Agent contains Chrome/131": "Chrome/131" in headers_text,
            "Accept-Language has en-SG": "en-SG" in headers_text,
            "Sec-Fetch-Dest present": "Sec-Fetch-Dest" in headers_text,
            "sec-ch-ua present": "sec-ch-ua" in headers_text,
            "Accept-Encoding has zstd": "zstd" in headers_text
        }

        print("\n✓ Header Checks:")
        for check, result in checks.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check}")

        browser.close()

        # Summary
        passed = sum(checks.values())
        total = len(checks)
        print(f"\n📊 Score: {passed}/{total} checks passed")

        if passed == total:
            print("   🎉 Perfect! Headers look completely natural")
        elif passed >= total * 0.8:
            print("   ✅ Good! Headers are mostly natural")
        else:
            print("   ⚠️  Headers might need improvement")


def test_mouse_movement():
    """Test mouse movement simulation"""
    print("\n" + "=" * 60)
    print("Testing Mouse Movement Simulation")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Add mouse tracking script
        page.add_init_script("""
            window.mouseEvents = [];
            document.addEventListener('mousemove', (e) => {
                window.mouseEvents.push({x: e.clientX, y: e.clientY, time: Date.now()});
            });
        """)

        page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded")
        time.sleep(2)

        print("\n🖱️  Simulating mouse movements...")

        # Simulate multiple mouse movements
        for i in range(5):
            x = random.randint(100, 1800)
            y = random.randint(100, 1000)
            page.evaluate(f"""
                () => {{
                    const event = new MouseEvent('mousemove', {{
                        clientX: {x},
                        clientY: {y},
                        bubbles: true
                    }});
                    document.dispatchEvent(event);
                }}
            """)
            print(f"   Movement {i+1}: ({x}, {y})")
            time.sleep(random.uniform(0.5, 1.5))

        # Check if events were recorded
        events_count = page.evaluate("() => window.mouseEvents.length")
        print(f"\n📊 Mouse events recorded: {events_count}")

        if events_count > 0:
            print("   ✅ Mouse movement simulation working!")

            # Get event details
            events = page.evaluate("() => window.mouseEvents")
            print(f"\n   Sample events:")
            for i, evt in enumerate(events[:3]):
                print(f"   {i+1}. Position: ({evt['x']}, {evt['y']})")
        else:
            print("   ❌ No mouse events detected")

        input("\nPress Enter to close browser...")
        browser.close()


def test_sgcarmart_scraping_safety():
    """Test actual scraping on SGCarmart with safety monitoring"""
    print("\n" + "=" * 60)
    print("Testing SGCarmart Scraping Safety")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-SG",
            timezone_id="Asia/Singapore",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-SG,en;q=0.9,id;q=0.8",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            }
        )

        page = context.new_page()

        # Add stealth
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
        """)

        print("\n🌐 Loading SGCarmart commercial listings...")
        start_time = time.time()

        # Monitor network requests
        requests = []
        page.on("response", lambda response: requests.append({
            "url": response.url,
            "status": response.status,
            "headers": dict(response.headers)
        }))

        try:
            page.goto("https://www.sgcarmart.com/used-cars/listing?veh=1&limit=100",
                     wait_until="domcontentloaded",
                     timeout=30000)

            # Wait like human
            wait_time = random.uniform(5, 7)
            print(f"   Reading page ({wait_time:.1f}s)...")
            time.sleep(wait_time)

            # Check if page loaded successfully
            title = page.title()
            print(f"\n📄 Page title: {title}")

            # Check for CAPTCHA or blocking
            page_content = page.content().lower()

            if "captcha" in page_content or "robot" in page_content:
                print("   ❌ CAPTCHA detected - might be flagged as bot")
            elif "access denied" in page_content or "403" in page_content:
                print("   ❌ Access denied - IP might be blocked")
            else:
                print("   ✅ Page loaded successfully")

            # Scroll naturally
            print("\n📜 Scrolling naturally...")
            for i in range(3):
                scroll_pos = (i + 1) / 3
                page.evaluate(f"window.scrollTo({{top: document.body.scrollHeight * {scroll_pos}, behavior: 'smooth'}})")
                time.sleep(random.uniform(2, 4))

            # Count listings
            listings_count = page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href*="info"]');
                    return links.length;
                }
            """)

            print(f"\n📊 Found {listings_count} potential listings")

            if listings_count > 10:
                print("   ✅ Good data extraction - not blocked")
            elif listings_count > 0:
                print("   ⚠️  Low listing count - might need adjustment")
            else:
                print("   ❌ No listings found - check if blocked")

            # Check network responses
            print(f"\n🌐 Network analysis:")
            print(f"   Total requests: {len(requests)}")

            # Check for blocked responses
            blocked = [r for r in requests if r['status'] in [403, 429, 503]]
            if blocked:
                print(f"   ❌ {len(blocked)} requests were blocked!")
                for b in blocked[:3]:
                    print(f"      - {b['url'][:60]}... [{b['status']}]")
            else:
                print(f"   ✅ All requests successful")

            elapsed = time.time() - start_time
            print(f"\n⏱️  Total time: {elapsed:.2f}s")

            if 20 < elapsed < 90:
                print("   ✅ Timing looks natural (20-90s range)")
            elif elapsed < 20:
                print("   ⚠️  Might be too fast for human behavior")
            else:
                print("   ⚠️  Took longer than expected")

            print("\n" + "=" * 60)
            print("Safety Test Complete")
            print("=" * 60)
            print("\n👁️  Check the browser window:")
            print("   - Do you see vehicle listings?")
            print("   - Is there a CAPTCHA?")
            print("   - Does page look normal?")
            input("\nPress Enter to close...")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   This might indicate blocking or network issues")

        finally:
            browser.close()


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🔍 SGCarmart Scraper - Safety & Human Behavior Tests")
    print("=" * 60)

    tests = {
        "1": ("Stealth Features (webdriver, plugins, etc.)", test_stealth_features),
        "2": ("Timing & Randomness", test_timing_randomness),
        "3": ("HTTP Headers", test_headers),
        "4": ("Mouse Movement Simulation", test_mouse_movement),
        "5": ("SGCarmart Scraping Safety (LIVE TEST)", test_sgcarmart_scraping_safety),
        "6": ("Run All Tests", None)
    }

    print("\nAvailable tests:")
    for key, (name, _) in tests.items():
        print(f"   {key}. {name}")

    choice = input("\nSelect test (1-6): ").strip()

    if choice == "6":
        # Run all tests
        for key in ["1", "2", "3", "4", "5"]:
            tests[key][1]()
            if key != "5":
                input("\nPress Enter to continue to next test...")
    elif choice in tests and tests[choice][1]:
        tests[choice][1]()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
