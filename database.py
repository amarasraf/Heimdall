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

import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DB_URL:
        return None
    return psycopg2.connect(DB_URL)

def get_user_profile(user_id: str):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                # Convert datetime to ISO format string to match previous behavior
                if row.get('subscription_end_date'):
                    row['subscription_end_date'] = row['subscription_end_date'].isoformat()
                return dict(row)
            return None
    except Exception as e:
        print(f"[ERROR] get_user_profile: {e}")
        return None
    finally:
        conn.close()

def extend_subscription(user_id: str, days: int = 30):
    conn = get_db_connection()
    if not conn: return False
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
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_profiles (user_id, subscription_end_date)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                SET subscription_end_date = EXCLUDED.subscription_end_date
            """, (user_id, new_end))
            conn.commit()
        return True
    except Exception as e:
        print(f"[ERROR] extend_subscription: {e}")
        return False
    finally:
        conn.close()

def save_user_keys(user_id: str, keys: dict):
    conn = get_db_connection()
    if not conn: return False
    try:
        import json
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_profiles (user_id, courier_keys)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                SET courier_keys = EXCLUDED.courier_keys
            """, (user_id, json.dumps(keys)))
            conn.commit()
        return True
    except Exception as e:
        print(f"[ERROR] save_user_keys: {e}")
        return False
    finally:
        conn.close()

def get_user_keys(user_id: str):
    profile = get_user_profile(user_id)
    if profile and profile.get("courier_keys"):
        return profile["courier_keys"]
    return {}
