import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.email, p.subscription_end_date 
        FROM auth.users u
        LEFT JOIN public.user_profiles p ON u.id = p.user_id
        WHERE u.email = 'amarasraf@gmail.com'
    """)
    result = cursor.fetchone()
    print("Database Check Result:", result)
    conn.close()
except Exception as e:
    print('Error:', e)
