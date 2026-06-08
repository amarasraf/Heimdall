import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS courier_keys JSONB DEFAULT '{}'::jsonb;")
    print('Migration successful!')
    conn.close()
except Exception as e:
    print('Error:', e)
