#!/usr/bin/env python3
import binascii
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_validation_runtime
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk


def build_runtime(calls):
    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Emoj":
            return ":%s:" % args[0]
        return "candy:%s" % kind

    return chunk_validation_runtime.ChunkValidationRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        checkpoint=lambda *args: calls.append(("checkpoint", args)) or "checkpoint-result",
        end=lambda: calls.append(("end",)),
        chunk_story_add_if_no_next=lambda *args: calls.append(("chunk_story", args)),
    )


def checkpoint_args(calls):
    matches = [call[1] for call in calls if call[0] == "checkpoint"]
    assert len(matches) == 1
    return matches[0]


def test_check_length_runtime_routes_found_next_chunk_checkpoint():
    calls = []
    data = PNG_SIGNATURE + build_png_chunk(b"IHDR", b"\x00" * 13) + IEND_CHUNK

    result = chunk_validation_runtime.run_check_length(
        build_runtime(calls),
        chunk_validation_runtime.CheckLengthContext(
            data_bytes=data,
            current_length_offset=len(PNG_SIGNATURE) * 2,
            previous_chunk=b"PNG",
            idat_average_length=0,
        ),
        "",
        "0000000d",
        b"IHDR",
    )

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == (
        False,
        False,
        "CheckLength",
        b"IHDR",
        ["-Found NextChunk"],
        "0000000d",
    )


def test_check_length_runtime_routes_missing_next_chunk_checkpoint():
    calls = []
    data = PNG_SIGNATURE + b"\x00\x00\x00\x04IDATab"

    result = chunk_validation_runtime.run_check_length(
        build_runtime(calls),
        chunk_validation_runtime.CheckLengthContext(
            data_bytes=data,
            current_length_offset=len(PNG_SIGNATURE) * 2,
            previous_chunk=b"IHDR",
            idat_average_length=9,
        ),
        "",
        "00000004",
        b"IDAT",
    )

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == (
        True,
        False,
        "CheckLength",
        b"IDAT",
        ["-No NextChunk"],
        b"IDAT",
        "00000004",
        b"IHDR",
    )


def test_checksum_runtime_valid_crc_records_chunk_story_and_checkpoint():
    calls = []
    chunk_type = b"IDAT"
    chunk_data = b"abc"
    crc = binascii.crc32(chunk_type + chunk_data).to_bytes(4, byteorder="big").hex()
    history = []
    indexes = []

    result = chunk_validation_runtime.run_checksum(
        build_runtime(calls),
        chunk_validation_runtime.ChecksumContext(
            current_length_offset=16,
            crc_offset=30,
            crc_offset_hex="0xf",
            original_chunk_type=b"IDAT",
            original_crc=crc,
            original_length="00000003",
            current_data_offset=24,
            chunks_history=history,
            chunks_history_index=indexes,
        ),
        chunk_type.hex(),
        chunk_data.hex(),
        crc,
    )

    assert result == "checkpoint-result"
    assert [call for call in calls if call[0] == "chunk_story"] == [
        ("chunk_story", (history, indexes, None, b"IDAT", 16, 38, 3))
    ]
    assert checkpoint_args(calls) == (
        False,
        False,
        "Checksum",
        b"IDAT",
        ["-Crc is correct"],
    )


def test_checksum_runtime_invalid_crc_routes_wrong_crc_checkpoint():
    calls = []

    result = chunk_validation_runtime.run_checksum(
        build_runtime(calls),
        chunk_validation_runtime.ChecksumContext(
            current_length_offset=16,
            crc_offset=30,
            crc_offset_hex="0xf",
            original_chunk_type=b"IDAT",
            original_crc="00000000",
            original_length="00000003",
            current_data_offset=24,
            chunks_history=[],
            chunks_history_index=[],
        ),
        b"IDAT".hex(),
        b"abc".hex(),
        "00000000",
    )

    assert result == "checkpoint-result"
    assert checkpoint_args(calls)[0:5] == (
        True,
        False,
        "Checksum",
        b"IDAT",
        ["-Wrong Crc b'IDAT'"],
    )


def main():
    checks = [
        ("CheckLength found next", test_check_length_runtime_routes_found_next_chunk_checkpoint),
        ("CheckLength missing next", test_check_length_runtime_routes_missing_next_chunk_checkpoint),
        ("Checksum valid", test_checksum_runtime_valid_crc_records_chunk_story_and_checkpoint),
        ("Checksum invalid", test_checksum_runtime_invalid_crc_routes_wrong_crc_checkpoint),
    ]

    print("Running chunk validation runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk validation runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
