import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
conn.autocommit = True
cursor = conn.cursor()
try:
    cursor.execute('CREATE POLICY "Allow all" ON public.user_profiles FOR ALL USING (true) WITH CHECK (true);')
    print("Policy created.")
except Exception as e:
    print("Error:", e)
