from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import io
import re
import csv
import os

app = FastAPI(title="AlamatPintar", description="Malaysian Address Parser for EasyParcel")

# ─── State map ───
STATE_MAP = {
    "johor": "Johor",
    "kedah": "Kedah",
    "kelantan": "Kelantan",
    "melaka": "Melaka",
    "malacca": "Melaka",
    "negeri sembilan": "Negeri Sembilan",
    "ns": "Negeri Sembilan",
    "n9": "Negeri Sembilan",
    "pahang": "Pahang",
    "penang": "Pulau Pinang",
    "pulau pinang": "Pulau Pinang",
    "perak": "Perak",
    "perlis": "Perlis",
    "sabah": "Sabah",
    "sarawak": "Sarawak",
    "selangor": "Selangor",
    "kl": "WP Kuala Lumpur",
    "kuala lumpur": "WP Kuala Lumpur",
    "terengganu": "Terengganu",
    "wp kuala lumpur": "WP Kuala Lumpur",
    "w.p. kuala lumpur": "WP Kuala Lumpur",
    "wp labuan": "WP Labuan",
    "wp putrajaya": "WP Putrajaya",
    "putrajaya": "WP Putrajaya",
}


def parse_address(text):
    """Parse messy Malaysian address into structured fields."""
    original = text.strip()
    name = phone = street = city = postcode = state = ""

    # Step 1: Extract phone
    phone_patterns = [
        r'(6?01[0-9])[\s-]?[\s-]?(\d{7,8})',
        r'(6?01[0-9][\s-]?\s?\d{7,8})',
        r'(01[0-9][- ]\d{3,4}[- ]\d{4,5})',
        r'(6?01[0-9][- ]?\d{3,4}[- ]?\d{3,4})',
    ]
    for pat in phone_patterns:
        m = re.search(pat, original)
        if m:
            raw_phone = m.group(0).replace(" ", "").replace("-", "")
            if len(raw_phone) in (9, 10, 11, 12):
                phone = raw_phone
                original = original.replace(m.group(0), "", 1)
                break

    # Step 2: Postcode
    pc_match = re.search(r'\b(\d{5})\b', original)
    if pc_match:
        postcode = pc_match.group(1)
        original = original.replace(pc_match.group(0), "", 1)

    # Step 3: State
    orig_for_state = re.sub(r'[,\|]', ' ', original)
    orig_for_state = re.sub(r'\s+', ' ', orig_for_state).strip()
    words = orig_for_state.split()
    state_found = False
    for i in range(len(words) - 1, -1, -1):
        for j in range(max(0, i - 2), i + 1):
            chunk = " ".join(words[j:i+1]).strip().lower()
            if chunk in STATE_MAP:
                state = STATE_MAP[chunk]
                original = original.replace(" ".join(words[j:i+1]), "", 1)
                state_found = True
                break
        if state_found:
            break

    # Step 4: Split name / street
    original = re.sub(r'\s*\|\s*', ', ', original)
    original = re.sub(r'\s+', ' ', original).strip().strip(',').strip()
    original = re.sub(r'\s+\d{1,2}$', '', original)
    parts = [p.strip() for p in re.split(r',', original) if p.strip()]
    if parts:
        name = parts[0]
        street = ", ".join(parts[1:]).strip() if len(parts) > 1 else ""

    return {
        "recipient_name": name,
        "phone": phone,
        "street": street,
        "city": city,
        "postcode": postcode,
        "state": state,
    }


# ─── Routes ───

@app.get("/", response_class=HTMLResponse)
async def index():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/parse")
async def parse_single(text: str):
    """Parse one messy address string."""
    return parse_address(text)


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Upload CSV with 'raw_text' column. Returns parsed JSON + download link."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files allowed")

    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))

    if 'raw_text' not in df.columns:
        raise HTTPException(400, "CSV must have a 'raw_text' column")

    results = []
    for _, row in df.iterrows():
        parsed = parse_address(str(row['raw_text']))
        results.append(parsed)

    return JSONResponse({
        "results": len(results),
        "data": results,
    })
