import os

file_path = 'templates/index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    # Headers & Intro
    'WhatsApp order -> Courier-ready CSV': 'Copy-paste order WhatsApp ➔ Terus jadi slip pos',
    'For EasyParcel': 'Untuk EasyParcel',
    'Paste your WhatsApp orders here...': 'Paste mesej order WhatsApp customer kat sini...',
    'Upload any CSV': 'Upload fail Excel/CSV',
    'one address per row': 'satu alamat sebaris',
    'or even files with multiple recipients crammed into one row': 'atau yang berselerak, Heimdall boleh susun!',
    
    # Sub Section
    'Unlimited Parsing Locked': 'Alamak, Pas Dah Expired! 🔒',
    'Your subscription has expired. Purchase a 30-Day Unlimited Pass via ToyyibPay (DuitNow QR or FPX) to unlock instant address parsing again.': 'Pas Heimdall anda dah tamat tempoh. Langgan Pas 30-Hari via DuitNow QR/FPX untuk terus guna Heimdall tanpa had.',
    'Buy 30-Day Pass': 'Beli Pas 30 Hari',
    
    # Auth
    'Welcome! Please Sign In': 'Jom Masuk! Login Dulu',
    'Email Address': 'Alamat Emel',
    'Password': 'Kata Laluan',
    '>Login<': '>Masuk<',
    'Sign Up (New Account)': 'Daftar Akaun Baru',
    
    # Settings
    'Configuration & API Keys': 'Setting Akaun (API EasyParcel)',
    'Heimdall allows you to connect your own courier accounts. Enter your API keys below.': 'Masukkan API Key EasyParcel anda kat bawah ni. Takde key? Klik "Cara nak dapatkan?".',
    'We only use EasyParcel now for maximum user friendliness': 'Sekarang kita guna EasyParcel je supaya senang kerja makcik!',
    'How to get this?': 'Cara nak dapatkan API Key ni?',
    'Log into EasyParcel': 'Login masuk website EasyParcel',
    'Go to Integrations > API': 'Pergi ke bahagian Integrations > API',
    'Generate a new API Key and copy it here.': 'Buat API Key baru dan copy-paste kat sini.',
    'Save Settings': 'Simpan Setting',
    
    # Main Dashboard
    'Parse Addresses': '✨ Susun Alamat Automatik',
    'Clear': 'Padam',
    'Choose CSV File': '📄 Pilih Fail Excel/CSV',
    
    # Results
    'Results': 'Hasil Susunan',
    'Push to EasyParcel': '🚀 Hantar ke EasyParcel',
    'Download CSV': '⬇ Download Excel',
    'Name': 'Nama',
    'Phone': 'No. Telefon',
    'Address': 'Alamat',
    'Postcode': 'Poskod',
    'State': 'Negeri',
    
    # Menu
    'VIP Pass Active': 'Pas VIP Aktif',
    'Sign Out': 'Keluar'
}

for eng, bm in replacements.items():
    content = content.replace(eng, bm)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Localization complete!")
