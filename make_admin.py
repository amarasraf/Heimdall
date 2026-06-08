import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    
    query = """
    UPDATE public.user_profiles 
    SET subscription_end_date = '2099-12-31 23:59:59+00' 
    WHERE user_id IN (SELECT id FROM auth.users WHERE email = 'amarasraf@gmail.com');
    """
    
    cursor.execute(query)
    
    if cursor.rowcount > 0:
        print("Successfully updated subscription for amarasraf@gmail.com!")
    else:
        print("User amarasraf@gmail.com not found in the database. Are they registered?")
        
    conn.close()
except Exception as e:
    print('Error:', e)
