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
import os
if not os.path.exists('static'):
    os.makedirs('static')
app.mount('/static', StaticFiles(directory='static'), name='static')


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

def check_subscription(user_id: str):
    profile = get_user_profile(user_id)
    if not profile or not profile.get('subscription_end_date'):
        raise HTTPException(status_code=402, detail="Subscription expired. Please purchase a 30-day pass.")
    
    end_date = datetime.datetime.fromisoformat(profile['subscription_end_date'].replace('Z', '+00:00'))
    now = datetime.datetime.now(datetime.timezone.utc)
    if now > end_date:
        raise HTTPException(status_code=402, detail="Subscription expired. Please purchase a 30-day pass.")

TOYYIBPAY_SECRET_KEY = os.getenv("TOYYIBPAY_SECRET_KEY", "your-sandbox-secret-key")
TOYYIBPAY_CATEGORY = os.getenv("TOYYIBPAY_CATEGORY", "your-sandbox-category-code")
TOYYIBPAY_URL = "https://dev.toyyibpay.com"

@app.get("/me")
async def get_me(user=Depends(get_current_user)):
    profile = get_user_profile(user.id)
    if profile:
        return {"user_id": user.id, "email": user.email, "subscription_end_date": profile.get("subscription_end_date"), "whatsapp_number": profile.get("whatsapp_number")}
    return {"user_id": user.id, "email": user.email, "subscription_end_date": None, "whatsapp_number": None}

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
async def create_bill(user=Depends(get_current_user)):
    payload = {
        'userSecretKey': TOYYIBPAY_SECRET_KEY,
        'categoryCode': TOYYIBPAY_CATEGORY,
        'billName': 'Heimdall 30-Day Unlimited Pass',
        'billDescription': '30 days of unlimited address parsing',
        'billPriceSetting': 1,
        'billPayorInfo': 1,
        'billAmount': 3000,
        'billReturnUrl': 'https://heimdall-517339133458.asia-southeast1.run.app/',
        'billCallbackUrl': 'https://heimdall-517339133458.asia-southeast1.run.app/webhook/toyyibpay',
        'billExternalReferenceNo': user.id,
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
        extend_subscription(bill_external_ref, 30)
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
    check_subscription(user.id)
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
            raise HTTPException(400, f"EasyParcel API Error: {data}")
    except Exception as e:
        raise HTTPException(500, str(e))

from whatsapp_service import send_whatsapp_message
from database import get_user_by_whatsapp, get_whatsapp_session, create_whatsapp_session, update_whatsapp_session, delete_whatsapp_session

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    
    sender = form_data.get("From", "")
    clean_sender = sender.replace("whatsapp:", "").replace("+", "").replace("-", "").replace(" ", "")
    body = form_data.get("Body", "").strip()
    
    # 1. Check if user exists
    profile = get_user_by_whatsapp(clean_sender)
    if not profile:
        return {"status": "unauthorized"}
        
    user_id = profile.get("user_id")
    keys = get_user_keys(user_id)
    tw_sid = keys.get("twilio_sid", "")
    tw_token = keys.get("twilio_token", "")
    
    # 2. Check subscription
    try:
        check_subscription(user_id)
    except HTTPException:
        send_whatsapp_message(sender, "Alamak bos, langganan Heimdall dah tamat tempoh! 😭\n\nSila renew di website.", tw_sid, tw_token)
        return {"status": "expired"}

    # 3. Handle State Machine
    session = get_whatsapp_session(user_id, sender)
    
    # helper for sending to easyparcel (simulated)
    def push_to_easyparcel(parsed, tp_sid, tp_token):
        send_whatsapp_message(
            sender, 
            f"Settle bos! 🎉 (Simulasi)\n\nOrder untuk *{parsed.get('recipient_name')}* dah direkod.\n\n*(Nota: Server EasyParcel rasmi sedang offline/down sekarang, jadi order ni disimpan sebagai draf dalam Heimdall!)*", 
            tp_sid, tp_token
        )

    if session and session.get("state") == "AWAITING_PRICE":
        # The user replied with a price
        import re
        price_match = re.search(r'\d+(\.\d{1,2})?', body)
        if not price_match:
            send_whatsapp_message(sender, "Maaf bos, tak nampak nombor harga. Cuba taip harga je (contoh: 50 atau 12.50).", tw_sid, tw_token)
            return {"status": "awaiting_price_retry"}
            
        amount = float(price_match.group(0))
        parsed = session.get("parsed_address", {})
        
        # Check payment gateway preference
        toyyib_secret = keys.get("toyyibpay_secret")
        toyyib_category = keys.get("toyyibpay_category")
        
        update_whatsapp_session(session["id"], {"state": "AWAITING_RECEIPT", "amount": amount})
        
        if toyyib_secret and toyyib_category:
            # Generate ToyyibPay link
            tp_payload = {
                'userSecretKey': toyyib_secret,
                'categoryCode': toyyib_category,
                'billName': f"Order {parsed.get('recipient_name', 'Customer')}",
                'billDescription': 'Pembelian dari WhatsApp',
                'billPriceSetting': 1,
                'billPayorInfo': 1,
                'billAmount': int(amount * 100),
                'billReturnUrl': '',
                'billCallbackUrl': 'https://heimdall-517339133458.asia-southeast1.run.app/webhook/toyyibpay',
                'billExternalReferenceNo': str(session["id"]),
                'billTo': parsed.get('recipient_name', 'Customer'),
                'billEmail': 'customer@example.com',
                'billPhone': parsed.get('phone', '0123456789'),
            }
            try:
                tp_res = requests.post(f"{TOYYIBPAY_URL}/index.php/api/createBill", data=tp_payload).json()
                bill_code = tp_res[0]['BillCode']
                payment_link = f"{TOYYIBPAY_URL}/{bill_code}"
                update_whatsapp_session(session["id"], {"payment_link": payment_link})
                
                send_whatsapp_message(
                    sender, 
                    f"Settle bos! Forward mesej ni kat customer:\n\n*Terima kasih, order anda RM{amount:.2f}.*\n*Sila buat pembayaran di link ini: {payment_link}*\n\nBila customer bayar, Heimdall akan auto-hantar ke EasyParcel!", 
                    tw_sid, tw_token
                )
            except Exception as e:
                send_whatsapp_message(sender, f"Gagal generate link ToyyibPay. Cek API Key bos. Error: {e}", tw_sid, tw_token)
        else:
            # Static DuitNow QR flow
            send_whatsapp_message(
                sender,
                f"Settle bos! Forward QR DuitNow bos kat customer dan minta RM{amount:.2f}.\n\n*(Nanti saya akan bagi fungsi upload QR)*\n\n*Lepas customer bayar, bos forward resit/taip 'Dah bayar' untuk auto-generate tracking number!*",
                tw_sid, tw_token
            )
        return {"status": "price_received"}
        
    elif session and session.get("state") == "AWAITING_RECEIPT":
        # Usually they forward a receipt. For now, accept "paid"
        if "bayar" in body.lower() or "paid" in body.lower():
            send_whatsapp_message(sender, "Resit disahkan! 🚀 Tengah hantar ke EasyParcel...", tw_sid, tw_token)
            parsed = session.get("parsed_address", {})
            push_to_easyparcel(parsed, tw_sid, tw_token)
            delete_whatsapp_session(session["id"])
        else:
            send_whatsapp_message(sender, "Sila upload gambar resit dari customer, atau taip 'Dah bayar' untuk teruskan.", tw_sid, tw_token)
        return {"status": "awaiting_receipt"}
        
    else:
        # New order! Parse Address.
        if re.search(r'(Nama penerima\s*:|Alamat penerima\s*:)', body, re.IGNORECASE):
            parsed_list = parse_easyparcel_row({"recipient_name": body})
        else:
            parsed_list = [parse_address(body)]
            
        parsed = parsed_list[0]
        
        # Check for price in the new message
        price_match = re.search(r'RM\s*(\d+(\.\d{1,2})?)', body, re.IGNORECASE)
        if price_match:
            amount = float(price_match.group(1))
            session_rec = create_whatsapp_session(user_id, sender, "AWAITING_RECEIPT", parsed, body)
            
            # Has price, ask for receipt directly
            send_whatsapp_message(
                sender,
                f"Alamat cun, RM{amount:.2f} dikesan!\n\nSila minta customer bayar, kemudian forward resit ke sini (atau taip 'Dah bayar') untuk hantar ke EasyParcel.",
                tw_sid, tw_token
            )
        else:
            # No price found, ask for price
            create_whatsapp_session(user_id, sender, "AWAITING_PRICE", parsed, body)
            send_whatsapp_message(
                sender, 
                f"Alamat cun! Berapa ringgit nak charge *{parsed.get('recipient_name', 'customer')}* ni bos? (Taip nombor je, contoh: 50)", 
                tw_sid, tw_token
            )
        
        return {"status": "parsed"}

