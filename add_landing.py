import re

file_path = 'templates/index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

landing_html = """
  <!-- Landing Section -->
  <div id="landing-section" style="width: 100%; text-align: center; animation: fadeIn 0.8s ease;">
    <div style="background: white; border-radius: 24px; padding: 50px 30px; box-shadow: 0 10px 40px -10px rgba(236, 72, 153, 0.2); margin-bottom: 40px;">
      <h2 style="font-size: 2.5rem; color: #be185d; margin-bottom: 20px; font-weight: 800; line-height: 1.2;">Penat Salin Alamat Customer<br>Tiap-Tiap Hari?</h2>
      <p style="font-size: 1.2rem; color: var(--text-muted); margin-bottom: 35px; max-width: 600px; margin-left: auto; margin-right: auto; line-height: 1.6;">
        Biar <strong>Heimdall</strong> tolong. Copy mesej WhatsApp customer, Heimdall akan susun alamat cantik-cantik & terus hantar ke EasyParcel. Siap dalam 2 saat. Tinggal print je!
      </p>
      <button class="btn" style="font-size: 1.3rem; padding: 18px 40px; box-shadow: 0 8px 25px rgba(236, 72, 153, 0.4);" onclick="showAuth()">🚀 Jom Mula Sekarang!</button>
    </div>
    
    <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; margin-bottom: 40px;">
      <div style="background: white; padding: 30px; border-radius: 20px; flex: 1; min-width: 250px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div style="font-size: 3rem; margin-bottom: 15px;">✂️</div>
        <h3 style="color: #1e293b; margin-bottom: 10px;">Copy-Paste Je</h3>
        <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.5;">Tak payah pening asingkan poskod, negeri atau daerah. Heimdall buat automatik.</p>
      </div>
      <div style="background: white; padding: 30px; border-radius: 20px; flex: 1; min-width: 250px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div style="font-size: 3rem; margin-bottom: 15px;">🚀</div>
        <h3 style="color: #1e293b; margin-bottom: 10px;">Terus ke EasyParcel</h3>
        <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.5;">Tekan satu butang, 100 order terus masuk sistem EasyParcel. Memang pantas!</p>
      </div>
      <div style="background: white; padding: 30px; border-radius: 20px; flex: 1; min-width: 250px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div style="font-size: 3rem; margin-bottom: 15px;">💰</div>
        <h3 style="color: #1e293b; margin-bottom: 10px;">Jimat Masa & Tenaga</h3>
        <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.5;">Siapkan 100 order dalam masa 5 minit. Boleh fokus layan customer lain pula.</p>
      </div>
    </div>
  </div>

  <!-- Auth Section -->
  <div id="auth-section" class="card hidden">
"""

# Replace the start of auth-section
html = html.replace('<!-- Auth Section -->\n  <div id="auth-section" class="card">', landing_html)

# Add showAuth function to scripts
js_to_add = """
function showAuth() {
  document.getElementById('landing-section').classList.add('hidden');
  document.getElementById('auth-section').classList.remove('hidden');
}

supabaseClient.auth.onAuthStateChange((event, session) => {
"""

html = html.replace('supabaseClient.auth.onAuthStateChange((event, session) => {', js_to_add)

# Update auth state change logic
old_auth_logic = """    document.getElementById('auth-section').classList.remove('hidden');
    document.getElementById('app-section').classList.add('hidden');"""

new_auth_logic = """    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('landing-section').classList.remove('hidden');
    document.getElementById('app-section').classList.add('hidden');"""

html = html.replace(old_auth_logic, new_auth_logic)

# Make sure if they are logged in, landing section is hidden
old_logged_in_logic = """    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('logoutBtn').classList.remove('hidden');"""

new_logged_in_logic = """    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('landing-section').classList.add('hidden');
    document.getElementById('logoutBtn').classList.remove('hidden');"""

html = html.replace(old_logged_in_logic, new_logged_in_logic)

# Replace the Heimdall header to link back to landing if clicked
old_header = """<div class="header">
    <h1><span class="emoji-icon">⚡</span> Heimdall</h1>"""

new_header = """<div class="header">
    <h1 style="cursor: pointer;" onclick="if(!currentSession) { document.getElementById('auth-section').classList.add('hidden'); document.getElementById('landing-section').classList.remove('hidden'); }"><span class="emoji-icon">📦</span> Heimdall Ekspres</h1>"""

html = html.replace(old_header, new_header)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("Landing page injected!")
