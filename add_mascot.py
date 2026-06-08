import re

file_path = 'templates/index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Current HTML for the Heimdall header
old_header = """<div class="header">
    <h1 style="cursor: pointer;" onclick="if(!currentSession) { document.getElementById('auth-section').classList.add('hidden'); document.getElementById('landing-section').classList.remove('hidden'); }"><span class="emoji-icon">📦</span> Heimdall Ekspres</h1>"""

new_header = """<div class="header">
    <h1 style="cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 15px;" onclick="if(!currentSession) { document.getElementById('auth-section').classList.add('hidden'); document.getElementById('landing-section').classList.remove('hidden'); }">
        <img src="/static/mascot.png" alt="Heimdall Cat Mascot" style="height: 60px; width: 60px; border-radius: 50%; box-shadow: 0 4px 10px rgba(236,72,153,0.3); object-fit: cover;">
        Heimdall Ekspres
    </h1>"""

if old_header in html:
    html = html.replace(old_header, new_header)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print("Mascot injected into header!")
else:
    print("Header not found. Injection failed.")
