from __future__ import annotations

import zlib
from dataclasses import dataclass
from pathlib import Path

from chunklate.png import iter_chunks, validate_png_structure

try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None


@dataclass(frozen=True)
class RepairValidationContext:
    case: object
    fixed_path: Path
    summary_path: Path | None = None


def validate_repaired_case(case, fixed_path: Path, summary_path: Path | None = None) -> list[str]:
    context = RepairValidationContext(case=case, fixed_path=fixed_path, summary_path=summary_path)
    errors: list[str] = []

    errors.extend(validate_png_structure_and_crc(context))
    errors.extend(validate_pillow_verify(context))

    if not case.validators:
        errors.append("%s: missing repair-specific validators" % case.fixture)

    for validator in case.validators:
        errors.extend(run_validator(validator, context))

    return errors


def validate_png_structure_and_crc(context: RepairValidationContext) -> list[str]:
    validation = validate_png_structure(context.fixed_path.read_bytes())
    if validation.errors:
        return [
            "invalid repaired PNG %s: %s"
            % (context.fixed_path.name, "; ".join(validation.errors))
        ]
    return []


def validate_pillow_verify(context: RepairValidationContext) -> list[str]:
    if Image is None:
        return []

    try:
        with Image.open(context.fixed_path) as img:
            img.verify()
    except Exception as exc:
        return ["Pillow rejected repaired PNG %s: %s" % (context.fixed_path.name, exc)]
    return []


def run_validator(validator: str, context: RepairValidationContext) -> list[str]:
    if validator == "idat_decompress":
        return validate_idat_decompress(context)
    if validator == "plte_non_empty":
        return validate_plte_non_empty(context)
    if validator == "gama_non_zero":
        return validate_gama_non_zero(context)

    name, _, argument = validator.partition(":")
    if name == "ihdr_dimensions":
        return validate_ihdr_dimensions(context, argument)
    if name == "idat_decompressed_len":
        return validate_idat_decompressed_len(context, argument)
    if name == "has_chunk":
        return validate_has_chunk(context, argument)
    if name == "missing_chunk":
        return validate_missing_chunk(context, argument)
    if name == "first_chunk":
        return validate_first_chunk(context, argument)
    if name == "last_chunk":
        return validate_last_chunk(context, argument)

    return ["unknown repair validator %r for %s" % (validator, context.case.fixture)]


def read_chunks(context: RepairValidationContext):
    try:
        return list(iter_chunks(context.fixed_path.read_bytes()))
    except Exception as exc:
        return exc


def chunk_names(context: RepairValidationContext) -> list[bytes] | list[str]:
    chunks = read_chunks(context)
    if isinstance(chunks, Exception):
        return ["chunk parse failed: %s" % chunks]
    return [chunk.chunk_type for chunk in chunks]


def validate_ihdr_dimensions(context: RepairValidationContext, expected: str) -> list[str]:
    chunks = read_chunks(context)
    if isinstance(chunks, Exception):
        return ["cannot read IHDR dimensions: %s" % chunks]
    if not chunks or chunks[0].chunk_type != b"IHDR":
        return ["first chunk is not IHDR"]

    ihdr = chunks[0].data
    width = int.from_bytes(ihdr[0:4], "big")
    height = int.from_bytes(ihdr[4:8], "big")
    actual = "%sx%s" % (width, height)
    if actual != expected:
        return ["expected IHDR dimensions %s, got %s" % (expected, actual)]
    return []


def validate_idat_decompress(context: RepairValidationContext) -> list[str]:
    errors, _data = decompress_idat(context)
    return errors


def validate_idat_decompressed_len(context: RepairValidationContext, expected: str) -> list[str]:
    errors, data = decompress_idat(context)
    if errors:
        return errors
    expected_len = int(expected)
    if len(data) != expected_len:
        return ["expected decompressed IDAT length %s, got %s" % (expected_len, len(data))]
    return []


def decompress_idat(context: RepairValidationContext) -> tuple[list[str], bytes]:
    chunks = read_chunks(context)
    if isinstance(chunks, Exception):
        return ["cannot read IDAT chunks: %s" % chunks], b""

    stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    if not stream:
        return ["missing IDAT chunk"], b""
    try:
        return [], zlib.decompress(stream)
    except Exception as exc:
        return ["IDAT stream does not decompress: %s" % exc], b""


def validate_plte_non_empty(context: RepairValidationContext) -> list[str]:
    chunks = read_chunks(context)
    if isinstance(chunks, Exception):
        return ["cannot read PLTE chunk: %s" % chunks]

    plte_chunks = [chunk for chunk in chunks if chunk.chunk_type == b"PLTE"]
    if not plte_chunks:
        return ["missing PLTE chunk"]
    bad_lengths = [len(chunk.data) for chunk in plte_chunks if len(chunk.data) == 0 or len(chunk.data) % 3]
    if bad_lengths:
        return ["malformed PLTE lengths after repair: %s" % bad_lengths]
    return []


def validate_gama_non_zero(context: RepairValidationContext) -> list[str]:
    chunks = read_chunks(context)
    if isinstance(chunks, Exception):
        return ["cannot read gAMA chunk: %s" % chunks]

    gama_values = [
        int.from_bytes(chunk.data, "big")
        for chunk in chunks
        if chunk.chunk_type == b"gAMA"
    ]
    if not gama_values:
        return ["missing gAMA chunk"]
    if any(value == 0 for value in gama_values):
        return ["gAMA value is still zero"]
    return []


def validate_has_chunk(context: RepairValidationContext, chunk_name: str) -> list[str]:
    expected = chunk_name.encode()
    names = chunk_names(context)
    if expected not in names:
        return ["expected chunk %s, got %s" % (chunk_name, names)]
    return []


def validate_missing_chunk(context: RepairValidationContext, chunk_name: str) -> list[str]:
    forbidden = chunk_name.encode()
    names = chunk_names(context)
    if forbidden in names:
        return ["chunk %s is still present" % chunk_name]
    return []


def validate_first_chunk(context: RepairValidationContext, chunk_name: str) -> list[str]:
    expected = chunk_name.encode()
    names = chunk_names(context)
    if not names or names[0] != expected:
        return ["expected first chunk %s, got %s" % (chunk_name, names[:1])]
    return []


def validate_last_chunk(context: RepairValidationContext, chunk_name: str) -> list[str]:
    expected = chunk_name.encode()
    names = chunk_names(context)
    if not names or names[-1] != expected:
        return ["expected last chunk %s, got %s" % (chunk_name, names[-1:])]
    return []
