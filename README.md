# Malaysian Address Parser — WhatsApp-to-Courier CSV Converter

A Micro-SaaS that converts messy WhatsApp/order messages into clean courier-ready CSV files for EasyParcel and other logistics providers.

## How to Use

1. Install Python dependencies:
   ```
   pip install pandas fastapi uvicorn python-multipart
   ```

2. Run the parser script:
   ```
   python test_parser.py
   ```

3. Or start the web API:
   ```
   uvicorn api:app --reload
   ```
   Then go to http://localhost:8000/docs to test it.

## Files

- `test_parser.py` — Standalone script to test parsing on sample data
- `api.py` — FastAPI web app with CSV upload endpoint
- `samples.csv` — Sample messy WhatsApp orders to test with
