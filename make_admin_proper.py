import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Check if they have a profile
    cursor.execute("SELECT id FROM auth.users WHERE email = 'amarasraf@gmail.com'")
    user_id = cursor.fetchone()
    if user_id:
        uid = user_id[0]
        # Insert or update
        query = f"""
        INSERT INTO public.user_profiles (user_id, subscription_end_date) 
        VALUES ('{uid}', '2099-12-31 23:59:59+00')
        ON CONFLICT (user_id) DO UPDATE SET subscription_end_date = '2099-12-31 23:59:59+00';
        """
        cursor.execute(query)
        print("Successfully made amarasraf@gmail.com an admin (sub valid until 2099)!")
    else:
        print("User not found.")
        
    conn.close()
except Exception as e:
    print('Error:', e)
