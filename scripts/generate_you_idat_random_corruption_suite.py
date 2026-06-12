#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import png


DEFAULT_SOURCE = Path("brokenjavapngsuite/you.png")
DEFAULT_OUTPUT_DIR = Path("brokenjavapngsuite/you_idat_random_corruptions_1_to_20_bytes")
DEFAULT_BYTE_COUNTS = "1-20"
DEFAULT_SPLIT_IDAT_COUNT = 4
DEFAULT_DOUBLE_IDAT_FILES = 6


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


def singular_or_plural(byte_count: int) -> str:
    return "Byte" if int(byte_count) == 1 else "Bytes"


def iter_idat_chunks(source_data: bytes) -> tuple[png.PngChunk, ...]:
    return tuple(chunk for chunk in png.iter_chunks(source_data) if chunk.chunk_type == b"IDAT")


def raw_chunk(chunk_type: bytes, payload: bytes, *, stored_crc: int | None = None) -> bytes:
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF if stored_crc is None else int(stored_crc)
    return struct.pack("!I", len(payload)) + chunk_type + payload + struct.pack("!I", crc)


def replace_chunk(source_data: bytes, chunk: png.PngChunk, payload: bytes, *, stored_crc: int) -> bytes:
    chunk_start = int(chunk.offset)
    chunk_end = chunk_start + 12 + int(chunk.length)
    return source_data[:chunk_start] + raw_chunk(b"IDAT", payload, stored_crc=stored_crc) + source_data[chunk_end:]


def random_bytes(rng: random.Random, byte_count: int) -> bytes:
    return bytes(rng.randrange(0, 256) for _ in range(byte_count))


def changed_bytes(rng: random.Random, original: bytes) -> bytes:
    values: list[int] = []
    for byte in original:
        replacement = rng.randrange(0, 255)
        if replacement >= byte:
            replacement += 1
        values.append(replacement)
    return bytes(values)


def corrupt_payload(
    payload: bytes,
    *,
    edit_kind: str,
    byte_count: int,
    offset: int,
    rng: random.Random,
) -> tuple[bytes, bytes, bytes]:
    original = payload[offset : offset + byte_count]
    if edit_kind == "Missing":
        return payload[:offset] + payload[offset + byte_count :], original, b""
    if edit_kind == "Extra":
        inserted = random_bytes(rng, byte_count)
        return payload[:offset] + inserted + payload[offset:], b"", inserted
    if edit_kind == "Changed":
        replacement = changed_bytes(rng, original)
        return payload[:offset] + replacement + payload[offset + byte_count :], original, replacement
    raise ValueError(f"unknown edit kind: {edit_kind}")


def random_offset(rng: random.Random, payload_len: int, edit_kind: str, byte_count: int) -> int:
    if edit_kind == "Extra":
        return rng.randrange(0, payload_len + 1)
    if byte_count > payload_len:
        raise ValueError("byte count does not fit in selected IDAT payload")
    return rng.randrange(0, payload_len - byte_count + 1)


def validate_bad_crc(
    generated_data: bytes,
    *,
    expected_bad_idat_indexes: set[int],
    expected_idat_count: int,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    idat_chunks = iter_idat_chunks(generated_data)
    if len(idat_chunks) != expected_idat_count:
        raise AssertionError(f"generated PNG has {len(idat_chunks)} IDAT chunks, expected {expected_idat_count}")

    bad_indexes = {index for index, chunk in enumerate(idat_chunks) if not chunk.crc_ok}
    if bad_indexes != set(expected_bad_idat_indexes):
        raise AssertionError(f"bad IDAT indexes {sorted(bad_indexes)} != expected {sorted(expected_bad_idat_indexes)}")

    for index, chunk in enumerate(idat_chunks):
        records.append(
            {
                "idat_index": index,
                "chunk_offset": int(chunk.offset),
                "data_offset": int(chunk.offset) + 8,
                "length": int(chunk.length),
                "stored_crc": f"{int(chunk.crc):08x}",
                "computed_crc": f"{int(chunk.computed_crc):08x}",
                "crc_ok": bool(chunk.crc_ok),
            }
        )
    return records


def corruption_filename(edit_kind: str, byte_count: int) -> str:
    return "You_IDAT_Chunk00_%s_%02d_%s_StoredOriginalCRC.png" % (
        edit_kind,
        byte_count,
        singular_or_plural(byte_count),
    )


def double_corruption_filename(case_index: int, edits: list[dict[str, object]]) -> str:
    edit_label = "_".join(
        "%s%02d" % (str(edit["edit_kind"]), int(edit["byte_count"]))
        for edit in edits
    )
    return f"You_MultiIDAT_TwoCorruptIDATs_Case{case_index:02d}_{edit_label}_StoredOriginalCRCs.png"


def split_payload(payload: bytes, split_count: int) -> tuple[bytes, ...]:
    if split_count < 2:
        raise ValueError("split count must be at least 2")
    if split_count > len(payload):
        raise ValueError("split count cannot exceed payload length")
    base, remainder = divmod(len(payload), split_count)
    chunks: list[bytes] = []
    cursor = 0
    for index in range(split_count):
        part_len = base + (1 if index < remainder else 0)
        chunks.append(payload[cursor : cursor + part_len])
        cursor += part_len
    return tuple(chunks)


def build_split_idat_png(source_data: bytes, source_idat: png.PngChunk, split_payloads: tuple[bytes, ...]) -> bytes:
    chunk_start = int(source_idat.offset)
    chunk_end = chunk_start + 12 + int(source_idat.length)
    split_chunks = b"".join(raw_chunk(b"IDAT", payload) for payload in split_payloads)
    return source_data[:chunk_start] + split_chunks + source_data[chunk_end:]


def generate_single_idat_records(
    source_data: bytes,
    source_idat: png.PngChunk,
    *,
    byte_counts: tuple[int, ...],
    rng: random.Random,
    output_dir: Path,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    payload = bytes(source_idat.data)
    for byte_count in byte_counts:
        for edit_kind in ("Extra", "Missing", "Changed"):
            offset = random_offset(rng, len(payload), edit_kind, byte_count)
            corrupted_payload, source_bytes, corruption_bytes = corrupt_payload(
                payload,
                edit_kind=edit_kind,
                byte_count=byte_count,
                offset=offset,
                rng=rng,
            )
            generated = replace_chunk(source_data, source_idat, corrupted_payload, stored_crc=int(source_idat.crc))
            idat_records = validate_bad_crc(
                generated,
                expected_bad_idat_indexes={0},
                expected_idat_count=1,
            )
            filename = corruption_filename(edit_kind, byte_count)
            (output_dir / filename).write_bytes(generated)
            records.append(
                {
                    "file": filename,
                    "group": "single_corrupt_idat",
                    "edit_kind": edit_kind,
                    "byte_count": byte_count,
                    "selected_idat_index": 0,
                    "idat_payload_offset": offset,
                    "png_data_offset": int(source_idat.offset) + 8 + offset,
                    "source_bytes_hex": source_bytes.hex(),
                    "corruption_bytes_hex": corruption_bytes.hex(),
                    "idat_length_delta": len(corrupted_payload) - len(payload),
                    "idats": idat_records,
                }
            )
    return records


def generate_double_idat_records(
    source_data: bytes,
    source_idat: png.PngChunk,
    *,
    split_count: int,
    file_count: int,
    rng: random.Random,
    output_dir: Path,
) -> list[dict[str, object]]:
    source_payloads = split_payload(bytes(source_idat.data), split_count)
    source_split_crcs = [zlib.crc32(b"IDAT" + payload) & 0xFFFFFFFF for payload in source_payloads]
    records: list[dict[str, object]] = []

    for case_index in range(1, file_count + 1):
        selected_indexes = sorted(rng.sample(range(split_count), 2))
        payloads = list(source_payloads)
        edits: list[dict[str, object]] = []

        for selected_index in selected_indexes:
            edit_kind = rng.choice(("Extra", "Missing", "Changed"))
            byte_count = rng.choice((1, 2))
            original_payload = source_payloads[selected_index]
            offset = random_offset(rng, len(original_payload), edit_kind, byte_count)
            corrupted_payload, source_bytes, corruption_bytes = corrupt_payload(
                original_payload,
                edit_kind=edit_kind,
                byte_count=byte_count,
                offset=offset,
                rng=rng,
            )
            payloads[selected_index] = corrupted_payload
            edits.append(
                {
                    "selected_idat_index": selected_index,
                    "edit_kind": edit_kind,
                    "byte_count": byte_count,
                    "idat_payload_offset": offset,
                    "source_bytes_hex": source_bytes.hex(),
                    "corruption_bytes_hex": corruption_bytes.hex(),
                    "idat_length_delta": len(corrupted_payload) - len(original_payload),
                }
            )

        chunk_start = int(source_idat.offset)
        chunk_end = chunk_start + 12 + int(source_idat.length)
        idat_bytes = b"".join(
            raw_chunk(b"IDAT", payload, stored_crc=source_split_crcs[index])
            for index, payload in enumerate(payloads)
        )
        generated = source_data[:chunk_start] + idat_bytes + source_data[chunk_end:]
        idat_records = validate_bad_crc(
            generated,
            expected_bad_idat_indexes=set(selected_indexes),
            expected_idat_count=split_count,
        )
        filename = double_corruption_filename(case_index, edits)
        (output_dir / filename).write_bytes(generated)
        records.append(
            {
                "file": filename,
                "group": "two_corrupt_idats",
                "split_idat_count": split_count,
                "edits": edits,
                "idats": idat_records,
            }
        )
    return records


def write_manifest(output_dir: Path, manifest: dict[str, object]) -> None:
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# You IDAT Random Stored-Original-CRC Corruption Suite",
        "",
        "Generated from `brokenjavapngsuite/you.png`.",
        "Every corrupted IDAT keeps the CRC that matched its pre-corruption payload.",
        "That means the stored IDAT CRC intentionally does not match the corrupted payload.",
        "",
        f"Seed: `{manifest['seed']}`",
        "",
        "| File | Group | Edit summary | Bad IDAT indexes |",
        "| --- | --- | --- | --- |",
    ]
    for record in manifest["records"]:
        if record["group"] == "single_corrupt_idat":
            edit_summary = "%s %s byte(s) at IDAT offset %s" % (
                record["edit_kind"],
                record["byte_count"],
                record["idat_payload_offset"],
            )
            bad_indexes = "0"
        else:
            edit_summary = ", ".join(
                "IDAT %s %s %s byte(s) at offset %s"
                % (
                    edit["selected_idat_index"],
                    edit["edit_kind"],
                    edit["byte_count"],
                    edit["idat_payload_offset"],
                )
                for edit in record["edits"]
            )
            bad_indexes = ", ".join(str(edit["selected_idat_index"]) for edit in record["edits"])
        lines.append(f"| {record['file']} | {record['group']} | {edit_summary} | {bad_indexes} |")
    lines.append("")
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def generate_suite(
    source_path: Path,
    output_dir: Path,
    *,
    byte_counts: tuple[int, ...],
    seed: int,
    split_count: int,
    double_idat_files: int,
    force: bool,
) -> dict[str, object]:
    source_data = source_path.read_bytes()
    idats = iter_idat_chunks(source_data)
    if not idats:
        raise ValueError("source PNG has no IDAT chunk")
    if not all(chunk.crc_ok for chunk in idats):
        raise ValueError("source PNG has at least one invalid IDAT CRC")

    if output_dir.exists():
        if not force:
            raise FileExistsError(f"{output_dir} already exists; pass --force to replace it")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    source_idat = idats[rng.randrange(0, len(idats))]
    records = generate_single_idat_records(
        source_data,
        source_idat,
        byte_counts=byte_counts,
        rng=rng,
        output_dir=output_dir,
    )
    records.extend(
        generate_double_idat_records(
            source_data,
            source_idat,
            split_count=split_count,
            file_count=double_idat_files,
            rng=rng,
            output_dir=output_dir,
        )
    )

    manifest: dict[str, object] = {
        "suite": "You IDAT random stored-original-CRC corruption suite",
        "source": str(source_path),
        "seed": seed,
        "source_idat_count": len(idats),
        "selected_source_idat_index": idats.index(source_idat),
        "selected_source_idat_offset": int(source_idat.offset),
        "selected_source_idat_data_offset": int(source_idat.offset) + 8,
        "selected_source_idat_length": int(source_idat.length),
        "selected_source_idat_crc": f"{int(source_idat.crc):08x}",
        "crc_policy": (
            "Single-IDAT files keep the source IDAT CRC. Two-corrupt-IDAT files first split "
            "the source IDAT stream into valid IDAT chunks, then each corrupted split IDAT "
            "keeps the CRC of its pre-corruption split payload."
        ),
        "records": records,
    }
    write_manifest(output_dir, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate random stored-original-CRC IDAT corruptions from you.png.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--byte-counts", default=DEFAULT_BYTE_COUNTS)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--split-idat-count", type=int, default=DEFAULT_SPLIT_IDAT_COUNT)
    parser.add_argument("--double-idat-files", type=int, default=DEFAULT_DOUBLE_IDAT_FILES)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    seed = int.from_bytes(os.urandom(8), "big") if args.seed is None else int(args.seed)
    manifest = generate_suite(
        args.source,
        args.output_dir,
        byte_counts=parse_byte_counts(args.byte_counts),
        seed=seed,
        split_count=args.split_idat_count,
        double_idat_files=args.double_idat_files,
        force=args.force,
    )
    print("generated %d corrupted PNG files in %s" % (len(manifest["records"]), args.output_dir))
    print("seed: %s" % manifest["seed"])
    print("source IDAT count: %s" % manifest["source_idat_count"])
    print("selected source IDAT index: %s" % manifest["selected_source_idat_index"])
    print("stored source IDAT CRC: %s" % manifest["selected_source_idat_crc"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
