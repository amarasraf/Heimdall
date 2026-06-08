import os
import time
import hmac
import hashlib
import requests
import json

# Lalamove API credentials will be pulled from user's keys in the DB or .env
# Sandbox URL: https://rest.sandbox.lalamove.com
# Production URL: https://rest.lalamove.com

def generate_signature(secret: str, method: str, path: str, body: str, timestamp: str) -> str:
    """
    Generates the HMAC SHA256 signature required by Lalamove's API.
    """
    raw_signature = f"{timestamp}\r\n{method}\r\n{path}\r\n\r\n{body}"
    return hmac.new(
        secret.encode('utf-8'),
        raw_signature.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_lalamove_quote(api_key: str, api_secret: str, origin: dict, destination: dict, is_sandbox: bool = True):
    """
    Fetches a delivery quotation from Lalamove.
    origin/destination dicts should contain 'lat', 'lng', and 'address'.
    """
    base_url = "https://rest.sandbox.lalamove.com" if is_sandbox else "https://rest.lalamove.com"
    path = "/v3/quotations"
    method = "POST"
    timestamp = str(int(time.time() * 1000))
    
    payload = {
        "data": {
            "scheduleAt": "", # Empty for immediate delivery
            "serviceType": "MOTORCYCLE", # Or CAR, VAN, etc.
            "specialRequests": [],
            "stops": [
                {
                    "coordinates": {"lat": origin["lat"], "lng": origin["lng"]},
                    "address": origin["address"]
                },
                {
                    "coordinates": {"lat": destination["lat"], "lng": destination["lng"]},
                    "address": destination["address"]
                }
            ],
            "isRouteOptimized": False
        }
    }
    
    body_str = json.dumps(payload)
    signature = generate_signature(api_secret, method, path, body_str, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"hmac {api_key}:{timestamp}:{signature}",
        "Market": "MY" # Malaysia
    }
    
    try:
        response = requests.post(base_url + path, headers=headers, data=body_str)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Lalamove Quote Failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[ERROR DETAILS]: {e.response.text}")
        return None

def place_lalamove_order(api_key: str, api_secret: str, quotation_id: str, sender: dict, recipient: dict, is_sandbox: bool = True):
    """
    Converts a quotation into an actual Lalamove order.
    """
    # Scaffolding for placing the order once the quote is approved.
    pass
