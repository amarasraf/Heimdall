import requests
import socket
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

CLIENT_ID = "32555940559.apps.googleusercontent.com"
CLIENT_SECRET = "ZmssLNjJy2998hD4CTg2ejr2"
SCOPE = "https://www.googleapis.com/auth/cloud-platform"
REDIRECT_URI = "http://localhost:8085/"

auth_code = None

class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        
        if 'code' in query:
            auth_code = query['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Berjaya! Anda boleh tutup tab ini sekarang.</h1><p>Bebbi sedang menyambung ke pelayan...</p><script>window.close()</script></body></html>")
            
            # Kill the server
            threading.Thread(target=self.server.shutdown).start()
        else:
            self.send_response(400)
            self.end_headers()

def run_auth_server():
    server = HTTPServer(('localhost', 8085), AuthHandler)
    server.serve_forever()

def update_cloud_run(access_token):
    project_id = "ryo-assistant-492506"
    region = "asia-southeast1"
    service_id = "evolution-api"
    url = f"https://run.googleapis.com/v2/projects/{project_id}/locations/{region}/services/{service_id}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print("\n[AI] Mengambil konfigurasi pelayan semasa...")
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(f"Failed to fetch service: {res.text}")
        return
        
    service = res.json()
    current_env = service.get("template", {}).get("containers", [{}])[0].get("env", [])
    
    new_vars = {
        "DATABASE_ENABLED": "true",
        "DATABASE_CONNECTION_URI": "postgresql://postgres.nrvsbggjlbvnhpxsahcg:JGY%26v78n%40gH%2CQ8p@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres",
        "DATABASE_CONNECTION_CLIENT_NAME": "evolution_api"
    }
    
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
            
    patch_data = {
        "template": {
            "containers": [
                {
                    "env": updated_env
                }
            ]
        }
    }
    
    print("[AI] Menulis tetapan Supabase ke dalam Google Cloud...")
    patch_url = f"{url}?updateMask=template.containers"
    patch_res = requests.patch(patch_url, headers=headers, json=patch_data)
    
    if patch_res.status_code == 200:
        print("\n[AI] \u2705 SUCCESS! WhatsApp server is restarting and officially connected to Supabase.")
    else:
        print(f"\n[AI] Update failed: {patch_res.text}")

if __name__ == "__main__":
    auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&scope={urllib.parse.quote(SCOPE)}&access_type=offline"
    
    print("\n==================================================")
    print("!!! KEBENARAN DIPERLUKAN UNTUK SAYA BANTU ANDA !!!")
    print("==================================================")
    print(f"Sila layari pautan ini untuk memberikan saya akses:\n")
    print(auth_url)
    print("\nMenunggu kelulusan dari browser anda...")
    
    run_auth_server()
    
    if auth_code:
        print("\n[AI] Kod diterima! Mendapatkan token pelayan...")
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": auth_code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        res = requests.post(token_url, data=data)
        token_data = res.json()
        
        if "access_token" in token_data:
            update_cloud_run(token_data["access_token"])
        else:
            print("Gagal dapatkan token:", token_data)
