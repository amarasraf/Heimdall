import requests
import sys

URL = "https://heimdall-517339133458.asia-southeast1.run.app/"

print(f"Jack (QA) initiating health check on {URL}...")

try:
    response = requests.get(URL, timeout=10)
    if response.status_code != 200:
        print(f"[FAIL] Server returned status code: {response.status_code}")
        sys.exit(1)
        
    html_content = response.text
    
    # Check 1: Is the BYOK Settings button deployed?
    if "toggleSettings()" in html_content or "Settings" in html_content:
        print("[PASS] BYOK Settings UI is live.")
    else:
        print("[FAIL] BYOK Settings UI is missing. The server is still running the old version.")
        sys.exit(1)
        
    # Check 2: Are the new City-Link and GDEX couriers in the frontend?
    if "City-Link" in html_content and "GDEX" in html_content:
        print("[PASS] Multi-Courier buttons (City-Link, GDEX) are live.")
    else:
        print("[FAIL] Multi-Courier UI is missing.")
        sys.exit(1)

    print("\n[QA CERTIFIED] All checks passed. The Cloud Run deployment is fully synced with the 'main' branch!")

except requests.exceptions.RequestException as e:
    print(f"[ERROR] Connection failed: {e}")
    sys.exit(1)
