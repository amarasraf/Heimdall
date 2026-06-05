"""
AlamatPintar — Core Parser Logic
Shared between main.py (FastAPI) and test scripts.
"""

import re

# ─── State map ───
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
    name = phone = street = city = postcode = state = ""

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
            if len(raw_phone) in (9, 10, 11, 12):
                phone = raw_phone
                original = original.replace(m.group(0), "", 1)
                break

    # Step 2: Postcode
    pc_match = re.search(r'\b(\d{5})\b', original)
    if pc_match:
        postcode = pc_match.group(1)
        original = original.replace(pc_match.group(0), "", 1)

    # Step 3: State
    orig_for_state = re.sub(r'[,\|]', ' ', original)
    orig_for_state = re.sub(r'\s+', ' ', orig_for_state).strip()
    words = orig_for_state.split()
    state_found = False
    for i in range(len(words) - 1, -1, -1):
        for j in range(max(0, i - 2), i + 1):
            chunk = " ".join(words[j:i+1]).strip().lower()
            if chunk in STATE_MAP:
                state = STATE_MAP[chunk]
                original = original.replace(" ".join(words[j:i+1]), "", 1)
                state_found = True
                break
        if state_found:
            break

    # Step 4: Split name / street
    original = re.sub(r'\s*\|\s*', ', ', original)
    original = re.sub(r'\s+', ' ', original).strip().strip(',').strip()
    original = re.sub(r'\s+\d{1,2}$', '', original)
    parts = [p.strip() for p in re.split(r',', original) if p.strip()]
    if parts:
        name = parts[0]
        street = ", ".join(parts[1:]).strip() if len(parts) > 1 else ""

    return {
        "recipient_name": name,
        "phone": phone,
        "street": street,
        "city": city,
        "postcode": postcode,
        "state": state,
    }


def parse_easyparcel_row(row):
    """
    Parse one row from EasyParcel-format CSV.
    Handles single-recipient rows AND multi-recipient rows where
    multiple recipients are concatenated into fields with labels
    like 'Nama penerima :', 'Alamat penerima :', etc.
    
    Returns a list of parsed recipient dicts.
    """
    name_raw = str(row.get("recipient_name", "")).strip()
    phone_raw = str(row.get("recipient_phone", "")).strip()
    addr_raw = str(row.get("recipient_address", "")).strip()
    pcode_raw = str(row.get("recipient_postcode", "")).strip()
    city_raw = str(row.get("recipient_city", "")).strip()
    state_raw = str(row.get("recipient_state", "")).strip()

    # Shared parcel defaults
    parcel_content = row.get("parcel_content", "General merchandise") or "General merchandise"
    parcel_value = row.get("parcel_value_rm", "100") or "100"
    weight = row.get("weight_kg", "0.5") or "0.5"
    quantity = row.get("quantity", "1") or "1"

    # Concatenate all fields to check for multi-recipient pattern
    all_text = " | ".join(filter(None, [name_raw, phone_raw, addr_raw, pcode_raw, city_raw, state_raw]))

    # Detect multi-recipient by looking for field labels
    # Every label acts as a split point
    split_pat = r'(?=(?:Nama penerima :|Alamat penerima :|Alamat kedua :|No\.\s*Tel penerima :|Poskod :|recipient_name:|recipient_phone:|recipient_address:|recipient_postcode:|recipient_city:|recipient_state:))'
    multi_recipients = re.split(split_pat, all_text, flags=re.IGNORECASE)

    chunks = [c.strip().rstrip('|').strip() for c in multi_recipients if c.strip()]
    if len(chunks) <= 1:
        # Single recipient
        addr_parts = [a for a in [addr_raw, city_raw, pcode_raw, state_raw] if a]
        full_address = ", ".join(addr_parts) if addr_parts else ""
        return [{
            "recipient_name": name_raw,
            "recipient_phone": phone_raw,
            "recipient_address": full_address,
            "recipient_postcode": pcode_raw,
            "recipient_city": city_raw,
            "recipient_state": state_raw,
            "parcel_content": str(parcel_content),
            "parcel_value_rm": str(parcel_value),
            "weight_kg": str(weight),
            "quantity": str(quantity),
        }]

    # Multi-recipient: reconstruct from labeled chunks
    results = []
    current = {}
    for chunk in chunks:
        # Strip | field separator artifacts (from all_text concatenation)
        # Take only the first segment before any |
        chunk = chunk.split(" | ", 1)[0].strip()
        chunk_lower = chunk.lower()
        if chunk_lower.startswith("nama penerima :") or chunk_lower.startswith("recipient_name:"):
            if current and current.get("recipient_name"):
                results.append(current)
                current = {}
            val = re.sub(r'^(?:nama penerima :|recipient_name:)\s*', '', chunk, flags=re.IGNORECASE).strip()
            current["recipient_name"] = val
        elif chunk_lower.startswith("alamat penerima :") or chunk_lower.startswith("recipient_address:"):
            val = re.sub(r'^(?:alamat penerima :|recipient_address:)\s*', '', chunk, flags=re.IGNORECASE).strip()
            current.setdefault("address_parts", []).append(val)
        elif chunk_lower.startswith("alamat kedua :"):
            val = re.sub(r'^alamat kedua :\s*', '', chunk, flags=re.IGNORECASE).strip()
            current.setdefault("address_parts", []).append(val)
        elif chunk_lower.startswith("no. tel penerima :") or chunk_lower.startswith("recipient_phone:"):
            val = re.sub(r'^(?:no\.?\s*tel\s*penerima :|recipient_phone:)\s*', '', chunk, flags=re.IGNORECASE).strip()
            current["recipient_phone"] = val
        elif chunk_lower.startswith("poskod :") or chunk_lower.startswith("recipient_postcode:"):
            val = re.sub(r'^(?:poskod :|recipient_postcode:)\s*', '', chunk, flags=re.IGNORECASE).strip()
            current["recipient_postcode"] = val
        elif chunk_lower.startswith("recipient_city:"):
            val = re.sub(r'^recipient_city:\s*', '', chunk, flags=re.IGNORECASE).strip()
            current["recipient_city"] = val
        elif chunk_lower.startswith("recipient_state:"):
            val = re.sub(r'^recipient_state:\s*', '', chunk, flags=re.IGNORECASE).strip()
            current["recipient_state"] = val
        else:
            if not current.get("recipient_name"):
                current["recipient_name"] = chunk.strip()
            elif not current.get("recipient_phone"):
                phone_pat = re.search(r'(6?01[0-9])[\s-]?[\s-]?(\d{7,8})', chunk)
                if phone_pat:
                    current["recipient_phone"] = phone_pat.group(0).replace(" ", "")
                else:
                    current.setdefault("address_parts", []).append(chunk.strip())
            else:
                current.setdefault("address_parts", []).append(chunk.strip())

    # Flush last recipient
    if current and current.get("recipient_name"):
        results.append(current)

    # Build output
    output = []
    for r in results:
        addr_parts = r.get("address_parts", [])
        full_address = ", ".join(addr_parts) if addr_parts else ""
        output.append({
            "recipient_name": r.get("recipient_name", ""),
            "recipient_phone": r.get("recipient_phone", phone_raw or ""),
            "recipient_address": full_address or addr_raw or "",
            "recipient_postcode": r.get("recipient_postcode", pcode_raw or ""),
            "recipient_city": r.get("recipient_city", city_raw or ""),
            "recipient_state": r.get("recipient_state", state_raw or ""),
            "parcel_content": str(parcel_content),
            "parcel_value_rm": str(parcel_value),
            "weight_kg": str(weight),
            "quantity": str(quantity),
        })

    return output if output else [{
        "recipient_name": name_raw,
        "recipient_phone": phone_raw,
        "recipient_address": addr_raw,
        "recipient_postcode": pcode_raw,
        "recipient_city": city_raw,
        "recipient_state": state_raw,
        "parcel_content": str(parcel_content),
        "parcel_value_rm": str(parcel_value),
        "weight_kg": str(weight),
        "quantity": str(quantity),
    }]


def to_easyparcel(parsed):
    """Map parse_address output to EasyParcel bulk upload columns."""
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
