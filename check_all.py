import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT email FROM auth.users
    """)
    users = cursor.fetchall()
    print("ALL USERS:", users)
    conn.close()
except Exception as e:
    print('Error:', e)
