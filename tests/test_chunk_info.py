#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_info


def test_parse_ihdr_reads_valid_fields():
    info = chunk_info.parse_ihdr("00000020000000100802000000")

    assert info.width == "32"
    assert info.height == "16"
    assert info.depth == "8"
    assert info.color == "2"
    assert info.method == "0"
    assert info.filter_method == "0"
    assert info.interlace == "0"
    assert info.fixes == ()


def test_parse_ihdr_reports_size_dimensions_and_estimated_resolution():
    zero = chunk_info.parse_ihdr("00000000000000100802000000")
    huge = chunk_info.parse_ihdr("000000150000000a0802000000", max_resolution=10)
    short = chunk_info.parse_ihdr("00000020")

    assert zero.fixes == (
        "-IHDR Width Must be between 1 to 2147483647. StructIndex:0",
    )
    assert huge.fixes == (
        "-IHDR Width Error 21 Above estimated max resolution(*2):20. StructIndex:0",
    )
    assert "-IHDR size have to always be 13 bytes" in short.fixes
    assert any(fix.startswith("-Error IHDR Width:") for fix in short.fixes)


def test_parse_ihdr_reports_depth_color_method_filter_and_interlace():
    info = chunk_info.parse_ihdr("00000001000000010303010202")

    assert info.fixes == (
        "-IHDR Depht: Wrong bit depht (depht must be 1,2,4,8 or 16). StructIndex:2",
        "-IHDR Color 3: Wrong bit depht with IHDR Color type 3 (depht must be 1,2,4 or 8). StructIndex:3",
        "-IHDR Filter Method Wrong value must be 0. StructIndex:4",
        "-IHDR Compression Algorithms : Wrong value must be 0. StructIndex:5",
        "-IHDR Interlace Method :Wrong value must be 0 (no interlace) or 1 (Adam7 interlace). StructIndex:6",
    )


def test_parse_bkgd_uses_color_type_and_depth():
    gray = chunk_info.parse_bkgd("0007", ihdr_color="0", ihdr_depth="8")
    rgb = chunk_info.parse_bkgd("00ff01000001", ihdr_color="2", ihdr_depth="8")
    indexed = chunk_info.parse_bkgd("02", ihdr_color="3", ihdr_depth="8")

    assert gray.gray == "7"
    assert gray.fixes == ()
    assert rgb.red == "255"
    assert rgb.green == "256"
    assert rgb.blue == "1"
    assert rgb.fixes == ("-Bkgd_Green Wrong value Must be less than 255",)
    assert indexed.index == "2"
    assert indexed.fixes == ()


def test_parse_hist_matches_palette_entry_count():
    valid = chunk_info.parse_hist("00010002", has_plte=True, plte_entries=2)
    missing_palette = chunk_info.parse_hist("0001")
    wrong_count = chunk_info.parse_hist("00010002", has_plte=True, plte_entries=1)

    assert valid.entries == ("0001", "0002")
    assert valid.fixes == ()
    assert missing_palette.fixes == (
        "-PLTE Chunk sPLT is missing.(hIST must be used after one of them)",
    )
    assert wrong_count.fixes == (
        "-Histogram frequencies entries must match PLTE entries number",
    )


def test_parse_trns_uses_color_type_and_palette_count():
    gray = chunk_info.parse_trns("0007", ihdr_color="0")
    truecolor = chunk_info.parse_trns("000100020003", ihdr_color="2")
    indexed = chunk_info.parse_trns(
        "000102",
        ihdr_color="3",
        has_plte=True,
        plte_entries=2,
    )

    assert gray.gray == "7"
    assert gray.fixes == ()
    assert truecolor.true_r == "1"
    assert truecolor.true_g == "2"
    assert truecolor.true_b == "3"
    assert truecolor.fixes == ()
    assert indexed.indexes == ("0", "1", "2")
    assert indexed.fixes == (
        "-tRNS Alpha indexes palettes entries must not be superior to PLTE entries",
    )


def test_parse_sbit_covers_color_dependent_shapes():
    gray = chunk_info.parse_sbit("08", ihdr_color="0", ihdr_depth="8")
    indexed = chunk_info.parse_sbit("090807", ihdr_color="3", ihdr_depth="8")
    gray_alpha = chunk_info.parse_sbit("0900", ihdr_color="4", ihdr_depth="8")
    true_alpha = chunk_info.parse_sbit("08080809", ihdr_color="6", ihdr_depth="8")

    assert gray.gray == "8"
    assert gray.fixes == ()
    assert indexed.fixes == ("-sBit red value (must be greater than 0",)
    assert gray_alpha.gray_scale == "9"
    assert gray_alpha.gray_alpha == "0"
    assert gray_alpha.fixes == (
        "-sBit Grayscale alpha value (must not be greater than 0)",
        "-sBit Grayscale value (must not be greater than 8)",
    )
    assert true_alpha.fixes == ("-sBit True alpha  value (must not be greater than 8)",)


def test_parse_plte_reads_entries_and_checks_depth_limit():
    valid = chunk_info.parse_plte("000102030405", ihdr_depth="8")
    too_many = chunk_info.parse_plte("000102030405060708", ihdr_depth="1")

    assert valid.red == ("00", "03")
    assert valid.green == ("01", "04")
    assert valid.blue == ("02", "05")
    assert valid.fixes == ()
    assert too_many.fixes == (
        "-PLTE Wrong RED 1 palettes not in bitdepht range (must not be > 2 power of image Depht:2)",
        "-PLTE 2 Wrong Green palettes not in bitdepht range: (must not be > 2 power of image Depht:2)",
        "-PLTE Blue palettes not in bitdepht range",
    )


def test_parse_splt_keeps_legacy_entry_slicing_and_name_checks():
    payload = "70616c0008" + ("01" * 13)
    valid = chunk_info.parse_splt(payload)
    duplicate = chunk_info.parse_splt(payload, previous_names=("70616c",))

    assert valid.name == "70616c"
    assert valid.decoded_name == "pal"
    assert valid.depth == "8"
    assert len(valid.red) == len(payload)
    assert valid.fixes == ()
    assert duplicate.fixes == (
        "-sPLT can be used multiple times but cannot share the same name.",
    )


def test_parse_text_reads_keyword_and_payload():
    info = chunk_info.parse_text("5469746c650048656c6c6f")
    long_key = chunk_info.parse_text(("41" * 80) + "00")

    assert info.keyword == "5469746c65"
    assert info.decoded_keyword == "Title"
    assert info.decoded_text == "Hello"
    assert info.fixes == ()
    assert long_key.fixes == ("-tEXt Keyword length is not Valid :160",)


def test_parse_ztxt_decompresses_payload():
    payload = "789cf348cdc9c90700058c01f5"
    info = chunk_info.parse_ztxt("4b65790000" + payload)
    malformed = chunk_info.parse_ztxt("4b65790000ff")

    assert info.decoded_keyword == "Key"
    assert info.decoded_text == "Hello"
    assert info.fixes == ()
    assert malformed.fixes[0].startswith("-zTXt Text Error:")


def test_parse_itxt_reads_uncompressed_payload():
    info = chunk_info.parse_itxt("4b6579000000000048656c6c6f")
    invalid_flag = chunk_info.parse_itxt("4b6579000200000048656c6c6f")

    assert info.decoded_keyword == "Key"
    assert info.compression_flag == "00"
    assert info.compression_method == "00"
    assert info.text == "Hello"
    assert info.fixes == ()
    assert invalid_flag.fixes == ("-iTXt Compression Flag must be 0 or 1",)


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
        ("IHDR valid", test_parse_ihdr_reads_valid_fields),
        ("IHDR dimensions", test_parse_ihdr_reports_size_dimensions_and_estimated_resolution),
        ("IHDR modes", test_parse_ihdr_reports_depth_color_method_filter_and_interlace),
        ("bKGD fields", test_parse_bkgd_uses_color_type_and_depth),
        ("hIST entries", test_parse_hist_matches_palette_entry_count),
        ("tRNS fields", test_parse_trns_uses_color_type_and_palette_count),
        ("sBIT fields", test_parse_sbit_covers_color_dependent_shapes),
        ("PLTE fields", test_parse_plte_reads_entries_and_checks_depth_limit),
        ("sPLT fields", test_parse_splt_keeps_legacy_entry_slicing_and_name_checks),
        ("tEXt fields", test_parse_text_reads_keyword_and_payload),
        ("zTXt fields", test_parse_ztxt_decompresses_payload),
        ("iTXt fields", test_parse_itxt_reads_uncompressed_payload),
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
