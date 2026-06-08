import os
import requests
from requests.auth import HTTPBasicAuth

# Billplz API Sandbox: https://www.billplz-sandbox.com/api/v3
# Billplz API Production: https://www.billplz.com/api/v3

def create_billplz_collection(api_key: str, title: str, is_sandbox: bool = True):
    """
    Creates a new collection in Billplz to group payments.
    """
    base_url = "https://www.billplz-sandbox.com/api/v3" if is_sandbox else "https://www.billplz.com/api/v3"
    url = f"{base_url}/collections"
    
    payload = {"title": title}
    try:
        response = requests.post(url, data=payload, auth=HTTPBasicAuth(api_key, ''))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Billplz Create Collection Failed: {e}")
        return None

def create_billplz_bill(api_key: str, collection_id: str, email: str, name: str, amount_rm: float, description: str, callback_url: str, is_sandbox: bool = True):
    """
    Generates an automated FPX/QR payment link via Billplz.
    amount_rm is in Ringgit (e.g., 50.00). Billplz expects cents (e.g., 5000).
    """
    base_url = "https://www.billplz-sandbox.com/api/v3" if is_sandbox else "https://www.billplz.com/api/v3"
    url = f"{base_url}/bills"
    
    payload = {
        "collection_id": collection_id,
        "email": email,
        "name": name,
        "amount": int(amount_rm * 100), # Convert RM to cents
        "callback_url": callback_url,
        "description": description
    }
    
    try:
        response = requests.post(url, data=payload, auth=HTTPBasicAuth(api_key, ''))
        response.raise_for_status()
        data = response.json()
        return data.get("url") # This is the payment link to send to the customer
    except Exception as e:
        print(f"[ERROR] Billplz Create Bill Failed: {e}")
        return None
