import requests
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import json
import os
from dotenv import load_dotenv

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

def inspect_and_update(access_token):
    project_id = "ryo-assistant-492506"
    region = "asia-southeast1"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    services = ["heimdall", "evolution-api"]
    
    for service_id in services:
        print(f"\n==========================================")
        print(f"Checking GCP Service: {service_id}")
        print(f"==========================================")
        url = f"https://run.googleapis.com/v2/projects/{project_id}/locations/{region}/services/{service_id}"
        
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            print(f"Failed to fetch service {service_id}: {res.text}")
            continue
            
        service = res.json()
        containers = service.get("template", {}).get("containers", [{}])
        current_env = containers[0].get("env", [])
        
        print("Current Env Variables:")
        for env_var in current_env:
            # Mask sensitive info but print key names
            name = env_var.get("name")
            val = env_var.get("value", "")
            masked_val = val[:5] + "..." if len(val) > 8 else val
            print(f"  - {name}: {masked_val}")
            
        # If the service is 'heimdall', check if GEMINI_API_KEY is present
        if service_id == "heimdall":
            # We want to make sure GEMINI_API_KEY is set to the local GEMINI_API_KEY if possible
            load_dotenv(override=True)
            local_key = os.environ.get("GEMINI_API_KEY", "").strip()
            print(f"\nLocal GEMINI_API_KEY found: {repr(local_key)}")
            
            # Let's check if the service already has a GEMINI_API_KEY and if it's set
            has_gemini = any(e.get("name") == "GEMINI_API_KEY" for e in current_env)
            
            # We will ask the user or update it
            new_vars = {
                "GEMINI_API_KEY": local_key
            }
            
            # Update env
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
                    
            current_image = containers[0].get("image")
            patch_data = {
                "template": {
                    "containers": [
                        {
                            "image": current_image,
                            "env": updated_env
                        }
                    ]
                }
            }
            
            print(f"Updating heimdall environment variables with GEMINI_API_KEY...")
            patch_url = f"{url}?updateMask=template.containers"
            patch_res = requests.patch(patch_url, headers=headers, json=patch_data)
            
            if patch_res.status_code == 200:
                print("SUCCESS! Heimdall service env variables updated successfully.")
            else:
                print(f"Update failed for heimdall: {patch_res.text}")

if __name__ == "__main__":
    auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&scope={urllib.parse.quote(SCOPE)}&access_type=offline"
    
    print("\n==================================================")
    print("!!! GCP AUTHORIZATION REQUIRED !!!")
    print("==================================================")
    print(f"Click the link to login to Google Cloud:\n")
    print(auth_url)
    print("\nWaiting for browser login...")
    
    run_auth_server()
    
    if auth_code:
        print("\nToken received! Fetching GCP service data...")
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
            inspect_and_update(token_data["access_token"])
        else:
            print("Failed to get token:", token_data)
