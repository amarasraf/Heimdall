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
        print(f"[ERROR] save_parse_result: {e}")

def get_user_profile(user_id: str):
    if not supabase:
        return None
    try:
        response = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"[ERROR] get_user_profile: {e}")
        return None

def extend_subscription(user_id: str, days: int = 30):
    if not supabase:
        return False
    try:
        profile = get_user_profile(user_id)
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if profile and profile.get('subscription_end_date'):
            current_end = datetime.datetime.fromisoformat(profile['subscription_end_date'].replace('Z', '+00:00'))
            base_date = current_end if current_end > now else now
        else:
            base_date = now
            
        new_end = base_date + datetime.timedelta(days=days)
        
        supabase.table("user_profiles").upsert({
            "user_id": user_id,
            "subscription_end_date": new_end.isoformat()
        }).execute()
        return True
    except Exception as e:
        print(f"[ERROR] extend_subscription: {e}")
        return False

def save_user_keys(user_id: str, keys: dict):
    if not supabase:
        return False
    try:
        supabase.table("user_profiles").upsert({
            "user_id": user_id,
            "courier_keys": keys
        }).execute()
        return True
    except Exception as e:
        print(f"[ERROR] save_user_keys: {e}")
        return False

def get_user_keys(user_id: str):
    profile = get_user_profile(user_id)
    if profile and profile.get("courier_keys"):
        return profile["courier_keys"]
    return {}
