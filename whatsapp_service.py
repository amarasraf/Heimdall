import requests

def send_whatsapp_message(to_number: str, body: str, sid: str, token: str, from_number: str = "whatsapp:+14155238886"):
    """
    Sends a WhatsApp message using Twilio's API dynamically.
    to_number should be formatted like "whatsapp:+60123456789"
    """
    if not sid or not token:
        print("[ERROR] Twilio credentials not provided.")
        return False
        
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"
        
    payload = {
        "From": from_number,
        "To": to_number,
        "Body": body
    }
    
    try:
        response = requests.post(url, data=payload, auth=(sid, token))
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send WhatsApp message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[ERROR DETAILS]: {e.response.text}")
        return False
