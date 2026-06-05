"""
Malaysian Address Parser — Test Script v2
Converts messy WhatsApp/order text into structured format for courier upload.

Usage: python test_parser.py
"""

import re
import sys
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# ─── SAMPLE DATA ───────────────────────────────────────────────
raw_orders = [
    {"raw_text": "Amar Mustapha, 0171234567, No 45 Jalan Bukit, Taman Desa, 43700 Beranang, Selangor"},
    {"raw_text": "Siti Aminah 60198887766 No 12 Lorong 4, Taman Idaman, Seremban 70300 Negeri Sembilan"},
    {"raw_text": "Kak Long | 0198765432 | No 8, Jalan SS15/4, Subang Jaya, 47500 Selangor"},
    {"raw_text": "Rajesh 016-5551234, 22 Jalan Meranti, Taman Mutiara, Johor Bahru, 81300 Johor"},
    {"raw_text": "Mei Ling, 0123456789, 15-3A Jalan Ampang, KL, 50450 WP Kuala Lumpur"},
    {"raw_text": "Encik Zul 011-22334455 Lot 1234, Kampung Tekek, Pulau Tioman, 26800 Pahang"},
    {"raw_text": "Fatimah 018-9876543 No 2 Jalan Dato Sagor, Ipoh Garden, 31400 Perak"},
    {"raw_text": "Zhang Wei 017-888 9999, 12-1 Jalan 2/3B, Bandar Baru Bangi, 43650 Selangor"},
    {"raw_text": "Mohan 012-345 2244, No 12 Jalan Tembaga, Taman Skudai Baru, 81200 Johor"},
]

STATE_MAP = {
    "johor": "Johor",
    "kedah": "Kedah",
    "kelantan": "Kelantan",
    "melaka": "Melaka",
    "malacca": "Melaka",
    "negeri sembilan": "Negeri Sembilan",
    "ns": "Negeri Sembilan",
    "n9": "Negeri Sembilan",
    "pahang": "Pahang",
    "penang": "Pulau Pinang",
    "pulau pinang": "Pulau Pinang",
    "perak": "Perak",
    "perlis": "Perlis",
    "sabah": "Sabah",
    "sarawak": "Sarawak",
    "selangor": "Selangor",
    "kl": "WP Kuala Lumpur",
    "kuala lumpur": "WP Kuala Lumpur",
    "terengganu": "Terengganu",
    "wp kuala lumpur": "WP Kuala Lumpur",
    "w.p. kuala lumpur": "WP Kuala Lumpur",
    "wp labuan": "WP Labuan",
    "wp putrajaya": "WP Putrajaya",
    "putrajaya": "WP Putrajaya",
}


def parse_address(text):
    """Parse messy Malaysian address into structured fields."""
    original = text.strip()

    name = ""
    phone = ""
    street = ""
    city = ""
    postcode = ""
    state = ""

    # Step 1: Extract phone
    phone_patterns = [
        r'(6?01[0-9])[\s-]?[\s-]?(\d{7,8})',
        r'(6?01[0-9][\s-]?\s?\d{7,8})',
        r'(01[0-9][- ]\d{3,4}[- ]\d{4,5})',
        r'(6?01[0-9][- ]?\d{3,4}[- ]?\d{3,4})',
    ]
    for pat in phone_patterns:
        m = re.search(pat, original)
        if m:
            raw_phone = m.group(0).replace(" ", "").replace("-", "")
            # Only valid Malaysian phone lengths
            if len(raw_phone) in (9, 10, 11, 12):
                phone = raw_phone
                original = original.replace(m.group(0), "", 1)
                break

    # Step 2: Extract postcode
    pc_match = re.search(r'\b(\d{5})\b', original)
    if pc_match:
        postcode = pc_match.group(1)
        original = original.replace(pc_match.group(0), "", 1)

    # Step 3: Detect state from remaining text
    original_for_state = re.sub(r'[,\|]', ' ', original)
    original_for_state = re.sub(r'\s+', ' ', original_for_state).strip()
    words = original_for_state.split()

    state_found = False
    for i in range(len(words) - 1, -1, -1):
        for j in range(max(0, i - 2), i + 1):
            chunk = " ".join(words[j:i+1]).strip().lower()
            if chunk in STATE_MAP:
                state = STATE_MAP[chunk]
                # Remove state words
                original = original.replace(" ".join(words[j:i+1]), "", 1)
                state_found = True
                break
        if state_found:
            break

    # Step 4: Split what's left
    # Clean up: replace | with comma, normalize spaces
    # Clean up: remove stray dashes from phone extraction, normalize
    original = re.sub(r'\s*\|\s*', ', ', original)
    original = re.sub(r'\s+', ' ', original).strip().strip(',').strip()
    # Strip trailing artifacts like lone digits or dashes from phone extraction
    original = re.sub(r'\s+\d{1,2}$', '', original)  # trailing single/double digit artifacts

    parts = [p.strip() for p in re.split(r',', original) if p.strip()]

    if parts:
        # First part is name
        name = parts[0]
        # Everything after is address
        if len(parts) > 1:
            street = ", ".join(parts[1:]).strip()

    return {
        "recipient_name": name,
        "phone": phone,
        "street": street,
        "city": city,
        "postcode": postcode,
        "state": state,
    }


def to_easyparcel(parsed):
    """Map to EasyParcel bulk upload columns."""
    return {
        "recipient_name": parsed["recipient_name"],
        "recipient_phone": parsed["phone"],
        "recipient_address": parsed["street"],
        "recipient_postcode": parsed["postcode"],
        "recipient_city": parsed["city"],
        "recipient_state": parsed["state"],
        "parcel_content": "General merchandise",
        "parcel_value_rm": "100",
        "weight_kg": "0.5",
        "quantity": "1",
    }


# ─── MAIN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  MALAYSIAN ADDRESS PARSER v2 — TEST RUN")
    print("=" * 60)

    results = []
    for order in raw_orders:
        parsed = parse_address(order["raw_text"])
        row = to_easyparcel(parsed)
        results.append(row)

        print(f"\n{'─' * 60}")
        print(f"  INPUT:   {order['raw_text']}")
        print(f"{'─' * 60}")
        print(f"  Name:     {parsed['recipient_name']}")
        print(f"  Phone:    {parsed['phone']}")
        print(f"  Street:   {parsed['street']}")
        print(f"  Postcode: {parsed['postcode']}")
        print(f"  State:    {parsed['state']}")
        print(f"  {'✓' if all([parsed['recipient_name'], parsed['phone'], parsed['postcode'], parsed['state']]) else '✗'} Parsed")

    df = pd.DataFrame(results)
    csv_path = "easyparcel_output.csv"
    df.to_csv(csv_path, index=False)

    success = sum(1 for r in results if r["recipient_name"] and r["recipient_phone"] and r["recipient_postcode"] and r["recipient_state"])
    print(f"\n{'=' * 60}")
    print(f"  ✅ EXPORTED: {csv_path}")
    print(f"  ✅ {success}/{len(results)} addresses fully parsed")
    print(f"  📁 Open in Excel or upload to EasyParcel")
    print(f"{'=' * 60}")
