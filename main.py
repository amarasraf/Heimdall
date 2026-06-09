from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Security
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
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

from fastapi import Request, BackgroundTasks

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

    try:
        if has_raw_text:
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
                val = str(row[first_col])
                if pd.isna(row[first_col]) or val.strip() == "" or val.lower() == "nan":
                    continue
                parsed = parse_address(val)
                results.append(to_easyparcel(parsed))
    except Exception as e:
        raise HTTPException(400, f"Error processing file rows: {str(e)}")

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

import google.generativeai as genai
import os
import requests
import json
from parser_core import to_easyparcel

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "https://evolution-api-517339133458.asia-southeast1.run.app")
EVOLUTION_GLOBAL_KEY = os.getenv("EVOLUTION_GLOBAL_KEY", "bebbi_secret_token_123")

def get_whatsapp_media(instance_name, message_data):
    url = f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{instance_name}"
    headers = {"apikey": EVOLUTION_GLOBAL_KEY, "Content-Type": "application/json"}
    try:
        res = requests.post(url, json={"message": message_data}, headers=headers, timeout=10)
        data = res.json()
        return data.get("base64")
    except Exception as e:
        print(f"[ERROR] Failed to fetch media: {e}")
        return None

def send_whatsapp_reply(instance_name, remote_jid, text):
    url = f"{EVOLUTION_API_URL}/message/sendText/{instance_name}"
    headers = {"apikey": EVOLUTION_GLOBAL_KEY, "Content-Type": "application/json"}
    payload = {
        "number": remote_jid,
        "options": {"delay": 1500, "presence": "composing"},
        "textMessage": {"text": text}
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code != 200 and supabase:
            try:
                supabase.table("parse_history").insert({"user_id": "system_error", "image_url": "error", "result_json": {"error": res.text, "payload": payload}}).execute()
            except: pass
    except Exception as e:
        print(f"[ERROR] Failed to send WA reply: {e}")
        if supabase:
            try:
                supabase.table("parse_history").insert({"user_id": "system_error", "image_url": "error", "result_json": {"error": str(e)}}).execute()
            except: pass

@app.get("/webhook/debug/logs")
async def get_webhook_logs():
    try:
        with open("webhook_debug.log", "r") as f:
            return PlainTextResponse(f.read())
    except Exception as e:
        return {"error": str(e)}

@app.post("/webhook/evolution")
async def evolution_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        
        # DEBUG: Log payload to file
        with open("webhook_debug.log", "a") as f:
            f.write(json.dumps(payload) + "\n")
            
        print(f"[WEBHOOK] Received: {json.dumps(payload)[:200]}...")
        
        # DEBUG: Log to Supabase so it survives Cloud Run sleep
        if supabase:
            try:
                supabase.table("parse_history").insert({
                    "user_id": "system_debug",
                    "result_json": payload
                }).execute()
            except Exception as se:
                print("Supabase logging failed:", se)
        
        # Evolution API v1.x / v2.x payload parsing
        if payload.get("event") != "messages.upsert":
            return {"status": "ignored", "reason": "not messages.upsert"}
            
        instance_name = payload.get("instance", "")
        if not instance_name.startswith("bebbi_user_"):
            return {"status": "ignored", "reason": "invalid instance name"}
            
        user_id = instance_name.replace("bebbi_user_", "")
        
        data = payload.get("data", {})
        
        # DEBUG: Send payload to admin WhatsApp
        try:
            admin_num = "601124285149@s.whatsapp.net"
            requests.post(
                f"{EVOLUTION_API_URL}/message/sendText/{instance_name}",
                json={
                    "number": admin_num,
                    "options": {"delay": 100},
                    "textMessage": {"text": f"DEBUG PAYLOAD:\n{json.dumps(payload)[:800]}"}
                },
                headers={"apikey": EVOLUTION_GLOBAL_KEY, "Content-Type": "application/json"},
                timeout=5
            )
        except Exception as admin_err:
            print("Failed to send debug to admin:", admin_err)
        
        message_obj = {}
        key = {}
        
        # Handle array format (Evolution API v1.x)
        if "messages" in data and len(data["messages"]) > 0:
            msg_item = data["messages"][0]
            key = msg_item.get("key", {})
            message_obj = msg_item.get("message", {})
        # Handle flat object format
        elif "key" in data and "message" in data:
            key = data.get("key", {})
            message_obj = data.get("message", {})
        else:
            # Fallback
            key = data.get("key", {})
            message_obj = data.get("message", {})
            
        remote_jid = key.get("remoteJid", "")
        
        if key.get("fromMe") == True or "@g.us" in remote_jid or "status@broadcast" in remote_jid:
            return {"status": "ignored", "reason": "from me or group/status"}
            
        text = ""
        has_media = False
        mime_type = ""
        
        if "conversation" in message_obj:
            text = message_obj["conversation"]
        elif "extendedTextMessage" in message_obj:
            text = message_obj["extendedTextMessage"].get("text", "")
        elif "imageMessage" in message_obj:
            has_media = True
            mime_type = message_obj["imageMessage"].get("mimetype", "image/jpeg")
            text = message_obj["imageMessage"].get("caption", "")
        elif "audioMessage" in message_obj:
            has_media = True
            mime_type = message_obj["audioMessage"].get("mimetype", "audio/ogg")
            text = "[VOICE NOTE RECEIVED]"
            
        if not text.strip() and not has_media:
            return {"status": "ignored", "reason": "empty text and no media"}
            
        print(f"[WEBHOOK] User {user_id} received from {remote_jid}: text={text[:50]}, media={has_media}")
        
        # Pass to background task so we don't timeout the webhook
        # Pass data instead of message_data for media fetching
        background_tasks.add_task(process_bebbi_ai, user_id, instance_name, remote_jid, text, data, has_media, mime_type)
        
        return {"status": "success"}
    except Exception as e:
        print(f"[ERROR] Webhook processing failed: {e}")
        return {"status": "error"}

def process_bebbi_ai(user_id, instance_name, remote_jid, text, message_data, has_media, mime_type):
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY is not set!")
        send_whatsapp_reply(instance_name, remote_jid, "Meow~ Bebbi minta maaf, otak AI Bebbi (Gemini API Key) belum di set oleh bos. 😿")
        return

    system_prompt = '''Anda adalah Bebbi, seekor kucing AI pintar yang bekerja sebagai pembantu peribadi kepada penjual online (Makcik/Abang).
Anda membalas mesej pelanggan di WhatsApp. Pelanggan mungkin menghantar teks, gambar resit, atau voice note (rakaman suara).
Gunakan Bahasa Melayu Pasar yang santai, manja, dan mesra (macam kucing). Guna emoji kucing 😻🐾.
Tugas anda:
1. Layan pelanggan dengan ramah.
2. Jika pelanggan hantar gambar resit, sahkan pembayaran jika boleh dibaca.
3. Jika pelanggan hantar voice note, jawab persoalan mereka dalam teks (anda boleh faham audio tersebut).
4. Kalau pelanggan bagi alamat atau butiran order untuk pos barang, detect alamat tersebut!
5. Kalau berjaya detect alamat, beritahu pelanggan anda telah simpankan alamat tersebut untuk bos proses.

PENTING: Anda MESTI membalas dalam format JSON sahaja.
{
  "reply": "Mesej santai Bebbi untuk dihantar ke pelanggan",
  "has_address": true/false,
  "parsed_address": {"name": "", "phone": "", "street": "", "postcode": "", "city": "", "state": ""} // jika tiada alamat, set null
}'''

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        contents = []
        if has_media:
            base64_data = get_whatsapp_media(instance_name, message_data)
            if base64_data:
                # Format required by Gemini (raw bytes)
                raw_bytes = base64.b64decode(base64_data)
                contents.append({
                    "mime_type": mime_type,
                    "data": raw_bytes
                })
        
        if text and text != "[VOICE NOTE RECEIVED]":
            contents.append(text)
        elif not contents:
            contents.append("Tolong layan pelanggan ini.")
            
        response = model.generate_content(contents)
        result = json.loads(response.text)
        
        reply_text = result.get("reply", "Meow! Bebbi dah terima mesej awak. 🐾")
        has_address = result.get("has_address", False)
        parsed_addr = result.get("parsed_address")
        
        send_whatsapp_reply(instance_name, remote_jid, reply_text)
        
        if has_address and parsed_addr:
            easyparcel_format = to_easyparcel([parsed_addr])[0] if isinstance(to_easyparcel([parsed_addr]), list) else parsed_addr
            save_parse_result("whatsapp", text, easyparcel_format, user_id)
            print(f"[BEBBI] Address saved for user {user_id}: {parsed_addr}")
            
    except Exception as e:
        print(f"[ERROR] Bebbi AI failed: {e}")
        send_whatsapp_reply(instance_name, remote_jid, "Meow... Bebbi pening sikit lerrr. Kejap lagi Bebbi reply ya! 🐾")

import qrcode
import base64
from io import BytesIO

import os
import requests

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "https://evolution-api-517339133458.asia-southeast1.run.app")
EVOLUTION_GLOBAL_KEY = os.getenv("EVOLUTION_GLOBAL_KEY", "bebbi_secret_token_123")

@app.post("/whatsapp/qr")
async def generate_whatsapp_qr(request: Request, user=Depends(get_current_user)):
    try:
        instance_name = f"bebbi_user_{user.id}"
        headers = {"apikey": EVOLUTION_GLOBAL_KEY, "Content-Type": "application/json"}
        
        forwarded_host = request.headers.get("x-forwarded-host")
        if forwarded_host:
            base_url = f"https://{forwarded_host}"
        else:
            base_url = str(request.base_url).rstrip("/")
            if base_url.startswith("http://") and "localhost" not in base_url:
                base_url = base_url.replace("http://", "https://")
                
        webhook_url = f"{base_url}/webhook/evolution"
        
        # ALWAYS ensure webhook is set for this instance
        webhook_payload = {
            "url": webhook_url,
            "webhook_by_events": False,
            "webhook_base64": False,
            "events": ["MESSAGES_UPSERT"]
        }
        try:
            # Try v1 format first
            res_wh = requests.post(f"{EVOLUTION_API_URL}/webhook/set/{instance_name}", json=webhook_payload, headers=headers, timeout=5)
            if res_wh.status_code >= 400:
                # Try v2 format
                webhook_payload_v2 = {"webhook": {"url": webhook_url, "byEvents": False, "base64": False, "events": ["MESSAGES_UPSERT"]}}
                requests.put(f"{EVOLUTION_API_URL}/webhook/set/{instance_name}", json=webhook_payload_v2, headers=headers, timeout=5)
        except Exception as e:
            print(f"[ERROR] Failed to set webhook: {e}")
            
        try:
            # 1. Check if instance already exists by trying to connect
            conn_res = requests.get(f"{EVOLUTION_API_URL}/instance/connect/{instance_name}", headers=headers, timeout=5)
            
            if conn_res.status_code == 404:
                # Instance doesn't exist, create it with dynamic webhook
                create_payload = {
                    "instanceName": instance_name, 
                    "token": instance_name, 
                    "qrcode": True,
                    "integration": "WHATSAPP-BAILEYS",
                    "webhook": {"url": webhook_url, "byEvents": False, "base64": False, "events": ["MESSAGES_UPSERT"]}
                }
                res = requests.post(f"{EVOLUTION_API_URL}/instance/create", json=create_payload, headers=headers, timeout=10)
                data = res.json()
                if "qrcode" in data and "base64" in data["qrcode"]:
                    real_qr_base64 = data["qrcode"]["base64"].replace("data:image/png;base64,", "")
                    return {"status": "success", "qr_base64": real_qr_base64, "message": "Sila scan QR code sebenar ini!"}
            else:
                data = conn_res.json()
                if "base64" in data:
                    real_qr_base64 = data["base64"].replace("data:image/png;base64,", "")
                    return {"status": "success", "qr_base64": real_qr_base64, "message": "Sila scan QR code sebenar ini!"}
                elif "instance" in data and data["instance"].get("state") == "open":
                    return {"status": "success", "message": "WhatsApp sudah disambungkan! (Linked)", "qr_base64": ""}
                    
        except Exception as api_err:
            print(f"Evolution API not reachable: {api_err}. Falling back to mock QR.")

        # 2. Fallback to Mock QR if Evolution API is offline or errors
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data("mock_whatsapp_qr_for_user_" + str(user.id) + "_evolution_api_is_offline")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return {"status": "success", "qr_base64": img_str, "message": "[MOCK] Evolution API offline. Sila buka server Evolution API."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/whatsapp/logout")
async def whatsapp_logout(user=Depends(get_current_user)):
    try:
        instance_name = f"bebbi_user_{user.id}"
        headers = {"apikey": EVOLUTION_GLOBAL_KEY, "Content-Type": "application/json"}
        
        # Logout first
        try:
            requests.delete(f"{EVOLUTION_API_URL}/instance/logout/{instance_name}", headers=headers, timeout=5)
        except:
            pass
        
        # Then delete the instance
        try:
            requests.delete(f"{EVOLUTION_API_URL}/instance/delete/{instance_name}", headers=headers, timeout=5)
        except:
            pass
            
        return {"status": "success", "message": "WhatsApp telah dilog keluar. Sila scan QR code baru."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/create-bill")
async def create_bill(tier: str = "pro", user=Depends(get_current_user)):
    # Scaffold for ToyyibPay Integration
    # We would call ToyyibPay /index.php/api/createBill here
    # Example Mock Response:
    profile = get_user_profile(user.id)
    
    toyyibpay_mock_url = "https://dev.toyyibpay.com/mock-bill-" + user.id + "?tier=" + tier
    
    # In a real scenario, after successful payment, ToyyibPay sends a callback to our webhook,
    # which calls `extend_subscription(user.id, months=1)`.
    
    return {"status": "success", "payment_url": toyyibpay_mock_url, "message": "Redirecting to ToyyibPay..."}
