import os
import requests
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886") # Default Twilio sandbox number

def send_whatsapp_message(to_number: str, body: str):
    """
    Sends a WhatsApp message using Twilio's API.
    to_number should be formatted like "whatsapp:+60123456789"
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("[ERROR] Twilio credentials not found in environment.")
        return False
        
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    # Twilio expects 'whatsapp:+1234567' format
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"
        
    payload = {
        "From": TWILIO_WHATSAPP_NUMBER,
        "To": to_number,
        "Body": body
    }
    
    try:
        response = requests.post(url, data=payload, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send WhatsApp message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[ERROR DETAILS]: {e.response.text}")
        return False
