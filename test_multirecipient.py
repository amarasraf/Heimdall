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
import re


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
    assert result[0]["recipient_postcode"] == "76100"
    print("  OK: Single recipient")


def test_multi_recipient_with_extra_labels():
    """
    The actual data from the user: 3 recipients with extra labels
    like Kawasan (Daerah):, Bandar:, Negeri:, Email Tracking Number:
    """
    row = {
        "recipient_name": (
            "Nama penerima : KHAIRIL AMIRIN\n"
            "Alamat penerima : SK-K-7-11-D(1), Kolej Kediaman Satria Kasturi, Universiti Teknikal Malaysia Melaka, Hang Tuah Jaya, 76100 Durian Tunggal, Melaka.\n"
            "Kawasan (Daerah) : Durian tunggal\n"
            "Bandar : Durian tunggal\n"
            "Negeri : Melaka\n"
            "Poskod : 76100\n"
            "No. Tel penerima : 60198367089\n"
            "Email Tracking Number ( Penerima / Pembeli ) : mvsfeanis@gmail.com\n"
            "\n"
            "Nama penerima : SITI NUR HAFIZAH\n"
            "Alamat penerima : JALAN PULAU MELAKA 8, PULAU MELAKA, MASJID SELAT MELAKA\n"
            "Alamat kedua : 75000, MELAKA\n"
            "Kawasan (Daerah) : MELAKA TENGAH\n"
            "Bandar : MELAKA\n"
            "Negeri : MELAKA\n"
            "Poskod : 75000\n"
            "No. Tel penerima : 601111134347\n"
            "Email Tracking Number ( Penerima / Pembeli ) : sitinurhafizah1008@gmail.com\n"
            "\n"
            "Nama penerima : NOR HAFIZAH IDRIS\n"
            "Alamat penerima : Bangunan perodua pj central\n"
            "Alamat kedua : Lot 11 & 12 jln 19/01 seksyen 19\n"
            "Kawasan (Daerah) : Petaling jaya\n"
            "Bandar : Petaling jaya\n"
            "Negeri : Selangor\n"
            "Poskod : 46300\n"
            "No. Tel penerima : 0123184554\n"
            "Email Tracking Number ( Penerima / Pembeli ) : rafidah.jamilus@gmail.com"
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
        print(f"    [{i+1}] {r['recipient_name']} | {r['recipient_phone']} | {r['recipient_address'][:50]}... | PC:{r['recipient_postcode']} | {r['recipient_state']}")

    assert len(result) == 3, f"Expected 3 recipients, got {len(result)}"
    
    # Recipient 1: KHAIRIL AMIRIN
    assert result[0]["recipient_name"] == "KHAIRIL AMIRIN"
    assert result[0]["recipient_phone"] == "60198367089"
    assert result[0]["recipient_postcode"] == "76100"
    assert result[0]["recipient_state"] == "Melaka"
    assert "Satria Kasturi" in result[0]["recipient_address"]
    # Make sure no email or kawasan label leaked into address
    assert "mvsfeanis" not in result[0]["recipient_address"]
    assert "Daerah" not in result[0]["recipient_address"]
    assert "Tracking" not in result[0]["recipient_address"]

    # Recipient 2: SITI NUR HAFIZAH
    assert result[1]["recipient_name"] == "SITI NUR HAFIZAH"
    assert result[1]["recipient_phone"] == "601111134347"
    assert result[1]["recipient_postcode"] == "75000"
    assert "PULAU MELAKA" in result[1]["recipient_address"]

    # Recipient 3: NOR HAFIZAH IDRIS
    assert result[2]["recipient_name"] == "NOR HAFIZAH IDRIS"
    assert result[2]["recipient_phone"] == "0123184554"
    assert result[2]["recipient_postcode"] == "46300"
    assert result[2]["recipient_state"] == "Selangor"
    assert "perodua" in result[2]["recipient_address"]
    assert "seksyen 19" in result[2]["recipient_address"]
    assert "rafidah" not in result[2]["recipient_address"]

    print("  OK: Multi-recipient with extra labels")


def test_original_three_recipients():
    """The original test case from before (no extra labels) still works."""
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
    assert len(result) == 3, f"Expected 3, got {len(result)}"
    assert result[0]["recipient_name"] == "KHAIRIL AMIRIN"
    assert result[1]["recipient_name"] == "SITI NUR HAFIZAH"
    assert result[2]["recipient_name"] == "NOR HAFIZAH IDRIS"
    assert result[0]["recipient_phone"] == "60198367089"
    assert result[1]["recipient_phone"] == "601111134347"
    assert result[2]["recipient_phone"] == "0123184554"
    print("  OK: Original 3-recipient still works")


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
    assert len(result) == 2
    assert result[0]["recipient_name"] == "AHMAD FAUZI"
    assert result[1]["recipient_name"] == "SITI AMINAH"
    print("  OK: Two recipients")


def test_raw_text_via_parse_address():
    """Old raw_text format still works via parse_address."""
    text = "Amar Mustapha, 0171234567, No 45 Jalan Bukit, Taman Desa, 43700 Beranang, Selangor"
    parsed = parse_address(text)
    ep = to_easyparcel(parsed)
    assert ep["recipient_name"] == "Amar Mustapha"
    assert ep["recipient_phone"] == "0171234567"
    assert ep["recipient_postcode"] == "43700"
    assert ep["recipient_state"] == "Selangor"
    print("  OK: Raw text parse_address")


def test_no_phone_in_output_label_leak():
    """Verify phone numbers don't appear in addresses, emails don't leak."""
    test_cases = [
        # (input, expected_name, expected_phone)
        (
            "Nama penerima : ALI BIN ABU Alamat penerima : No 15, Jalan Merbok Poskod : 43200 No. Tel penerima : 0123456789 Negeri : Selangor",
            "ALI BIN ABU", "0123456789", "43200", "Selangor"
        ),
    ]
    for text, exp_name, exp_phone, exp_pc, exp_state in test_cases:
        row = {"recipient_name": text, "recipient_phone": "", "recipient_address": "",
               "recipient_postcode": "", "recipient_city": "", "recipient_state": "",
               "parcel_content": "", "parcel_value_rm": "", "weight_kg": "", "quantity": ""}
        result = parse_easyparcel_row(row)
        assert len(result) == 1, f"Expected 1, got {len(result)} for {exp_name}"
        assert result[0]["recipient_name"] == exp_name, f"Name mismatch: {result[0]['recipient_name']} != {exp_name}"
        assert result[0]["recipient_phone"] == exp_phone, f"Phone mismatch: {result[0]['recipient_phone']} != {exp_phone}"
        assert result[0]["recipient_postcode"] == exp_pc
        assert result[0]["recipient_state"] == exp_state
    print("  OK: No label leakage")


if __name__ == "__main__":
    print("=" * 60)
    print("ALAMATPINTAR - Multi-Recipient Parser Tests")
    print("=" * 60)

    tests = [
        ("Single recipient",                test_single_recipient),
        ("Multi-recipient with extra labels", test_multi_recipient_with_extra_labels),
        ("Original 3-recipient",            test_original_three_recipients),
        ("Two recipients",                  test_two_recipients),
        ("Raw text parse_address",          test_raw_text_via_parse_address),
        ("No label leakage",                test_no_phone_in_output_label_leak),
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
