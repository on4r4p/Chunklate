#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_info


def test_parse_gama_keeps_zero_as_useless_fix():
    info = chunk_info.parse_gama("00000000")

    assert info.value == "0"
    assert info.fixes == ("-A gAMA Chunk of 0 is Useless.",)


def test_parse_phys_preserves_legacy_field_order_and_unit_validation():
    info = chunk_info.parse_phys("000000010000000202")

    assert info.y == "1"
    assert info.x == "2"
    assert info.unit == "2"
    assert info.fixes == (
        "-Unit specifier :Wrong value Must be between 0 (unknown) or 1(meter).",
    )


def test_parse_phys_reports_high_and_missing_values():
    high = chunk_info.parse_phys("800000008000000001")
    short = chunk_info.parse_phys("")

    assert high.fixes == (
        "-Pixels per unit, Y axis: Wrong size (Too high) Must be between 1 to 2147483647.",
        "-Pixels per unit, X axis: Wrong size (Too high) Must be between 1 to 2147483647.",
    )
    assert "-Error pHYs Y:" in short.fixes[0]
    assert "-Error pHYs X:" in short.fixes[1]
    assert "-Error pHYs U:" in short.fixes[2]
    assert short.fixes[3:] == (
        "-Pixels per unit, Y axis: Wrong size (Too low) Must be between 1 to 2147483647.",
        "-Pixels per unit, X axis: Wrong size (Too low) Must be between 1 to 2147483647.",
    )


def test_parse_time_reads_valid_fields():
    info = chunk_info.parse_time("07e80515112233", current_year=2026)

    assert info.year == "2024"
    assert info.month == "5"
    assert info.day == "21"
    assert info.hour == "17"
    assert info.minute == "34"
    assert info.second == "51"
    assert info.can_print_timestamp is True
    assert info.fixes == ()


def test_parse_time_keeps_parse_and_validation_fixes_separate():
    invalid_values = chunk_info.parse_time("07ff0d20243d3d", current_year=2026)
    short = chunk_info.parse_time("00", current_year=2026)

    assert invalid_values.can_print_timestamp is True
    assert invalid_values.parse_fixes == ()
    assert invalid_values.validation_fixes == (
        "-Year is > than current year2047",
        "-Month value is not valid 13",
        "-Day value is not valid32",
        "-Hour value is not valid 36",
        "-Minute value is not valid61",
        "-Second  value is not valid61",
    )
    assert short.can_print_timestamp is False
    assert short.fixes == ("-tIME Not enough bytes inside tIME data.",)


def test_parse_ster_validates_mode():
    info = chunk_info.parse_ster("02")

    assert info.mode == "2"
    assert info.fixes == ("-sTER should be 0 or 1",)


def test_parse_srgb_validates_rendering_intent_and_chrm_override():
    valid = chunk_info.parse_srgb("02")
    invalid = chunk_info.parse_srgb("04")
    overridden = chunk_info.parse_srgb("01", has_chrm=True)

    assert valid.value == "2"
    assert valid.fixes == ()
    assert invalid.fixes == ("-sRGB value must be between 0 to 3.",)
    assert overridden.fixes == ("-cHRM is overided by sRGB chunk",)


def test_parse_chrm_reads_eight_unsigned_fields_and_override():
    data = (
        "00000001"
        "00000002"
        "00000003"
        "00000004"
        "00000005"
        "00000006"
        "00000007"
        "00000008"
    )
    info = chunk_info.parse_chrm(data)
    overridden = chunk_info.parse_chrm(data, has_srgb_or_iccp=True)
    malformed = chunk_info.parse_chrm("zz" + data[2:])

    assert info.white_x == "1"
    assert info.white_y == "2"
    assert info.red_x == "3"
    assert info.red_y == "4"
    assert info.green_x == "5"
    assert info.green_y == "6"
    assert info.blue_x == "7"
    assert info.blue_y == "8"
    assert info.fixes == ()
    assert overridden.fixes == ("-cHRM is overided by sRGB chunk and iCCP",)
    assert malformed.white_x == ""
    assert malformed.fixes[0].startswith("-cHRM WhiteX Error:")


def test_parse_offs_validates_signed_offsets_and_unit():
    valid = chunk_info.parse_offs("00000001ffffffff01")
    invalid = chunk_info.parse_offs("800000007fffffff02")
    malformed = chunk_info.parse_offs("0000000100000001zz")

    assert valid.x == "1"
    assert valid.y == "-1"
    assert valid.unit == "1"
    assert valid.fixes == ()
    assert invalid.fixes == (
        "-Wrong Offset position X must be between -2,147,483,647 to +2,147,483,647",
        "-Wrong Offset unit must be between 0 or 1",
    )
    assert malformed.unit == chunk_info.OFFS_PARSE_FALLBACK
    assert malformed.fixes == ("-Wrong Offset unit must be between 0 or 1",)


def test_parse_gifg_reads_legacy_numeric_fields():
    info = chunk_info.parse_gifg("010203")
    malformed = chunk_info.parse_gifg("01")

    assert info.disposal_method == "1"
    assert info.user_input_flag == "2"
    assert info.delay_time == "3"
    assert info.fixes == ()
    assert malformed.disposal_method == "1"
    assert malformed.user_input_flag == ""
    assert malformed.delay_time == ""
    assert malformed.fixes[0].startswith("-gIFg User Input Flag Error:")
    assert malformed.fixes[1].startswith("-gIFg Delay Time Error:")


def test_parse_gifx_reads_legacy_numeric_fields():
    info = chunk_info.parse_gifx("0000000000000001000002ff")
    malformed = chunk_info.parse_gifx("0000000000000001000002")

    assert info.application_identifier == "1"
    assert info.authentication_code == "2"
    assert info.application_data == "255"
    assert info.fixes == ()
    assert malformed.application_identifier == "1"
    assert malformed.authentication_code == "2"
    assert malformed.application_data == ""
    assert malformed.fixes[0].startswith("-gIFx Application Data Error:")


def test_parse_iccp_reads_profile_name_method_and_profile_length():
    info = chunk_info.parse_iccp("4943430000abcd", raw_length_hex="00000007")
    bad_length = chunk_info.parse_iccp("4943430000abcd", raw_length_hex="00000008")

    assert info.name == "ICC"
    assert info.method == 0
    assert info.profile == "abcd"
    assert info.null_pos == 6
    assert info.fixes == ()
    assert bad_length.fixes == ("-iCCP Profile length is not Valid",)


def test_parse_iccp_reports_bad_name_method_and_chrm_override():
    bad_char = chunk_info.parse_iccp("0143430000abcd", raw_length_hex="00000007")
    bad_method = chunk_info.parse_iccp("4943430001abcd", raw_length_hex="00000007")
    overridden = chunk_info.parse_iccp(
        "4943430000abcd",
        raw_length_hex="00000007",
        has_chrm=True,
    )

    assert bad_char.name == "€CC"
    assert bad_char.bad_chars == (("\x01", 0),)
    assert bad_char.fixes == (
        "-Character not allowed \x01 at index 0 in iCCP_Name\n-Replaced by [€]",
        ["badchar", 0],
    )
    assert bad_method.method == 1
    assert bad_method.fixes == ("-Compression method is supposed to be 0 but is 1 instead .",)
    assert overridden.fixes == (
        "-cHRM already present cHRM will be overide if reconized by decoders",
    )


def test_parse_iccp_reports_long_name_and_malformed_method():
    long_name = chunk_info.parse_iccp(("41" * 40) + "0000", raw_length_hex="0000002a")
    malformed = chunk_info.parse_iccp("49434300zzabcd", raw_length_hex="00000007")

    assert long_name.null_pos == 80
    assert long_name.fixes == ("-Length of iCCP Profile name is not valid",)
    assert malformed.method == ""
    assert malformed.fixes[0].startswith("-iCCP Method Error:")


def test_parse_exif_reads_endian_and_raw_values():
    little = chunk_info.parse_exif("494900000000")
    big = chunk_info.parse_exif("4d4d")

    assert little.endian == "II"
    assert little.raw_values == ("4949000000",)
    assert little.fixes == ()
    assert big.endian == "MM"
    assert big.raw_values == ()
    assert big.fixes == ()


def test_parse_exif_rejects_unknown_or_malformed_endian():
    unknown = chunk_info.parse_exif("0000")
    malformed = chunk_info.parse_exif("zzzz")

    assert unknown.endian == "\x00\x00"
    assert unknown.fixes == ("-eXIf endianess should be II or MM",)
    assert malformed.endian == ""
    assert malformed.fixes[0].startswith("-eXIf endianess error:")
    assert malformed.fixes[1] == "-eXIf endianess should be II or MM"


def main():
    checks = [
        ("gAMA zero", test_parse_gama_keeps_zero_as_useless_fix),
        ("pHYs fields", test_parse_phys_preserves_legacy_field_order_and_unit_validation),
        ("pHYs limits", test_parse_phys_reports_high_and_missing_values),
        ("tIME valid", test_parse_time_reads_valid_fields),
        ("tIME invalid", test_parse_time_keeps_parse_and_validation_fixes_separate),
        ("sTER mode", test_parse_ster_validates_mode),
        ("sRGB intent", test_parse_srgb_validates_rendering_intent_and_chrm_override),
        ("cHRM fields", test_parse_chrm_reads_eight_unsigned_fields_and_override),
        ("oFFs values", test_parse_offs_validates_signed_offsets_and_unit),
        ("gIFg fields", test_parse_gifg_reads_legacy_numeric_fields),
        ("gIFx fields", test_parse_gifx_reads_legacy_numeric_fields),
        ("iCCP valid", test_parse_iccp_reads_profile_name_method_and_profile_length),
        ("iCCP invalid", test_parse_iccp_reports_bad_name_method_and_chrm_override),
        ("iCCP malformed", test_parse_iccp_reports_long_name_and_malformed_method),
        ("eXIf valid", test_parse_exif_reads_endian_and_raw_values),
        ("eXIf invalid", test_parse_exif_rejects_unknown_or_malformed_endian),
    ]

    print("Running chunk info tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk info tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
