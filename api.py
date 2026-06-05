from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import io
import re
import csv
import os

from parser_core import parse_address, parse_easyparcel_row, to_easyparcel

app = FastAPI(title="AlamatPintar", description="Malaysian Address Parser for EasyParcel")


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
    """Upload CSV with 'raw_text' or EasyParcel columns. Returns parsed JSON."""
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

    return JSONResponse({
        "results": len(results),
        "data": results,
    })
