import requests
import time
import json
import os

CLIENT_ID = "32555940559.apps.googleusercontent.com"
CLIENT_SECRET = "ZmssLNjJy2998hD4CTg2ejr2"
SCOPE = "https://www.googleapis.com/auth/cloud-platform"

def get_device_code():
    url = "https://oauth2.googleapis.com/device/code"
    data = {
        "client_id": CLIENT_ID,
        "scope": SCOPE
    }
    response = requests.post(url, data=data)
    return response.json()

def poll_for_token(device_code, interval):
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
    }
    
    print("\nMenunggu kelulusan dari bos...")
    while True:
        time.sleep(interval)
        response = requests.post(url, data=data)
        result = response.json()
        
        if "access_token" in result:
            print("Login berjaya!")
            return result["access_token"]
        elif result.get("error") == "authorization_pending":
            continue
        elif result.get("error") == "slow_down":
            interval += 2
            continue
        else:
            print("Ralat:", result)
            return None

def update_cloud_run(access_token):
    # GCP Project ID: ryo-assistant-492506
    # Region: asia-southeast1
    # Service: evolution-api
    
    project_id = "ryo-assistant-492506"
    region = "asia-southeast1"
    service_id = "evolution-api"
    
    url = f"https://run.googleapis.com/v2/projects/{project_id}/locations/{region}/services/{service_id}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 1. Fetch current service state to get the current env vars
    print("\nFetching current server configuration...")
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(f"Failed to fetch service: {res.text}")
        return
        
    service = res.json()
    
    # 2. Extract current env vars and append the new ones
    current_env = service.get("template", {}).get("containers", [{}])[0].get("env", [])
    
    new_vars = {
        "DATABASE_ENABLED": "true",
        "DATABASE_CONNECTION_URI": "postgresql://postgres.nrvsbggjlbvnhpxsahcg:JGY%26v78n%40gH%2CQ8p@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres",
        "DATABASE_CONNECTION_CLIENT_NAME": "evolution_api",
        "DATABASE_SAVE_DATA_INSTANCE": "true"
    }
    
    # Update existing or append new
    updated_env = []
    seen = set()
    for env_var in current_env:
        name = env_var["name"]
        if name in new_vars:
            updated_env.append({"name": name, "value": new_vars[name]})
            seen.add(name)
        else:
            updated_env.append(env_var)
            
    for name, value in new_vars.items():
        if name not in seen:
            updated_env.append({"name": name, "value": value})
            
    # 3. Patch the service with new env vars
    print("Injecting Supabase keys into Google Cloud Run...")
    patch_data = {
        "template": {
            "containers": [
                {
                    "env": updated_env
                }
            ]
        }
    }
    
    patch_url = f"{url}?updateMask=template.containers"
    patch_res = requests.patch(patch_url, headers=headers, json=patch_data)
    
    if patch_res.status_code == 200:
        print("SUCCESS! The WhatsApp server is now restarting and linking to Supabase permanently.")
    else:
        print(f"Update failed: {patch_res.text}")

if __name__ == "__main__":
    device_info = get_device_code()
    print("==================================================")
    print("!!! KEBENARAN DIPERLUKAN (GOOGLE CLOUD SECURE LINK) !!!")
    print("==================================================")
    print(f"Sila layari pautan ini di browser: {device_info['verification_url']}")
    print(f"Dan masukkan kod rahsia ini: {device_info['user_code']}")
    print("==================================================")
    
    token = poll_for_token(device_info['device_code'], device_info['interval'])
    if token:
        update_cloud_run(token)
