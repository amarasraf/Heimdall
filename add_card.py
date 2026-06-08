import re

file_path = 'templates/index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

new_card = """
      <div style="background: white; padding: 30px; border-radius: 20px; flex: 1; min-width: 250px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div style="font-size: 3rem; margin-bottom: 15px;">💸</div>
        <h3 style="color: #1e293b; margin-bottom: 10px;">Lebih Jimat & Bebas!</h3>
        <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.5;">Takde akaun VIP courier? Takpe! Terus dapat harga borong paling murah & bebas pilih kurier (J&T, NinjaVan, PosLaju).</p>
      </div>
"""

# Insert the new card before the closing div of the flex container
target_str = """      <div style="background: white; padding: 30px; border-radius: 20px; flex: 1; min-width: 250px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div style="font-size: 3rem; margin-bottom: 15px;">💰</div>
        <h3 style="color: #1e293b; margin-bottom: 10px;">Jimat Masa & Tenaga</h3>
        <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.5;">Siapkan 100 order dalam masa 5 minit. Boleh fokus layan customer lain pula.</p>
      </div>"""

if target_str in html:
    html = html.replace(target_str, target_str + new_card)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print("New card added!")
else:
    print("Target string not found!")
