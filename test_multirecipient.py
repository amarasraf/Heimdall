"""
Test: Multi-recipient CSV parsing for AlamatPintar
Tests parse_easyparcel_row with multi-recipient rows.
"""

import sys
import os
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from parser_core import parse_easyparcel_row, parse_address, to_easyparcel, STATE_MAP


def test_single_recipient():
    """Normal single recipient row — should pass through cleanly."""
    row = {
        "recipient_name": "KHAIRIL AMIRIN",
        "recipient_phone": "60198367089",
        "recipient_address": "Kolej Kediaman Satria Kasturi, Durian Tunggal",
        "recipient_postcode": "76100",
        "recipient_city": "Durian Tunggal",
        "recipient_state": "Melaka",
        "parcel_content": "General merchandise",
        "parcel_value_rm": "100",
        "weight_kg": "0.5",
        "quantity": "1",
    }
    result = parse_easyparcel_row(row)
    assert len(result) == 1, f"Expected 1 recipient, got {len(result)}"
    assert result[0]["recipient_name"] == "KHAIRIL AMIRIN"
    assert result[0]["recipient_phone"] == "60198367089"
    assert result[0]["recipient_state"] == "Melaka"
    print("  ✓ Single recipient")


def test_multi_recipient_concatenated():
    """
    The actual EasyParcel bug: 3 recipients concatenated 
    into recipient_name with labels like 'Nama penerima :'.
    """
    row = {
        "recipient_name": (
            "Nama penerima : KHAIRIL AMIRIN "
            "Alamat penerima : ***(1) Kolej Kediaman Satria Kasturi "
            "Alamat kedua : Universiti Teknikal Malaysia Melaka Hang Tuah Jaya Durian Tunggal Melaka "
            "No. Tel penerima : 60198367089 "
            "Poskod : 76100 "
            "Nama penerima : SITI NUR HAFIZAH "
            "Alamat penerima : JALAN PULAU MELAKA 8, PULAU MELAKA, MASJID SELAT MELAKA "
            "Alamat kedua : 75000, MELAKA "
            "No. Tel penerima : 601111134347 "
            "Poskod : 75000 "
            "Nama penerima : NOR HAFIZAH IDRIS "
            "Alamat penerima : Bangunan perodua pj central "
            "Alamat kedua : Lot 11 & 12 jln 19/01 seksyen 19 "
            "No. Tel penerima : 0123184554 "
            "Poskod : 46300"
        ),
        "recipient_phone": "",
        "recipient_address": "",
        "recipient_postcode": "",
        "recipient_city": "",
        "recipient_state": "",
        "parcel_content": "General merchandise",
        "parcel_value_rm": "100",
        "weight_kg": "0.5",
        "quantity": "1",
    }
    result = parse_easyparcel_row(row)
    print(f"  Got {len(result)} recipients:")
    for i, r in enumerate(result):
        print(f"    [{i+1}] {r['recipient_name']} | {r['recipient_phone']} | {r['recipient_postcode']} | {r['recipient_address'][:60]}...")

    assert len(result) == 3, f"Expected 3, got {len(result)}"
    assert result[0]["recipient_name"] == "KHAIRIL AMIRIN"
    assert result[1]["recipient_name"] == "SITI NUR HAFIZAH"
    assert result[2]["recipient_name"] == "NOR HAFIZAH IDRIS"
    assert result[0]["recipient_phone"] == "60198367089"
    assert result[1]["recipient_phone"] == "601111134347"
    assert result[2]["recipient_phone"] == "0123184554"
    assert result[0]["recipient_postcode"] == "76100"
    assert result[1]["recipient_postcode"] == "75000"
    assert result[2]["recipient_postcode"] == "46300"
    print("  ✓ Multi-recipient split correctly")


def test_two_recipients():
    """Two recipients crammed into name field only."""
    row = {
        "recipient_name": "Nama penerima : AHMAD FAUZI Nama penerima : SITI AMINAH",
        "recipient_phone": "",
        "recipient_address": "Jalan 1/1, Taman Bahagia",
        "recipient_postcode": "43650",
        "recipient_city": "Bangi",
        "recipient_state": "Selangor",
        "parcel_content": "T-shirt",
        "parcel_value_rm": "50",
        "weight_kg": "0.3",
        "quantity": "2",
    }
    result = parse_easyparcel_row(row)
    print(f"  Got {len(result)} recipients:")
    for i, r in enumerate(result):
        print(f"    [{i+1}] {r['recipient_name']} | {r['recipient_address'][:40]}")
    assert len(result) == 2
    assert result[0]["recipient_name"] == "AHMAD FAUZI"
    assert result[1]["recipient_name"] == "SITI AMINAH"
    print("  ✓ Two recipients")


def test_raw_text_via_parse_address():
    """Old raw_text format still works via parse_address."""
    text = "Amar Mustapha, 0171234567, No 45 Jalan Bukit, Taman Desa, 43700 Beranang, Selangor"
    parsed = parse_address(text)
    ep = to_easyparcel(parsed)
    assert ep["recipient_name"] == "Amar Mustapha"
    assert ep["recipient_phone"] == "0171234567"
    assert ep["recipient_postcode"] == "43700"
    assert ep["recipient_state"] == "Selangor"
    print("  ✓ Raw text parse_address")


def test_multi_recipient_from_columns():
    """
    Multi-recipient where some data is in separate columns too.
    This tests the more complex scenario: name+phone in the concordant
    name field, but additional data split across columns.
    """
    row = {
        "recipient_name": "Nama penerima : ZULKIFLI BIN ALI Nama penerima : ROSMAH BINTI ZAIN",
        "recipient_phone": "",
        "recipient_address": "",
        "recipient_postcode": "",
        "recipient_city": "",
        "recipient_state": "",
        "parcel_content": "Books",
        "parcel_value_rm": "200",
        "weight_kg": "1.0",
        "quantity": "2",
    }
    result = parse_easyparcel_row(row)
    assert len(result) == 2
    assert result[0]["recipient_name"] == "ZULKIFLI BIN ALI"
    assert result[1]["recipient_name"] == "ROSMAH BINTI ZAIN"
    print("  ✓ Multi from columns")


def test_state_map():
    """Verify important states are mapped."""
    required = ["selangor", "melaka", "johor", "kuala lumpur", "penang"]
    for s in required:
        assert s in STATE_MAP, f"Missing state: {s}"
    print("  ✓ State map OK")


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    print("=" * 60)
    print("ALAMATPINTAR - Multi-Recipient Parser Tests")
    print("=" * 60)

    tests = [
        ("Single recipient",          test_single_recipient),
        ("Multi-recipient (3)",       test_multi_recipient_concatenated),
        ("Two recipients",            test_two_recipients),
        ("Raw text parse_address",    test_raw_text_via_parse_address),
        ("Multi from columns",        test_multi_recipient_from_columns),
        ("State map verification",    test_state_map),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n-- {name}")
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"OK: {passed}/{passed + failed} tests passed")
    if failed:
        print(f"FAILED: {failed} tests")
    print(f"{'=' * 60}")
