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

load_dotenv()

from parser_core import parse_address, parse_easyparcel_row, to_easyparcel
from database import save_parse_result, supabase, get_user_profile, extend_subscription

app = FastAPI(title="Heimdall", description="Malaysian Address Parser for EasyParcel")

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
        return {"user_id": user.id, "email": user.email, "subscription_end_date": profile.get("subscription_end_date")}
    return {"user_id": user.id, "email": user.email, "subscription_end_date": None}

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
