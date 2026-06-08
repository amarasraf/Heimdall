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

NINJAVAN_CLIENT_ID = os.getenv("NINJAVAN_CLIENT_ID", "")
NINJAVAN_CLIENT_SECRET = os.getenv("NINJAVAN_CLIENT_SECRET", "")

@app.post("/submit-ninjavan")
async def submit_ninjavan(req: SubmitOrderRequest, user=Depends(get_current_user)):
    check_subscription(user.id)
    keys = get_user_keys(user.id)
    nv_client = keys.get("ninjavan_client_id", NINJAVAN_CLIENT_ID)
    nv_secret = keys.get("ninjavan_client_secret", NINJAVAN_CLIENT_SECRET)
    
    if not nv_client or not nv_secret:
        # Simulated success
        return JSONResponse({
            "status": "success", 
            "message": "Simulated Ninja Van submission successful (No API Key set).", 
            "tracking_numbers": [f"NV{str(i).zfill(8)}MY" for i in range(len(req.orders))]
        })
    
    # Real Ninja Van API Integration (Malaysia Sandbox/Production)
    # 1. Get OAuth Token (Simulated here if real endpoint is used, usually requires POST to /oauth/access_token)
    # We will assume a simplified direct post for demonstration, or you can implement the OAuth flow.
    nv_url = "https://api.ninjavan.co/my/4.1/orders"
    
    # Standard Ninja Van Order Payload Structure
    payload = {
        "service_type": "Standard",
        "service_level": "Standard",
        "from": {
            "name": "Heimdall Sender",
            "phone_number": "+60123456789",
            "email": "sender@heimdall.com",
            "address": {
                "address1": "HQ",
                "city": "Kuala Lumpur",
                "state": "Kuala Lumpur",
                "postcode": "50000",
                "country": "MY"
            }
        },
        "parcel_job": {
            "is_pickup_required": True,
            "pickup_date": (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "pickup_timeslot": {
                "start_time": "09:00",
                "end_time": "18:00",
                "timezone": "Asia/Kuala_Lumpur"
            }
        },
        "orders": []
    }
    
    for idx, order in enumerate(req.orders):
        payload["orders"].append({
            "requested_tracking_number": f"NV-HEIMDALL-{idx}-{int(datetime.datetime.now().timestamp())}",
            "reference": {
                "merchant_order_number": f"HEIMDALL-{idx}"
            },
            "to": {
                "name": order.get("recipient_name", "Recipient") or "Recipient",
                "phone_number": order.get("phone", "+60123456789") or "+60123456789",
                "email": "customer@example.com",
                "address": {
                    "address1": order.get("street", "Address") or "Address",
                    "city": order.get("city", "City") or "City",
                    "state": order.get("state", "State") or "State",
                    "postcode": order.get("postcode", "00000") or "00000",
                    "country": "MY"
                }
            },
            "parcel_job": {
                "dimensions": {
                    "weight": float(order.get("weight_kg", "0.5"))
                }
            }
        })

    try:
        # In a real app, you'd fetch the Bearer token first using Client ID/Secret
        headers = {
            "Authorization": f"Bearer {nv_secret}", # Simplified for demonstration
            "Content-Type": "application/json"
        }
        response = requests.post(nv_url, json=payload, headers=headers)
        data = response.json()
        
        # Ninja Van usually returns 200/201 on success
        if response.status_code in [200, 201]:
            return JSONResponse({"status": "success", "data": data})
        else:
            raise HTTPException(400, f"Ninja Van API Error: {data}")
    except Exception as e:
        raise HTTPException(500, str(e))

JNT_API_KEY = os.getenv("JNT_API_KEY", "")
DHL_API_KEY = os.getenv("DHL_API_KEY", "")
DHL_API_SECRET = os.getenv("DHL_API_SECRET", "")

@app.post("/submit-jnt")
async def submit_jnt(req: SubmitOrderRequest, user=Depends(get_current_user)):
    check_subscription(user.id)
    keys = get_user_keys(user.id)
    jnt_key = keys.get("jnt", JNT_API_KEY)
    
    if not jnt_key:
        # Simulated success
        return JSONResponse({
            "status": "success", 
            "message": "Simulated J&T Express submission successful (No API Key set).", 
            "tracking_numbers": [f"JT{str(i).zfill(9)}MY" for i in range(len(req.orders))]
        })
    
    # Generic J&T API Integration setup
    jnt_url = "https://api.jtexpress.my/openapi/order/create"
    
    payload = {
        "customerCode": "HEIMDALL_VIP",
        "digest": "generated_signature",
        "orders": []
    }
    
    for idx, order in enumerate(req.orders):
        payload["orders"].append({
            "txlogisticId": f"HEIMDALL-JT-{idx}-{int(datetime.datetime.now().timestamp())}",
            "sender": {
                "name": "Heimdall Sender",
                "mobile": "0123456789",
                "city": "Kuala Lumpur",
                "prov": "Kuala Lumpur",
                "address": "HQ Address"
            },
            "receiver": {
                "name": order.get("recipient_name", "Recipient") or "Recipient",
                "mobile": order.get("phone", "0123456789") or "0123456789",
                "city": order.get("city", "City") or "City",
                "prov": order.get("state", "State") or "State",
                "address": order.get("street", "Address") or "Address",
                "postcode": order.get("postcode", "00000") or "00000"
            },
            "weight": order.get("weight_kg", "0.5"),
            "itemName": order.get("parcel_content", "General items")
        })

    try:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(jnt_url, data={"logistics_interface": str(payload)}, headers=headers)
        data = response.json()
        if data.get("responseitems", [{}])[0].get("success") == "true":
            return JSONResponse({"status": "success", "data": data})
        else:
            raise HTTPException(400, f"J&T API Error: {data}")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/submit-dhl")
async def submit_dhl(req: SubmitOrderRequest, user=Depends(get_current_user)):
    check_subscription(user.id)
    keys = get_user_keys(user.id)
    dhl_key = keys.get("dhl_key", DHL_API_KEY)
    dhl_secret = keys.get("dhl_secret", DHL_API_SECRET)
    
    if not dhl_key or not dhl_secret:
        # Simulated success
        return JSONResponse({
            "status": "success", 
            "message": "Simulated DHL eCommerce submission successful (No API Key set).", 
            "tracking_numbers": [f"DHL{str(i).zfill(8)}MY" for i in range(len(req.orders))]
        })
    
    # Generic DHL eCommerce Integration setup
    dhl_url = "https://api.dhl.com/ecommerce/ap/v1/orders"
    
    payload = {
        "shipments": []
    }
    
    for idx, order in enumerate(req.orders):
        payload["shipments"].append({
            "shipmentId": f"HEIMDALL-DHL-{idx}-{int(datetime.datetime.now().timestamp())}",
            "shipper": {
                "name": "Heimdall Sender",
                "contactNumber": "0123456789",
                "address": {
                    "line1": "HQ Address",
                    "city": "Kuala Lumpur",
                    "state": "Kuala Lumpur",
                    "postalCode": "50000",
                    "country": "MY"
                }
            },
            "consignee": {
                "name": order.get("recipient_name", "Recipient") or "Recipient",
                "contactNumber": order.get("phone", "0123456789") or "0123456789",
                "address": {
                    "line1": order.get("street", "Address") or "Address",
                    "city": order.get("city", "City") or "City",
                    "state": order.get("state", "State") or "State",
                    "postalCode": order.get("postcode", "00000") or "00000",
                    "country": "MY"
                }
            },
            "details": {
                "weight": float(order.get("weight_kg", "0.5")),
                "productCode": "PDO" # Parcel Delivery Online
            }
        })

    try:
        headers = {
            "Authorization": f"Basic {dhl_key}:{dhl_secret}", # Pseudo auth
            "Content-Type": "application/json"
        }
        response = requests.post(dhl_url, json=payload, headers=headers)
        data = response.json()
        if response.status_code in [200, 201]:
            return JSONResponse({"status": "success", "data": data})
        else:
            raise HTTPException(400, f"DHL API Error: {data}")
    except Exception as e:
        raise HTTPException(500, str(e))

CITYLINK_API_KEY = os.getenv("CITYLINK_API_KEY", "")
GDEX_API_KEY = os.getenv("GDEX_API_KEY", "")

@app.post("/submit-citylink")
async def submit_citylink(req: SubmitOrderRequest, user=Depends(get_current_user)):
    check_subscription(user.id)
    keys = get_user_keys(user.id)
    cl_key = keys.get("citylink", CITYLINK_API_KEY)
    if not cl_key:
        # Simulated success
        return JSONResponse({
            "status": "success", 
            "message": "Simulated City-Link Express submission successful (No API Key set).", 
            "tracking_numbers": [f"CL{str(i).zfill(9)}MY" for i in range(len(req.orders))]
        })
    
    citylink_url = "https://api.citylinkexpress.com.my/v1/shipment/create"
    
    payload = {
        "account_no": "HEIMDALL_ACC",
        "shipments": []
    }
    
    for idx, order in enumerate(req.orders):
        payload["shipments"].append({
            "reference_no": f"HEIMDALL-CL-{idx}-{int(datetime.datetime.now().timestamp())}",
            "shipper": {
                "name": "Heimdall Sender",
                "phone": "0123456789",
                "address": "HQ Address",
                "city": "Kuala Lumpur",
                "postcode": "50000",
                "state": "KUL"
            },
            "consignee": {
                "name": order.get("recipient_name", "Recipient") or "Recipient",
                "phone": order.get("phone", "0123456789") or "0123456789",
                "address": order.get("street", "Address") or "Address",
                "city": order.get("city", "City") or "City",
                "postcode": order.get("postcode", "00000") or "00000",
                "state": order.get("state", "State") or "State"
            },
            "parcel_desc": order.get("parcel_content", "General items"),
            "weight": float(order.get("weight_kg", "0.5")),
            "pieces": 1
        })

    try:
        headers = {
            "Authorization": f"Bearer {cl_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(citylink_url, json=payload, headers=headers)
        data = response.json()
        if data.get("status") == "success":
            return JSONResponse({"status": "success", "data": data})
        else:
            raise HTTPException(400, f"City-Link API Error: {data}")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/submit-gdex")
async def submit_gdex(req: SubmitOrderRequest, user=Depends(get_current_user)):
    check_subscription(user.id)
    keys = get_user_keys(user.id)
    gdex_key = keys.get("gdex", GDEX_API_KEY)
    
    if not gdex_key:
        # Simulated success
        return JSONResponse({
            "status": "success", 
            "message": "Simulated GDEX submission successful (No API Key set).", 
            "tracking_numbers": [f"MY{str(i).zfill(10)}" for i in range(len(req.orders))]
        })
    
    gdex_url = "https://api.gdexpress.com/v1/cn/create"
    
    payload = {
        "subscription_key": gdex_key,
        "consignments": []
    }
    
    for idx, order in enumerate(req.orders):
        payload["consignments"].append({
            "order_no": f"HEIMDALL-GDEX-{idx}-{int(datetime.datetime.now().timestamp())}",
            "sender_name": "Heimdall Sender",
            "sender_contact": "0123456789",
            "sender_address1": "HQ Address",
            "sender_postcode": "50000",
            "receiver_name": order.get("recipient_name", "Recipient") or "Recipient",
            "receiver_contact": order.get("phone", "0123456789") or "0123456789",
            "receiver_address1": order.get("street", "Address") or "Address",
            "receiver_postcode": order.get("postcode", "00000") or "00000",
            "receiver_city": order.get("city", "City") or "City",
            "receiver_state": order.get("state", "State") or "State",
            "actual_weight": float(order.get("weight_kg", "0.5")),
            "description": order.get("parcel_content", "General items")
        })

    try:
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(gdex_url, json=payload, headers=headers)
        data = response.json()
        if data.get("IsSuccess") == True:
            return JSONResponse({"status": "success", "data": data})
        else:
            raise HTTPException(400, f"GDEX API Error: {data}")
    except Exception as e:
        raise HTTPException(500, str(e))
