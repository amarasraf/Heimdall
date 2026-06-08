"""
Heimdall — Core Parser Logic
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
        first = parts[0]
        # Heuristic: treat as address-only if first segment starts with common address prefixes
        # (prevents "No 1 Jalan..." being misparsed as recipient_name)
        address_starters = r'\b(No\.?\s*\d|Lot\s*\d|Unit\s*\d|Blok\s*\d|\d+[\s,]*Jalan|\d+[\s,]*Lorong|\d+[\s,]*Taman)'
        is_address_number = bool(re.match(r'^([A-Za-z]?[-]?\d+[-/\dA-Za-z]*)$', first.strip()))
        
        street_parts = []
        addr_match = re.search(address_starters, first, re.IGNORECASE)
        
        if addr_match and addr_match.start() > 0:
            name = first[:addr_match.start()].strip()
            street_parts = [first[addr_match.start():].strip()] + parts[1:]
        elif addr_match or is_address_number:
            name = ""
            street_parts = parts
        else:
            name = first
            street_parts = parts[1:]
            
        if len(street_parts) > 1:
            last_part = street_parts[-1].strip()
            # If last part is 1-3 words and no digits, treat as city
            if len(last_part.split()) <= 3 and not re.search(r'\d', last_part):
                city = last_part
                street = ", ".join(street_parts[:-1]).strip()
            else:
                street = ", ".join(street_parts).strip()
        else:
            street = ", ".join(street_parts).strip()

    return {
        "recipient_name": name,
        "phone": phone,
        "street": street,
        "city": city,
        "postcode": postcode,
        "state": state,
    }


def _extract_phone(text):
    """Extract phone from text, return (phone, text_with_phone_removed)."""
    phone_patterns = [
        r'(6?01[0-9])[\s-]?[\s-]?(\d{7,8})',
        r'(6?01[0-9][\s-]?\s?\d{7,8})',
        r'(01[0-9][- ]\d{3,4}[- ]\d{4,5})',
        r'(6?01[0-9][- ]?\d{3,4}[- ]?\d{3,4})',
    ]
    for pat in phone_patterns:
        m = re.search(pat, text)
        if m:
            raw_phone = m.group(0).replace(" ", "").replace("-", "")
            if len(raw_phone) in (9, 10, 11, 12):
                return raw_phone, text.replace(m.group(0), "", 1).strip()
    return "", text


def _strip_unwanted_labels(text):
    """Remove known non-delivery labels from text to clean up addresses."""
    # Remove lines/segments matching labels we don't want in address
    for pat in [
        r'[Ee]mail\s+[Tt]racking\s+[Nn]umber\s*\([^)]*\)\s*:\s*\S+@\S+',
        r'[Ee]mail\s+[Pp]enerima\s*/\s*[Pp]embeli\s*\)\s*:\s*\S+@\S+',
        r'\S+@\S+\.\w+',  # any email
        r'[Ee]mail\s+[Tt]racking\s+[Nn]umber\s*\([^)]*\)\s*:',
        r'[Ee]mail\s+[Pp]enerima\s*/\s*[Pp]embeli\s*\)\s*:',
        r'[Ee]mail\s+[Tt]racking\s+[Nn]umber\s*:',
        r'Kawasan\s*\(Daerah\)\s*:\s*[^\n]+',
        r'[Kk]awasan\s*\([Dd]aerah\)\s*:',
    ]:
        text = re.sub(pat, '', text).strip()
    return text


def parse_easyparcel_row(row):
    """
    Parse one row from EasyParcel-format CSV.
    Handles single-recipient rows AND multi-recipient rows where
    multiple recipients are concatenated into fields with labels
    like 'Nama penerima :', 'Alamat penerima :', etc.

    Now also handles extra labels: Kawasan (Daerah) :, Bandar :, Negeri :,
    Email Tracking Number, etc.
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

    # Build all_text with newlines as separators
    parts = [p for p in [name_raw, phone_raw, addr_raw, pcode_raw, city_raw, state_raw] if p]
    all_text = "\n".join(parts)

    # Remove unwanted labels first
    all_text = _strip_unwanted_labels(all_text)

    # === New multi-recipient strategy ===
    # Split on "Nama penerima :" as the primary delimiter (most reliable)
    # This handles cases where multiple recipients are crammed into one row
    recipient_blocks = re.split(r'(?i)(?=Nama penerima :)', all_text)
    recipient_blocks = [b.strip() for b in recipient_blocks if b.strip()]

    if len(recipient_blocks) <= 1 and "Alamat penerima" not in all_text:
        # Single recipient - use original column values
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

    # Multi-recipient: parse each block
    results = []
    for block in recipient_blocks:
        # Extract fields from this block
        name_match = re.search(r'Nama penerima\s*:\s*(.+?)(?=\n|Alamat|$)', block, re.IGNORECASE)
        phone_match = re.search(r'No\.\s*Tel\s*penerima\s*:\s*([0-9\s-]+)', block, re.IGNORECASE)
        addr_match = re.search(r'Alamat penerima\s*:\s*(.+?)(?=Poskod|Kawasan|Bandar|Negeri|No\. Tel|Email|$)', block, re.IGNORECASE | re.DOTALL)
        pcode_match = re.search(r'Poskod\s*:\s*(\d{5})', block, re.IGNORECASE)
        city_match = re.search(r'Bandar\s*:\s*(.+?)(?=\n|Negeri|$)', block, re.IGNORECASE)
        state_match = re.search(r'Negeri\s*:\s*(.+?)(?=\n|$)', block, re.IGNORECASE)

        rec = {
            "recipient_name": name_match.group(1).strip() if name_match else "",
            "recipient_phone": "",
            "recipient_address": addr_match.group(1).strip() if addr_match else "",
            "recipient_postcode": pcode_match.group(1) if pcode_match else "",
            "recipient_city": city_match.group(1).strip() if city_match else "",
            "recipient_state": state_match.group(1).strip() if state_match else "",
        }

        # Clean phone
        if phone_match:
            digits = re.sub(r'\D', '', phone_match.group(1))
            if len(digits) >= 9:
                rec["recipient_phone"] = digits

        # Fallback phone extraction if not found via label
        if not rec["recipient_phone"]:
            phone_val, _ = _extract_phone(block)
            if phone_val:
                rec["recipient_phone"] = phone_val

        results.append(rec)

    # Build output — fill missing fields from column defaults
    output = []
    for r in results:
        addr_val = r.get("recipient_address", "")
        if not addr_val:
            addr_val = addr_raw or ""

        # State normalization
        state_val = r.get("recipient_state", state_raw or "").strip()
        state_lower = state_val.lower()
        if state_lower in STATE_MAP:
            state_val = STATE_MAP[state_lower]

        output.append({
            "recipient_name": r.get("recipient_name", name_raw),
            "recipient_phone": r.get("recipient_phone", phone_raw or ""),
            "recipient_address": addr_val,
            "recipient_postcode": r.get("recipient_postcode", pcode_raw or ""),
            "recipient_city": r.get("recipient_city", city_raw or ""),
            "recipient_state": state_val,
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
