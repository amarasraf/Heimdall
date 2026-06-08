import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()
cursor.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'user_profiles'")
row = cursor.fetchone()
print(f"RLS Enabled: {row[0]}")
