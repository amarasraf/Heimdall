import urllib.request

try:
    with urllib.request.urlopen("https://heimdall-517339133458.asia-southeast1.run.app/") as response:
        html = response.read().decode()
        if "Settings" in html and "Ninja Van" in html:
            print("DEPLOYED_SUCCESSFULLY")
        else:
            print("OLD_VERSION")
except Exception as e:
    print("Error:", e)
