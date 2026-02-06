"""Test which depreciation value is correct"""
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
import time

url = "https://www.sgcarmart.com/used_cars/info.php?ID=1436938"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="en-SG")
    page = context.new_page()
    stealth_sync(page)
    
    page.goto("https://www.sgcarmart.com", wait_until="domcontentloaded")
    time.sleep(3)
    
    page.goto(url, wait_until="domcontentloaded", timeout=15000)
    time.sleep(2)
    
    # Get all depreciation matches with context
    result = page.evaluate(r"""
        () => {
            const all = [];
            const regex = /\$\s*([\d,]+)\s*\/\s*yr/gi;
            const bodyText = document.body.textContent;
            
            let match;
            let lastIndex = 0;
            while ((match = regex.exec(bodyText)) !== null) {
                const start = Math.max(0, match.index - 50);
                const end = Math.min(bodyText.length, match.index + match[0].length + 50);
                const context = bodyText.substring(start, end).replace(/\s+/g, ' ');
                all.push({
                    value: match[0],
                    context: context,
                    index: match.index
                });
                if (all.length >= 10) break;  // Just first 10
            }
            
            return all;
        }
    """)
    
    print(f"\nFirst 10 depreciation matches with context:\n")
    for i, item in enumerate(result):
        print(f"{i+1}. {item['value']}")
        print(f"   Context: ...{item['context']}...")
        print()
    
    input("Press Enter to close...")
    browser.close()
