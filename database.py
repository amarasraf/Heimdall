import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != "your-supabase-url-here":
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[OK] Connected to Supabase!")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Supabase client: {e}")
else:
    print("[WARNING] Supabase credentials not configured in .env. History will not be saved.")

def save_parse_result(source: str, input_text: str, result: dict | list, user_id: str = None):
    if not supabase:
        return
        
    try:
        data = {
            "source": source,
            "input_text": input_text,
            "result_json": result,
            "user_id": user_id
        }
        supabase.table("parse_history").insert(data).execute()
    except Exception as e:
        print(f"[ERROR] Supabase DB Insert Error: {e}")
