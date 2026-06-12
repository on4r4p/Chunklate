#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import struct
import zlib
from pathlib import Path

from chunklate import png


DEFAULT_SOURCE = Path("Kagebushin.png")
DEFAULT_OUTPUT_DIR = Path("brokenjavapngsuite/kagebushin_idat_stored_original_crc_corruptions_1_to_20_bytes")
DEFAULT_IDAT_OFFSET = 1_061_222
DEFAULT_BYTE_COUNTS = "1-20"


def parse_byte_counts(spec: str) -> tuple[int, ...]:
    counts: set[int] = set()
    for raw_part in str(spec).split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            raw_start, raw_end = part.split("-", 1)
            start = int(raw_start, 10)
            end = int(raw_end, 10)
            if end < start:
                raise ValueError(f"invalid descending byte-count range: {part}")
            counts.update(range(start, end + 1))
        else:
            counts.add(int(part, 10))
    if not counts:
        raise ValueError("at least one byte count is required")
    if min(counts) <= 0:
        raise ValueError("byte counts must be positive")
    return tuple(sorted(counts))


def first_idat_chunk(data: bytes) -> png.PngChunk:
    for chunk in png.iter_chunks(data):
        if chunk.chunk_type == b"IDAT":
            return chunk
    raise ValueError("source PNG has no IDAT chunk")


def build_png_with_idat_payload(source_data: bytes, chunk: png.PngChunk, payload: bytes) -> bytes:
    chunk_start = int(chunk.offset)
    data_start = chunk_start + 8
    crc_start = data_start + int(chunk.length)
    crc_end = crc_start + 4
    original_crc = source_data[crc_start:crc_end]
    return (
        source_data[:chunk_start]
        + struct.pack("!I", len(payload))
        + b"IDAT"
        + payload
        + original_crc
        + source_data[crc_end:]
    )


def singular_or_plural(byte_count: int) -> str:
    return "Byte" if int(byte_count) == 1 else "Bytes"


def corruption_filename(kind: str, byte_count: int) -> str:
    return "Kagebushin_IDAT_%s_%02d_%s_StoredOriginalCRC.png" % (
        kind,
        byte_count,
        singular_or_plural(byte_count),
    )


def validate_generated_png(
    generated_data: bytes,
    *,
    source_crc: int,
    expected_length: int,
) -> tuple[str, str]:
    chunk = first_idat_chunk(generated_data)
    if int(chunk.length) != int(expected_length):
        raise AssertionError(f"generated IDAT length {chunk.length} != expected {expected_length}")
    if int(chunk.crc) != int(source_crc):
        raise AssertionError("generated PNG did not preserve the original stored IDAT CRC")
    computed_crc = zlib.crc32(chunk.chunk_type + chunk.data) & 0xFFFFFFFF
    if computed_crc == int(source_crc):
        raise AssertionError("generated corruption unexpectedly still matches the original IDAT CRC")
    return f"{chunk.crc:08x}", f"{computed_crc:08x}"


def write_manifest(output_dir: Path, records: list[dict[str, object]]) -> None:
    manifest = {
        "suite": "Kagebushin IDAT stored-original-CRC corruption suite",
        "crc_policy": (
            "Each corrupted PNG stores the source IDAT CRC. The corrupted IDAT payload CRC "
            "does not match, which gives Chunklate an OldCrc oracle for SBB/CRC-forge repair."
        ),
        "records": records,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Kagebushin IDAT Stored-Original-CRC Corruption Suite",
        "",
        "Each PNG corrupts the first IDAT payload while keeping the source IDAT CRC stored in the chunk.",
        "That means the PNG chunk CRC is intentionally wrong for the corrupted payload, but useful as OldCrc.",
        "",
        "| File | Kind | Bytes | IDAT payload offset | PNG byte offset | Stored CRC | Corrupted payload CRC |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for record in records:
        lines.append(
            "| {file} | {kind} | {byte_count} | {idat_payload_offset} | {png_data_offset} | {stored_crc} | {computed_crc} |".format(
                **record
            )
        )
    lines.append("")
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def generate_suite(source_path: Path, output_dir: Path, byte_counts: tuple[int, ...], offset: int) -> list[dict[str, object]]:
    source_data = source_path.read_bytes()
    chunk = first_idat_chunk(source_data)
    if not chunk.crc_ok:
        raise ValueError("source IDAT CRC is not valid")
    payload = bytes(chunk.data)
    max_count = max(byte_counts)
    if int(offset) < 0 or int(offset) + max_count > len(payload):
        raise ValueError("offset plus max byte count must fit inside the source IDAT payload")

    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    source_crc = int(chunk.crc)
    png_data_offset = int(chunk.offset) + 8 + int(offset)

    for byte_count in byte_counts:
        original_bytes = payload[offset : offset + byte_count]
        extra_bytes = b"\x00" * byte_count
        changed_bytes = bytes(byte ^ 0xFF for byte in original_bytes)
        corruptions = (
            ("Missing", payload[:offset] + payload[offset + byte_count :], original_bytes),
            ("Extra", payload[:offset] + extra_bytes + payload[offset:], extra_bytes),
            ("Changed", payload[:offset] + changed_bytes + payload[offset + byte_count :], changed_bytes),
        )
        for kind, corrupted_payload, corruption_bytes in corruptions:
            filename = corruption_filename(kind, byte_count)
            generated_data = build_png_with_idat_payload(source_data, chunk, corrupted_payload)
            stored_crc, computed_crc = validate_generated_png(
                generated_data,
                source_crc=source_crc,
                expected_length=len(corrupted_payload),
            )
            (output_dir / filename).write_bytes(generated_data)
            records.append(
                {
                    "file": filename,
                    "kind": kind,
                    "byte_count": byte_count,
                    "idat_payload_offset": int(offset),
                    "png_data_offset": png_data_offset,
                    "stored_crc": stored_crc,
                    "computed_crc": computed_crc,
                    "source_bytes_hex": original_bytes.hex(),
                    "corruption_bytes_hex": corruption_bytes.hex(),
                    "idat_length_delta": len(corrupted_payload) - len(payload),
                }
            )
    write_manifest(output_dir, records)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Kagebushin IDAT stored-original-CRC corruption fixtures.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--offset", type=int, default=DEFAULT_IDAT_OFFSET, help="IDAT payload offset to corrupt.")
    parser.add_argument(
        "--byte-counts",
        default=DEFAULT_BYTE_COUNTS,
        help="Comma-separated counts and ranges, for example 1,2,6-10 or 1-20.",
    )
    args = parser.parse_args()

    records = generate_suite(
        args.source,
        args.output_dir,
        parse_byte_counts(args.byte_counts),
        args.offset,
    )
    print("generated %d corrupted PNG files in %s" % (len(records), args.output_dir))
    print("stored original IDAT CRC: %s" % records[0]["stored_crc"])
    print("IDAT payload offset: %s" % records[0]["idat_payload_offset"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
