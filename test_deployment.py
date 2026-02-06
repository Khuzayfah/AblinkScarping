"""Quick test to verify deployment"""
import requests
import sys

BASE_URL = "http://xoccsg84ogkc40sk4swkgw4w.76.13.22.221.sslip.io"

def test_endpoints():
    """Test all main endpoints"""

    tests = [
        ("Health Check", f"{BASE_URL}/api/health"),
        ("Root Page", f"{BASE_URL}/"),
        ("Latest Data", f"{BASE_URL}/api/latest-data"),
    ]

    print("Testing Deployment...\n")
    print("="*60)

    for name, url in tests:
        try:
            print(f"\nTesting: {name}")
            print(f"URL: {url}")

            response = requests.get(url, timeout=10)

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                print("✓ SUCCESS")
                if 'application/json' in response.headers.get('content-type', ''):
                    print(f"Response: {response.json()}")
                else:
                    print(f"Content Length: {len(response.text)} bytes")
            else:
                print("✗ FAILED")
                print(f"Response: {response.text[:200]}")

        except requests.exceptions.RequestException as e:
            print(f"✗ ERROR: {e}")

    print("\n" + "="*60)

if __name__ == "__main__":
    test_endpoints()
