#!/usr/bin/env python3
import sys
import struct
import tempfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import output, writer, writer_runtime
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk, iter_chunks


def tiny_png_bytes():
    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        + IEND_CHUNK
    )


def structurally_aligned_bad_idat_bytes():
    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    payload = b"not-zlib"
    bad_idat = (
        len(payload).to_bytes(4, "big")
        + b"IDAT"
        + payload
        + b"\x00\x00\x00\x00"
    )
    return PNG_SIGNATURE + build_png_chunk(b"IHDR", ihdr) + bad_idat + IEND_CHUNK


def clone_plan(*, save_count=1, max_saves_reached=False, data=None):
    if data is None:
        data = tiny_png_bytes()
    return writer.CloneWritePlan(
        target=output.CloneTarget(
            name="sample.0_Fixed.png",
            directory="/tmp/Folder_sample",
            path="/tmp/Folder_sample/sample.0_Fixed.png",
        ),
        data=data,
        save_count=save_count,
        max_saves_reached=max_saves_reached,
    )


def artifact_clone_plan(*, save_count=1, data=None):
    if data is None:
        data = tiny_png_bytes()
    return writer.CloneWritePlan(
        target=output.CloneTarget(
            name="sample.0_Artifact.bin",
            directory="/tmp/Folder_sample/Debug_Payloads",
            path="/tmp/Folder_sample/Debug_Payloads/sample.0_Artifact.bin",
        ),
        data=data,
        save_count=save_count,
        max_saves_reached=False,
    )


def build_runtime(calls, side_notes=None, *, plan=None, prepare_error=None, write_error=None):
    if side_notes is None:
        side_notes = []
    state = {"sample": None, "save_count": None, "have_a_kitkat": False}
    if plan is None:
        plan = clone_plan()

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    def prepare(*args):
        calls.append(("prepare", args))
        if prepare_error is not None:
            raise prepare_error
        return plan

    def write(prepared_plan):
        calls.append(("write", prepared_plan))
        if write_error is not None:
            raise write_error

    runtime = writer_runtime.WriteCloneRuntime(
        remember_current_sample=lambda: calls.append(("remember",)),
        prepare_clone_write=prepare,
        write_prepared_clone=write,
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        end=lambda: calls.append(("end",)),
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        pause=lambda message: calls.append(("pause", message)),
        summarise=lambda infos: calls.append(("summarise", infos)),
        exit_process=lambda code: calls.append(("exit", code)),
        set_sample=lambda value: state.__setitem__("sample", value),
        set_save_count=lambda value: state.__setitem__("save_count", value),
        set_have_a_kitkat=lambda value: state.__setitem__("have_a_kitkat", value),
        side_notes=side_notes,
    )
    return runtime, state


def base_context(**updates):
    values = {
        "file_origin": "sample.png",
        "file_dir": "/tmp",
        "save_count": 0,
        "max_saves": None,
        "pause_enabled": False,
    }
    values.update(updates)
    return writer_runtime.WriteCloneContext(**values)


def test_write_clone_builders_wire_namespace_and_context():
    calls = []
    side_notes = []
    namespace = {
        "FILE_Origin": "sample.png",
        "FILE_DIR": "/tmp",
        "SAVE_COUNT": 3,
        "MAX_SAVES": 5,
        "PAUSE": True,
        "Sample": "old.png",
        "Have_A_KitKat": False,
    }

    runtime = writer_runtime.build_write_clone_runtime(
        namespace=namespace,
        remember_current_sample=lambda: calls.append(("remember",)),
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        end=lambda: calls.append(("end",)),
        candy=lambda kind, *args: "<%s:%s>" % (args[0], args[1]) if kind == "Color" else "candy",
        emit=lambda message: calls.append(("emit", message)),
        pause=lambda message: calls.append(("pause", message)),
        summarise=lambda infos: calls.append(("summarise", infos)),
        exit_process=lambda code: calls.append(("exit", code)),
        side_notes=side_notes,
        prepare_clone_write=lambda *args: calls.append(("prepare", args)) or clone_plan(save_count=4),
        write_prepared_clone=lambda plan: calls.append(("write", plan)),
    )
    context = writer_runtime.build_write_clone_context(namespace)

    assert context == writer_runtime.WriteCloneContext(
        file_origin="sample.png",
        file_dir="/tmp",
        save_count=3,
        max_saves=5,
        pause_enabled=True,
    )
    writer_runtime.run_write_clone(runtime, context, "89504e47", "summary")

    assert namespace["Sample"] == "/tmp/Folder_sample/sample.0_Fixed.png"
    assert namespace["SAVE_COUNT"] == 4
    assert namespace["Have_A_KitKat"] is True
    assert side_notes == ["-Saving to : /tmp/Folder_sample/sample.0_Fixed.png"]


def test_write_clone_namespace_bridge_builds_runtime_and_context():
    calls = []
    side_notes = []

    class FakeSys:
        def exit(self, code):
            calls.append(("exit", code))

    namespace = {
        "FILE_Origin": "sample.png",
        "FILE_DIR": "/tmp",
        "SAVE_COUNT": 3,
        "MAX_SAVES": 5,
        "PAUSE": True,
        "Sample": "old.png",
        "Have_A_KitKat": False,
        "Pandemonium_Remember_Current_Sample": lambda: calls.append(("remember",)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "TheEnd": lambda: calls.append(("end",)),
        "Candy": lambda kind, *args: "<%s:%s>" % (args[0], args[1]) if kind == "Color" else "candy",
        "PRINT": lambda message: calls.append(("emit", message)),
        "Pause": lambda message: calls.append(("pause", message)),
        "Summarise": lambda infos: calls.append(("summarise", infos)),
        "sys": FakeSys(),
        "SideNotes": side_notes,
    }

    def runner(runtime, context, data, infos):
        assert runtime.remember_current_sample is namespace["Pandemonium_Remember_Current_Sample"]
        assert runtime.betterror is namespace["Betterror"]
        assert runtime.end is namespace["TheEnd"]
        assert runtime.candy is namespace["Candy"]
        assert runtime.emit is namespace["PRINT"]
        assert runtime.pause is namespace["Pause"]
        assert runtime.summarise is namespace["Summarise"]
        assert runtime.side_notes is side_notes
        assert context == writer_runtime.WriteCloneContext(
            file_origin="sample.png",
            file_dir="/tmp",
            save_count=3,
            max_saves=5,
            pause_enabled=True,
        )
        assert (data, infos) == ("89504e47", "summary")
        runtime.set_sample("new.png")
        runtime.set_save_count(4)
        runtime.set_have_a_kitkat(True)
        return "written"

    result = writer_runtime.run_write_clone_from_namespace(
        namespace,
        "89504e47",
        "summary",
        runner=runner,
    )

    assert result == "written"
    assert namespace["Sample"] == "new.png"
    assert namespace["SAVE_COUNT"] == 4
    assert namespace["Have_A_KitKat"] is True


def test_write_clone_runtime_writes_updates_state_and_summarises():
    calls = []
    side_notes = []
    runtime, state = build_runtime(calls, side_notes)

    result = writer_runtime.run_write_clone(runtime, base_context(), "89504e47", "summary")

    assert result is None
    assert ("remember",) in calls
    assert ("prepare", ("sample.png", "/tmp", "89504e47", 0, None)) in calls
    assert ("write", clone_plan()) in calls
    assert (
        "candy",
        ("Cowsay", "I am about to write a clone: sample.0_Fixed.png", "good"),
    ) in calls
    assert ("emit", "<green:-Saving to : /tmp/Folder_sample/sample.0_Fixed.png>") in calls
    assert ("summarise", "summary") in calls
    assert side_notes == ["-Saving to : /tmp/Folder_sample/sample.0_Fixed.png"]
    assert state == {
        "sample": "/tmp/Folder_sample/sample.0_Fixed.png",
        "save_count": 1,
        "have_a_kitkat": True,
    }


def test_write_clone_invalid_png_is_artifact_only_not_final_sample():
    calls = []
    side_notes = []
    runtime, state = build_runtime(calls, side_notes, plan=clone_plan(data=b"fixed"))

    result = writer_runtime.run_write_clone(runtime, base_context(), "89504e47", "summary")

    assert result is None
    assert ("write", artifact_clone_plan(data=b"fixed")) in calls
    assert state == {
        "sample": None,
        "save_count": None,
        "have_a_kitkat": False,
    }
    assert not [call for call in calls if call[0] == "exit"]
    assert any(
        call == (
            "emit",
            "<yellow:-Clone written as artifact only; PNG/IDAT validation failed: PNG signature is not at offset 0>",
        )
        for call in calls
    )
    assert (
        "summarise",
        "summary\n-Clone written as artifact only; PNG/IDAT validation failed: PNG signature is not at offset 0",
    ) in calls
    assert side_notes == [
        "-Saving to : /tmp/Folder_sample/Debug_Payloads/sample.0_Artifact.bin",
        "-Clone written as artifact only; PNG/IDAT validation failed: PNG signature is not at offset 0",
    ]


def test_write_clone_structural_intermediate_can_still_be_promoted():
    calls = []
    side_notes = []
    intermediate = PNG_SIGNATURE + build_png_chunk(b"tEXt", b"k\x00v") + IEND_CHUNK
    runtime, state = build_runtime(calls, side_notes, plan=clone_plan(data=intermediate))

    result = writer_runtime.run_write_clone(runtime, base_context(), "89504e47", "summary")

    assert result is None
    assert ("write", clone_plan(data=intermediate)) in calls
    assert state == {
        "sample": "/tmp/Folder_sample/sample.0_Fixed.png",
        "save_count": 1,
        "have_a_kitkat": True,
    }
    assert not any(
        call[0] == "emit" and "artifact only" in str(call[1])
        for call in calls
    )
    assert ("summarise", "summary") in calls


def test_write_clone_structural_idat_repair_promotes_despite_remaining_idat_errors():
    calls = []
    side_notes = []
    intermediate = structurally_aligned_bad_idat_bytes()
    runtime, state = build_runtime(calls, side_notes, plan=clone_plan(data=intermediate))
    summary = "-Repair hypothesis tried: IDAT chain header repair."

    result = writer_runtime.run_write_clone(runtime, base_context(), "89504e47", summary)

    assert result is None
    assert ("write", clone_plan(data=intermediate)) in calls
    assert state == {
        "sample": "/tmp/Folder_sample/sample.0_Fixed.png",
        "save_count": 1,
        "have_a_kitkat": True,
    }
    assert not any(
        call[0] == "emit" and "artifact only" in str(call[1])
        for call in calls
    )
    assert any(
        call[0] == "emit" and "structural intermediate" in str(call[1])
        for call in calls
    )
    assert any("structural intermediate" in note for note in side_notes)
    assert ("summarise", summary) in calls


def test_write_clone_unmarked_bad_idat_stays_artifact_only():
    calls = []
    side_notes = []
    bad_idat = structurally_aligned_bad_idat_bytes()
    runtime, state = build_runtime(calls, side_notes, plan=clone_plan(data=bad_idat))

    result = writer_runtime.run_write_clone(runtime, base_context(), "89504e47", "summary")

    assert result is None
    assert ("write", artifact_clone_plan(data=bad_idat)) in calls
    assert state == {
        "sample": None,
        "save_count": None,
        "have_a_kitkat": False,
    }
    assert any(
        call[0] == "emit" and "artifact only" in str(call[1])
        for call in calls
    )


def test_write_clone_runtime_preserves_pause_and_max_saves_exit():
    calls = []
    side_notes = []
    runtime, state = build_runtime(
        calls,
        side_notes,
        plan=clone_plan(save_count=2, max_saves_reached=True),
    )

    writer_runtime.run_write_clone(
        runtime,
        base_context(max_saves=2, pause_enabled=True),
        b"fixed",
        "summary",
    )

    assert ("pause", "-Clone ready. Press Return to write it:") in calls
    assert calls.index(("pause", "-Clone ready. Press Return to write it:")) < calls.index(
        ("write", clone_plan(save_count=2, max_saves_reached=True))
    )
    assert ("emit", "-Max saves reached: 2") in calls
    assert ("exit", 0) in calls
    assert state["save_count"] == 2


def test_write_clone_runtime_prepare_error_routes_betterror_and_end():
    calls = []
    side_notes = []
    runtime, state = build_runtime(calls, side_notes, prepare_error=ValueError("bad prepare"))

    result = writer_runtime.run_write_clone(runtime, base_context(), "data", "summary")

    assert result is None
    assert ("betterror", "bad prepare", "WriteClone") in calls
    assert ("end",) in calls
    assert not [call for call in calls if call[0] == "write"]
    assert side_notes == []
    assert state["sample"] is None


def test_write_clone_runtime_write_error_routes_betterror_emit_and_end():
    calls = []
    side_notes = []
    runtime, state = build_runtime(calls, side_notes, write_error=OSError("disk full"))

    result = writer_runtime.run_write_clone(runtime, base_context(), "data", "summary")

    assert result is None
    assert ("betterror", "disk full", "WriteClone") in calls
    assert ("emit", "<red:Error WriteClone:%s>" % "<yellow:disk full>") in calls
    assert ("end",) in calls
    assert not [call for call in calls if call[0] == "summarise"]
    assert side_notes == ["-Saving to : /tmp/Folder_sample/sample.0_Fixed.png"]
    assert state["have_a_kitkat"] is False


def clone_patch_runtime(calls, *, data_hex="0011223344556677", save_debug_payloads=None):
    state = {"show_must_go_on": False}

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        return "candy:%s" % kind

    runtime = writer_runtime.ClonePatchRuntime(
        data_hex=data_hex,
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        write_clone=lambda data, infos: calls.append(("write_clone", data, infos)) or "written",
        set_show_must_go_on=lambda value: state.__setitem__("show_must_go_on", value),
        save_debug_payloads=save_debug_payloads,
    )
    return runtime, state


def test_run_remove_chunk_builds_fixed_data_and_writes_clone():
    calls = []
    runtime, state = clone_patch_runtime(calls)

    result = writer_runtime.run_remove_chunk(runtime, 4, 10, "infos")

    assert result == "written"
    assert ("candy", ("Title", "Removing Chunk")) in calls
    assert ("write_clone", "0011556677", "infos") in calls
    assert state == {"show_must_go_on": False}


def test_run_save_clone_builds_fixed_data_sets_flag_and_writes_clone():
    calls = []
    runtime, state = clone_patch_runtime(calls)

    result = writer_runtime.run_save_clone(runtime, "aabb", 4, 10, "infos")

    assert result == "written"
    assert state == {"show_must_go_on": True}
    assert ("candy", ("Title", "Saving Clone")) in calls
    assert ("emit", "-Data : b'\\xaa\\xbb'\n") in calls
    assert ("candy", ("Cowsay", "Patch bytes ready: b'\\xaa\\xbb'", "com")) in calls
    assert (
        "write_clone",
        "0011aabb556677",
        "infos\n-Clone patch note: Patch bytes ready: b'\\xaa\\xbb'",
    ) in calls


def test_run_save_clone_explains_named_patch_when_source_is_bytes():
    calls = []
    runtime, state = clone_patch_runtime(calls)

    result = writer_runtime.run_save_clone(runtime, "49444154", 4, 12, b"IDA^")

    assert result == "written"
    assert state == {"show_must_go_on": True}
    assert ("emit", "-Data : b'IDAT'\n") in calls
    assert (
        "candy",
        ("Cowsay", "Patch: I am replacing b'IDA^' with b'IDAT' in the clone.", "com"),
    ) in calls
    assert (
        "write_clone",
        "0011494441546677",
        "b'IDA^'\n-Clone patch note: Patch: I am replacing b'IDA^' with b'IDAT' in the clone.",
    ) in calls


def test_run_save_clone_shortens_large_patch_preview():
    calls = []

    def save_debug_payloads(label, start, end, payloads):
        calls.append(("save_debug_payloads", label, start, end, payloads))
        return [
            "Debug_Payloads/clone_patch_source.bin",
            "Debug_Payloads/clone_patch_replacement.bin",
        ]

    runtime, state = clone_patch_runtime(calls, save_debug_payloads=save_debug_payloads)
    data_fix = bytes(range(24)).hex()

    result = writer_runtime.run_save_clone(runtime, data_fix, 4, 10, b"old" * 8)

    assert result == "written"
    assert state == {"show_must_go_on": True}
    assert (
        "candy",
        (
            "Cowsay",
            "Patch: I am replacing b'oldoldoldoldoldo'... (24 bytes total) with "
            "b'\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\t\\n\\x0b\\x0c\\r\\x0e\\x0f'... (24 bytes total) in the clone.",
            "com",
        ),
    ) in calls
    assert any(
        call[0] == "write_clone"
        and "b'oldoldoldoldoldo'... (24 bytes total)" in call[2]
        and "b'\\x00\\x01\\x02\\x03" in call[2]
        and "-Clone debug payload: Debug_Payloads/clone_patch_source.bin" in call[2]
        and "-Clone debug payload: Debug_Payloads/clone_patch_replacement.bin" in call[2]
        for call in calls
    )
    assert (
        "save_debug_payloads",
        "clone_patch",
        4,
        10,
        {
            "source": b"old" * 8,
            "replacement": bytes(range(24)),
        },
    ) in calls


def test_run_save_clone_blocks_idat_crc_only_when_deflate_still_breaks():
    calls = []
    side_notes = []
    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    compressed = bytearray(zlib.compress(b"\x00abc"))
    compressed[2] ^= 0xFF
    data = PNG_SIGNATURE + build_png_chunk(b"IHDR", ihdr) + build_png_chunk(b"IDAT", bytes(compressed)) + IEND_CHUNK
    idat_chunk = next(chunk for chunk in iter_chunks(data) if chunk.chunk_type == b"IDAT")
    crc_offset = idat_chunk.offset + 8 + idat_chunk.length
    replacement_crc = data[crc_offset:crc_offset + 4].hex()
    broken_crc_data = bytearray(data)
    broken_crc_data[crc_offset:crc_offset + 4] = b"\x00\x00\x00\x00"
    runtime, state = clone_patch_runtime(calls, data_hex=bytes(broken_crc_data).hex())
    runtime = writer_runtime.ClonePatchRuntime(
        data_hex=runtime.data_hex,
        candy=runtime.candy,
        emit=runtime.emit,
        betterror=runtime.betterror,
        write_clone=runtime.write_clone,
        set_show_must_go_on=runtime.set_show_must_go_on,
        save_debug_payloads=runtime.save_debug_payloads,
        side_notes=side_notes,
    )

    result = writer_runtime.run_save_clone(
        runtime,
        replacement_crc,
        crc_offset * 2,
        crc_offset * 2 + 8,
        "-Found Chunk[b'IDAT'] has Wrong Crc",
    )

    assert result is None
    assert state == {"show_must_go_on": False}
    assert not [call for call in calls if call[0] == "write_clone"]
    assert (
        "candy",
        (
            "Cowsay",
            "That would only repaint an IDAT CRC label while the compressed stream still falls apart.",
            "bad",
        ),
    ) in calls
    assert any(note.startswith("-Deferred IDAT CRC-only patch: zlib stream still invalid:") for note in side_notes)


def test_run_save_clone_blocks_invalid_full_png_before_writing_fixed_file():
    calls = []
    side_notes = []
    source = tiny_png_bytes()
    invalid_full_png = PNG_SIGNATURE + IEND_CHUNK
    runtime, state = clone_patch_runtime(calls, data_hex=source.hex())
    runtime = writer_runtime.ClonePatchRuntime(
        data_hex=runtime.data_hex,
        candy=runtime.candy,
        emit=runtime.emit,
        betterror=runtime.betterror,
        write_clone=runtime.write_clone,
        set_show_must_go_on=runtime.set_show_must_go_on,
        save_debug_payloads=runtime.save_debug_payloads,
        side_notes=side_notes,
    )

    result = writer_runtime.run_save_clone(
        runtime,
        invalid_full_png.hex(),
        0,
        len(source.hex()),
        "-Previous Crc checksum found by replacing datas",
    )

    assert result is None
    assert state == {"show_must_go_on": False}
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any("Rejected full clone before write" in note for note in side_notes)


def test_run_save_clone_allows_structural_full_png_replacement_without_brawl_marker():
    calls = []
    source = tiny_png_bytes()
    structural_candidate = PNG_SIGNATURE + IEND_CHUNK
    runtime, state = clone_patch_runtime(calls, data_hex=source.hex())

    result = writer_runtime.run_save_clone(
        runtime,
        structural_candidate.hex(),
        0,
        len(source.hex()),
        "-NameShift: Extra bytes has been found.",
    )

    assert result == "written"
    assert state == {"show_must_go_on": True}
    assert any(call[0] == "write_clone" for call in calls)


def test_run_save_clone_full_png_sentinel_replaces_entire_source():
    calls = []
    source = tiny_png_bytes() + b"stale-tail"
    replacement = tiny_png_bytes()
    runtime, state = clone_patch_runtime(calls, data_hex=source.hex())

    result = writer_runtime.run_save_clone(
        runtime,
        replacement.hex(),
        0,
        -1,
        "-Previous Crc checksum found by replacing datas",
    )

    assert result == "written"
    assert state == {"show_must_go_on": True}
    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert write_calls
    assert write_calls[-1][1] == replacement.hex()
    assert "stale-tail".encode().hex() not in write_calls[-1][1]


def test_save_clone_debug_payloads_writes_large_payload_files():
    with tempfile.TemporaryDirectory() as tmp:
        paths = writer_runtime.save_clone_debug_payloads(
            "sample.png",
            tmp,
            "clone_patch",
            4,
            10,
            {
                "replacement": b"replacement-bytes",
                "source": b"source-bytes",
            },
        )

        assert len(paths) == 2
        folder = Path(tmp) / "Folder_sample"
        for path in paths:
            assert path.startswith("Debug_Payloads/clone_patch_000004_000010_")
            assert (folder / path).exists()
        assert any((folder / path).read_bytes() == b"source-bytes" for path in paths)
        assert any((folder / path).read_bytes() == b"replacement-bytes" for path in paths)


def test_run_save_clone_preserves_bad_hex_error_path_before_write():
    calls = []
    runtime, state = clone_patch_runtime(calls)

    result = writer_runtime.run_save_clone(runtime, "not-hex", 4, 10, "infos")

    assert result == "written"
    assert state == {"show_must_go_on": True}
    assert any(call[0] == "betterror" and call[2] == "SaveClone" for call in calls)
    assert (
        "write_clone",
        "0011not-hex556677",
        "infos\n-Clone patch note: I am about to write a clone with bytes I cannot print cleanly. That is already a mood.",
    ) in calls


def main():
    checks = [
        ("Write builders", test_write_clone_builders_wire_namespace_and_context),
        ("Write namespace bridge", test_write_clone_namespace_bridge_builds_runtime_and_context),
        ("Write and state", test_write_clone_runtime_writes_updates_state_and_summarises),
        (
            "Write structural IDAT intermediate",
            test_write_clone_structural_idat_repair_promotes_despite_remaining_idat_errors,
        ),
        ("Write unmarked bad IDAT artifact", test_write_clone_unmarked_bad_idat_stays_artifact_only),
        ("Pause and max saves", test_write_clone_runtime_preserves_pause_and_max_saves_exit),
        ("Prepare error", test_write_clone_runtime_prepare_error_routes_betterror_and_end),
        ("Write error", test_write_clone_runtime_write_error_routes_betterror_emit_and_end),
        ("Remove chunk", test_run_remove_chunk_builds_fixed_data_and_writes_clone),
        ("Save clone", test_run_save_clone_builds_fixed_data_sets_flag_and_writes_clone),
        ("Save clone named patch", test_run_save_clone_explains_named_patch_when_source_is_bytes),
        ("Save clone large patch preview", test_run_save_clone_shortens_large_patch_preview),
        (
            "Save clone blocks broken IDAT CRC-only patch",
            test_run_save_clone_blocks_idat_crc_only_when_deflate_still_breaks,
        ),
        (
            "Save clone blocks invalid Daedalus full PNG",
            test_run_save_clone_blocks_invalid_full_png_before_writing_fixed_file,
        ),
        (
            "Save clone allows structural full PNG replacement",
            test_run_save_clone_allows_structural_full_png_replacement_without_brawl_marker,
        ),
        ("Save clone debug payload files", test_save_clone_debug_payloads_writes_large_payload_files),
        ("Save clone bad hex", test_run_save_clone_preserves_bad_hex_error_path_before_write),
    ]

    print("Running writer runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"writer runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
