#!/usr/bin/env python3
import binascii
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import name_shift, name_shift_runtime, runtime_state


def chunk_hex(chunk_type=b"tEXt", data=b"abc", *, file_length="00000000", crc=None):
    if crc is None:
        crc = binascii.crc32(chunk_type + data).to_bytes(4, byteorder="big").hex()
    return file_length + chunk_type.hex() + data.hex() + crc


def build_runtime(calls, side_notes=None, *, spec_length="00000003"):
    if side_notes is None:
        side_notes = []

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Emoj":
            return ":%s:" % args[0]
        return "candy:%s" % kind

    return name_shift_runtime.NameShiftRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        pause=lambda message: calls.append(("pause", message)),
        end=lambda: calls.append(("end",)),
        spec_length=lambda chunk, current_length: calls.append(
            ("spec_length", chunk, current_length)
        )
        or spec_length,
        side_notes=side_notes,
        raw_print=lambda *args: calls.append(("raw_print", args)),
    )


def build_context(data_hex, current_type_offset, *, indexes=(), chunks=(), known=(b"tEXt",)):
    return name_shift_runtime.NameShiftContext(
        name_shift_context=runtime_state.NameShiftRuntimeContext(
            data_hex=data_hex,
            current_type_offset=current_type_offset,
            chunks_history_index=tuple(indexes),
            known_chunks=tuple(known),
        ),
        chunks_history=tuple(chunks),
    )


def test_name_shift_runtime_returns_false_without_candidate():
    calls = []
    runtime = build_runtime(calls)

    result = name_shift_runtime.run_name_shift(
        runtime,
        build_context("00" * 32, 20),
    )

    assert result is False
    assert ("candy", ("Title", "Checking around Chunk's position:")) in calls
    assert runtime.side_notes == []


def test_name_shift_runtime_repairs_extra_bytes_when_crc_matches():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    data_hex = "aaaaaaaa" + chunk_hex()

    result = name_shift_runtime.run_name_shift(
        runtime,
        build_context(
            data_hex,
            12,
            indexes=("0:0:4:0",),
            chunks=(b"PNG",),
        ),
    )

    fixed = chunk_hex(file_length="00000003")
    assert result == name_shift.extra_bytes_repair_result(fixed, 4, 12)
    assert name_shift.crc_valid_note() in side_notes
    assert name_shift.extra_bytes_found_note() in side_notes
    assert ("spec_length", b"tEXt", "00000000") in calls


def test_name_shift_runtime_repairs_missing_bytes_when_crc_matches():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    data_hex = "aaaaaaaa" + chunk_hex()

    result = name_shift_runtime.run_name_shift(
        runtime,
        build_context(data_hex, 20),
    )

    fixed = chunk_hex(file_length="00000003")
    assert result == name_shift.missing_bytes_repair_result(fixed, 4, 20)
    assert name_shift.crc_valid_note() in side_notes
    assert name_shift.missing_bytes_found_note() in side_notes


def test_name_shift_runtime_keeps_legacy_double_end_when_length_is_not_corrupted():
    calls = []
    runtime = build_runtime(calls, spec_length="00000003")
    data_hex = chunk_hex(file_length="00000003")

    result = name_shift_runtime.run_name_shift(
        runtime,
        build_context(data_hex, 8),
    )

    assert result is None
    assert calls.count(("end",)) == 2
    assert ("emit", "<yellow:\n-ToDo>") in calls


def main():
    checks = [
        ("No candidate", test_name_shift_runtime_returns_false_without_candidate),
        ("Extra bytes repair", test_name_shift_runtime_repairs_extra_bytes_when_crc_matches),
        ("Missing bytes repair", test_name_shift_runtime_repairs_missing_bytes_when_crc_matches),
        ("Legacy double end", test_name_shift_runtime_keeps_legacy_double_end_when_length_is_not_corrupted),
    ]

    print("Running name shift runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"name shift runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
