from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class RepairCase:
    fixture: str
    corruption: str
    expected_strategy: str
    max_saves: int
    expected_outputs: tuple[str, ...]
    summary_contains: tuple[str, ...] = ()
    validators: tuple[str, ...] = ()


VALID_32_PALETTE = (
    "chunk_order_exact:IHDR,gAMA,PLTE,IDAT,IEND",
    "first_chunk:IHDR",
    "ihdr_dimensions:32x32",
    "has_chunk:PLTE",
    "plte_non_empty",
    "plte_len:768",
    "gama_non_zero",
    "idat_chunk_count:1",
    "idat_decompress",
    "idat_decompressed_len:1056",
    "last_chunk:IEND",
)
VALID_32_PALETTE_NO_GAMA = (
    "chunk_order_exact:IHDR,PLTE,IDAT,IEND",
    "first_chunk:IHDR",
    "ihdr_dimensions:32x32",
    "has_chunk:PLTE",
    "plte_non_empty",
    "plte_len:768",
    "idat_chunk_count:1",
    "idat_decompress",
    "idat_decompressed_len:1056",
    "last_chunk:IEND",
)
VALID_32_NO_PLTE = (
    "chunk_order_exact:IHDR,gAMA,IDAT,IEND",
    "first_chunk:IHDR",
    "ihdr_dimensions:32x32",
    "missing_chunk:PLTE",
    "gama_non_zero",
    "idat_chunk_count:1",
    "idat_decompress",
    "idat_decompressed_len:6176",
    "last_chunk:IEND",
)
VALID_260 = (
    "chunk_order_exact:IHDR,gAMA,cHRM,bKGD,tIME,IDAT*2,tEXt*2,IEND",
    "first_chunk:IHDR",
    "ihdr_dimensions:260x195",
    "gama_non_zero",
    "idat_chunk_count:2",
    "idat_decompress",
    "idat_decompressed_len:202995",
    "last_chunk:IEND",
)
VALID_477 = (
    "chunk_order_exact:IHDR,gAMA,cHRM,bKGD,pHYs,tIME,IDAT*19,tEXt*2,IEND",
    "first_chunk:IHDR",
    "ihdr_dimensions:477x599",
    "gama_non_zero",
    "idat_chunk_count:19",
    "idat_decompress",
    "idat_decompressed_len:857768",
    "last_chunk:IEND",
)
VALID_272_PROFILE_REMOVED = (
    "chunk_order_exact:IHDR,gAMA,cHRM,pHYs,IDAT*2,IEND",
    "first_chunk:IHDR",
    "ihdr_dimensions:272x170",
    "missing_chunk:iCCP",
    "gama_non_zero",
    "idat_chunk_count:2",
    "idat_decompress",
    "idat_decompressed_len:185130",
    "last_chunk:IEND",
)


REPAIR_MATRIX: tuple[RepairCase, ...] = (
    RepairCase(
        fixture="Bad-Chunk-Lenght-Missing-Bit.png",
        corruption="chunk length with one missing bit",
        expected_strategy="recover chunk length",
        max_saves=1,
        expected_outputs=("Bad-Chunk-Lenght-Missing-Bit.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Bad-Chunk-Length-Missing-Bit.png",
        corruption="chunk length with one missing bit",
        expected_strategy="recover chunk length",
        max_saves=1,
        expected_outputs=("Bad-Chunk-Length-Missing-Bit.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Bad-Chunk-Length-Exceeding-Bit.png",
        corruption="chunk length with one exceeding bit",
        expected_strategy="recover chunk length",
        max_saves=1,
        expected_outputs=("Bad-Chunk-Length-Exceeding-Bit.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Classic-Bad-Chunk-Crc.png",
        corruption="chunk CRC mismatch",
        expected_strategy="repair CRC",
        max_saves=1,
        expected_outputs=("Classic-Bad-Chunk-Crc.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Classic-Bad-Chunk-Length.png",
        corruption="chunk length mismatch",
        expected_strategy="repair chunk length",
        max_saves=1,
        expected_outputs=("Classic-Bad-Chunk-Length.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Good-Chunk-lenght-Missing-Bit.png",
        corruption="chunk data with one missing bit and reliable length",
        expected_strategy="recover missing byte from chunk data",
        max_saves=1,
        expected_outputs=("Good-Chunk-lenght-Missing-Bit.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IHDR-Messed-Up-Bad-Crc.png",
        corruption="IHDR data corruption with bad CRC",
        expected_strategy="repair IHDR",
        max_saves=1,
        expected_outputs=("IHDR-Messed-Up-Bad-Crc.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IHDR-Wrong-Height-Above-Estimated-Max-Resolution.png",
        corruption="IHDR height above estimated maximum",
        expected_strategy="repair IHDR height",
        max_saves=1,
        expected_outputs=("IHDR-Wrong-Height-Above-Estimated-Max-Resolution.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IHDR-Wrong-Quick.png",
        corruption="IHDR dimension corruption",
        expected_strategy="repair IHDR quickly",
        max_saves=1,
        expected_outputs=("IHDR-Wrong-Quick.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IHDR-Wrong-Width-Bad-Crc.png",
        corruption="IHDR width corruption with bad CRC",
        expected_strategy="repair IHDR width",
        max_saves=1,
        expected_outputs=("IHDR-Wrong-Width-Bad-Crc.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IHDR-Wrong-Width.png",
        corruption="IHDR width corruption",
        expected_strategy="repair IHDR width",
        max_saves=1,
        expected_outputs=("IHDR-Wrong-Width.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IHDR_Messed_Up_Crc_Valid.png",
        corruption="IHDR data corruption with valid CRC",
        expected_strategy="repair IHDR",
        max_saves=1,
        expected_outputs=("IHDR_Messed_Up_Crc_Valid.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IHDR_Missplaced.png",
        corruption="IHDR placed after another chunk",
        expected_strategy="move IHDR back to the first chunk position",
        max_saves=1,
        expected_outputs=("IHDR_Missplaced.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IEND_Missing.png",
        corruption="missing IEND chunk",
        expected_strategy="append IEND",
        max_saves=1,
        expected_outputs=("IEND_Missing.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IEND_Missing_And_Extra_Bytes.png",
        corruption="missing IEND and trailing bytes",
        expected_strategy="append IEND and remove extra bytes",
        max_saves=1,
        expected_outputs=("IEND_Missing_And_Extra_Bytes.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IDAT_Partial_Blackfill.png",
        corruption="partially readable IDAT stream",
        expected_strategy="partial-idat-blackfill",
        max_saves=1,
        expected_outputs=("IDAT_Partial_Blackfill.0_Fixed.png",),
    ),
    RepairCase(
        fixture="IncorrectSrgbProfile.png",
        corruption="known bad sRGB/iCCP profile",
        expected_strategy="remove bad color profile chunk",
        max_saves=1,
        expected_outputs=("IncorrectSrgbProfile.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Incorrect_Srgb_Profile.png",
        corruption="known bad sRGB/iCCP profile",
        expected_strategy="remove bad color profile chunk",
        max_saves=1,
        expected_outputs=("Incorrect_Srgb_Profile.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Missplaced_Ihdr.png",
        corruption="IHDR placed after another chunk",
        expected_strategy="move IHDR back to the first chunk position",
        max_saves=1,
        expected_outputs=("Missplaced_Ihdr.0_Fixed.png",),
    ),
    RepairCase(
        fixture="No_Png_Header.png",
        corruption="missing PNG signature",
        expected_strategy="restore PNG signature",
        max_saves=1,
        expected_outputs=("No_Png_Header.0_Fixed.png",),
    ),
    RepairCase(
        fixture="No_Png_Header_Corrupted_Length.png",
        corruption="missing PNG signature and corrupted length",
        expected_strategy="restore PNG signature and chunk length",
        max_saves=1,
        expected_outputs=("No_Png_Header_Corrupted_Length.0_Fixed.png",),
    ),
    RepairCase(
        fixture="No_Png_Header_Missing_Chunk_Corrupted.png",
        corruption="missing PNG signature and missing/corrupted IHDR",
        expected_strategy="rebuild missing IHDR",
        max_saves=2,
        expected_outputs=("No_Png_Header_Missing_Chunk_Corrupted.1_Fixed.png",),
    ),
    RepairCase(
        fixture="PLTE_Empty_Bad_Crc.png",
        corruption="empty PLTE with bad CRC",
        expected_strategy="repair empty PLTE",
        max_saves=1,
        expected_outputs=("PLTE_Empty_Bad_Crc.0_Fixed.png",),
    ),
    RepairCase(
        fixture="PLTE_Empty_Good_Crc.png",
        corruption="empty PLTE with valid CRC",
        expected_strategy="repair empty PLTE",
        max_saves=1,
        expected_outputs=("PLTE_Empty_Good_Crc.0_Fixed.png",),
    ),
    RepairCase(
        fixture="plte_length_mod_three.png",
        corruption="PLTE length is not divisible by three",
        expected_strategy="rebuild malformed indexed PLTE",
        max_saves=1,
        expected_outputs=("plte_length_mod_three.0_Fixed.png",),
    ),
    RepairCase(
        fixture="plte_too_many_entries.png",
        corruption="PLTE contains too many entries for indexed bit depth",
        expected_strategy="rebuild low-diversity PLTE",
        max_saves=1,
        expected_outputs=("plte_too_many_entries.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Private_Critical_Chunk_Bad_Crc.png",
        corruption="unknown private critical chunk with bad CRC",
        expected_strategy="remove unsafe private critical chunk",
        max_saves=2,
        expected_outputs=("Private_Critical_Chunk_Bad_Crc.1_Fixed.png",),
    ),
    RepairCase(
        fixture="Private_Critical_Chunk_Crc_Valid.png",
        corruption="unknown private critical chunk with valid CRC",
        expected_strategy="remove unsafe private critical chunk",
        max_saves=2,
        expected_outputs=("Private_Critical_Chunk_Crc_Valid.1_Fixed.png",),
    ),
    RepairCase(
        fixture="Wrong-Chunk-Name-Bad-Crc.png",
        corruption="wrong chunk name with bad CRC",
        expected_strategy="repair chunk name",
        max_saves=1,
        expected_outputs=("Wrong-Chunk-Name-Bad-Crc.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Wrong-Chunk-Name-Crc-Valid.png",
        corruption="wrong chunk name with valid CRC",
        expected_strategy="repair chunk name",
        max_saves=2,
        expected_outputs=("Wrong-Chunk-Name-Crc-Valid.1_Fixed.png",),
    ),
    RepairCase(
        fixture="chunk_crc.png",
        corruption="chunk CRC mismatch",
        expected_strategy="repair CRC",
        max_saves=1,
        expected_outputs=("chunk_crc.0_Fixed.png",),
    ),
    RepairCase(
        fixture="chunk_private_critical.png",
        corruption="unknown private critical chunk",
        expected_strategy="remove unsafe private critical chunk",
        max_saves=1,
        expected_outputs=("chunk_private_critical.0_Fixed.png",),
    ),
    RepairCase(
        fixture="chunk_private_critical_badcrc.png",
        corruption="unknown private critical chunk with bad CRC",
        expected_strategy="remove unsafe private critical chunk",
        max_saves=2,
        expected_outputs=("chunk_private_critical_badcrc.1_Fixed.png",),
    ),
    RepairCase(
        fixture="chunk_private_critical_goodcrc.png",
        corruption="unknown private critical chunk with valid CRC",
        expected_strategy="remove unsafe private critical chunk",
        max_saves=2,
        expected_outputs=("chunk_private_critical_goodcrc.1_Fixed.png",),
    ),
    RepairCase(
        fixture="chunk_type.png",
        corruption="wrong chunk type/name",
        expected_strategy="repair chunk name",
        max_saves=2,
        expected_outputs=("chunk_type.1_Fixed.png",),
    ),
    RepairCase(
        fixture="gama_zero.png",
        corruption="gAMA chunk with zero value",
        expected_strategy="repair gAMA",
        max_saves=1,
        expected_outputs=("gama_zero.0_Fixed.png",),
    ),
    RepairCase(
        fixture="length_gama.png",
        corruption="gAMA chunk with one missing byte",
        expected_strategy="infer common gAMA payload",
        max_saves=1,
        expected_outputs=("length_gama.0_Fixed.png",),
    ),
    RepairCase(
        fixture="length_gifg.png",
        corruption="gIFg chunk with one extra byte",
        expected_strategy="trim gIFg payload",
        max_saves=1,
        expected_outputs=("length_gifg.0_Fixed.png",),
    ),
    RepairCase(
        fixture="length_hist.png",
        corruption="hIST chunk shorter than PLTE entry count",
        expected_strategy="pad hIST payload",
        max_saves=1,
        expected_outputs=("length_hist.0_Fixed.png",),
    ),
    RepairCase(
        fixture="ihdr_image_size.png",
        corruption="IHDR image size mismatch",
        expected_strategy="repair IHDR dimensions",
        max_saves=1,
        expected_outputs=("ihdr_image_size.0_Fixed.png",),
    ),
    RepairCase(
        fixture="Unhandled-Critical-Chunk.png",
        corruption="unknown unsafe critical chunk",
        expected_strategy="remove unsafe critical chunk",
        max_saves=1,
        expected_outputs=("Unhandled-Critical-Chunk.0_Fixed.png",),
    ),
)


_VALIDATORS_BY_FIXTURE = {
    "Bad-Chunk-Lenght-Missing-Bit.png": VALID_32_PALETTE,
    "Bad-Chunk-Length-Missing-Bit.png": VALID_32_PALETTE,
    "Bad-Chunk-Length-Exceeding-Bit.png": VALID_32_PALETTE,
    "Classic-Bad-Chunk-Crc.png": VALID_32_PALETTE,
    "Classic-Bad-Chunk-Length.png": VALID_32_PALETTE,
    "Good-Chunk-lenght-Missing-Bit.png": VALID_32_PALETTE,
    "IHDR-Messed-Up-Bad-Crc.png": VALID_260,
    "IHDR-Wrong-Height-Above-Estimated-Max-Resolution.png": VALID_477,
    "IHDR-Wrong-Quick.png": VALID_477,
    "IHDR-Wrong-Width-Bad-Crc.png": VALID_477,
    "IHDR-Wrong-Width.png": VALID_477,
    "IHDR_Messed_Up_Crc_Valid.png": VALID_32_PALETTE,
    "IHDR_Missplaced.png": VALID_32_PALETTE,
    "IEND_Missing.png": VALID_260,
    "IEND_Missing_And_Extra_Bytes.png": (
        "chunk_order_exact:IHDR,sBIT,IDAT*97,IEND",
        "first_chunk:IHDR",
        "ihdr_dimensions:1920x1200",
        "idat_chunk_count:97",
        "idat_decompress",
        "idat_decompressed_len:9217200",
        "last_chunk:IEND",
    ),
    "IDAT_Partial_Blackfill.png": (
        "chunk_order_exact:IHDR,IDAT,IEND",
        "first_chunk:IHDR",
        "ihdr_dimensions:1x10",
        "idat_chunk_count:1",
        "idat_decompress",
        "idat_decompressed_len:40",
        "last_chunk:IEND",
    ),
    "IncorrectSrgbProfile.png": VALID_272_PROFILE_REMOVED,
    "Incorrect_Srgb_Profile.png": VALID_272_PROFILE_REMOVED,
    "Missplaced_Ihdr.png": VALID_32_PALETTE,
    "No_Png_Header.png": VALID_260,
    "No_Png_Header_Corrupted_Length.png": VALID_260,
    "No_Png_Header_Missing_Chunk_Corrupted.png": (
        "chunk_order_exact:IHDR,gAMA,PLTE,hIST,IDAT,IEND",
        "first_chunk:IHDR",
        "ihdr_dimensions:32x32",
        "has_chunk:PLTE",
        "has_chunk:hIST",
        "plte_non_empty",
        "plte_len:768",
        "gama_non_zero",
        "idat_chunk_count:1",
        "idat_decompress",
        "idat_decompressed_len:1056",
        "last_chunk:IEND",
    ),
    "PLTE_Empty_Bad_Crc.png": VALID_32_NO_PLTE,
    "PLTE_Empty_Good_Crc.png": VALID_32_PALETTE,
    "plte_length_mod_three.png": VALID_32_PALETTE,
    "plte_too_many_entries.png": (
        "chunk_order_exact:IHDR,gAMA,sBIT,PLTE,IDAT,IEND",
        "first_chunk:IHDR",
        "ihdr_dimensions:32x32",
        "has_chunk:PLTE",
        "has_chunk:sBIT",
        "plte_non_empty",
        "plte_len:48",
        "gama_non_zero",
        "idat_chunk_count:1",
        "idat_decompress",
        "idat_decompressed_len:544",
        "last_chunk:IEND",
    ),
    "Private_Critical_Chunk_Bad_Crc.png": VALID_32_PALETTE + ("missing_chunk:baMA",),
    "Private_Critical_Chunk_Crc_Valid.png": VALID_32_PALETTE + ("missing_chunk:baMA",),
    "Wrong-Chunk-Name-Bad-Crc.png": (
        "chunk_order_exact:IHDR,sRGB,gAMA,pHYs,IDAT*4,IEND",
        "first_chunk:IHDR",
        "ihdr_dimensions:1642x1095",
        "gama_non_zero",
        "idat_chunk_count:4",
        "idat_decompress",
        "idat_decompressed_len:5395065",
        "last_chunk:IEND",
    ),
    "Wrong-Chunk-Name-Crc-Valid.png": VALID_32_PALETTE,
    "chunk_crc.png": VALID_32_PALETTE,
    "chunk_private_critical.png": VALID_32_PALETTE + ("missing_chunk:GaMA",),
    "chunk_private_critical_badcrc.png": VALID_32_PALETTE + ("missing_chunk:baMA",),
    "chunk_private_critical_goodcrc.png": VALID_32_PALETTE + ("missing_chunk:baMA",),
    "chunk_type.png": VALID_32_PALETTE,
    "gama_zero.png": (
        "chunk_order_exact:IHDR,IDAT,IEND",
        "first_chunk:IHDR",
        "ihdr_dimensions:32x32",
        "missing_chunk:gAMA",
        "idat_chunk_count:1",
        "idat_decompress",
        "idat_decompressed_len:3104",
        "last_chunk:IEND",
    ),
    "length_gama.png": VALID_32_PALETTE,
    "length_gifg.png": (
        "chunk_order_exact:IHDR,gIFx,tEXt,PLTE,bKGD,gIFg,cmPP,IDAT,msOG,IEND",
        "first_chunk:IHDR",
        "ihdr_dimensions:32x32",
        "has_chunk:PLTE",
        "has_chunk:gIFg",
        "plte_non_empty",
        "plte_len:48",
        "idat_chunk_count:1",
        "idat_decompress",
        "idat_decompressed_len:544",
        "last_chunk:IEND",
    ),
    "length_hist.png": (
        "chunk_order_exact:IHDR,gAMA,sBIT,PLTE,hIST,IDAT,IEND",
        "first_chunk:IHDR",
        "ihdr_dimensions:32x32",
        "has_chunk:PLTE",
        "has_chunk:hIST",
        "plte_non_empty",
        "plte_len:45",
        "gama_non_zero",
        "idat_chunk_count:1",
        "idat_decompress",
        "idat_decompressed_len:544",
        "last_chunk:IEND",
    ),
    "ihdr_image_size.png": VALID_32_PALETTE,
    "Unhandled-Critical-Chunk.png": VALID_32_PALETTE_NO_GAMA + ("missing_chunk:QpZZ",),
}

_SUMMARY_MARKERS_BY_FIXTURE = {
    "Bad-Chunk-Lenght-Missing-Bit.png": (
        "Chunk length has been corrupted due to some missing bytes",
    ),
    "Bad-Chunk-Length-Missing-Bit.png": (
        "Chunk length has been corrupted due to some missing bytes",
    ),
    "Bad-Chunk-Length-Exceeding-Bit.png": (
        "Found 1 extra byte(s) before Chunk[gAMA]",
    ),
    "Classic-Bad-Chunk-Crc.png": (
        "rebuilt IHDR from IDAT scanline size",
        "Selected IHDR 32x32",
    ),
    "Classic-Bad-Chunk-Length.png": (
        "Found Chunk[b'gAMA'] has Wrong length",
        "Replaced with: 00000004",
    ),
    "Good-Chunk-lenght-Missing-Bit.png": (
        "recovered missing data byte in PLTE chunk",
    ),
    "IHDR-Messed-Up-Bad-Crc.png": (
        "restored IHDR values matching stored CRC",
    ),
    "IHDR-Wrong-Height-Above-Estimated-Max-Resolution.png": (
        "rebuilt IHDR from IDAT scanline size",
        "Selected IHDR 477x599",
    ),
    "IHDR-Wrong-Quick.png": (
        "rebuilt IHDR from IDAT scanline size",
        "Selected IHDR 477x599",
    ),
    "IHDR-Wrong-Width-Bad-Crc.png": (
        "restored IHDR values matching stored CRC",
    ),
    "IHDR-Wrong-Width.png": (
        "restored IHDR values matching stored CRC",
    ),
    "IHDR_Messed_Up_Crc_Valid.png": (
        "rebuilt IHDR from IDAT scanline size",
        "Selected IHDR 32x32",
    ),
    "IHDR_Missplaced.png": (
        "Found Missing Data:[b'IHDR']",
    ),
    "IEND_Missing.png": (
        "Critical Chunk b'IEND' is Missing",
        "Filling with a dummy chunk",
    ),
    "IEND_Missing_And_Extra_Bytes.png": (
        "Critical Chunk b'IEND' is Missing",
        "Filling with a dummy chunk",
    ),
    "IDAT_Partial_Blackfill.png": (
        "partial-idat-blackfill recovered 1/10 scanlines",
        "Selected IHDR 1x10",
    ),
    "IncorrectSrgbProfile.png": (
        "removed known bad sRGB iCCP profile",
    ),
    "Incorrect_Srgb_Profile.png": (
        "removed known bad sRGB iCCP profile",
    ),
    "Missplaced_Ihdr.png": (
        "Found Missing Data:[b'IHDR']",
    ),
    "No_Png_Header.png": (
        "File does not start with a png signature",
        "Did prepending a png signature at offset: 0x4",
    ),
    "No_Png_Header_Corrupted_Length.png": (
        "File does not start with a png signature",
        "Did prepending a png signature at offset: 0x2",
    ),
    "No_Png_Header_Missing_Chunk_Corrupted.png": (
        "Did prepending a png signature at offset: 0x3",
        "rebuilt missing IHDR from IDAT scanline size",
        "Selected IHDR 32x32",
    ),
    "PLTE_Empty_Bad_Crc.png": (
        "removed empty non-indexed PLTE chunk",
    ),
    "PLTE_Empty_Good_Crc.png": (
        "rebuilt empty indexed PLTE as grayscale palette",
    ),
    "plte_length_mod_three.png": (
        "rebuilt malformed indexed PLTE as grayscale palette",
    ),
    "plte_too_many_entries.png": (
        "rebuilt oversized indexed PLTE as grayscale palette",
    ),
    "Private_Critical_Chunk_Bad_Crc.png": (
        "turning it into a valid Chunk name: gAMA",
        "Replaced with: 31e8965f",
    ),
    "Private_Critical_Chunk_Crc_Valid.png": (
        "turning it into a valid Chunk name: gAMA",
        "Replaced with: 31e8965f",
    ),
    "Wrong-Chunk-Name-Bad-Crc.png": (
        "turning it into a valid Chunk name: IDAT",
        "stored CRC matched candidate chunk name",
    ),
    "Wrong-Chunk-Name-Crc-Valid.png": (
        "turning it into a valid Chunk name: gAMA",
        "Replaced with: 31e8965f",
    ),
    "chunk_crc.png": (
        "rebuilt IHDR from IDAT scanline size",
        "Selected IHDR 32x32",
    ),
    "chunk_private_critical.png": (
        "renamed known chunk GaMA to gAMA and rebuilt CRC",
    ),
    "chunk_private_critical_badcrc.png": (
        "turning it into a valid Chunk name: gAMA",
        "Replaced with: 31e8965f",
    ),
    "chunk_private_critical_goodcrc.png": (
        "turning it into a valid Chunk name: gAMA",
        "Replaced with: 31e8965f",
    ),
    "chunk_type.png": (
        "turning it into a valid Chunk name: gAMA",
        "Replaced with: 31e8965f",
    ),
    "gama_zero.png": (
        "removed zero gAMA chunk",
    ),
    "length_gama.png": (
        "inferred 1 missing gAMA byte(s) from common gamma value and rebuilt CRC",
    ),
    "length_gifg.png": (
        "trimmed gIFg length from 5 to 4 and rebuilt CRC",
    ),
    "length_hist.png": (
        "hIST length is not Valid :28 must be 30 for PLTE entries",
        "padded hIST length from 28 to 30 with zero frequencies and rebuilt CRC",
    ),
    "ihdr_image_size.png": (
        "rebuilt IHDR from IDAT scanline size",
        "Selected IHDR 32x32",
    ),
    "Unhandled-Critical-Chunk.png": (
        "removed unknown private critical unsafe-to-copy chunk(s): QpZZ",
    ),
}


REPAIR_MATRIX = tuple(
    replace(
        repair,
        summary_contains=_SUMMARY_MARKERS_BY_FIXTURE[repair.fixture],
        validators=_VALIDATORS_BY_FIXTURE[repair.fixture],
    )
    for repair in REPAIR_MATRIX
)


PILLOW_LENIENT_REPAIR_CASES: dict[str, str] = {}
LEGACY_CRC_ONLY_REPAIR_CASES: dict[str, tuple[int, tuple[str, ...], str]] = {}
PILLOW_ONLY_REPAIR_CASES: dict[str, tuple[int, tuple[str, ...], str]] = {}
UNCOVERED_REPAIR_CASES: dict[str, str] = {
    "badlinefeed1.png": "local line-feed corruption candidate; not yet promoted to a strict repair regression",
    "bkgd_after_idat.png": "misplaced ancillary chunk fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "chrm_after_idat.png": "misplaced ancillary chunk fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "chrm_after_plte.png": "misplaced ancillary chunk fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "chunk_length.png": "generic chunk length fixture kept for manual exploration; not yet in strict repair matrix",
    "gama_after_idat.png": "misplaced ancillary chunk fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "gama_after_plte.png": "misplaced ancillary chunk fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "hist_after_idat.png": "misplaced ancillary chunk fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "hist_before_plte.png": "misplaced ancillary chunk fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "iccp_after_idat.png": "misplaced ancillary chunk fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "iccp_after_plte.png": "misplaced ancillary chunk fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "ihdr_16bit_palette.png": "IHDR value repair fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "ihdr_1bit_alpha.png": "IHDR value repair fixture kept for manual exploration; not yet in strict repair matrix",
    "ihdr_bit_depth.png": "IHDR value repair fixture kept for manual exploration; not yet in strict repair matrix",
    "ihdr_color_type.png": "IHDR value repair fixture kept for manual exploration; not yet in strict repair matrix",
    "ihdr_compression_method.png": "IHDR value repair fixture kept for manual exploration; not yet in strict repair matrix",
    "ihdr_filter_method.png": "IHDR value repair fixture kept for manual exploration; not yet in strict repair matrix",
    "ihdr_interlace_method.png": "IHDR value repair fixture kept for manual exploration; not yet in strict repair matrix",
    "itxt_compression_flag.png": "iTXt metadata repair fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "itxt_compression_method.png": "iTXt metadata repair fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "itxt_keyword_length.png": "iTXt metadata fixture accepted by libpng; not yet in strict repair matrix",
    "itxt_keyword_length_2.png": "iTXt metadata fixture accepted by libpng; not yet in strict repair matrix",
    "length_bkgd_gray.png": "bKGD length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_bkgd_palette.png": "bKGD length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_bkgd_rgb.png": "bKGD length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_chrm.png": "cHRM length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_iend.png": "IEND length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_ihdr.png": "IHDR length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_offs.png": "oFFs length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_phys.png": "pHYs length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_sbit.png": "sBIT length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_sbit_2.png": "sBIT length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_srgb.png": "sRGB length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_ster.png": "sTER length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_time.png": "tIME length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_trns_gray.png": "grayscale tRNS length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_trns_palette.png": "indexed tRNS length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "length_trns_rgb.png": "truecolor tRNS length repair fixture covered by targeted tests; not yet in strict repair matrix",
    "linefeedcorruption1.png": "line-feed corruption fixture covered by targeted tests; not yet in strict repair matrix",
    "linefeedcorruption2.png": "line-feed corruption fixture covered by targeted tests; not yet in strict repair matrix",
    "linefeedcorruption3.png": "line-feed corruption fixture covered by targeted tests; not yet in strict repair matrix",
    "missing_idat.png": "missing IDAT fixture covered by targeted tests; not yet in strict repair matrix",
    "missing_ihdr.png": "missing IHDR fixture covered by targeted tests; not yet in strict repair matrix",
    "missing_plte.png": "missing PLTE fixture covered by targeted tests; not yet in strict repair matrix",
    "missing_plte_2.png": "missing PLTE fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_bkgd.png": "duplicate bKGD fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_chrm.png": "duplicate cHRM fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_gama.png": "duplicate gAMA fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_hist.png": "duplicate hIST fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_iccp.png": "duplicate iCCP fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_ihdr.png": "duplicate IHDR fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_offs.png": "duplicate oFFs fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_pcal.png": "duplicate pCAL fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_phys.png": "duplicate pHYs fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_plte.png": "duplicate PLTE fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_sbit.png": "duplicate sBIT fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_scal.png": "duplicate sCAL fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_srgb.png": "duplicate sRGB fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_ster.png": "duplicate sTER fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_time.png": "duplicate tIME fixture covered by targeted tests; not yet in strict repair matrix",
    "multiple_trns.png": "duplicate tRNS fixture covered by targeted tests; not yet in strict repair matrix",
    "nonconsecutive_idat.png": "non-consecutive IDAT fixture covered by targeted tests; not yet in strict repair matrix",
    "offs_after_idat.png": "misplaced oFFs fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "offs_unit_specifier.png": "oFFs unit specifier fixture covered by targeted tests; not yet in strict repair matrix",
    "pcal_after_idat.png": "misplaced pCAL fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "phys_after_idat.png": "misplaced pHYs fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "phys_unit_specifier.png": "pHYs unit specifier fixture covered by targeted tests; not yet in strict repair matrix",
    "plte_after_idat.png": "misplaced PLTE fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "sbit_after_idat.png": "misplaced sBIT fixture covered by targeted runtime tests; not yet in strict repair matrix",
    "noidat.png": "terminal malformed PNG with no IDAT image stream to recover",
    "xs7n0g01.png": "local schaik sample with invalid PNG dimensions; not yet a repair regression",
}


REPAIR_CASES = {
    repair.fixture: (repair.max_saves, repair.expected_outputs)
    for repair in REPAIR_MATRIX
}
