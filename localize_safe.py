import os

file_path = 'templates/index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    'WhatsApp order -> Courier-ready CSV': 'Copy-paste mesej order WhatsApp ➔ Terus jadi slip pos',
    'For EasyParcel': 'Khas untuk seller',
    'Unlimited Parsing Locked': 'Alamak, Pas Heimdall Dah Tamat Tempoh! 🔒',
    'Your subscription has expired. Purchase a 30-Day Unlimited Pass via ToyyibPay (DuitNow QR or FPX) to unlock instant address parsing again.': 'Pas anda dah expired. Langgan Pas 30-Hari via DuitNow QR/FPX untuk terus guna Heimdall tanpa had.',
    'Buy 30-Day Pass (RM 30)': 'Beli Pas 30 Hari (RM 30 je)',
    'Welcome! Please Sign In': 'Jom Masuk! Login Dulu',
    'placeholder="Email Address"': 'placeholder="Alamat Emel"',
    'placeholder="Password"': 'placeholder="Kata Laluan"',
    '>Login<': '>Masuk<',
    '>Sign Up (New Account)<': '>Daftar Akaun Baru<',
    '⚙️ Configuration & API Keys': '⚙️ Setting Akaun',
    'Heimdall allows you to connect your own courier accounts. Enter your API keys below.': 'Masukkan API Key EasyParcel anda kat bawah ni.',
    'We only use EasyParcel now for maximum user friendliness': 'Sekarang kita guna EasyParcel je supaya senang kerja!',
    '>Save Settings<': '>Simpan Setting<',
    '>Parse Address Text (Auto-Detect)<': '>Susun Alamat Dari Teks<',
    'placeholder="Paste a messy address or multiple recipients here..."': 'placeholder="Paste mesej WhatsApp pelanggan kat sini..."',
    '>Parse Address<': '>Susun Alamat<',
    '>Clear<': '>Padam<',
    '>Bulk Upload (CSV)<': '>Upload Pukal (CSV/Excel)<',
    'Upload any CSV — <code>raw_text</code> (one address per row), <strong>EasyParcel export</strong> (with recipient columns),': 'Boleh upload fail Excel/CSV biasa, atau fail yang pelanggan hantar.',
    'or even files with multiple recipients crammed into one row.': 'Heimdall akan automatik susun semua.',
    '>📄 Choose CSV File<': '>📄 Pilih Fail Excel/CSV<',
    '>📊 Results<': '>📊 Hasil Carian<',
    '>🚀 Push to EasyParcel<': '>🚀 Hantar ke EasyParcel<',
    '>⬇ CSV<': '>⬇ Download Excel<',
    '<th>Name</th>': '<th>Nama</th>',
    '<th>Phone</th>': '<th>No Telefon</th>',
    '<th>Address</th>': '<th>Alamat</th>',
    '<th>Postcode</th>': '<th>Poskod</th>',
    '<th>State</th>': '<th>Negeri</th>'
}

for eng, bm in replacements.items():
    content = content.replace(eng, bm)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Localization complete safely!")
