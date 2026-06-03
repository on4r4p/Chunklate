#!/usr/bin/env python3
import binascii
import struct
import sys
import tempfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import dummy_chunk_runtime
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk, iter_chunks, validate_png_structure


def fixture_bytes(name):
    for path in (
        ROOT / "brokenjavapngsuite" / name,
        ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / name,
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / name,
    ):
        if path.exists():
            return path.read_bytes()
    raise FileNotFoundError("%s fixture not found" % name)


def rgb_ihdr(width=1, height=1):
    return struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)


def build_runtime(
    calls,
    *,
    data_hex,
    side_notes=None,
    debug=False,
    pause_debug=False,
    question=None,
    file_origin="",
    write_clone=None,
):
    side_notes = [] if side_notes is None else side_notes

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    def checkpoint(*args):
        calls.append(("checkpoint", args))
        return "checkpoint-result"

    def emit(message):
        calls.append(("emit", message))

    def end():
        calls.append(("end", ()))
        return "end-result"

    def pause(prompt):
        calls.append(("pause", (prompt,)))

    def get_spec(*args, **kwargs):
        calls.append(("get_spec", args, kwargs))
        return (26, ("!I",), ["1"], "2")

    def spec_length(chunk_name):
        calls.append(("spec_length", (chunk_name,), {}))
        return "0000000d"

    def random_sample(chunk_data, color_type, chunk_format):
        calls.append(("random_sample", (chunk_data, color_type, chunk_format), {}))
        return "00000001000000010802000000"

    def repair_note(repair):
        calls.append(("repair_note", (repair,), {}))
        return "repair-note:%s" % repair.strategy

    return dummy_chunk_runtime.DummyChunkRuntime(
        data_hex=data_hex,
        side_notes=side_notes,
        candy=candy,
        emit=emit,
        checkpoint=checkpoint,
        end=end,
        pause=pause,
        get_spec=get_spec,
        spec_length=spec_length,
        random_sample=random_sample,
        repair_note=repair_note,
        debug=debug,
        pause_debug=pause_debug,
        question=question,
        file_origin=file_origin,
        write_clone=write_clone,
    )


def checkpoint_call(calls):
    matches = [call for call in calls if call[0] == "checkpoint"]
    assert len(matches) == 1
    return matches[0][1]


def test_dummy_chunk_runtime_routes_strict_ihdr_repair():
    data = PNG_SIGNATURE + build_png_chunk(b"IDAT", zlib.compress(b"\x00abc")) + IEND_CHUNK
    calls = []
    side_notes = []
    runtime = build_runtime(calls, data_hex=data.hex(), side_notes=side_notes)

    result = dummy_chunk_runtime.run_dummy_chunk(
        runtime,
        b"IHDR",
        8,
        len(PNG_SIGNATURE) * 2,
        len(PNG_SIGNATURE) * 2,
        "from-error",
    )

    args = checkpoint_call(calls)
    assert result == "checkpoint-result"
    assert args[:6] == (
        True,
        True,
        "DummyChunk",
        b"IHDR",
        ["Filling with a dummy chunk"],
        args[5],
    )
    assert args[6:] == (13, 8, len(PNG_SIGNATURE) * 2, len(PNG_SIGNATURE) * 2, "from-error")
    assert validate_png_structure(bytes.fromhex(args[5])).ok
    assert side_notes == ["repair-note:rebuilt missing IHDR from IDAT scanline size"]


def test_dummy_chunk_runtime_completes_iend_tail():
    data = PNG_SIGNATURE + build_png_chunk(b"IHDR", rgb_ihdr()) + build_png_chunk(
        b"IDAT",
        zlib.compress(b"\x00abc"),
    )
    calls = []
    runtime = build_runtime(calls, data_hex=data.hex())

    result = dummy_chunk_runtime.run_dummy_chunk(
        runtime,
        b"IEND",
        10,
        len(data) * 2,
        len(data) * 2,
        "from-error",
    )

    args = checkpoint_call(calls)
    assert result == "checkpoint-result"
    assert args[0:5] == (True, True, "DummyChunk", b"IEND", ["Filling with a dummy chunk"])
    assert args[6:] == (0, 10, len(data) * 2, len(data) * 2, "from-error")
    assert bytes.fromhex(args[5]).endswith(IEND_CHUNK)
    assert validate_png_structure(bytes.fromhex(args[5])).ok
    assert ("candy", ("Cowsay", "Fake datas ready to be served! Bonne appetit !", "good")) in calls


def test_dummy_chunk_runtime_keeps_legacy_ihdr_fallback_and_debug():
    calls = []
    runtime = build_runtime(
        calls,
        data_hex="aabbcc",
        debug=True,
        pause_debug=True,
    )

    result = dummy_chunk_runtime.run_dummy_chunk(
        runtime,
        b"IHDR",
        99,
        2,
        4,
        "from-error",
    )

    sample_data = "00000001000000010802000000"
    expected_crc = hex(binascii.crc32(b"IHDR" + bytes.fromhex(sample_data))).replace(
        "0x",
        "",
    )
    expected_chunk = "0000000d49484452" + sample_data + expected_crc
    args = checkpoint_call(calls)
    assert result == "checkpoint-result"
    assert args == (
        True,
        False,
        "DummyChunk",
        b"IHDR",
        ["Filling with a dummy chunk"],
        "aa" + expected_chunk + "bbcc",
        len(sample_data),
        99,
        2,
        4,
        "from-error",
    )
    assert ("emit", "chunklen_spec:26") in calls
    assert ("emit", "datax:bb") in calls
    assert ("pause", ("Pause Debug",)) in calls


def test_dummy_chunk_runtime_keeps_idat_todo_path():
    calls = []
    runtime = build_runtime(calls, data_hex="")

    result = dummy_chunk_runtime.run_dummy_chunk(
        runtime,
        b"IDAT",
        0,
        0,
        0,
        "from-error",
    )

    assert result == "end-result"
    assert ("emit", "<yellow:\n-ToDo>") in calls
    assert ("end", ()) in calls
    assert not [call for call in calls if call[0] == "checkpoint"]


def test_dummy_chunk_runtime_repairs_truncated_idat_before_missing_iend_with_donor():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        broken_dir = root / "brokenjavapngsuite"
        donor_dir = root / "schaik-javapng-samples"
        broken_dir.mkdir()
        donor_dir.mkdir()
        broken_path = broken_dir / "truncate_zlib.png"
        donor_path = donor_dir / "ch2n3p08.png"
        broken_data = fixture_bytes("truncate_zlib.png")
        donor_data = (ROOT / "schaik-javapng-samples" / "ch2n3p08.png").read_bytes()
        broken_path.write_bytes(broken_data)
        donor_path.write_bytes(donor_data)
        calls = []
        questions = []
        side_notes = []
        writes = []
        runtime = build_runtime(
            calls,
            data_hex=broken_data.hex(),
            side_notes=side_notes,
            question=lambda **kwargs: questions.append(kwargs) or True,
            file_origin=str(broken_path),
            write_clone=lambda data_hex, info: writes.append((data_hex, info)) or "write-result",
        )

        result = dummy_chunk_runtime.run_dummy_chunk(
            runtime,
            b"IEND",
            len(broken_data),
            len(broken_data) * 2,
            len(broken_data) * 2,
            "CheckLength_Error_0:-No NextChunk",
        )

    assert result == "write-result"
    assert not [call for call in calls if call[0] == "checkpoint"]
    assert len(writes) == 1
    assert writes[0][1] == "-idat-donor-ch2n3p08."
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    fixed_stream = b"".join(
        chunk.data for chunk in iter_chunks(fixed_data) if chunk.chunk_type == b"IDAT"
    )
    donor_stream = b"".join(
        chunk.data for chunk in iter_chunks(donor_data) if chunk.chunk_type == b"IDAT"
    )
    assert fixed_stream == donor_stream
    assert questions == [
        {
            "id": "IDAT donor repair:-Truncated IDAT. Replace IDAT with local donor %s?"
            % donor_path,
            "idhash": ("IDAT-donor", str(donor_path), 32, 32, 8, 3),
            "skipauto": True,
        }
    ]
    assert any("declared 433 byte(s), but only 24 byte(s)" in note for note in side_notes)
    assert any("bounded IDAT brute force found no complete zlib stream" in note for note in side_notes)
    assert side_notes[-1] == "repair-note:idat-donor-ch2n3p08"


def test_dummy_chunk_runtime_repairs_truncated_adam7_idat_before_missing_iend():
    broken_data = fixture_bytes("truncate_zlib_2.png")
    calls = []
    questions = []
    side_notes = []
    writes = []
    runtime = build_runtime(
        calls,
        data_hex=broken_data.hex(),
        side_notes=side_notes,
        file_origin="truncate_zlib_2.png",
        write_clone=lambda data_hex, info: writes.append((data_hex, info)) or "write-result",
    )

    result = dummy_chunk_runtime.run_dummy_chunk(
        runtime,
        b"IEND",
        len(broken_data),
        len(broken_data) * 2,
        len(broken_data) * 2,
        "CheckLength_Error_0:-No NextChunk",
    )

    assert result == "write-result"
    assert questions == []
    assert len(writes) == 1
    assert writes[0][1] == "-partial-idat-blackfill recovered 113/131 scanlines."
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    assert any("declared 8119 byte(s), but only 6004 byte(s)" in note for note in side_notes)
    assert side_notes[-1] == "repair-note:partial-idat-blackfill recovered 113/131 scanlines"


def main():
    checks = [
        ("Strict IHDR repair", test_dummy_chunk_runtime_routes_strict_ihdr_repair),
        ("Complete IEND tail", test_dummy_chunk_runtime_completes_iend_tail),
        ("Legacy IHDR fallback/debug", test_dummy_chunk_runtime_keeps_legacy_ihdr_fallback_and_debug),
        ("IDAT TODO path", test_dummy_chunk_runtime_keeps_idat_todo_path),
        (
            "Truncated IDAT donor before IEND",
            test_dummy_chunk_runtime_repairs_truncated_idat_before_missing_iend_with_donor,
        ),
        (
            "Truncated Adam7 IDAT blackfill before IEND",
            test_dummy_chunk_runtime_repairs_truncated_adam7_idat_before_missing_iend,
        ),
    ]

    print("Running dummy chunk runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"dummy chunk runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
