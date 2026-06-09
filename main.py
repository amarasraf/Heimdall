from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Security
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import pandas as pd
import os
import io
import re
import datetime
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

from parser_core import parse_address, parse_easyparcel_row, to_easyparcel
from database import save_parse_result, supabase, get_user_profile, extend_subscription, get_user_keys, save_user_keys

app = FastAPI(title="Heimdall", description="Malaysian Address Parser for EasyParcel")
import asyncio
from datetime import datetime, timezone, timedelta

import os
if not os.path.exists('static'):
    os.makedirs('static')
app.mount('/static', StaticFiles(directory='static'), name='static')

# Background Task: Abandoned Cart Follow-Up
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(abandoned_cart_worker())

async def abandoned_cart_worker():
    """
    Scans the database every hour for users stuck in AWAITING_RECEIPT
    and sends a follow-up WhatsApp message.
    """
    from database import supabase, get_user_keys
    from whatsapp_service import send_whatsapp_message
    
    while True:
        try:
            if supabase:
                # Find sessions created more than 1 hour ago still in AWAITING_RECEIPT
                one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
                
                res = supabase.table('whatsapp_sessions').select('*').eq('state', 'AWAITING_RECEIPT').lt('created_at', one_hour_ago).execute()
                
                for session in res.data:
                    # To prevent spamming, we should mark it as FOLLOWED_UP or delete it
                    # For this MVP, we will change state to AWAITING_RECEIPT_FOLLOWED_UP
                    user_id = session.get('user_id')
                    sender = session.get('phone_number')
                    
                    keys = get_user_keys(user_id)
                    tw_sid = keys.get("twilio_sid", "")
                    tw_token = keys.get("twilio_token", "")
                    
                    if tw_sid and tw_token:
                        send_whatsapp_message(
                            sender, 
                            "Hi! Nak confirm jadi ke order tadi? Kalau ada masalah payment, boleh rogol saya ya. Terima kasih! 🙏", 
                            tw_sid, tw_token
                        )
                    # Update state so we don't message again
                    supabase.table('whatsapp_sessions').update({'state': 'AWAITING_RECEIPT_FOLLOWED_UP'}).eq('id', session['id']).execute()
        except Exception as e:
            print(f"[ERROR] Abandoned Cart Worker failed: {e}")
            
        await asyncio.sleep(3600) # Wait 1 hour before checking again


security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        # Verify the JWT token with Supabase
        user_response = supabase.auth.get_user(credentials.credentials)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_response.user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed or token expired")

def check_subscription(user_id: str, required_tier: str = "basic"):
    profile = get_user_profile(user_id)
    if not profile or not profile.get('subscription_end_date'):
        raise HTTPException(status_code=402, detail="Langganan tamat tempoh. Sila upah Bebbi dahulu.")
    
    end_date = datetime.fromisoformat(profile['subscription_end_date'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    if now > end_date:
        raise HTTPException(status_code=402, detail="Langganan tamat tempoh. Sila upah Bebbi dahulu.")
        
    user_tier = profile.get('subscription_tier', 'basic')
    if required_tier == "pro" and user_tier != "pro":
         raise HTTPException(status_code=403, detail="Fungsi ini perlukan Pakej Bebbi Buat Semua (RM30/sebulan).")

TOYYIBPAY_SECRET_KEY = os.getenv("TOYYIBPAY_SECRET_KEY", "your-sandbox-secret-key")
TOYYIBPAY_CATEGORY = os.getenv("TOYYIBPAY_CATEGORY", "your-sandbox-category-code")
TOYYIBPAY_URL = "https://dev.toyyibpay.com"

@app.get("/me")
async def get_me(user=Depends(get_current_user)):
    profile = get_user_profile(user.id)
    if profile:
        return {"user_id": user.id, "email": user.email, "subscription_end_date": profile.get("subscription_end_date"), "whatsapp_number": profile.get("whatsapp_number"), "subscription_tier": profile.get("subscription_tier", "basic")}
    return {"user_id": user.id, "email": user.email, "subscription_end_date": None, "whatsapp_number": None, "subscription_tier": "none"}

class PhoneRequest(BaseModel):
    whatsapp_number: str

@app.post("/whatsapp-number")
async def update_phone(req: PhoneRequest, user=Depends(get_current_user)):
    from database import save_whatsapp_number
    clean_num = req.whatsapp_number.replace("+", "").replace("-", "").replace(" ", "").replace("whatsapp:", "")
    if save_whatsapp_number(user.id, clean_num):
        return {"status": "success"}
    raise HTTPException(500, "Failed to save phone number")

@app.get("/api-keys")
async def fetch_api_keys(user=Depends(get_current_user)):
    keys = get_user_keys(user.id)
    return keys

class ApiKeysRequest(BaseModel):
    keys: dict

@app.post("/api-keys")
async def update_api_keys(req: ApiKeysRequest, user=Depends(get_current_user)):
    if save_user_keys(user.id, req.keys):
        return {"status": "success"}
    raise HTTPException(500, "Failed to save keys")

from fastapi import Request

@app.post("/create-bill")
async def create_bill(tier: str = "basic", user=Depends(get_current_user)):
    amount = 500 if tier == "basic" else 3000
    bill_name = 'Pakej Bebbi Tolong Susun' if tier == "basic" else 'Pakej Bebbi Buat Semua'
    
    payload = {
        'userSecretKey': TOYYIBPAY_SECRET_KEY,
        'categoryCode': TOYYIBPAY_CATEGORY,
        'billName': bill_name,
        'billDescription': '30 days subscription',
        'billPriceSetting': 1,
        'billPayorInfo': 1,
        'billAmount': amount,
        'billReturnUrl': 'https://heimdall-517339133458.asia-southeast1.run.app/',
        'billCallbackUrl': 'https://heimdall-517339133458.asia-southeast1.run.app/webhook/toyyibpay',
        'billExternalReferenceNo': f"{user.id}|{tier}",
        'billTo': user.email,
        'billEmail': user.email,
        'billPhone': '0123456789'
    }
    try:
        response = requests.post(f"{TOYYIBPAY_URL}/index.php/api/createBill", data=payload)
        data = response.json()
        if isinstance(data, list) and len(data) > 0 and 'BillCode' in data[0]:
            bill_code = data[0]['BillCode']
            payment_url = f"{TOYYIBPAY_URL}/{bill_code}"
            return {"payment_url": payment_url}
        else:
            raise HTTPException(400, f"ToyyibPay Error: {data}")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/webhook/toyyibpay")
async def toyyibpay_webhook(request: Request):
    form_data = await request.form()
    status_id = form_data.get('status_id')
    bill_external_ref = form_data.get('refno')
    
    if status_id == '1' and bill_external_ref:
        parts = str(bill_external_ref).split('|')
        user_id = parts[0]
        tier = parts[1] if len(parts) > 1 else 'basic'
        extend_subscription(user_id, 30, tier)
        return {"status": "success"}
    return {"status": "ignored"}



@app.get("/", response_class=HTMLResponse)
async def index():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    from database import SUPABASE_URL, SUPABASE_KEY
    html = html.replace("{{SUPABASE_URL}}", SUPABASE_URL or "")
    html = html.replace("{{SUPABASE_KEY}}", SUPABASE_KEY or "")
    return html


from pydantic import BaseModel

class ParseRequest(BaseModel):
    text: str

@app.get("/parse")
async def parse_single_get(text: str, user=Depends(get_current_user)):
    check_subscription(user.id)
    if re.search(r'(Nama penerima\s*:|Alamat penerima\s*:)', text, re.IGNORECASE):
        parsed = parse_easyparcel_row({"recipient_name": text})
    else:
        parsed = [parse_address(text)]
        
    save_parse_result("single", text, parsed, user.id)
    return parsed

@app.post("/parse")
async def parse_text(req: ParseRequest, user=Depends(get_current_user)):
    check_subscription(user.id)
    text = req.text
    if re.search(r'(Nama penerima\s*:|Alamat penerima\s*:)', text, re.IGNORECASE):
        parsed = parse_easyparcel_row({"recipient_name": text})
    else:
        parsed = [parse_address(text)]
        
    save_parse_result("single", text, parsed, user.id)
    return parsed


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...), user=Depends(get_current_user)):
    check_subscription(user.id)
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files allowed")

    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"Failed to parse CSV: {e}")

    # Detect format
    has_raw_text = 'raw_text' in df.columns
    has_easyparcel_cols = any(c in df.columns for c in ['recipient_name', 'recipient_phone', 'recipient_address'])

    results = []

    if has_raw_text:
        from parser_core import to_easyparcel
        for _, row in df.iterrows():
            parsed = parse_address(str(row['raw_text']))
            results.append(to_easyparcel(parsed))

    elif has_easyparcel_cols:
        for _, row in df.iterrows():
            parsed_rows = parse_easyparcel_row(row)
            results.extend(parsed_rows)

    else:
        first_col = df.columns[0]
        for _, row in df.iterrows():
            parsed = parse_address(str(row[first_col]))
            results.append(to_easyparcel(parsed))

    save_parse_result("bulk", f"CSV Upload: {file.filename} ({len(df)} rows)", results, user.id)
    return JSONResponse({"results": len(results), "data": results})

EASYPARCEL_API_KEY = os.getenv("EASYPARCEL_API_KEY", "")

class SubmitOrderRequest(BaseModel):
    orders: list

@app.post("/submit-easyparcel")
async def submit_easyparcel(req: SubmitOrderRequest, user=Depends(get_current_user)):
    check_subscription(user.id, "pro")
    keys = get_user_keys(user.id)
    ep_key = keys.get("easyparcel", EASYPARCEL_API_KEY)
    
    if not ep_key:
        # Simulated success
        return JSONResponse({
            "status": "success", 
            "message": "Simulated EasyParcel submission successful (No API Key set).", 
            "tracking_numbers": [f"EP{str(i).zfill(8)}MY" for i in range(len(req.orders))]
        })
    
    url = "https://api.easyparcel.my/ep-api/v1.2/"
    payload = {
        "api": ep_key,
        "bulk": []
    }
    
    for idx, order in enumerate(req.orders):
        payload["bulk"].append({
            "weight": order.get("weight_kg", "0.5"),
            "content": order.get("parcel_content", "General merchandise"),
            "value": order.get("parcel_value_rm", "100"),
            "pick_point": "P1", 
            "pick_name": "Heimdall Sender",
            "pick_company": "Heimdall Co",
            "pick_contact": "0123456789",
            "pick_mobile": "0123456789",
            "pick_addr1": "HQ",
            "pick_city": "Kuala Lumpur",
            "pick_state": "kuala lumpur",
            "pick_code": "50000",
            "send_name": order.get("recipient_name", "Recipient") or "Recipient",
            "send_contact": order.get("phone", "0123456789") or "0123456789",
            "send_mobile": order.get("phone", "0123456789") or "0123456789",
            "send_addr1": order.get("street", "Address") or "Address",
            "send_city": order.get("city", "City") or "City",
            "send_state": order.get("state", "State") or "State",
            "send_code": order.get("postcode", "00000") or "00000",
            "reference": f"HEIMDALL-{idx}"
        })

    try:
        response = requests.post(url, data=payload)
        data = response.json()
        if data.get("api_status") == "Success":
            return JSONResponse({"status": "success", "data": data})
        else:
            error_msg = str(data)
            if "credit" in error_msg.lower() or "fund" in error_msg.lower() or "balance" in error_msg.lower() or "topup" in error_msg.lower():
                raise HTTPException(400, "Alamak! Kredit EasyParcel anda tak cukup. Sila topup serendah RM20 di pautan Topup EasyParcel untuk teruskan penghantaran.")
            raise HTTPException(400, f"EasyParcel API Error: {data}")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(500, str(e))

# Evolution API Webhook Placeholder
# This endpoint will receive messages from our Node.js QR Engine
@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    payload = await request.json()
    
    # Expected payload from EvolutionAPI:
    # {"data": {"message": {"conversation": "The actual message text", "key": {"remoteJid": "60123456789@s.whatsapp.net"}}}}
    
    # Check subscription status and handle parser/auto-reply logic here later
    # This keeps Twilio out of our system!
    
    return {"status": "success", "message": "Evolution API webhook received"}

