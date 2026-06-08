import asyncio
from database import get_user_profile
from main import supabase

async def test():
    response = supabase.auth.admin.list_users()
    admin_id = None
    for u in response:
        if u.email == 'amarasraf@gmail.com':
            admin_id = u.id
            break
            
    if not admin_id:
        print("Admin user not found in auth.users")
        return
        
    print(f"Admin ID: {admin_id}")
    profile = get_user_profile(admin_id)
    print(f"Profile: {profile}")

asyncio.run(test())
