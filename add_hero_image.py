import re

file_path = 'templates/index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Current HTML for the landing header:
old_header = """<div style="background: white; border-radius: 24px; padding: 50px 30px; box-shadow: 0 10px 40px -10px rgba(236, 72, 153, 0.2); margin-bottom: 40px;">
      <h2 style="font-size: 2.5rem; color: #be185d; margin-bottom: 20px; font-weight: 800; line-height: 1.2;">Penat Salin Alamat Customer<br>Tiap-Tiap Hari?</h2>
      <p style="font-size: 1.2rem; color: var(--text-muted); margin-bottom: 35px; max-width: 600px; margin-left: auto; margin-right: auto; line-height: 1.6;">
        Biar <strong>Heimdall</strong> tolong. Copy mesej WhatsApp customer, Heimdall akan susun alamat cantik-cantik & terus hantar ke EasyParcel. Siap dalam 2 saat. Tinggal print je!
      </p>
      <button class="btn" style="font-size: 1.3rem; padding: 18px 40px; box-shadow: 0 8px 25px rgba(236, 72, 153, 0.4);" onclick="showAuth()">🚀 Jom Mula Sekarang!</button>
    </div>"""

new_header = """<div style="background: white; border-radius: 24px; padding: 50px 30px; box-shadow: 0 10px 40px -10px rgba(236, 72, 153, 0.2); margin-bottom: 40px; display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 40px;">
      <div style="flex: 1; min-width: 300px; text-align: left;">
        <h2 style="font-size: 2.5rem; color: #be185d; margin-bottom: 20px; font-weight: 800; line-height: 1.2;">Penat Salin Alamat Customer<br>Tiap-Tiap Hari?</h2>
        <p style="font-size: 1.2rem; color: var(--text-muted); margin-bottom: 35px; max-width: 600px; line-height: 1.6;">
          Biar <strong>Heimdall</strong> tolong. Copy mesej WhatsApp customer, Heimdall akan susun alamat cantik-cantik & terus hantar ke EasyParcel. Siap dalam 2 saat. Tinggal print je!
        </p>
        <button class="btn" style="font-size: 1.3rem; padding: 18px 40px; box-shadow: 0 8px 25px rgba(236, 72, 153, 0.4);" onclick="showAuth()">🚀 Jom Mula Sekarang!</button>
      </div>
      <div style="flex: 1; min-width: 300px; display: flex; justify-content: center;">
        <img src="/static/hero.png" alt="Heimdall Fast Delivery" style="max-width: 100%; height: auto; border-radius: 20px; box-shadow: 0 15px 35px rgba(236,72,153,0.15); transform: rotate(2deg); transition: transform 0.3s ease;" onmouseover="this.style.transform='rotate(0deg) scale(1.02)'" onmouseout="this.style.transform='rotate(2deg) scale(1)'">
      </div>
    </div>"""

if old_header in html:
    html = html.replace(old_header, new_header)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print("Hero image injected!")
else:
    print("Header not found. Injection failed.")
