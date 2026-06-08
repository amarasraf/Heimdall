import os
import psycopg2
from dotenv import load_dotenv
from database import get_user_profile
from main import check_subscription

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()
cursor.execute("SELECT id FROM auth.users WHERE email = 'amarasraf@gmail.com'")
row = cursor.fetchone()
if row:
    user_id = row[0]
    print(f"User ID: {user_id}")
    profile = get_user_profile(user_id)
    print(f"Profile: {profile}")
    try:
        check_subscription(user_id)
        print("Subscription check PASSED!")
    except Exception as e:
        print(f"Subscription check FAILED: {e}")
else:
    print("User not found.")
