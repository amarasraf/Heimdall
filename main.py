from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Security
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import pandas as pd
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()

from parser_core import parse_address, parse_easyparcel_row, to_easyparcel
from database import save_parse_result, supabase

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
    if re.search(r'(Nama penerima\s*:|Alamat penerima\s*:)', text, re.IGNORECASE):
        parsed = parse_easyparcel_row({"recipient_name": text})
    else:
        parsed = [parse_address(text)]
        
    save_parse_result("single", text, parsed, user.id)
    return parsed

@app.post("/parse")
async def parse_text(req: ParseRequest, user=Depends(get_current_user)):
    text = req.text
    if re.search(r'(Nama penerima\s*:|Alamat penerima\s*:)', text, re.IGNORECASE):
        parsed = parse_easyparcel_row({"recipient_name": text})
    else:
        parsed = [parse_address(text)]
        
    save_parse_result("single", text, parsed, user.id)
    return parsed


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...), user=Depends(get_current_user)):
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
