import os
import psycopg2
from dotenv import load_dotenv
from database import get_user_profile

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()
cursor.execute("SELECT id FROM auth.users WHERE email = 'amarasraf@gmail.com'")
row = cursor.fetchone()
if row:
    user_id = row[0]
    profile = get_user_profile(user_id)
    print(f"Profile via anon Supabase client: {profile}")
