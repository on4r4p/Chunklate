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
    "first_chunk:IHDR",
    "ihdr_dimensions:32x32",
    "has_chunk:PLTE",
    "plte_non_empty",
    "gama_non_zero",
    "idat_decompress",
    "last_chunk:IEND",
)
VALID_32_PALETTE_NO_GAMA = (
    "first_chunk:IHDR",
    "ihdr_dimensions:32x32",
    "has_chunk:PLTE",
    "plte_non_empty",
    "idat_decompress",
    "last_chunk:IEND",
)
VALID_32_NO_PLTE = (
    "first_chunk:IHDR",
    "ihdr_dimensions:32x32",
    "missing_chunk:PLTE",
    "gama_non_zero",
    "idat_decompress",
    "last_chunk:IEND",
)
VALID_260 = (
    "first_chunk:IHDR",
    "ihdr_dimensions:260x195",
    "gama_non_zero",
    "idat_decompress",
    "last_chunk:IEND",
)
VALID_477 = (
    "first_chunk:IHDR",
    "ihdr_dimensions:477x599",
    "gama_non_zero",
    "idat_decompress",
    "last_chunk:IEND",
)
VALID_272_PROFILE_REMOVED = (
    "first_chunk:IHDR",
    "ihdr_dimensions:272x170",
    "missing_chunk:iCCP",
    "gama_non_zero",
    "idat_decompress",
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
        "first_chunk:IHDR",
        "ihdr_dimensions:1920x1200",
        "idat_decompress",
        "last_chunk:IEND",
    ),
    "IDAT_Partial_Blackfill.png": (
        "first_chunk:IHDR",
        "ihdr_dimensions:1x10",
        "idat_decompress",
        "idat_decompressed_len:40",
        "last_chunk:IEND",
    ),
    "IncorrectSrgbProfile.png": VALID_272_PROFILE_REMOVED,
    "Incorrect_Srgb_Profile.png": VALID_272_PROFILE_REMOVED,
    "Missplaced_Ihdr.png": VALID_32_PALETTE,
    "No_Png_Header.png": VALID_260,
    "No_Png_Header_Corrupted_Length.png": VALID_260,
    "No_Png_Header_Missing_Chunk_Corrupted.png": VALID_32_PALETTE + ("has_chunk:hIST",),
    "PLTE_Empty_Bad_Crc.png": VALID_32_NO_PLTE,
    "PLTE_Empty_Good_Crc.png": VALID_32_PALETTE,
    "Private_Critical_Chunk_Bad_Crc.png": VALID_32_PALETTE + ("missing_chunk:baMA",),
    "Private_Critical_Chunk_Crc_Valid.png": VALID_32_PALETTE + ("missing_chunk:baMA",),
    "Wrong-Chunk-Name-Bad-Crc.png": (
        "first_chunk:IHDR",
        "ihdr_dimensions:1642x1095",
        "gama_non_zero",
        "idat_decompress",
        "last_chunk:IEND",
    ),
    "Wrong-Chunk-Name-Crc-Valid.png": VALID_32_PALETTE,
    "chunk_crc.png": VALID_32_PALETTE,
    "chunk_private_critical.png": VALID_32_PALETTE + ("missing_chunk:GaMA",),
    "chunk_private_critical_badcrc.png": VALID_32_PALETTE + ("missing_chunk:baMA",),
    "chunk_private_critical_goodcrc.png": VALID_32_PALETTE + ("missing_chunk:baMA",),
    "chunk_type.png": VALID_32_PALETTE,
    "gama_zero.png": (
        "first_chunk:IHDR",
        "ihdr_dimensions:32x32",
        "missing_chunk:gAMA",
        "idat_decompress",
        "last_chunk:IEND",
    ),
    "ihdr_image_size.png": VALID_32_PALETTE,
    "Unhandled-Critical-Chunk.png": VALID_32_PALETTE_NO_GAMA + ("missing_chunk:QpZZ",),
}


REPAIR_MATRIX = tuple(
    replace(repair, validators=_VALIDATORS_BY_FIXTURE[repair.fixture])
    for repair in REPAIR_MATRIX
)


PILLOW_LENIENT_REPAIR_CASES: dict[str, str] = {}
LEGACY_CRC_ONLY_REPAIR_CASES: dict[str, tuple[int, tuple[str, ...], str]] = {}
PILLOW_ONLY_REPAIR_CASES: dict[str, tuple[int, tuple[str, ...], str]] = {}
UNCOVERED_REPAIR_CASES: dict[str, str] = {}


REPAIR_CASES = {
    repair.fixture: (repair.max_saves, repair.expected_outputs)
    for repair in REPAIR_MATRIX
}
