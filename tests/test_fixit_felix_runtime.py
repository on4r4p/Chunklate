#!/usr/bin/env python3
import json
import sys
import tempfile
import zlib
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import fixit_felix
from chunklate import fixit_felix_runtime
from chunklate import idat
from chunklate import idat_bruteforce
from chunklate import ultimate_reference_ui
from chunklate import messages
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk, iter_chunks, validate_png_structure


def valid_png_bytes():
    ihdr = b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00"
    idat = zlib.compress(b"\x00\x00")
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", idat)
        + IEND_CHUNK
    )


def test_sbb_reference_regions_path_normalizes_fixed_clone_origin(tmp_path):
    origin = tmp_path / "Folder_Flag.3_Fixed" / "Flag.3_Fixed.png"
    runtime = SimpleNamespace(
        ultimate_linefeed_reference_regions=lambda: "",
        file_origin=str(origin),
        file_dir=str(tmp_path),
    )

    path = fixit_felix_runtime._sbb_reference_regions_path(runtime)

    assert path == str(tmp_path / "Folder_Flag" / "_ULF.reference_regions.json")


def test_idat_diagnostic_artifact_uses_runtime_clone_folder(tmp_path):
    side_notes = []
    runtime = SimpleNamespace(
        file_origin="Flag.1_Fixed.png",
        file_dir=str(tmp_path),
        side_notes=side_notes,
    )
    before = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=1,
        expected_size=2,
        decompressed_size=0,
        error_offset=3,
    )
    after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="incomplete_stream",
        height=1,
        expected_size=2,
        decompressed_size=1,
        usable_scanlines=0,
        error_offset=4,
    )
    candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        data=b"not-a-final-png",
        operations=(),
        before=before,
        after=after,
        state_id=6,
    )

    path = fixit_felix_runtime._write_idat_diagnostic_artifact(
        runtime,
        candidate,
        label="idat_lf_diagnostic",
    )

    assert path is not None
    artifact = Path(path)
    assert artifact.parent == tmp_path / "Folder_Flag" / "Debug_Payloads"
    assert artifact.name.startswith("Flag_idat_lf_diagnostic_state6_")
    assert artifact.read_bytes() == b"not-a-final-png"
    assert not (tmp_path / "Folder_idat_diagnostic").exists()
    assert any(
        note.startswith("-IDAT diagnostic artifact: Debug_Payloads/")
        for note in side_notes
    )


def test_idat_diagnostic_artifact_skips_missing_file_origin(tmp_path, monkeypatch):
    side_notes = []
    monkeypatch.chdir(tmp_path)
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=side_notes,
    )
    before = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=1,
        expected_size=2,
        decompressed_size=0,
        error_offset=3,
    )
    after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="incomplete_stream",
        height=1,
        expected_size=2,
        decompressed_size=1,
        usable_scanlines=0,
        error_offset=4,
    )
    candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        data=b"not-a-final-png",
        operations=(),
        before=before,
        after=after,
        state_id=6,
    )

    path = fixit_felix_runtime._write_idat_diagnostic_artifact(
        runtime,
        candidate,
        label="idat_lf_diagnostic",
    )

    assert path is None
    assert not (tmp_path / "Folder_idat_diagnostic").exists()
    assert "-IDAT diagnostic artifact skipped: source file origin is unavailable." in side_notes


def test_idat_bruteforce_target_prefers_crc_bad_idat_chunk():
    ihdr_chunk = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00",
    )
    first_idat = build_png_chunk(b"IDAT", b"abcdef")
    second_idat = build_png_chunk(b"IDAT", b"ghijkl")
    data = bytearray(PNG_SIGNATURE + ihdr_chunk + first_idat + second_idat + IEND_CHUNK)
    first_idat_offset = len(PNG_SIGNATURE) + len(ihdr_chunk)
    first_idat_payload_offset = first_idat_offset + 8
    data[first_idat_payload_offset + 2] ^= 0xFF

    target = fixit_felix_runtime._idat_bruteforce_target(bytes(data))

    assert target is not None
    assert target.offset == first_idat_offset


def zero_dimension_missing_idat_bytes():
    ihdr = b"\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00"
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"gAMA", (100000).to_bytes(4, "big"))
    )


def zero_scanline_blackfill_repair():
    ihdr = b"\x00\x00\x00\x01\x00\x00\x00\x02\x08\x02\x00\x00\x00"
    original = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", zlib.compress(b""))
        + IEND_CHUNK
    )
    repair = idat.rebuild_partial_idat_blackfill(original)
    assert repair is not None
    assert repair.recovered_scanlines == 0
    return repair


def partial_scanline_blackfill_source_and_repair():
    ihdr = b"\x00\x00\x00\x01\x00\x00\x00\x05\x08\x02\x00\x00\x00"
    raw = b"".join(b"\x00" + bytes((value, value, value)) for value in range(5))
    compressed = zlib.compress(raw, level=0)
    for cut in range(2, len(compressed)):
        source = (
            PNG_SIGNATURE
            + build_png_chunk(b"IHDR", ihdr)
            + build_png_chunk(b"IDAT", compressed[:cut])
            + IEND_CHUNK
        )
        repair = idat.rebuild_partial_idat_blackfill(source)
        if repair is not None and 0 < repair.recovered_scanlines < repair.total_scanlines:
            return source, repair
    raise AssertionError("test fixture did not produce a partial IDAT blackfill")


def truncate_idat_1_fixture_bytes():
    for path in (
        ROOT / "brokenjavapngsuite" / "truncate_idat_1.png",
        ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "truncate_idat_1.png",
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "truncate_idat_1.png",
    ):
        if path.exists():
            return path.read_bytes()
    raise FileNotFoundError("truncate_idat_1.png fixture not found")


def png_with_split_idat(interrupter: bytes = b"heRB"):
    compressed = zlib.compress(b"\x00\x00")
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00")
        + build_png_chunk(b"IDAT", compressed[:2])
        + build_png_chunk(interrupter, b"")
        + build_png_chunk(b"IDAT", compressed[2:])
        + IEND_CHUNK
    )


def plte_empty_fixture_bytes():
    return (ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "plte_empty.png").read_bytes()


def plte_length_mod_three_fixture_bytes():
    return (ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "plte_length_mod_three.png").read_bytes()


def plte_too_many_entries_fixture_bytes():
    return (ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "plte_too_many_entries.png").read_bytes()


def splt_duplicate_name_fixture_bytes():
    return (ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "splt_duplicate_name.png").read_bytes()


def splt_sample_depth_fixture_bytes():
    return (ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "splt_sample_depth.png").read_bytes()


def ster_mode_fixture_bytes():
    return (ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "ster_mode.png").read_bytes()


def text_trailing_null_fixture_bytes():
    return (ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "text_trailing_null.png").read_bytes()


def trns_too_many_entries_fixture_bytes():
    return (ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "trns_too_many_entries.png").read_bytes()


def time_value_range_fixture_bytes():
    return (ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "time_value_range.png").read_bytes()


def test_apply_repair_records_note_and_writes_clone():
    side_notes = []
    writes = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
    )
    repair = SimpleNamespace(
        data=b"fixed",
        strategy="unit-test-repair",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert candy_calls == [
        (
            "Cowsay",
            "I found an automatic repair path: unit-test-repair. I am writing a separate clone with that change, leaving the original file untouched.",
            "com",
        )
    ]
    assert side_notes == ["-FixItFelix:unit-test-repair."]
    assert writes == [("6669786564", "-unit-test-repair.")]


def test_automatic_repair_success_message_explains_private_compression():
    repair = SimpleNamespace(
        strategy="converted private gzip compression method to standard zlib IDAT",
    )

    message = fixit_felix_runtime.automatic_repair_success_message(repair)

    assert "IHDR compression byte is private" in message
    assert "standard zlib" in message


def test_automatic_repair_success_message_describes_focused_idat_crc_forge():
    repair = SimpleNamespace(
        strategy="focused 4-byte IDAT CRC repair around file offset 0x20c before blackfill",
    )

    message = fixit_felix_runtime.automatic_repair_success_message(repair)

    assert "HermesProbe localized a deflate error near a single bad IDAT CRC" in message
    assert "focused 4-byte repair" in message


def test_apply_repair_prompts_after_writing_focused_idat_crc_clone():
    side_notes = []
    calls = []
    repair = fixit_felix.IdatCrcForgeRepair(
        data=valid_png_bytes(),
        strategy="focused 4-byte IDAT CRC repair around file offset 0x20c before blackfill",
        error_file_offset=0x20F,
        window_start=0x20C,
        window_end=0x20F,
    )
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *args: calls.append(("write", args)),
        question=lambda **kwargs: calls.append(("question", kwargs)) or True,
        preview_repair_image=lambda *args: calls.append(("preview", args)),
        data_hex=repair.data.hex(),
        interactive=True,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert (
        "candy",
        (
            "Cowsay",
            "HermesProbe localized a deflate error near file offset 0x20f.",
            "com",
        ),
    ) in [(call[0], call[1]) for call in calls]
    write_call = next(call for call in calls if call[0] == "write")
    preview_call = next(call for call in calls if call[0] == "preview")
    question_call = next(call for call in calls if call[0] == "question")
    assert write_call == ("write", (repair.data.hex(), "-focused 4-byte IDAT CRC repair around file offset 0x20c before blackfill."))
    assert preview_call == ("preview", (repair.data, "IDAT_CRC_Focused_Preview"))
    assert question_call == (
        "question",
        {
            "id": "IDAT CRC Forge:-Keep the focused 4-byte repair after preview?",
            "idhash": ("IDAT-focused-crc-forge", 0x20F, 0x20C, 0x20F),
            "skipauto": True,
        },
    )
    assert calls.index(write_call) < calls.index(preview_call) < calls.index(question_call)
    assert side_notes[0] == "-FixItFelix:focused 4-byte IDAT CRC repair around file offset 0x20c before blackfill."


def test_automatic_repair_success_message_prefers_trns_over_plte_wording():
    repair = SimpleNamespace(
        strategy="trimmed indexed tRNS length from 200 to PLTE entry count 173 and rebuilt CRC",
    )

    message = fixit_felix_runtime.automatic_repair_success_message(repair)

    assert "transparency metadata" in message
    assert "selected tRNS branch" in message


def test_apply_repair_offers_tkinter_controls_after_empty_plte_preview():
    original = plte_empty_fixture_bytes()
    repair = fixit_felix.plte_cleanup(
        original,
        ["GetInfo_Error_0:-PLTE Wrong RED palettes entry must Not be empty"],
        auto=False,
        nodialogue=False,
        max_saves=None,
    )
    plte = next(chunk for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"PLTE")
    start = plte.offset * 2
    end = (plte.offset + 12 + plte.length) * 2
    side_notes = []
    calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *args: calls.append(("write", args)),
        question=lambda **kwargs: calls.append(("question", kwargs)) or True,
        preview_repair_image=lambda *args: calls.append(("preview", args)),
        tk_manual_plte=lambda *args: calls.append(("manual", args)),
        data_hex=original.hex(),
        file_origin="plte_empty.png",
        interactive=True,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert ("preview", (repair.data, "empty_plte_grayscale_plte")) in calls
    assert ("question", {
        "id": "PLTE Palette Editor:-Open Tkinter to tune this reconstructed PLTE?",
        "idhash": ("PLTE", start, end, "empty-indexed-grayscale"),
        "skipauto": True,
    }) in calls
    assert ("manual", ("plte_empty.png", b"PLTE", end, start, "-PLTE Wrong Data", repair.data.hex())) in calls
    assert [call for call in calls if call[0] == "write"] == []
    assert side_notes == ["-FixItFelix:opened Tkinter PLTE editor after grayscale PLTE preview."]


def test_apply_repair_keeps_empty_plte_auto_path_without_interactive_tty():
    original = plte_empty_fixture_bytes()
    repair = fixit_felix.plte_cleanup(
        original,
        ["GetInfo_Error_0:-PLTE Wrong RED palettes entry must Not be empty"],
        auto=False,
        nodialogue=False,
        max_saves=None,
    )
    writes = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=[],
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **kwargs: False,
        preview_repair_image=lambda *args: None,
        tk_manual_plte=lambda *args: None,
        data_hex=original.hex(),
        file_origin="plte_empty.png",
        interactive=False,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert writes == [(repair.data.hex(), "-rebuilt empty indexed PLTE as grayscale palette.")]


def test_apply_repair_offers_tkinter_controls_after_malformed_plte_preview():
    original = plte_length_mod_three_fixture_bytes()
    repair = fixit_felix.plte_cleanup(
        original,
        ["GetInfo_Error_0:-PLTE Total palettes number must be divisible by 3"],
        auto=False,
        nodialogue=False,
        max_saves=None,
    )
    plte = next(chunk for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"PLTE")
    start = plte.offset * 2
    end = (plte.offset + 12 + plte.length) * 2
    calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=[],
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *args: calls.append(("write", args)),
        question=lambda **kwargs: calls.append(("question", kwargs)) or True,
        preview_repair_image=lambda *args: calls.append(("preview", args)),
        tk_manual_plte=lambda *args: calls.append(("manual", args)),
        data_hex=original.hex(),
        file_origin="plte_length_mod_three.png",
        interactive=True,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert repair.strategy == "rebuilt malformed indexed PLTE as grayscale palette"
    assert ("preview", (repair.data, "malformed_plte_grayscale_plte")) in calls
    assert ("question", {
        "id": "PLTE Palette Editor:-Open Tkinter to tune this reconstructed PLTE?",
        "idhash": ("PLTE", start, end, "malformed-indexed-grayscale"),
        "skipauto": True,
    }) in calls
    assert ("manual", ("plte_length_mod_three.png", b"PLTE", end, start, "-PLTE Wrong Data", repair.data.hex())) in calls
    assert [call for call in calls if call[0] == "write"] == []


def test_apply_repair_offers_tkinter_controls_after_oversized_black_plte_preview():
    original = plte_too_many_entries_fixture_bytes()
    repair = fixit_felix.plte_cleanup(
        original,
        ["GetInfo_Error_0:-PLTE Wrong RED palettes not in bitdepht range"],
        auto=False,
        nodialogue=False,
        max_saves=None,
    )
    plte = next(chunk for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"PLTE")
    start = plte.offset * 2
    end = (plte.offset + 12 + plte.length) * 2
    calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=[],
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *args: calls.append(("write", args)),
        question=lambda **kwargs: calls.append(("question", kwargs)) or True,
        preview_repair_image=lambda *args: calls.append(("preview", args)),
        tk_manual_plte=lambda *args: calls.append(("manual", args)),
        data_hex=original.hex(),
        file_origin="plte_too_many_entries.png",
        interactive=True,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert repair.strategy == "rebuilt oversized indexed PLTE as grayscale palette"
    assert ("preview", (repair.data, "oversized_plte_grayscale_plte")) in calls
    assert ("question", {
        "id": "PLTE Palette Editor:-Open Tkinter to tune this reconstructed PLTE?",
        "idhash": ("PLTE", start, end, "oversized-indexed-grayscale"),
        "skipauto": True,
    }) in calls
    assert ("manual", ("plte_too_many_entries.png", b"PLTE", end, start, "-PLTE Wrong Data", repair.data.hex())) in calls
    assert [call for call in calls if call[0] == "write"] == []


def test_apply_repair_prompts_to_move_idat_interruption_before_writing_clone():
    original = png_with_split_idat(b"heRB")
    repair = fixit_felix.idat_interruption_cleanup(
        original,
        ["CheckChunkName_Error_0:-Found Next Chunk[b'heRB'] has Wrong Chunk name after Chunk[b'IDAT']"],
    )
    side_notes = []
    writes = []
    questions = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **kwargs: questions.append(kwargs) or True,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert questions == [
        {
            "id": "IDAT Interruption Move:-Move ancillary chunk(s) out of the IDAT chain?",
            "idhash": "IDAT-interruption:move:heRB",
            "skipauto": True,
        }
    ]
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    assert [chunk.chunk_type for chunk in iter_chunks(fixed_data)] == [
        b"IHDR",
        b"IDAT",
        b"IDAT",
        b"heRB",
        b"IEND",
    ]
    assert side_notes == [
        "-FixItFelix:moved IDAT-interrupting ancillary chunk(s) after final IDAT: heRB."
    ]


def test_apply_repair_can_remove_safe_to_copy_idat_interruption_when_move_declined():
    original = png_with_split_idat(b"heRb")
    repair = fixit_felix.idat_interruption_cleanup(
        original,
        ["CheckChunkName_Error_0:-Found Next Chunk[b'heRb'] has Wrong Chunk name after Chunk[b'IDAT']"],
    )
    answers = iter((False, True))
    side_notes = []
    writes = []
    questions = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **kwargs: questions.append(kwargs) or next(answers),
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert [question["id"] for question in questions] == [
        "IDAT Interruption Move:-Move ancillary chunk(s) out of the IDAT chain?",
        "IDAT Interruption Removal:-Remove safe-to-copy ancillary chunk(s) from the clone?",
    ]
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    assert [chunk.chunk_type for chunk in iter_chunks(fixed_data)] == [
        b"IHDR",
        b"IDAT",
        b"IDAT",
        b"IEND",
    ]
    assert side_notes == [
        "-FixItFelix:removed safe-to-copy IDAT-interrupting ancillary chunk(s): heRb."
    ]


def test_apply_repair_prompts_to_repair_malformed_duplicate_splt():
    original = splt_duplicate_name_fixture_bytes()
    repair = fixit_felix.splt_payload_cleanup(
        original,
        [
            "GetInfo_Error_0:-Wrong Red sPLT length",
            "GetInfo_Error_1:-sPLT can be used multiple times but cannot share the same name.",
        ],
    )
    side_notes = []
    writes = []
    questions = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **kwargs: questions.append(kwargs) or True,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert questions == [
        {
            "id": "sPLT Payload Repair:-Try to repair malformed/duplicate sPLT chunk(s)?",
            "idhash": "sPLT-payload:sPLT,sPLT",
        }
    ]
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    assert [chunk.data for chunk in iter_chunks(fixed_data) if chunk.chunk_type == b"sPLT"] == [
        b"Lemonade\x00\x08\x00\x00\x00\xff\x00\x00",
        b"Lemonade-2\x00\x08\x00\x00\x00\xff\x00\x00",
    ]
    assert side_notes == ["-FixItFelix:repaired malformed/duplicate sPLT chunk(s)."]


def test_apply_repair_can_remove_malformed_duplicate_splt_when_repair_declined():
    original = splt_duplicate_name_fixture_bytes()
    repair = fixit_felix.splt_payload_cleanup(
        original,
        [
            "GetInfo_Error_0:-Wrong Red sPLT length",
            "GetInfo_Error_1:-sPLT can be used multiple times but cannot share the same name.",
        ],
    )
    side_notes = []
    writes = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **_kwargs: False,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    assert b"sPLT" not in [chunk.chunk_type for chunk in iter_chunks(fixed_data)]
    assert side_notes == ["-FixItFelix:removed malformed/duplicate sPLT chunk(s)."]


def test_apply_repair_prompts_to_remove_all_transparent_overlong_trns_alpha_table():
    original = trns_too_many_entries_fixture_bytes()
    repair = fixit_felix.trns_length(
        original,
        ["GetInfo_Error_0:-tRNS Alpha indexes palettes entries must not be superior to PLTE entries"],
    )
    side_notes = []
    writes = []
    questions = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **kwargs: questions.append(kwargs) or True,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert questions == [
        {
            "id": (
                "tRNS Indexed Alpha Removal:-Trimmed tRNS would make every PLTE entry "
                "transparent. Remove tRNS instead?"
            ),
            "idhash": "tRNS-transparency:tRNS",
        }
    ]
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    assert b"tRNS" not in [chunk.chunk_type for chunk in iter_chunks(fixed_data)]
    assert side_notes == ["-FixItFelix:removed overlong indexed tRNS chunk."]


def test_apply_repair_can_trim_overlong_trns_when_removal_declined():
    original = trns_too_many_entries_fixture_bytes()
    repair = fixit_felix.trns_length(
        original,
        ["GetInfo_Error_0:-tRNS Alpha indexes palettes entries must not be superior to PLTE entries"],
    )
    side_notes = []
    writes = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **_kwargs: False,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    trns = next(chunk for chunk in iter_chunks(fixed_data) if chunk.chunk_type == b"tRNS")
    assert trns.length == 173
    assert side_notes == [
        "-FixItFelix:trimmed indexed tRNS length from 200 to PLTE entry count 173 and rebuilt CRC."
    ]


def test_apply_repair_prompts_before_zero_scanline_blackfill_and_declines_placeholder():
    repair = zero_scanline_blackfill_repair()
    side_notes = []
    writes = []
    questions = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **kwargs: questions.append(kwargs) or False,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result == (False, None)
    assert writes == []
    assert questions == [
        {
            "id": "IDAT Zero Scanline Blackfill:-No readable IDAT scanlines. Write all-black placeholder anyway?",
            "idhash": ("IDAT-zero-blackfill", 1, 2, 8, 2),
            "skipauto": True,
        }
    ]
    assert side_notes == [
        "-FixItFelix:skipped all-black placeholder because IDAT recovered 0/2 scanlines."
    ]


def test_apply_repair_can_write_zero_scanline_blackfill_when_confirmed():
    repair = zero_scanline_blackfill_repair()
    side_notes = []
    writes = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **_kwargs: True,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert len(writes) == 1
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    assert side_notes == [
        "-FixItFelix:partial-idat-blackfill recovered 0/2 scanlines.\n"
        "-FixItFelix:Selected IHDR 1x2, bit depth 8, color type 2."
    ]


def test_apply_repair_parks_partial_blackfill_preview_before_source_idat_bruteforce():
    source, repair = partial_scanline_blackfill_source_and_repair()
    idat_chunk = next(chunk for chunk in iter_chunks(source) if chunk.chunk_type == b"IDAT")
    side_notes = []
    writes = []
    previews = []
    questions = []
    smash_calls = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **kwargs: questions.append(kwargs) or True,
        preview_repair_image=lambda *args, **kwargs: previews.append((args, kwargs)),
        smash_brute_brawl=lambda *args, **kwargs: smash_calls.append((args, kwargs)),
        data_hex=source.hex(),
        file_origin="source-idat.png",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert writes == []
    assert previews == [((repair.data, "IDAT_Blackfill_Preview"), {"show": False})]
    assert questions == [
        {
            "id": (
                "IDAT partial blackfill:-Launch HephaestusForge after low "
                "chance diagnostic? (chance of success: maybe)"
            ),
            "idhash": (
                "IDAT-partial-blackfill-hephaestus",
                idat_chunk.offset,
                idat_chunk.length,
                repair.recovered_scanlines,
                repair.total_scanlines,
                repair.width,
                repair.height,
                "Insert",
            ),
            "skipauto": True,
        }
    ]
    assert smash_calls == [
        (
            (
                "source-idat.png",
                "IDAT",
                idat_chunk.length,
                idat_chunk.offset * 2,
                "FixItFelix partial IDAT blackfill HephaestusForge",
            ),
            {
                "EditMode": "Insert",
                "BfMode": "Brutus",
                "BruteCrc": True,
                "BruteLength": True,
                "BruteLevel": 1,
            },
        )
    ]
    assert "-FixItFelix: partial IDAT blackfill parked as preview while DaedalusForce runs; no final clone written yet." in side_notes
    assert "-FixItFelix: low DaedalusForce diagnostic selected HephaestusForge (Insert-first)." in side_notes
    assert "-FixItFelix: stored IDAT CRC already matches current bytes; using image probe." in side_notes
    diagnostic_messages = [call[1] for call in candy_calls if len(call) > 1 and "DaedalusForce IDAT diagnostic:" in call[1]]
    assert diagnostic_messages
    assert "image:" in diagnostic_messages[0]
    assert "decompressed:" in diagnostic_messages[0]
    assert "scanlines:" in diagnostic_messages[0]
    assert "CRC target: not useful" in diagnostic_messages[0]
    assert "DaedalusForce chance:" in diagnostic_messages[0]
    assert "HephaestusForge order: Insert -> Replace -> Remove" in diagnostic_messages[0]
    assert any("CRC is not an oracle for this run" in call[1] for call in candy_calls)


def test_apply_repair_keeps_visual_reference_blackfill_preview_only_without_sbb():
    source, repair = partial_scanline_blackfill_source_and_repair()
    side_notes = []
    writes = []
    previews = []
    candy_calls = []
    original_diagnostic = fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic

    def fake_diagnostic(_data, *, crc_target_trusted=False):
        return idat.SmashBruteBrawlIdatDiagnostic(
            supported=True,
            width=1,
            height=5,
            bit_depth=8,
            color_type=2,
            color_label="RGB",
            expected_decompressed_size=20,
            decompressed_size=21,
            missing_decompressed_size=0,
            complete_scanlines=5,
            total_scanlines=5,
            partial_scanline_bytes=0,
            scanline_size=4,
            idat_chunk_count=1,
            compressed_size=20,
            zlib_status="partial",
            crc_target_trusted=crc_target_trusted,
            crc_target_useful=False,
            success_estimate="maybe",
            success_reason="structure decodes but visual proof is missing.",
            recommended_repair_family="extra",
            hephaestus_order=("Remove", "Replace", "Insert"),
            cheap_twobytes_viable=True,
            requires_visual_reference=True,
        )

    fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = fake_diagnostic
    try:
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=side_notes,
            candy=lambda *args: candy_calls.append(args),
            write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
            preview_repair_image=lambda *args, **kwargs: previews.append((args, kwargs)),
            data_hex=source.hex(),
            file_origin="source-idat.png",
        )

        result = fixit_felix_runtime.apply_repair(runtime, repair)
    finally:
        fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = original_diagnostic

    assert result is True
    assert writes == []
    assert previews == [((repair.data, "IDAT_Blackfill_Preview"), {"show": False})]
    assert any("preview-only artifact" in note for note in side_notes)
    assert any("visual proof is missing" in call[1] for call in candy_calls if len(call) > 1)


def test_apply_repair_keeps_extra_data_blackfill_preview_only_without_sbb():
    source, repair = partial_scanline_blackfill_source_and_repair()
    repair = idat.PartialIdatBlackfillRepair(
        data=repair.data,
        strategy=repair.strategy,
        recovered_scanlines=repair.total_scanlines,
        total_scanlines=repair.total_scanlines,
        width=repair.width,
        height=repair.height,
        bit_depth=repair.bit_depth,
        color_type=repair.color_type,
    )
    side_notes = []
    writes = []
    previews = []
    original_diagnostic = fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic

    def fake_diagnostic(_data, *, crc_target_trusted=False):
        return idat.SmashBruteBrawlIdatDiagnostic(
            supported=True,
            width=1,
            height=5,
            bit_depth=8,
            color_type=2,
            color_label="RGB",
            expected_decompressed_size=20,
            decompressed_size=21,
            missing_decompressed_size=0,
            complete_scanlines=5,
            total_scanlines=5,
            partial_scanline_bytes=0,
            scanline_size=4,
            idat_chunk_count=1,
            compressed_size=20,
            zlib_status="partial",
            crc_target_trusted=crc_target_trusted,
            crc_target_useful=False,
            success_estimate="maybe",
            success_reason="structure decodes past the expected image payload.",
            recommended_repair_family="extra",
            hephaestus_order=("Remove", "Replace", "Insert"),
            cheap_twobytes_viable=True,
            requires_visual_reference=False,
        )

    fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = fake_diagnostic
    try:
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=side_notes,
            candy=lambda *args: None,
            write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
            preview_repair_image=lambda *args, **kwargs: previews.append((args, kwargs)),
            data_hex=source.hex(),
            file_origin="source-idat.png",
        )

        result = fixit_felix_runtime.apply_repair(runtime, repair)
    finally:
        fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = original_diagnostic

    assert result is True
    assert writes == []
    assert previews == [((repair.data, "IDAT_Blackfill_Preview"), {"show": False})]
    assert any("preview-only artifact" in note for note in side_notes)


def test_partial_blackfill_low_chance_opens_hephaestusforge():
    source, repair = partial_scanline_blackfill_source_and_repair()
    idat_chunk = next(chunk for chunk in iter_chunks(source) if chunk.chunk_type == b"IDAT")
    side_notes = []
    questions = []
    smash_calls = []
    candy_calls = []
    original_diagnostic = fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic

    def fake_diagnostic(_data, *, crc_target_trusted=False):
        return idat.SmashBruteBrawlIdatDiagnostic(
            supported=True,
            width=900,
            height=580,
            bit_depth=8,
            color_type=2,
            color_label="RGB",
            expected_decompressed_size=1_566_580,
            decompressed_size=1_491_984,
            missing_decompressed_size=74_596,
            complete_scanlines=552,
            total_scanlines=580,
            partial_scanline_bytes=1032,
            scanline_size=2701,
            idat_chunk_count=2,
            compressed_size=223_816,
            zlib_status="incomplete_stream",
            crc_target_trusted=crc_target_trusted,
            success_estimate="low",
            success_reason="no trusted CRC target and the decompressed gap is large.",
            recommended_repair_family="missing",
            hephaestus_order=("Insert", "Replace", "Remove"),
            cheap_twobytes_viable=False,
        )

    fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = fake_diagnostic
    try:
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=side_notes,
            candy=lambda *args: candy_calls.append(args),
            write_clone=lambda *_args: None,
            question=lambda **kwargs: questions.append(kwargs) or True,
            preview_repair_image=lambda *_args: None,
            smash_brute_brawl=lambda *args, **kwargs: smash_calls.append((args, kwargs)),
            data_hex=source.hex(),
            file_origin="source-idat.png",
        )

        result = fixit_felix_runtime.maybe_launch_partial_blackfill_bruteforce(runtime, repair)
    finally:
        fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = original_diagnostic

    assert result is True
    assert [question["idhash"][0] for question in questions] == [
        "IDAT-partial-blackfill-hephaestus",
    ]
    assert all("chance of success: low" in question["id"] for question in questions)
    assert questions[0]["idhash"][-1] == "Insert"
    assert smash_calls == [
        (
            (
                "source-idat.png",
                "IDAT",
                idat_chunk.length,
                idat_chunk.offset * 2,
                "FixItFelix partial IDAT blackfill HephaestusForge",
            ),
            {
                "EditMode": "Insert",
                "BfMode": "Brutus",
                "BruteCrc": True,
                "BruteLength": True,
                "BruteLevel": 1,
            },
        )
    ]
    assert any("may take years and still fail" in call[1] for call in candy_calls)
    assert "-FixItFelix: low DaedalusForce diagnostic selected HephaestusForge (Insert-first)." in side_notes


def test_partial_blackfill_hephaestus_can_prepare_visual_reference_roi():
    source, repair = partial_scanline_blackfill_source_and_repair()
    idat_chunk = next(chunk for chunk in iter_chunks(source) if chunk.chunk_type == b"IDAT")
    side_notes = []
    questions = []
    smash_calls = []
    editor_calls = []
    state = {}
    retry_state = {}
    original_diagnostic = fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic

    def fake_diagnostic(_data, *, crc_target_trusted=False):
        return idat.SmashBruteBrawlIdatDiagnostic(
            supported=True,
            width=900,
            height=580,
            bit_depth=8,
            color_type=2,
            color_label="RGB",
            expected_decompressed_size=1_566_580,
            decompressed_size=1_491_984,
            missing_decompressed_size=74_596,
            complete_scanlines=552,
            total_scanlines=580,
            partial_scanline_bytes=1032,
            scanline_size=2701,
            idat_chunk_count=2,
            compressed_size=223_816,
            zlib_status="incomplete_stream",
            crc_target_trusted=crc_target_trusted,
            success_estimate="low",
            success_reason="no trusted CRC target and the decompressed gap is large.",
            recommended_repair_family="missing",
            hephaestus_order=("Insert", "Replace", "Remove"),
            cheap_twobytes_viable=False,
            requires_visual_reference=True,
        )

    def fake_editor(*args, **kwargs):
        editor_calls.append((args, kwargs))
        return ultimate_reference_ui.ReferenceRegionEditorResult(
            True,
            args[2],
            region_count=1,
            reference_path="reference.png",
        )

    fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = fake_diagnostic
    try:
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=side_notes,
            candy=lambda *args: None,
            write_clone=lambda *_args: None,
            question=lambda **kwargs: questions.append(kwargs) or True,
            preview_repair_image=lambda *_args: None,
            smash_brute_brawl=lambda *args, **kwargs: smash_calls.append((args, kwargs)),
            data_hex=source.hex(),
            file_origin="source-idat.png",
            retry_state=retry_state,
            ultimate_linefeed_reference=lambda: "",
            ultimate_linefeed_reference_regions=lambda: "",
            ultimate_linefeed_reference_region_editor_run=fake_editor,
            set_ultimate_linefeed_reference=lambda value: state.__setitem__("reference", value),
            set_ultimate_linefeed_reference_mode=lambda value: state.__setitem__("mode", value),
            set_ultimate_linefeed_reference_regions=lambda value: state.__setitem__("regions", value),
        )

        result = fixit_felix_runtime.maybe_launch_partial_blackfill_bruteforce(runtime, repair)
    finally:
        fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = original_diagnostic

    assert result is True
    assert [question["idhash"][0] for question in questions] == [
        "IDAT-partial-blackfill-hephaestus",
        "IDAT-partial-blackfill-visual-reference",
    ]
    expected_regions = str(Path("Folder_source-idat") / "_ULF.reference_regions.json")
    assert editor_calls == [
        (
            (
                "source-idat.png",
                "",
                expected_regions,
            ),
            {"source_data": source},
        )
    ]
    assert state == {
        "reference": "reference.png",
        "mode": "similar",
        "regions": expected_regions,
    }
    assert retry_state["visual_reference"] == "reference.png"
    assert retry_state["visual_reference_regions"] == expected_regions
    assert "-FixItFelix: Visual reference ROI saved for DaedalusForce/HephaestusForge: %s" % expected_regions in side_notes
    assert smash_calls[0][0][3] == idat_chunk.offset * 2
    assert smash_calls[0][1]["BfMode"] == "Brutus"


def assert_partial_blackfill_cheap_route_uses_edit_mode(edit_mode, family, order):
    source, repair = partial_scanline_blackfill_source_and_repair()
    smash_calls = []
    original_diagnostic = fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic

    def fake_diagnostic(_data, *, crc_target_trusted=False):
        return idat.SmashBruteBrawlIdatDiagnostic(
            supported=True,
            width=1,
            height=5,
            bit_depth=8,
            color_type=2,
            color_label="RGB",
            expected_decompressed_size=20,
            decompressed_size=12,
            missing_decompressed_size=8,
            complete_scanlines=3,
            total_scanlines=5,
            partial_scanline_bytes=0,
            scanline_size=4,
            idat_chunk_count=1,
            compressed_size=20,
            zlib_status="partial",
            crc_target_trusted=crc_target_trusted,
            success_estimate="good",
            success_reason="stored IDAT CRC is a useful target.",
            recommended_repair_family=family,
            hephaestus_order=order,
            cheap_twobytes_viable=True,
        )

    fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = fake_diagnostic
    try:
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=[],
            candy=lambda *args: None,
            write_clone=lambda *_args: None,
            question=lambda **_kwargs: True,
            smash_brute_brawl=lambda *args, **kwargs: smash_calls.append((args, kwargs)),
            data_hex=source.hex(),
            file_origin="source-idat.png",
        )

        result = fixit_felix_runtime.maybe_launch_partial_blackfill_bruteforce(runtime, repair)
    finally:
        fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = original_diagnostic

    assert result is True
    assert smash_calls
    assert smash_calls[0][1]["EditMode"] == edit_mode
    assert smash_calls[0][1]["BfMode"] == "TwoBytes"
    assert smash_calls[0][1]["BruteLevel"] == 0
    idat_chunk = next(chunk for chunk in iter_chunks(source) if chunk.chunk_type == b"IDAT")
    assert smash_calls[0][0][3] == (idat_chunk.offset + 8) * 2


def test_partial_blackfill_cheap_missing_uses_insert():
    assert_partial_blackfill_cheap_route_uses_edit_mode(
        "Insert",
        "missing",
        ("Insert", "Replace", "Remove"),
    )


def test_partial_blackfill_cheap_extra_uses_remove():
    assert_partial_blackfill_cheap_route_uses_edit_mode(
        "Remove",
        "extra",
        ("Remove", "Replace", "Insert"),
    )


def test_partial_blackfill_force_level_starts_twobytes_at_requested_level():
    source, repair = partial_scanline_blackfill_source_and_repair()
    smash_calls = []
    side_notes = []
    retry_state = {}
    original_diagnostic = fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic

    def fake_diagnostic(_data, *, crc_target_trusted=False):
        return idat.SmashBruteBrawlIdatDiagnostic(
            supported=True,
            width=1,
            height=5,
            bit_depth=8,
            color_type=2,
            color_label="RGB",
            expected_decompressed_size=20,
            decompressed_size=12,
            missing_decompressed_size=8,
            complete_scanlines=3,
            total_scanlines=5,
            partial_scanline_bytes=0,
            scanline_size=4,
            idat_chunk_count=1,
            compressed_size=20,
            zlib_status="partial",
            crc_target_trusted=crc_target_trusted,
            success_estimate="good",
            success_reason="stored IDAT CRC is a useful target.",
            recommended_repair_family="missing",
            hephaestus_order=("Insert", "Replace", "Remove"),
            cheap_twobytes_viable=True,
        )

    fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = fake_diagnostic
    try:
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=side_notes,
            candy=lambda *args: None,
            write_clone=lambda *_args: None,
            question=lambda **_kwargs: True,
            smash_brute_brawl=lambda *args, **kwargs: smash_calls.append((args, kwargs)),
            data_hex=source.hex(),
            file_origin="source-idat.png",
            retry_state=retry_state,
            smash_brute_brawl_force_level=2,
        )

        result = fixit_felix_runtime.maybe_launch_partial_blackfill_bruteforce(runtime, repair)
    finally:
        fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = original_diagnostic

    assert result is True
    assert smash_calls[0][1]["BfMode"] == "TwoBytes"
    assert smash_calls[0][1]["BruteLevel"] == 2
    assert retry_state["active_pass"]["brute_level"] == 2
    assert "-FixItFelix: DaedalusForce forced to start at brute-force level 2." in side_notes


def test_partial_blackfill_focus_prompt_defaults_to_recommendation():
    source, repair = partial_scanline_blackfill_source_and_repair()
    inputs = []
    smash_calls = []
    retry_state = {}
    original_diagnostic = fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic

    def fake_diagnostic(_data, *, crc_target_trusted=False):
        return idat.SmashBruteBrawlIdatDiagnostic(
            supported=True,
            width=1,
            height=5,
            bit_depth=8,
            color_type=2,
            color_label="RGB",
            expected_decompressed_size=20,
            decompressed_size=20,
            missing_decompressed_size=0,
            complete_scanlines=5,
            total_scanlines=5,
            partial_scanline_bytes=0,
            scanline_size=4,
            idat_chunk_count=1,
            compressed_size=20,
            zlib_status="bad_adler",
            crc_target_trusted=crc_target_trusted,
            success_estimate="good",
            success_reason="stored IDAT CRC is a useful target.",
            recommended_repair_family="extra",
            hephaestus_order=("Remove", "Replace", "Insert"),
            cheap_twobytes_viable=True,
        )

    fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = fake_diagnostic
    try:
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=[],
            candy=lambda *args: None,
            write_clone=lambda *_args: None,
            question=lambda **_kwargs: True,
            smash_brute_brawl=lambda *args, **kwargs: smash_calls.append((args, kwargs)),
            data_hex=source.hex(),
            file_origin="source-idat.png",
            interactive=True,
            retry_state=retry_state,
            input_func=lambda prompt: inputs.append(prompt) or "",
        )

        result = fixit_felix_runtime.maybe_launch_partial_blackfill_bruteforce(runtime, repair)
    finally:
        fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = original_diagnostic

    assert result is True
    assert inputs and inputs[0].startswith("DaedalusForce focus [2 Remove focus]")
    assert retry_state["campaign_focus"] == "remove"
    assert retry_state["hephaestus_order"] == ("Remove", "Replace", "Insert")
    assert smash_calls[0][1]["EditMode"] == "Remove"


def test_partial_blackfill_focus_prompt_can_override_recommendation():
    source, repair = partial_scanline_blackfill_source_and_repair()
    smash_calls = []
    retry_state = {}
    original_diagnostic = fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic

    def fake_diagnostic(_data, *, crc_target_trusted=False):
        return idat.SmashBruteBrawlIdatDiagnostic(
            supported=True,
            width=1,
            height=5,
            bit_depth=8,
            color_type=2,
            color_label="RGB",
            expected_decompressed_size=20,
            decompressed_size=20,
            missing_decompressed_size=0,
            complete_scanlines=5,
            total_scanlines=5,
            partial_scanline_bytes=0,
            scanline_size=4,
            idat_chunk_count=1,
            compressed_size=20,
            zlib_status="bad_adler",
            crc_target_trusted=crc_target_trusted,
            success_estimate="good",
            success_reason="stored IDAT CRC is a useful target.",
            recommended_repair_family="extra",
            hephaestus_order=("Remove", "Replace", "Insert"),
            cheap_twobytes_viable=True,
        )

    fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = fake_diagnostic
    try:
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=[],
            candy=lambda *args: None,
            write_clone=lambda *_args: None,
            question=lambda **_kwargs: True,
            smash_brute_brawl=lambda *args, **kwargs: smash_calls.append((args, kwargs)),
            data_hex=source.hex(),
            file_origin="source-idat.png",
            interactive=True,
            retry_state=retry_state,
            input_func=lambda _prompt: "3",
        )

        result = fixit_felix_runtime.maybe_launch_partial_blackfill_bruteforce(runtime, repair)
    finally:
        fixit_felix_runtime.idat.analyze_sbb_idat_diagnostic = original_diagnostic

    assert result is True
    assert retry_state["campaign_focus"] == "replace"
    assert retry_state["hephaestus_order"] == ("Replace", "Remove", "Insert")
    assert smash_calls[0][1]["EditMode"] == "Replace"


def test_partial_blackfill_bruteforce_uses_stored_crc_only_when_it_targets_original():
    source, repair = partial_scanline_blackfill_source_and_repair()
    idat_chunk = next(chunk for chunk in iter_chunks(source) if chunk.chunk_type == b"IDAT")
    mutable = bytearray(source)
    mutable[idat_chunk.offset + 8] ^= 0x01
    smash_calls = []
    side_notes = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda *_args: None,
        question=lambda **_kwargs: True,
        smash_brute_brawl=lambda *args, **kwargs: smash_calls.append((args, kwargs)),
        data_hex=bytes(mutable).hex(),
        file_origin="source-idat.png",
    )

    result = fixit_felix_runtime.maybe_launch_partial_blackfill_bruteforce(runtime, repair)

    assert result is True
    assert smash_calls[0][1]["BruteLevel"] == 0
    assert smash_calls[0][1]["OldCrc"] == idat_chunk.crc.to_bytes(4, "big").hex()
    assert side_notes[-1] == "-FixItFelix: DaedalusForce will use stored IDAT CRC as target."


def test_apply_repair_offers_local_idat_donor_before_black_placeholder():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        broken_dir = root / "brokenjavapngsuite"
        donor_dir = root / "schaik-javapng-samples"
        broken_dir.mkdir()
        donor_dir.mkdir()
        broken_path = broken_dir / "truncate_idat_1.png"
        donor_path = donor_dir / "basn0g01.png"
        broken_data = truncate_idat_1_fixture_bytes()
        donor_data = (ROOT / "schaik-javapng-samples" / "basn0g01.png").read_bytes()
        broken_path.write_bytes(broken_data)
        donor_path.write_bytes(donor_data)

        repair = idat.rebuild_partial_idat_blackfill(broken_data)
        assert repair is not None
        assert repair.recovered_scanlines == 0

        side_notes = []
        writes = []
        questions = []
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=side_notes,
            candy=lambda *args: None,
            write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
            question=lambda **kwargs: questions.append(kwargs) or True,
            data_hex=broken_data.hex(),
            file_origin=str(broken_path),
        )

        result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert len(writes) == 1
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    fixed_stream = b"".join(
        chunk.data for chunk in iter_chunks(fixed_data) if chunk.chunk_type == b"IDAT"
    )
    donor_stream = b"".join(
        chunk.data for chunk in iter_chunks(donor_data) if chunk.chunk_type == b"IDAT"
    )
    assert zlib.decompress(fixed_stream) == zlib.decompress(donor_stream)
    assert questions == [
        {
            "id": (
                "IDAT donor repair:-No readable IDAT scanlines. Replace IDAT with "
                "local donor %s?"
                % donor_path
            ),
            "idhash": (
                "IDAT-donor",
                str(donor_path),
                32,
                32,
                1,
                0,
            ),
            "skipauto": True,
        }
    ]
    assert side_notes == [
        "-FixItFelix:idat-donor-basn0g01.\n"
        "-FixItFelix:Selected IHDR 32x32, bit depth 1, color type 0. "
        "-FixItFelix:IDAT donor: %s." % donor_path
    ]


def test_apply_repair_offers_synthetic_idat_when_no_local_donor_exists():
    broken_data = truncate_idat_1_fixture_bytes()
    repair = idat.rebuild_partial_idat_blackfill(broken_data)
    assert repair is not None
    assert repair.recovered_scanlines == 0

    side_notes = []
    writes = []
    questions = []
    original_candidates = fixit_felix_runtime._candidate_idat_donor_paths
    fixit_felix_runtime._candidate_idat_donor_paths = lambda _file_origin: ()
    try:
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=side_notes,
            candy=lambda *args: None,
            write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
            question=lambda **kwargs: questions.append(kwargs) or True,
            data_hex=broken_data.hex(),
            file_origin="truncate_idat_1.png",
        )

        result = fixit_felix_runtime.apply_repair(runtime, repair)
    finally:
        fixit_felix_runtime._candidate_idat_donor_paths = original_candidates

    assert result is True
    assert len(writes) == 1
    fixed_data = bytes.fromhex(writes[0][0])
    assert validate_png_structure(fixed_data).ok
    stream = b"".join(chunk.data for chunk in iter_chunks(fixed_data) if chunk.chunk_type == b"IDAT")
    assert zlib.decompress(stream) != b"\x00" * 160
    assert questions == [
        {
            "id": "IDAT synthetic repair:-No original scanlines. Build synthetic diagnostic IDAT?",
            "idhash": ("IDAT-synthetic", 32, 32, 1, 0),
            "skipauto": True,
        }
    ]
    assert side_notes == [
        "-FixItFelix:idat-synthetic-diagnostic.\n"
        "-FixItFelix:Selected IHDR 32x32, bit depth 1, color type 0. "
        "-FixItFelix:synthetic IDAT pattern: diagnostic; original pixels were not recoverable."
    ]


def test_apply_repair_prompts_before_unproven_chrm_inference():
    side_notes = []
    writes = []
    question_calls = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **kwargs: question_calls.append(kwargs) or True,
    )
    repair = SimpleNamespace(
        data=b"inferred",
        strategy="inferred 1 missing cHRM byte(s) and rebuilt CRC",
        chunk_offset=49,
        old_length=31,
        new_length=32,
        missing_bytes=1,
        inferred_payload=b"x" * 32,
        removal_data=b"removed",
        preserved_crc=False,
        removed=False,
        crc_candidates_tested=256,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert question_calls[0]["skipauto"] is True
    assert question_calls[0]["id"] == "cHRM Missing Bytes Inference:-cHRM length is not Valid"
    assert any("None matched" in call[1] for call in candy_calls if len(call) > 1)
    assert side_notes == ["-FixItFelix:inferred 1 missing cHRM byte(s) and rebuilt CRC."]
    assert writes == [("696e666572726564", "-inferred 1 missing cHRM byte(s) and rebuilt CRC.")]


def test_apply_repair_removes_short_chrm_when_inference_declined():
    side_notes = []
    writes = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **_kwargs: False,
    )
    repair = SimpleNamespace(
        data=b"inferred",
        strategy="inferred 1 missing cHRM byte(s) and rebuilt CRC",
        chunk_offset=49,
        old_length=31,
        new_length=32,
        missing_bytes=1,
        inferred_payload=b"x" * 32,
        removal_data=b"removed",
        preserved_crc=False,
        removed=False,
        crc_candidates_tested=256,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert side_notes == [
        "-FixItFelix:removed short cHRM chunk length 31 below required 32 after declining inferred cHRM completion."
    ]
    assert writes == [("72656d6f766564", "-removed short cHRM chunk length 31 below required 32.")]


def test_apply_repair_explains_ihdr_rebuild_before_writing_clone():
    side_notes = []
    writes = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        pandora_box={
            "Checksum_Error_0:Wrong Crc b'IHDR'": {},
        },
    )
    data = valid_png_bytes()
    repair = SimpleNamespace(
        data=data,
        strategy="rebuilt IHDR from IDAT scanline size",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert candy_calls == [
        (
            "Cowsay",
            "This is not just a cheap CRC sticker swap. I rebuilt IHDR from the image clues first.",
            "com",
        ),
        (
            "Cowsay",
            "Now I can write a clone with a coherent header instead of pretending the old one was fine.",
            "com",
        ),
    ]
    assert side_notes == ["-FixItFelix:rebuilt IHDR from IDAT scanline size."]
    assert writes == [(data.hex(), "-rebuilt IHDR from IDAT scanline size.")]


def test_apply_repair_explains_ihdr_value_rebuild_without_crc_noise():
    side_notes = []
    writes = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        pandora_box={
            "GetInfo_Error_0:-IHDR Color 3: Wrong bit depht with IHDR Color type 3": {},
        },
    )
    data = valid_png_bytes()
    repair = SimpleNamespace(
        data=data,
        strategy="rebuilt IHDR from IDAT scanline size",
        width=32,
        height=32,
        bit_depth=8,
        color_type=3,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert candy_calls == [
        (
            "Cowsay",
            "IHDR's CRC is not the complaint here. The header values themselves are impossible together.",
            "bad",
        ),
        (
            "Cowsay",
            "I rebuilt IHDR from the IDAT scanline math: 32x32, bit depth 8, color type 3.",
            "com",
        ),
        (
            "Cowsay",
            "Now I can write a clone with a coherent header instead of pretending the old one was fine.",
            "com",
        ),
    ]
    assert not any("cheap CRC" in call[1] for call in candy_calls)
    assert side_notes == [
        "-FixItFelix:rebuilt IHDR from IDAT scanline size.\n"
        "-FixItFelix:Selected IHDR 32x32, bit depth 8, color type 3."
    ]
    assert writes == [(data.hex(), "-rebuilt IHDR from IDAT scanline size.")]


def test_apply_repair_rejects_invalid_ihdr_rebuild_before_clone():
    side_notes = []
    writes = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
    )
    repair = SimpleNamespace(
        data=b"fixed",
        strategy="rebuilt IHDR from IDAT scanline size",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result == (False, None)
    assert writes == []
    assert candy_calls == [
        (
            "Cowsay",
            "The rebuilt IHDR still does not make a structurally valid PNG: PNG signature is not at offset 0",
            "bad",
        ),
        (
            "Cowsay",
            "So I am not writing that clone. Next stop is the IHDR brute force path.",
            "com",
        ),
    ]
    assert side_notes == [
        "-FixItFelix:IHDR automatic repair rejected before clone write: PNG signature is not at offset 0."
    ]


def test_apply_repair_explains_duplicate_ihdr_cut_without_rebuild_noise():
    data = valid_png_bytes()
    side_notes = []
    writes = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, summary: writes.append((data_hex, summary)),
    )
    repair = SimpleNamespace(
        data=data,
        strategy="removed duplicate IHDR chunk(s) after first header",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert candy_calls == [
        (
            "Cowsay",
            "PNG only gets one IHDR. I am keeping the first header and cutting the duplicate.",
            "com",
        ),
    ]
    assert side_notes == ["-FixItFelix:removed duplicate IHDR chunk(s) after first header."]
    assert writes == [
        (
            data.hex(),
            "-removed duplicate IHDR chunk(s) after first header.",
        ),
    ]


def test_try_ihdr_stored_crc_bruteforce_uses_loader_and_writes_valid_candidate():
    data = valid_png_bytes()
    calls = []
    side_notes = []
    original_run_scan = fixit_felix_runtime.bruteforce_runtime.run_scan

    def fake_run_scan(scan_runtime, scan_context):
        calls.append(("scan_context", scan_context))
        scan_runtime.loadingbar(50, 2, 0, True)
        scan_runtime.loadingbar(50, 2, 25, False)
        scan_runtime.minibar(Indication="scan-started")
        return fixit_felix_runtime.bruteforce_runtime.SmashBruteBrawlScanResult(
            state=fixit_felix_runtime.bruteforce.BruteForceMatchState(bingo=True),
            old_crc=b"crc!",
            bf_mode="Brutus",
            full_new_data=b"",
            png_bytes=data,
            to_brute="",
            diff="",
            crash=False,
            eta_seconds=0,
        )

    try:
        fixit_felix_runtime.bruteforce_runtime.run_scan = fake_run_scan
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=side_notes,
            candy=lambda *args: calls.append(("candy", args)),
            write_clone=lambda data_hex, summary: calls.append(("write_clone", data_hex, summary)),
            question=lambda **kwargs: calls.append(("question", kwargs)) or True,
            data_hex=data.hex(),
            pandora_box={"Checksum_Error_0:Wrong Crc b'IHDR'": {}},
            get_spec=lambda *args, **kwargs: calls.append(("get_spec", args, kwargs)),
            product=lambda *args, **kwargs: calls.append(("product", args, kwargs)),
            loadingbar=lambda *args, **kwargs: calls.append(("loadingbar", args, kwargs)),
            minibar=lambda *args, **kwargs: calls.append(("minibar", args, kwargs)),
            file_origin="sample.png",
        )
        repair = SimpleNamespace(
            data=data,
            strategy="rebuilt IHDR from IDAT scanline size",
            preserved_crc=False,
        )

        result = fixit_felix_runtime.try_ihdr_stored_crc_bruteforce(runtime, repair)
    finally:
        fixit_felix_runtime.bruteforce_runtime.run_scan = original_run_scan

    assert result is True
    assert (
        "question",
        {"id": "IHDR CRC Brute Force:-Wrong Crc b'IHDR'", "idhash": ("IHDR", 8, 981375829)},
    ) in calls
    assert ("minibar", (), {"Indication": "IHDR CRC brute force: stored CRC target"}) in calls
    assert ("minibar", (), {"Indication": "IHDR CRC 0/50"}) in calls
    assert ("minibar", (), {"Indication": "IHDR CRC 25/50"}) in calls
    assert ("minibar", (), {"Indication": "scan-started"}) in calls
    scan_context = next(call[1] for call in calls if call[0] == "scan_context")
    assert scan_context.chunk_name == b"IHDR"
    assert scan_context.bf_mode == "Brutus"
    assert scan_context.old_crc is not False
    assert any(call[0] == "write_clone" and call[1] == data.hex() for call in calls)
    assert "-FixItFelix:IHDR stored-CRC brute force succeeded." in side_notes


def test_try_ihdr_stored_crc_bruteforce_decline_falls_back_to_rebuild():
    data = valid_png_bytes()
    calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=[],
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *args: calls.append(("write_clone", args)),
        question=lambda **kwargs: calls.append(("question", kwargs)) or False,
        data_hex=data.hex(),
        pandora_box={"Checksum_Error_0:Wrong Crc b'IHDR'": {}},
        minibar=lambda *args, **kwargs: calls.append(("minibar", args, kwargs)),
    )
    repair = SimpleNamespace(
        data=data,
        strategy="rebuilt IHDR from IDAT scanline size",
        preserved_crc=False,
    )

    result = fixit_felix_runtime.try_ihdr_stored_crc_bruteforce(runtime, repair)

    assert result is None
    assert (
        "question",
        {"id": "IHDR CRC Brute Force:-Wrong Crc b'IHDR'", "idhash": ("IHDR", 8, 981375829)},
    ) in calls
    assert not any(call[0] == "write_clone" for call in calls)


def test_apply_gama_zero_discards_false_positive_and_returns_legacy_target():
    finding = "GetInfo_Error_0:gAMA Chunk of 0 is Useless"
    pandora_box = {finding: {"gAMA_Tool_0": "sample.png"}}
    side_notes = []
    candy_calls = []
    target = object()
    runtime = fixit_felix_runtime.GamaZeroRuntime(
        candy=lambda *args: candy_calls.append(args),
        pandora_box=pandora_box,
        side_notes=side_notes,
        return_value=target,
    )

    result = fixit_felix_runtime.apply_gama_zero(
        runtime,
        fixit_felix.gama_zero_decision(finding),
    )

    assert result == (True, target)
    assert candy_calls == [
        ("Cowsay", "Bah that's just a warning who cares ?! !", "good")
    ]
    assert pandora_box == {}
    assert side_notes == [
        "-Found False-Positive :[Error:-GetInfo_Error_0:gAMA Chunk of 0 is Useless]."
    ]


def test_apply_gama_zero_rejects_unknown_action():
    runtime = fixit_felix_runtime.GamaZeroRuntime(
        candy=lambda *args: None,
        pandora_box={},
        side_notes=[],
        return_value=object(),
    )

    try:
        fixit_felix_runtime.apply_gama_zero(
            runtime,
            SimpleNamespace(action="unknown"),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix gAMA action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown gAMA action")


def critical_miss_runtime(emitted, pauses, *, candy_calls=None):
    if candy_calls is None:
        candy_calls = []
    state = {"explained": False, "seen": set()}

    def remember_finding(finding):
        text = str(finding)
        if text in state["seen"]:
            return False
        state["seen"].add(text)
        return True

    return fixit_felix_runtime.CriticalMissRuntime(
        emit=emitted.append,
        candy=lambda *args: candy_calls.append(args),
        pause=pauses.append,
        idat_crc_patch_failed=lambda: False,
        idat_crc_patch_failed_finding=lambda: None,
        idat_crc_defer_explained=lambda: state["explained"],
        set_idat_crc_defer_explained=lambda value: state.__setitem__("explained", value),
        remember_deferred_idat_crc_finding=remember_finding,
    )


def test_apply_critical_miss_emits_and_pauses_on_debug_action():
    emitted = []
    pauses = []
    runtime = critical_miss_runtime(emitted, pauses)
    finding = "CheckChunkOrder_Error_0:Critical"

    result = fixit_felix_runtime.apply_critical_miss(
        runtime,
        fixit_felix.critical_miss_decision(
            finding,
            debug=True,
            pause_debug=True,
        ),
    )

    assert result == (False, None)
    assert emitted == ["\n-\033[1;31;49mCriticalMiss\033[m: %s" % finding]
    assert pauses == ["Pause:Debug"]


def test_apply_critical_miss_continue_does_not_pause():
    emitted = []
    pauses = []
    runtime = critical_miss_runtime(emitted, pauses)
    finding = "CheckChunkOrder_Error_0:Critical"

    result = fixit_felix_runtime.apply_critical_miss(
        runtime,
        fixit_felix.critical_miss_decision(
            finding,
            debug=True,
            pause_debug=False,
        ),
    )

    assert result == (False, None)
    assert emitted == ["\n-\033[1;31;49mCriticalMiss\033[m: %s" % finding]
    assert pauses == []


def test_apply_critical_miss_rejects_unknown_action():
    runtime = critical_miss_runtime([], [])

    try:
        fixit_felix_runtime.apply_critical_miss(
            runtime,
            SimpleNamespace(action="unknown", finding="Critical"),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix critical-miss action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown critical-miss action")


def test_repeated_deferred_repair_message_templates_are_adaptable():
    assert len(fixit_felix_runtime.REPEATED_DEFER_MESSAGE_TEMPLATES) == 20

    first = fixit_felix_runtime.repeated_deferred_repair_message(
        error_label="wrong CRC",
        chunk=b"IDAT",
        chooser=lambda choices: choices[0],
    )
    other_chunk = fixit_felix_runtime.repeated_deferred_repair_message(
        error_label="wrong CRC",
        chunk=b"PLTE",
        chooser=lambda choices: choices[1],
    )
    other_error = fixit_felix_runtime.repeated_deferred_repair_message(
        error_label="bad length",
        chunk=b"IEND",
        chooser=lambda choices: choices[-1],
    )
    generic = fixit_felix_runtime.repeated_deferred_repair_message(
        error_label="repeated route",
        chooser=lambda choices: choices[-1],
    )

    assert first == (
        "Ah shit ...here we go again ...another wrong CRC in an IDAT chunk in Grove Street. "
        "I will keep it for later."
    )
    assert "wrong CRC in a PLTE chunk" in other_chunk
    assert "bad length in an IEND chunk" in other_error
    assert generic == "Fine. repeated route goes into the later pile."


def wrong_crc_tools(*, chunk=b"IDAT", offset="0x2a", start=12, end=20, replacement_crc="fixed-crc-data"):
    return SimpleNamespace(
        replacement_crc=replacement_crc,
        start=start,
        end=end,
        chunk=chunk,
        offset=offset,
        old_crc="old-crc",
    )


def bad_deflate_png_crc_patch():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00",
    )
    idat_payload = b"\x00\x00\xff\xff"
    idat_chunk = build_png_chunk(b"IDAT", idat_payload)
    data = PNG_SIGNATURE + ihdr + idat_chunk + IEND_CHUNK
    idat_offset = len(PNG_SIGNATURE) + len(ihdr)
    crc_start = (idat_offset + 8 + len(idat_payload)) * 2
    crc_end = crc_start + 8
    replacement_crc = data[idat_offset + 8 + len(idat_payload) : idat_offset + 12 + len(idat_payload)].hex()
    return data.hex(), replacement_crc, crc_start, crc_end


def one_byte_corrupt_deflate_png_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x02\x08\x02\x00\x00\x00",
    )
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[2] ^= 0xFF
    data = PNG_SIGNATURE + ihdr + build_png_chunk(b"IDAT", bytes(compressed)) + IEND_CHUNK
    return data.hex()


def semantic_token_corrupt_deflate_png_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x64\x08\x02\x00\x00\x00",
    )
    filtered = b"".join(
        b"\x00" + bytes(((row * 3) % 256, (row * 7) % 256, (row * 11) % 256))
        for row in range(100)
    )
    compressed = zlib.compress(filtered, 1)
    corrupted = idat_bruteforce._replace_stream_bits_preserve_length(
        compressed,
        618,
        619,
        (1, 1, 0),
    )
    assert corrupted is not None
    data = PNG_SIGNATURE + ihdr + build_png_chunk(b"IDAT", corrupted) + IEND_CHUNK
    return data.hex()


def crc_guided_deflate_png_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x64\x08\x02\x00\x00\x00",
    )
    filtered = b"".join(
        b"\x00" + bytes(((row * 3) % 256, (row * 7) % 256, (row * 11) % 256))
        for row in range(100)
    )
    compressed = zlib.compress(filtered, 1)
    data = (
        PNG_SIGNATURE
        + ihdr
        + build_png_chunk(b"IDAT", compressed[:256])
        + build_png_chunk(b"IDAT", compressed[256:])
        + IEND_CHUNK
    )
    candidate = bytearray(data)
    idat_chunks = [chunk for chunk in iter_chunks(data) if chunk.chunk_type == b"IDAT"]
    for bit in (604, 618, 620):
        remaining = bit // 8
        for chunk in idat_chunks:
            if remaining < chunk.length:
                candidate[chunk.offset + 8 + remaining] ^= 1 << (bit % 8)
                break
            remaining -= chunk.length
    return bytes(candidate).hex()


def bad_adler_png_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x02\x08\x02\x00\x00\x00",
    )
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    data = PNG_SIGNATURE + ihdr + build_png_chunk(b"IDAT", bytes(compressed)) + IEND_CHUNK
    return data.hex()


def bad_adler_three_scanline_png_bytes():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x03\x08\x00\x00\x00\x00",
    )
    filtered = b"\x00A\x00B\x00C"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    return PNG_SIGNATURE + ihdr + build_png_chunk(b"IDAT", bytes(compressed)) + IEND_CHUNK


def bad_adler_three_scanline_one_bad_filter_png_bytes():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x03\x08\x00\x00\x00\x00",
    )
    filtered = b"\x00A\x00B\x11C"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    return PNG_SIGNATURE + ihdr + build_png_chunk(b"IDAT", bytes(compressed)) + IEND_CHUNK


def grayscale_png_from_rows(rows):
    height = len(rows)
    width = len(rows[0]) if rows else 1
    ihdr = build_png_chunk(
        b"IHDR",
        width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x00\x00\x00\x00",
    )
    filtered = b"".join(b"\x00" + bytes(row) for row in rows)
    return PNG_SIGNATURE + ihdr + build_png_chunk(b"IDAT", zlib.compress(filtered)) + IEND_CHUNK


def smooth_gray_png(width=32, height=16):
    rows = [
        bytes(min(255, (row * 3) + (column // 4)) for column in range(width))
        for row in range(height)
    ]
    return grayscale_png_from_rows(rows)


def noisy_gray_png(width=32, height=16):
    rows = [
        bytes(((row * 73) + (column * 151) + ((row ^ column) * 37)) & 0xFF for column in range(width))
        for row in range(height)
    ]
    return grayscale_png_from_rows(rows)


def wrong_crc_runtime(
    calls,
    *,
    answers=(),
    pandora_box=None,
    cl_offset=33,
    crc_offset=101,
    original_chunk_length_hex="0d",
    debug=False,
    pause_debug=False,
    data_hex="00112233445566778899",
    side_notes=None,
    last_question_status=None,
    deferred_routes=None,
    deflate_probe_keys=None,
    preview_repair_image=None,
    loadingbar=None,
    minibar=None,
    interactive=False,
    input_func=None,
    deep_beam_workers=None,
    deep_beam_gpu=None,
    deep_beam_gpu_config=None,
    deep_beam_budget=None,
    deep_beam_max_depth=None,
    huffman_kraft_budget=None,
    huffman_kraft_workers=None,
    huffman_kraft_gpu_config=None,
    kraft_backref_budget=None,
    global_crc_residue_budget=None,
    affine_corruption_budget=None,
    deflate_salvage_budget=None,
    file_origin="",
    file_dir="",
):
    answer_iter = iter(answers)
    if deferred_routes is None:
        deferred_routes = set()
    if deflate_probe_keys is None:
        deflate_probe_keys = set()
    if side_notes is None:
        side_notes = []

    def record(name, result=None):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return callback

    def question(*args, **kwargs):
        calls.append(("question", args, kwargs))
        return next(answer_iter)

    def remember_deferred_route(finding, tools):
        calls.append(("remember_deferred_idat_crc_route", (finding, tools), {}))
        deferred_routes.add(fixit_felix_runtime.deferred_idat_crc_route_key(finding, tools))

    def is_deferred_route(finding, tools):
        calls.append(("is_deferred_idat_crc_route", (finding, tools), {}))
        return fixit_felix_runtime.deferred_idat_crc_route_key(finding, tools) in deferred_routes

    def remember_deflate_probe(analysis):
        calls.append(("remember_idat_deflate_probe", (analysis,), {}))
        key = fixit_felix_runtime.idat_deflate_probe_key(analysis)
        if key in deflate_probe_keys:
            return False
        deflate_probe_keys.add(key)
        return True

    return fixit_felix_runtime.WrongCrcRuntime(
        emit=record("emit"),
        candy=record("candy"),
        question=question,
        save_clone=record("save_clone", "saved"),
        write_clone=record("write_clone", "written"),
        chunk_story=record("chunk_story"),
        set_skip_bad_crc=record("set_skip_bad_crc"),
        set_old_bad_crc=record("set_old_bad_crc"),
        side_notes=side_notes,
        pandora_box=pandora_box if pandora_box is not None else {},
        data_hex=data_hex,
        cl_offset=cl_offset,
        crc_offset=crc_offset,
        original_chunk_length_hex=original_chunk_length_hex,
        last_question_status=lambda: last_question_status,
        set_idat_crc_patch_failed=record("set_idat_crc_patch_failed"),
        set_idat_crc_patch_failed_finding=record("set_idat_crc_patch_failed_finding"),
        remember_deferred_idat_crc_route=remember_deferred_route,
        is_deferred_idat_crc_route=is_deferred_route,
        remember_idat_deflate_probe=remember_deflate_probe,
        debug=debug,
        pause_debug=pause_debug,
        preview_repair_image=preview_repair_image,
        loadingbar=loadingbar,
        minibar=minibar,
        file_origin=file_origin,
        file_dir=file_dir,
        interactive=interactive,
        input_func=input_func,
        deep_beam_workers=deep_beam_workers,
        deep_beam_gpu=deep_beam_gpu,
        deep_beam_gpu_config=deep_beam_gpu_config,
        deep_beam_budget=deep_beam_budget,
        deep_beam_max_depth=deep_beam_max_depth,
        huffman_kraft_budget=huffman_kraft_budget,
        huffman_kraft_workers=huffman_kraft_workers,
        huffman_kraft_gpu_config=huffman_kraft_gpu_config,
        kraft_backref_budget=kraft_backref_budget,
        global_crc_residue_budget=global_crc_residue_budget,
        affine_corruption_budget=affine_corruption_budget,
        deflate_salvage_budget=deflate_salvage_budget,
        set_idat_deflate_route_consumed=record("set_idat_deflate_route_consumed"),
    )


def mock_frontier_routes_empty(monkeypatch):
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_periodic_model_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_affine_corruption_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_huffman_kraft_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_first_filter_literal_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_kraft_backref_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_stored_block_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_huffman_oracle_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_global_crc_residue_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_crc_periodic_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_deflate_resync_salvage_runtime", lambda *_args, **_kwargs: None)


def idat_deep_beam_seed(data, *, state_id=1, kind="test-seed"):
    before = idat.analyze_idat_stream(data)
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    return idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(
            idat_bruteforce.IdatDeepBeamOperation(
                kind,
                0,
                stream[:1],
                stream[:1],
            ),
        ),
        before=before,
        after=before,
        state_id=state_id,
        parent_id=0,
        source_offsets=(0,),
        score=(state_id,),
    )


def idat_progress_seed(
    data,
    *,
    state_id,
    usable_scanlines,
    decompressed_size,
    kind="test-seed",
    complete_scanlines=None,
):
    before = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=1,
    )
    after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="bad_adler",
        height=10,
        expected_size=1000,
        decompressed_size=decompressed_size,
        usable_scanlines=usable_scanlines,
        complete_scanlines=usable_scanlines if complete_scanlines is None else complete_scanlines,
        error_offset=state_id,
    )
    stream = b"stream-%d" % state_id
    return idat_bruteforce.IdatDeepBeamCandidate(
        data=data + bytes((state_id,)),
        stream=stream,
        operations=(
            idat_bruteforce.IdatDeepBeamOperation(
                kind,
                state_id,
                stream[:1],
                stream[-1:],
            ),
        ),
        before=before,
        after=after,
        state_id=state_id,
        parent_id=0,
        source_offsets=(state_id,),
        score=(state_id,),
    )


def test_apply_wrong_crc_easy_answer_saves_clone():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'gAMA'"
    chkd = "gAMA_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(chunk=b"gAMA"),
    )

    assert result == (True, "saved")
    assert (
        "candy",
        (
            "Cowsay",
            "This is the cheap CRC-only patch: I am changing the checksum label, not the chunk data.",
            "com",
        ),
        {},
    ) in calls
    assert (
        "candy",
        (
            "Cowsay",
            "If the bytes are lying too, this will not save them. But the structure lets me try this tiny bandage.",
            "com",
        ),
        {},
    ) in calls
    assert calls[-1] == (
        "save_clone",
        (
            "fixed-crc-data",
            12,
            20,
            "-Found Chunk[b'gAMA'] has Wrong Crc at offset: 0x2a\n"
            "-Replaced with: fixed-crc-data old value was: old-crc",
        ),
        {},
    )


def test_apply_wrong_crc_easy_decline_then_final_decline_keeps_skip_none_and_saves():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'gAMA'"
    chkd = "gAMA_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(False, False),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(chunk=b"gAMA"),
    )

    assert result == (True, "saved")
    assert ("set_skip_bad_crc", (None,), {}) in calls
    assert calls[-1][0] == "save_clone"


def test_deferred_idat_crc_route_key_ignores_error_counter():
    tools = wrong_crc_tools(chunk=b"IDAT", offset=182, start=12, end=20)

    first = fixit_felix_runtime.deferred_idat_crc_route_key(
        "Checksum_Error_0:Wrong Crc b'IDAT'",
        tools,
    )
    second = fixit_felix_runtime.deferred_idat_crc_route_key(
        "Checksum_Error_1:Wrong Crc b'IDAT'",
        tools,
    )
    other_offset = fixit_felix_runtime.deferred_idat_crc_route_key(
        "Checksum_Error_1:Wrong Crc b'IDAT'",
        wrong_crc_tools(chunk=b"IDAT", offset=184, start=12, end=20),
    )

    assert first == second
    assert first != other_offset


def test_deferred_idat_crc_route_records_structural_state():
    namespace = {}
    tools = wrong_crc_tools(chunk=b"IDAT", offset=182, start=12, end=20)
    key = fixit_felix_runtime.deferred_idat_crc_route_key(
        "Checksum_Error_0:Wrong Crc b'IDAT'",
        tools,
    )

    fixit_felix_runtime.remember_deferred_idat_crc_route(
        namespace,
        "Checksum_Error_0:Wrong Crc b'IDAT'",
        tools,
    )

    assert namespace["REPAIR_ROUTE_STATES"][key] == "deferred"
    assert fixit_felix_runtime.is_deferred_idat_crc_route(
        namespace,
        "Checksum_Error_1:Wrong Crc b'IDAT'",
        tools,
    ) is True
    assert namespace["REPAIR_ROUTE_STATES"][key] == "skipped_duplicate"


def test_apply_wrong_crc_skips_question_for_deferred_idat_route():
    calls = []
    chkd = "IDAT_Tool_"
    tools = wrong_crc_tools(chunk=b"IDAT", offset=182, start=12, end=20)
    routes = {
        fixit_felix_runtime.deferred_idat_crc_route_key(
            "Checksum_Error_0:Wrong Crc b'IDAT'",
            tools,
        )
    }
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={"Checksum_Error_1:Wrong Crc b'IDAT'": {chkd + "0": "fixed-crc-data"}},
        deferred_routes=routes,
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", "Checksum_Error_1:Wrong Crc b'IDAT'", 0),
        chkd,
        tools,
    )

    assert result == (False, None)
    assert not any(call[0] == "question" for call in calls)
    assert (
        "candy",
        (
            "Cowsay",
            "Oh, I know that one already... I hoped it would have gone away by itself. Anyway, let's keep going.",
            "com",
        ),
        {},
    ) in calls
    assert calls[-3:] == [
        ("chunk_story", ("add", b"IDAT", 33, 109, 13), {}),
        ("set_old_bad_crc", ("old-crc",), {}),
        ("set_skip_bad_crc", (True,), {}),
    ]


def test_apply_wrong_crc_records_failed_idat_crc_route_when_patch_still_breaks():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    tools = wrong_crc_tools(chunk=b"IDAT", offset=182, start=12, end=20)
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
        data_hex="00112233445566778899",
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        tools,
    )

    assert result == (False, None)
    assert not any(call[0] == "question" for call in calls)
    assert ("set_idat_crc_patch_failed", (True,), {}) in calls
    assert ("set_idat_crc_patch_failed_finding", (finding,), {}) in calls
    assert any(call[0] == "remember_deferred_idat_crc_route" for call in calls)
    assert (
        "candy",
        (
            "Cowsay",
            "So i'm not asking you to bless a fake fix. I will keep that CRC for later.",
            "com",
        ),
        {},
    ) in calls


def test_apply_wrong_crc_defers_crc_only_when_idat_stream_stays_invalid():
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    data_hex, replacement_crc, start, end = bad_deflate_png_crc_patch()
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": replacement_crc}},
        data_hex=data_hex,
        side_notes=side_notes,
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(chunk=b"IDAT", replacement_crc=replacement_crc, start=start, end=end),
    )

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "save_clone"]
    assert not [call for call in calls if call[0] == "question"]
    assert any(note.startswith("-IDAT stream diagnosis: status=bad_zlib_header") for note in side_notes)
    assert any(note.startswith("-Deferred IDAT CRC-only patch: zlib stream still invalid:") for note in side_notes)


def test_apply_wrong_crc_writes_improved_deflate_probe_instead_of_crc_clone():
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
        data_hex=one_byte_corrupt_deflate_png_hex(),
        side_notes=side_notes,
        minibar=lambda *args: calls.append(("minibar", args, {})),
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(chunk=b"IDAT", replacement_crc="00000000", start=12, end=20),
    )

    assert result == (True, "written")
    assert not [call for call in calls if call[0] == "save_clone"]
    assert not [call for call in calls if call[0] == "question"]
    assert ("candy", ("Title", "probe_idat_deflate_local_candidates"), {}) in calls
    assert ("candy", ("Title", "probe_deflate_header_candidates"), {}) in calls
    assert any(call[0] == "minibar" and "IDAT deflate-header" in call[1][0] for call in calls)
    assert [call for call in calls if call[0] == "write_clone"]
    assert "-Repair hypothesis tried: targeted IDAT deflate header probe." in calls[-1][1][1]
    assert any(note.startswith("-IDAT local deflate diagnostic:") for note in side_notes)
    assert any(note.startswith("-IDAT deflate probe: strategy=deflate-local") for note in side_notes)
    assert any(note.startswith("-IDAT deflate candidate:") for note in side_notes)


def test_hermesprobe_writes_dynamic_huffman_semantic_candidate():
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data_hex,
    )
    analysis = idat.analyze_idat_stream(bytes.fromhex(data_hex))

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result == (True, "written")
    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert write_calls
    repaired = write_calls[-1][1][0]
    assert idat.analyze_idat_stream(repaired).complete is True
    assert any("strategy=dynamic-huffman-semantic" in note for note in side_notes)
    assert any(note.startswith("-IDAT deflate candidate:") and "rewrite Huffman" in note for note in side_notes)


def test_hermesprobe_writes_dynamic_huffman_crc_guided_candidate():
    calls = []
    side_notes = []
    data_hex = crc_guided_deflate_png_hex()
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data_hex,
    )
    analysis = idat.analyze_idat_stream(bytes.fromhex(data_hex))

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result == (True, "written")
    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert write_calls
    repaired = write_calls[-1][1][0]
    repaired_analysis = idat.analyze_idat_stream(repaired)
    assert repaired_analysis.complete is True
    repaired_chunks = [chunk for chunk in iter_chunks(repaired) if chunk.chunk_type == b"IDAT"]
    assert len(repaired_chunks) == 2
    assert all(chunk.crc == chunk.computed_crc for chunk in repaired_chunks)
    assert any("strategy=dynamic-huffman-crc-guided" in note for note in side_notes)
    assert any(note.startswith("-IDAT deflate candidate:") and "CRC-guided" in note for note in side_notes)


def test_hermesprobe_logs_dynamic_huffman_semantic_diagnostic_without_clone(monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    original_probe = fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates
    original_lf = fixit_felix_runtime._probe_idat_lf_route_for_diagnostics
    original_deep = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam
    mock_frontier_routes_empty(monkeypatch)

    def no_candidate_probe(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        semantic_probe = fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            1,
            7,
            False,
            "dynamic-huffman-semantic",
            "semantic_headers=1; valid_headers=1; best_scanlines=0",
        )
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            0,
            7,
            False,
            "deflate-header",
            "mocked",
            subprobes=(semantic_probe,),
        )

    def no_deep_candidate(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        operation = fixit_felix_runtime.idat_bruteforce.IdatDeepBeamOperation(
            "crc-guided-diagnostic",
            0,
            b"\x00",
            b"\x00",
            (1,),
        )
        diagnostic = fixit_felix_runtime.idat_bruteforce.IdatDeepBeamCandidate(
            data=data,
            stream=b"",
            operations=(operation,),
            before=before,
            after=before,
            state_id=1,
            parent_id=0,
            source_offsets=(0,),
            score=(1, 0, 0),
        )
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (diagnostic,),
            0,
            1,
            3,
            False,
            1,
            1,
            1,
            workers=1,
            reason="mocked",
        )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = no_candidate_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = lambda *_args, **_kwargs: False
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = no_deep_candidate
        runtime = wrong_crc_runtime(
            calls,
            answers=(),
            side_notes=side_notes,
            data_hex=data_hex,
        )
        analysis = idat.analyze_idat_stream(bytes.fromhex(data_hex))

        result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = original_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = original_lf
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = original_deep

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any("strategy=dynamic-huffman-semantic" in note for note in side_notes)
    assert any(note.startswith("-IDAT deflate deep beam:") for note in side_notes)
    assert any("crc-guided-diagnostic" in note for note in side_notes)
    assert "-IDAT deflate header probe found no clone-worthy scanline progress." in side_notes
    assert "-IDAT deep beam found no clone-worthy scanline progress." in side_notes
    assert ("set_idat_deflate_route_consumed", (True,), {}) in calls


def test_hermesprobe_runs_post_deep_routes_before_consuming_live_seed(monkeypatch):
    calls = []
    side_notes = []
    data = bytes.fromhex(semantic_token_corrupt_deflate_png_hex())
    before = idat.analyze_idat_stream(data)
    seed = idat_deep_beam_seed(data, state_id=41, kind="deep-checkpoint-seed")
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data.hex(),
    )

    def no_deep_best(probe_data, **_kwargs):
        assert probe_data == data
        return idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (seed,),
            0,
            1,
            25,
            False,
            19,
            2,
            2,
            workers=1,
            reason="stop=hard depth limit reached",
        )

    def post_deep_backref(_runtime, _data, _analysis, *, seed_candidates=(), path_label="kraft_backref", seed_checkpoint_path=None):
        calls.append(("post_deep_backref", path_label, seed_candidates, seed_checkpoint_path))
        assert path_label in {"kraft_backref_deep", "kraft_backref_deep2"}
        assert seed_checkpoint_path == ""
        assert seed_candidates == (seed,)
        if path_label == "kraft_backref_deep2":
            return idat_bruteforce.IdatKraftBackrefRepairResult(
                before,
                None,
                (seed,),
                1,
                False,
                reason="mocked",
            )
        return idat_bruteforce.IdatKraftBackrefRepairResult(
            before,
            seed,
            (seed,),
            1,
            False,
            reason="mocked",
        )

    monkeypatch.setattr(idat_bruteforce, "probe_idat_deflate_deep_beam", no_deep_best)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_kraft_backref_runtime", post_deep_backref)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_stored_block_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_seed_local_continuation_runtime", lambda *_args, **_kwargs: (None, ()))

    result = fixit_felix_runtime._run_idat_deep_beam_runtime(
        runtime,
        data,
        before,
        checkpoint_path="",
        progress_path="",
    )

    assert result == (False, None)
    assert [call for call in calls if call[0] == "post_deep_backref"]
    assert not [call for call in calls if call[0] == "write_clone"]
    assert not [call for call in calls if call[0] == "set_idat_deflate_route_consumed"]
    assert any(note.startswith("-IDAT post-deep frontier seeded with 1") for note in side_notes)
    assert any("not promoted as clone" in note for note in side_notes)


def test_hermesprobe_hard_depth_with_live_seed_keeps_idat_route_open(monkeypatch):
    calls = []
    side_notes = []
    data = bytes.fromhex(semantic_token_corrupt_deflate_png_hex())
    before = idat.analyze_idat_stream(data)
    seed = idat_deep_beam_seed(data, state_id=42, kind="deep-checkpoint-seed")
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data.hex(),
    )

    def no_deep_best(probe_data, **_kwargs):
        assert probe_data == data
        return idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (seed,),
            0,
            1,
            25,
            False,
            19,
            2,
            2,
            workers=1,
            reason="stop=hard depth limit reached",
        )

    monkeypatch.setattr(idat_bruteforce, "probe_idat_deflate_deep_beam", no_deep_best)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_kraft_backref_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_stored_block_runtime", lambda *_args, **_kwargs: None)

    result = fixit_felix_runtime._run_idat_deep_beam_runtime(
        runtime,
        data,
        before,
        checkpoint_path="",
        progress_path="",
    )

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "set_idat_deflate_route_consumed"]
    assert (
        "-IDAT deep beam stopped with checkpointed candidates still available; route left open for resume/post-deep passes."
        in side_notes
    )


def test_hermesprobe_interrupted_deep_beam_stops_instead_of_relaunching(monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    original_probe = fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates
    original_lf = fixit_felix_runtime._probe_idat_lf_route_for_diagnostics
    original_deep = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam

    def no_candidate_probe(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            1,
            7,
            False,
            "deflate-header",
            "mocked",
        )

    def interrupted_deep_probe(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (),
            0,
            1,
            3,
            False,
            1,
            1,
            1,
            workers=1,
            progress_path="/tmp/deep.progress.json",
            reason="mocked",
            interrupted=True,
        )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = no_candidate_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = lambda *_args, **_kwargs: False
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = interrupted_deep_probe
        mock_frontier_routes_empty(monkeypatch)
        runtime = wrong_crc_runtime(
            calls,
            answers=(),
            side_notes=side_notes,
            data_hex=data_hex,
        )
        analysis = idat.analyze_idat_stream(bytes.fromhex(data_hex))

        try:
            fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)
        except SystemExit as exc:
            exit_code = exc.code
        else:
            exit_code = None
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = original_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = original_lf
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = original_deep

    assert exit_code == 130
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any(note.startswith("-IDAT deflate deep beam:") and "interrupted" in note for note in side_notes)
    assert "-IDAT deep beam interrupted by user; checkpoint/progress saved, stopping repair pass." in side_notes
    assert "-IDAT deep beam found no clone-worthy scanline progress." not in side_notes


def _write_matching_deep_beam_progress(
    path,
    data: bytes,
    *,
    source_hash: str | None = None,
    tested_candidates: int = 1234,
    depth: int = 2,
    max_depth: int = 5,
    hard_depth_limit: int = 6,
    budget: int = 5000,
    interrupted: bool = True,
):
    if source_hash is None:
        _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
        source_hash = idat_bruteforce._stream_state_key(stream)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(
            {
                "version": 2,
                "source_hash": source_hash,
                "tested_candidates": tested_candidates,
                "depth": depth,
                "max_depth": max_depth,
                "hard_depth_limit": hard_depth_limit,
                "budget": budget,
                "interrupted": interrupted,
                "gpu_shard_size": idat_bruteforce.DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE,
                "gpu_done_shards": [],
            }
        ),
        encoding="utf-8",
    )


def test_hermesprobe_resume_deep_beam_skips_short_probes(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        deep_beam_budget=4321,
    )
    checkpoint_path, progress_path = fixit_felix_runtime._idat_deep_beam_paths(runtime)
    _write_matching_deep_beam_progress(progress_path, data)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("short pre-deep-beam probe should not run during resume")

    monkeypatch.setattr(fixit_felix_runtime, "try_focused_idat_crc_forge", forbidden)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_local_candidates", forbidden)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_deflate_header_candidates", forbidden)
    monkeypatch.setattr(fixit_felix_runtime, "_probe_idat_lf_route_for_diagnostics", forbidden)
    mock_frontier_routes_empty(monkeypatch)

    def deep_probe(probe_data, **kwargs):
        calls.append(("deep_probe_kwargs", kwargs, {}))
        before = fixit_felix_runtime.idat.analyze_idat_stream(probe_data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (),
            0,
            1,
            3,
            False,
            2,
            1,
            1,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            progress_resumed=True,
            workers=1,
            reason="mocked",
        )

    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_deep_beam", deep_probe)
    analysis = idat.analyze_idat_stream(data)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "remember_idat_deflate_probe"]
    deep_call = next(call for call in calls if call[0] == "deep_probe_kwargs")
    assert deep_call[1]["checkpoint_path"] == checkpoint_path
    assert deep_call[1]["progress_path"] == progress_path
    assert deep_call[1]["budget"] == 4321
    assert "-IDAT deep beam resume-first: existing checkpoint/progress matches this IDAT stream." in side_notes
    assert any(note.startswith("-IDAT deep beam resume: source matched;") for note in side_notes)
    assert "-IDAT deep beam resume did not return to short probes; checkpoint/progress remain the next state." in side_notes


def test_hermesprobe_resume_tries_checkpoint_post_deep_before_relaunching_deep(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        deep_beam_budget=4321,
    )
    _checkpoint_path, progress_path = fixit_felix_runtime._idat_deep_beam_paths(runtime)
    _write_matching_deep_beam_progress(progress_path, data)
    deep_seed = idat_deep_beam_seed(data, state_id=99, kind="checkpoint-deep-seed")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("deep beam should not relaunch before checkpoint post-deep routes")

    def post_deep(probe_runtime, probe_data, probe_analysis, seed_candidates):
        calls.append(("post_deep", probe_runtime, probe_data, probe_analysis, seed_candidates))
        return True, "post-deep-clone"

    mock_frontier_routes_empty(monkeypatch)
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_load_idat_deep_beam_seed_candidates",
        lambda *_args, **_kwargs: (deep_seed,),
    )
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_post_deep_frontier_routes_runtime", post_deep)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_deep_beam", forbidden)
    analysis = idat.analyze_idat_stream(data)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result == (True, "post-deep-clone")
    post_call = next(call for call in calls if call[0] == "post_deep")
    assert post_call[4] == (deep_seed,)
    assert not any(call[0] == "deep_probe_kwargs" for call in calls)


def test_hermesprobe_resume_deep_beam_auto_bumps_max_depth_after_hard_guard(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        deep_beam_budget=10000000,
    )
    _checkpoint_path, progress_path = fixit_felix_runtime._idat_deep_beam_paths(runtime)
    _write_matching_deep_beam_progress(
        progress_path,
        data,
        tested_candidates=2828836,
        depth=19,
        max_depth=5,
        hard_depth_limit=6,
        budget=10000000,
        interrupted=False,
    )
    mock_frontier_routes_empty(monkeypatch)

    def deep_probe(probe_data, **kwargs):
        calls.append(("deep_probe_kwargs", kwargs, {}))
        before = fixit_felix_runtime.idat.analyze_idat_stream(probe_data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (),
            0,
            1,
            3,
            False,
            19,
            1,
            1,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            progress_resumed=True,
            workers=1,
            reason="mocked",
        )

    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_deep_beam", deep_probe)
    analysis = idat.analyze_idat_stream(data)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result == (False, None)
    deep_call = next(call for call in calls if call[0] == "deep_probe_kwargs")
    assert deep_call[1]["max_depth"] == 20
    assert any(
        note == "-IDAT deep beam depth configuration: max_depth=20; auto_bumped_from_resume=yes."
        for note in side_notes
    )


def test_hermesprobe_explicit_deep_beam_max_depth_overrides_auto_bump(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        deep_beam_budget=10000000,
        deep_beam_max_depth=7,
    )
    _checkpoint_path, progress_path = fixit_felix_runtime._idat_deep_beam_paths(runtime)
    _write_matching_deep_beam_progress(
        progress_path,
        data,
        tested_candidates=2828836,
        depth=19,
        max_depth=5,
        hard_depth_limit=6,
        budget=10000000,
        interrupted=False,
    )
    mock_frontier_routes_empty(monkeypatch)

    def deep_probe(probe_data, **kwargs):
        calls.append(("deep_probe_kwargs", kwargs, {}))
        before = fixit_felix_runtime.idat.analyze_idat_stream(probe_data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (),
            0,
            1,
            3,
            False,
            7,
            1,
            1,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            progress_resumed=True,
            workers=1,
            reason="mocked",
        )

    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_deep_beam", deep_probe)
    analysis = idat.analyze_idat_stream(data)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result == (False, None)
    deep_call = next(call for call in calls if call[0] == "deep_probe_kwargs")
    assert deep_call[1]["max_depth"] == 7
    assert any(
        note == "-IDAT deep beam depth configuration: max_depth=7; auto_bumped_from_resume=no."
        for note in side_notes
    )


def test_hermesprobe_resume_deep_beam_seeds_from_periodic_model(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        deep_beam_budget=4321,
    )
    _checkpoint_path, progress_path = fixit_felix_runtime._idat_deep_beam_paths(runtime)
    _write_matching_deep_beam_progress(progress_path, data)
    before = fixit_felix_runtime.idat.analyze_idat_stream(data)
    _chunks, stream = fixit_felix_runtime.idat_bruteforce._all_chunks_and_idat_stream(data)
    seed = fixit_felix_runtime.idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(
            fixit_felix_runtime.idat_bruteforce.IdatDeepBeamOperation(
                "periodic-replace-xor",
                2,
                stream[2:3],
                bytes((stream[2] ^ 1,)),
            ),
        ),
        before=before,
        after=before,
        state_id=77,
        parent_id=0,
        source_offsets=(2,),
        score=(0,),
    )

    def periodic_probe(probe_data, **kwargs):
        return fixit_felix_runtime.idat_bruteforce.IdatPeriodicCorruptionModelResult(
            fixit_felix_runtime.idat.analyze_idat_stream(probe_data),
            None,
            (seed,),
            12,
            True,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            model_path=kwargs["convoy_model_path"],
            reason="mocked",
        )

    def deep_probe(probe_data, **kwargs):
        calls.append(("deep_probe_kwargs", kwargs, {}))
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            fixit_felix_runtime.idat.analyze_idat_stream(probe_data),
            None,
            (),
            0,
            1,
            3,
            False,
            2,
            1,
            1,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            progress_resumed=True,
            workers=1,
            reason="mocked",
        )

    monkeypatch.setattr(
        fixit_felix_runtime.idat_bruteforce,
        "probe_idat_periodic_corruption_model",
        periodic_probe,
    )
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_affine_corruption_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_huffman_kraft_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_first_filter_literal_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_kraft_backref_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_huffman_oracle_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_global_crc_residue_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_crc_periodic_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime, "_run_deflate_resync_salvage_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_deep_beam", deep_probe)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, before)

    assert result == (False, None)
    deep_call = next(call for call in calls if call[0] == "deep_probe_kwargs")
    assert deep_call[1]["seed_candidates"] == (seed,)
    assert any(note.startswith("-IDAT periodic corruption model:") for note in side_notes)
    assert "-IDAT deep beam seeded with 1 frontier candidate(s)." in side_notes


def test_hermesprobe_resume_runs_frontier_routes_before_deep_beam(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        deep_beam_budget=4321,
    )
    _checkpoint_path, progress_path = fixit_felix_runtime._idat_deep_beam_paths(runtime)
    _write_matching_deep_beam_progress(progress_path, data)
    before = fixit_felix_runtime.idat.analyze_idat_stream(data)
    _chunks, stream = fixit_felix_runtime.idat_bruteforce._all_chunks_and_idat_stream(data)

    def seed(kind, state_id):
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamCandidate(
            data=data,
            stream=stream,
            operations=(
                fixit_felix_runtime.idat_bruteforce.IdatDeepBeamOperation(
                    kind,
                    state_id,
                    stream[:1],
                    stream[:1],
                ),
            ),
            before=before,
            after=before,
            state_id=state_id,
            parent_id=0,
            source_offsets=(state_id,),
            score=(state_id,),
        )

    periodic_seed = seed("periodic", 1)
    affine_seed = seed("affine", 2)
    kraft_seed = seed("kraft", 3)
    first_filter_seed = seed("first-filter", 4)
    backref_seed = seed("kraft-backref", 5)
    stored_block_seed = seed("stored-block", 6)
    huffman_seed = seed("huffman", 7)
    oracle_backref_seed = seed("kraft-backref-oracle", 8)
    oracle_stored_block_seed = seed("stored-block-oracle", 9)
    global_crc_seed = seed("global-crc", 10)
    crc_seed = seed("crc-periodic", 11)
    order = []

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_periodic_model_runtime",
        lambda *_args, **_kwargs: order.append("periodic")
        or fixit_felix_runtime.idat_bruteforce.IdatPeriodicCorruptionModelResult(
            before,
            None,
            (periodic_seed,),
            1,
            True,
        ),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_affine_corruption_runtime",
        lambda *_args, **_kwargs: order.append("affine")
        or fixit_felix_runtime.idat_bruteforce.IdatAffineCorruptionModelResult(
            before,
            None,
            (affine_seed,),
            1,
            True,
        ),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_huffman_kraft_runtime",
        lambda *_args, **_kwargs: order.append("kraft")
        or fixit_felix_runtime.idat_bruteforce.IdatHuffmanKraftSolverResult(
            before,
            None,
            (kraft_seed,),
            1,
            True,
        ),
    )

    def first_filter_runtime(_runtime, _data, _analysis, *, seed_candidates=()):
        order.append("first-filter")
        assert seed_candidates == (kraft_seed,)
        return fixit_felix_runtime.idat_bruteforce.IdatFirstFilterLiteralResult(
            before,
            None,
            (first_filter_seed,),
            1,
            True,
        )

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_first_filter_literal_runtime",
        first_filter_runtime,
    )

    def backref_runtime(_runtime, _data, _analysis, *, seed_candidates=(), path_label="kraft_backref", seed_checkpoint_path=None):
        order.append("backref")
        if path_label == "kraft_backref":
            assert seed_candidates == (first_filter_seed,)
            result_seed = backref_seed
        else:
            assert path_label == "kraft_backref_oracle"
            assert seed_checkpoint_path == ""
            assert seed_candidates == (huffman_seed,)
            result_seed = oracle_backref_seed
        return fixit_felix_runtime.idat_bruteforce.IdatKraftBackrefRepairResult(
            before,
            None,
            (result_seed,),
            1,
            True,
        )

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_kraft_backref_runtime",
        backref_runtime,
    )

    def stored_block_runtime(_runtime, _data, _analysis, *, seed_candidates=(), path_label="stored_block", seed_checkpoint_path=None):
        order.append("stored-block")
        if path_label == "stored_block":
            assert seed_candidates == (backref_seed,)
            result_seed = stored_block_seed
        else:
            assert path_label == "stored_block_oracle"
            assert seed_checkpoint_path == ""
            assert seed_candidates == (oracle_backref_seed,)
            result_seed = oracle_stored_block_seed
        return fixit_felix_runtime.idat_bruteforce.IdatStoredBlockLengthRepairResult(
            before,
            None,
            (result_seed,),
            1,
            True,
        )

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_stored_block_runtime",
        stored_block_runtime,
    )

    def huffman_runtime(_runtime, _data, _analysis, *, seed_candidates=()):
        order.append("huffman")
        assert seed_candidates == (
            periodic_seed,
            affine_seed,
            kraft_seed,
            first_filter_seed,
            backref_seed,
            stored_block_seed,
        )
        return fixit_felix_runtime.idat_bruteforce.IdatHuffmanOracleSolverResult(
            before,
            None,
            (huffman_seed,),
            1,
            True,
        )

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_huffman_oracle_runtime",
        huffman_runtime,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_global_crc_residue_runtime",
        lambda *_args, **_kwargs: order.append("global-crc")
        or fixit_felix_runtime.idat_bruteforce.IdatGlobalCrcResidueSolverResult(
            before,
            None,
            (global_crc_seed,),
            1,
            True,
        ),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_crc_periodic_runtime",
        lambda *_args, **_kwargs: order.append("crc")
        or fixit_felix_runtime.idat_bruteforce.IdatCrcPeriodicPayloadSolverResult(
            before,
            None,
            (crc_seed,),
            1,
            True,
        ),
    )
    monkeypatch.setattr(fixit_felix_runtime, "_run_deflate_resync_salvage_runtime", lambda *_args, **_kwargs: None)

    def deep_probe(probe_data, **kwargs):
        order.append("deep")
        calls.append(("deep_probe_kwargs", kwargs, {}))
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            fixit_felix_runtime.idat.analyze_idat_stream(probe_data),
            None,
            (),
            0,
            1,
            3,
            False,
            2,
            1,
            1,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            progress_resumed=True,
            workers=1,
            reason="mocked",
        )

    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_deep_beam", deep_probe)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, before)

    assert result == (False, None)
    assert order == [
        "periodic",
        "affine",
        "kraft",
        "first-filter",
        "backref",
        "stored-block",
        "huffman",
        "backref",
        "stored-block",
        "global-crc",
        "crc",
        "deep",
    ]
    deep_call = next(call for call in calls if call[0] == "deep_probe_kwargs")
    assert deep_call[1]["seed_candidates"] == (
        periodic_seed,
        affine_seed,
        kraft_seed,
        first_filter_seed,
        backref_seed,
        stored_block_seed,
        huffman_seed,
        oracle_backref_seed,
        oracle_stored_block_seed,
        global_crc_seed,
        crc_seed,
    )
    assert "-IDAT deep beam seeded with 11 frontier candidate(s)." in side_notes


def test_hermesprobe_resume_mismatch_runs_short_probes(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    mock_frontier_routes_empty(monkeypatch)
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
    )
    _checkpoint_path, progress_path = fixit_felix_runtime._idat_deep_beam_paths(runtime)
    _write_matching_deep_beam_progress(progress_path, data, source_hash="wrong-source")

    def no_candidate_probe(probe_data, **_kwargs):
        calls.append(("short_probe", (), {}))
        before = fixit_felix_runtime.idat.analyze_idat_stream(probe_data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            1,
            7,
            False,
            "deflate-header",
            "mocked",
        )

    monkeypatch.setattr(fixit_felix_runtime, "try_focused_idat_crc_forge", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_local_candidates", no_candidate_probe)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_deflate_header_candidates", no_candidate_probe)
    monkeypatch.setattr(fixit_felix_runtime, "_probe_idat_lf_route_for_diagnostics", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        fixit_felix_runtime.idat_bruteforce,
        "probe_idat_deflate_deep_beam",
        lambda probe_data, **_kwargs: fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            fixit_felix_runtime.idat.analyze_idat_stream(probe_data),
            None,
            (),
            0,
            1,
            3,
            False,
            1,
            1,
            1,
            workers=1,
            reason="mocked",
        ),
    )
    analysis = idat.analyze_idat_stream(data)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result == (False, None)
    assert [call for call in calls if call[0] == "short_probe"]
    assert any(note.startswith("-IDAT deep beam resume ignored:") for note in side_notes)


def test_runtime_idat_queue_progress_pads_counter_to_budget_width():
    calls = []
    runtime = SimpleNamespace(minibar=lambda text: calls.append(text))
    progress = fixit_felix_runtime._runtime_idat_queue_progress(runtime)

    progress("deep-beam", 208670, 50000000)
    progress("huffman-kraft", 548314, 1000000)
    progress("kraft-backref", 123, 250000)
    progress("phase2-lf-insert", 298, 298)

    assert calls
    assert calls[0].startswith("IDAT deep-beam 00208670/50000000 eta=")
    assert calls[1].startswith("IDAT huffman-kraft 0548314/1000000 eta=")
    assert calls[2].startswith("IDAT kraft-backref 000123/250000 eta=")
    assert calls[3].startswith("IDAT phase2-lf-insert 298/298 eta=")
    assert all(" rate=" in call for call in calls)


def test_hermesprobe_prompts_deep_beam_workers_and_gpu_when_unconfigured(monkeypatch):
    calls = []
    side_notes = []
    prompts = []
    answers = iter(("2", "yes"))
    data_hex = semantic_token_corrupt_deflate_png_hex()
    original_probe = fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates
    original_lf = fixit_felix_runtime._probe_idat_lf_route_for_diagnostics
    original_deep = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam

    def no_candidate_probe(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            1,
            7,
            False,
            "deflate-header",
            "mocked",
        )

    def input_func(prompt):
        calls.append(("input_func", (prompt,), {}))
        prompts.append(prompt)
        return next(answers)

    def deep_probe(data, **kwargs):
        calls.append(("deep_probe_kwargs", kwargs, {}))
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (),
            0,
            1,
            3,
            False,
            1,
            1,
            1,
            workers=2,
            gpu_requested=True,
            gpu_backend="opengl-active",
            reason="mocked",
        )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = no_candidate_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = lambda *_args, **_kwargs: False
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = deep_probe
        mock_frontier_routes_empty(monkeypatch)
        runtime = wrong_crc_runtime(
            calls,
            answers=(),
            side_notes=side_notes,
            data_hex=data_hex,
            interactive=True,
            input_func=input_func,
        )
        analysis = idat.analyze_idat_stream(bytes.fromhex(data_hex))

        result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = original_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = original_lf
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = original_deep

    assert result == (False, None)
    assert prompts == [
        "Deep beam worker profile [auto] > ",
        "Enable OpenGL GPU prefilter for deep beam? [no] > ",
    ]
    launch_index = next(
        index
        for index, call in enumerate(calls)
        if call[0] == "candy"
        and call[1][0] == "Cowsay"
        and call[1][1]
        == "I am launching the aggressive deep IDAT beam now. It is checkpointed; CRCs remain evidence, not a final proof."
    )
    prompt_index = next(index for index, call in enumerate(calls) if call[0] == "input_func")
    assert launch_index < prompt_index
    deep_call = next(call for call in calls if call[0] == "deep_probe_kwargs")
    assert deep_call[1]["workers"] == 2
    assert deep_call[1]["gpu"] is True
    assert deep_call[1]["gpu_config"] == fixit_felix_runtime.gpu_runtime.GpuRuntimeConfig(enabled=True, backend="opengl")
    assert deep_call[1]["budget"] == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_BUDGET
    assert deep_call[1]["gpu_shard_size"] == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE
    assert deep_call[1]["cpu_batch_size"] == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE
    assert any(
        note.startswith("-IDAT deep beam configuration: workers=2; gpu_requested=yes; gpu_backend=opengl;")
        for note in side_notes
    )
    assert "-IDAT deep beam GPU prefilter enabled; CPU workers remain the validation path." in side_notes


def test_hermesprobe_deep_beam_options_prompt_gpu_when_disabled_config_default():
    calls = []
    prompts = []
    answers = iter(("yes",))
    side_notes = []

    def candy(*args, **kwargs):
        calls.append(("candy", args, kwargs))

    def input_func(prompt):
        prompts.append(prompt)
        return next(answers)

    runtime = SimpleNamespace(
        interactive=True,
        input_func=input_func,
        candy=candy,
        side_notes=side_notes,
        deep_beam_workers=1,
        deep_beam_gpu=None,
        deep_beam_gpu_config=fixit_felix_runtime.gpu_runtime.GpuRuntimeConfig(enabled=False),
    )

    workers, gpu_requested, gpu_config, budget, gpu_shard_size, cpu_batch_size = fixit_felix_runtime._runtime_deep_beam_options(runtime)

    assert workers == 1
    assert gpu_requested is True
    assert gpu_config == fixit_felix_runtime.gpu_runtime.GpuRuntimeConfig(enabled=True, backend="opengl")
    assert budget == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_BUDGET
    assert gpu_shard_size == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE
    assert cpu_batch_size == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE
    assert prompts == ["Enable OpenGL GPU prefilter for deep beam? [no] > "]
    assert any(
        note.startswith("-IDAT deep beam configuration: workers=1; gpu_requested=yes; gpu_backend=opengl;")
        for note in side_notes
    )


def test_hermesprobe_deep_beam_gpu_argument_overrides_enabled_global_config():
    side_notes = []
    runtime = SimpleNamespace(
        interactive=True,
        input_func=lambda prompt: (_ for _ in ()).throw(AssertionError("unexpected prompt: %s" % prompt)),
        candy=lambda *args, **kwargs: None,
        side_notes=side_notes,
        deep_beam_workers=1,
        deep_beam_gpu=False,
        deep_beam_gpu_config=fixit_felix_runtime.gpu_runtime.GpuRuntimeConfig(enabled=True, backend="opengl"),
    )

    workers, gpu_requested, gpu_config, budget, gpu_shard_size, cpu_batch_size = fixit_felix_runtime._runtime_deep_beam_options(runtime)

    assert workers == 1
    assert gpu_requested is False
    assert gpu_config.enabled is False
    assert budget == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_BUDGET
    assert gpu_shard_size == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE
    assert cpu_batch_size == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE
    assert any(
        note.startswith("-IDAT deep beam configuration: workers=1; gpu_requested=no; gpu_backend=none;")
        for note in side_notes
    )


def test_hermesprobe_deep_beam_advanced_sizes_are_runtime_options_not_prompts():
    prompts = []
    side_notes = []
    runtime = SimpleNamespace(
        interactive=True,
        input_func=lambda prompt: prompts.append(prompt) or "yes",
        candy=lambda *args, **kwargs: None,
        side_notes=side_notes,
        deep_beam_workers=1,
        deep_beam_gpu=False,
        deep_beam_gpu_config=None,
        deep_beam_budget="12345",
        deep_beam_gpu_shard_size="4096",
        deep_beam_cpu_batch_size="64",
    )

    workers, gpu_requested, gpu_config, budget, gpu_shard_size, cpu_batch_size = fixit_felix_runtime._runtime_deep_beam_options(runtime)

    assert workers == 1
    assert gpu_requested is False
    assert gpu_config.enabled is False
    assert budget == 12345
    assert gpu_shard_size == 4096
    assert cpu_batch_size == 64
    assert prompts == []
    assert any("budget=12345; gpu_shard_size=4096; cpu_batch_size=64" in note for note in side_notes)


def test_hermesprobe_deep_beam_invalid_budget_falls_back_to_default():
    side_notes = []
    runtime = SimpleNamespace(
        interactive=False,
        input_func=None,
        candy=lambda *args, **kwargs: None,
        side_notes=side_notes,
        deep_beam_workers=1,
        deep_beam_gpu=False,
        deep_beam_gpu_config=None,
        deep_beam_budget="not-a-number",
        deep_beam_gpu_shard_size=None,
        deep_beam_cpu_batch_size=None,
    )

    _workers, _gpu_requested, _gpu_config, budget, _gpu_shard_size, _cpu_batch_size = fixit_felix_runtime._runtime_deep_beam_options(runtime)

    assert budget == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_BUDGET
    assert any("budget=%s" % fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_BUDGET in note for note in side_notes)


def test_hermesprobe_uses_explicit_deep_beam_workers_and_gpu_config_without_prompts(monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    original_probe = fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates
    original_lf = fixit_felix_runtime._probe_idat_lf_route_for_diagnostics
    original_deep = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam
    gpu_config = fixit_felix_runtime.gpu_runtime.GpuRuntimeConfig(
        enabled=True,
        backend="opengl",
        install_missing=False,
    )

    def no_candidate_probe(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            1,
            7,
            False,
            "deflate-header",
            "mocked",
        )

    def input_func(prompt):
        raise AssertionError("unexpected prompt: %s" % prompt)

    def deep_probe(data, **kwargs):
        calls.append(("deep_probe_kwargs", kwargs, {}))
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (),
            0,
            1,
            3,
            False,
            1,
            1,
            1,
            workers=3,
            gpu_requested=True,
            gpu_backend="opengl-active",
            reason="mocked",
        )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = no_candidate_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = lambda *_args, **_kwargs: False
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = deep_probe
        mock_frontier_routes_empty(monkeypatch)
        runtime = wrong_crc_runtime(
            calls,
            answers=(),
            side_notes=side_notes,
            data_hex=data_hex,
            interactive=True,
            input_func=input_func,
            deep_beam_workers=3,
            deep_beam_gpu_config=gpu_config,
            deep_beam_budget=9876,
        )
        analysis = idat.analyze_idat_stream(bytes.fromhex(data_hex))

        result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = original_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = original_lf
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = original_deep

    assert result == (False, None)
    deep_call = next(call for call in calls if call[0] == "deep_probe_kwargs")
    assert deep_call[1]["workers"] == 3
    assert deep_call[1]["gpu"] is True
    assert deep_call[1]["gpu_config"] == gpu_config
    assert deep_call[1]["budget"] == 9876
    assert deep_call[1]["gpu_shard_size"] == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE
    assert deep_call[1]["cpu_batch_size"] == fixit_felix_runtime.idat_bruteforce.DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE
    assert any(
        note.startswith("-IDAT deep beam configuration: workers=3; gpu_requested=yes; gpu_backend=opengl;")
        for note in side_notes
    )


def test_hermesprobe_huffman_kraft_uses_configured_workers(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    gpu_config = fixit_felix_runtime.gpu_runtime.GpuRuntimeConfig(enabled=True, backend="opengl")

    def kraft_probe(probe_data, **kwargs):
        calls.append(("kraft_probe_kwargs", kwargs, {}))
        before = fixit_felix_runtime.idat.analyze_idat_stream(probe_data)
        return fixit_felix_runtime.idat_bruteforce.IdatHuffmanKraftSolverResult(
            before,
            None,
            (),
            0,
            False,
            workers=int(kwargs["workers"]),
            gpu_status="opengl-active" if kwargs["gpu"] else "off",
            reason="mocked",
        )

    monkeypatch.setattr(fixit_felix_runtime, "_block_deep_beam_if_chunk_names_are_stale", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_huffman_kraft_solver", kraft_probe)
    runtime = wrong_crc_runtime(
        calls,
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        deep_beam_workers="2",
        huffman_kraft_workers="6",
        huffman_kraft_gpu_config=gpu_config,
    )
    data = bytes.fromhex(data_hex)
    analysis = idat.analyze_idat_stream(data)

    result = fixit_felix_runtime._run_idat_huffman_kraft_runtime(runtime, data, analysis)

    assert result is not None
    kraft_call = next(call for call in calls if call[0] == "kraft_probe_kwargs")
    assert kraft_call[1]["workers"] == "6"
    assert kraft_call[1]["gpu"] is True
    assert kraft_call[1]["gpu_config"] == gpu_config
    assert result.workers == 6
    assert any("workers=6" in note and "gpu=opengl-active" in note for note in side_notes)


def test_hermesprobe_huffman_kraft_memory_guard_with_seeds_continues(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    before = fixit_felix_runtime.idat.analyze_idat_stream(data)
    _chunks, stream = fixit_felix_runtime.idat_bruteforce._all_chunks_and_idat_stream(data)
    seed = fixit_felix_runtime.idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(),
        before=before,
        after=before,
        state_id=7,
        parent_id=0,
        source_offsets=(),
        score=(1,),
    )

    def kraft_probe(probe_data, **kwargs):
        calls.append(("kraft_probe_kwargs", kwargs, {}))
        before_analysis = fixit_felix_runtime.idat.analyze_idat_stream(probe_data)
        return fixit_felix_runtime.idat_bruteforce.IdatHuffmanKraftSolverResult(
            before_analysis,
            None,
            (seed,),
            123,
            False,
            workers=4,
            gpu_status="disabled-memory-pressure",
            memory_mode="hard",
            memory_throttle_events=1,
            reason="stop=memory_guard; top=1; memory_mode=hard",
        )

    monkeypatch.setattr(fixit_felix_runtime, "_block_deep_beam_if_chunk_names_are_stale", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_huffman_kraft_solver", kraft_probe)
    runtime = wrong_crc_runtime(
        calls,
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        deep_beam_workers="12",
    )

    result = fixit_felix_runtime._run_idat_huffman_kraft_runtime(runtime, data, before)

    assert result is not None
    assert result.top_candidates == (seed,)
    assert any("throttled before the desktop ran out of memory" in call[1][1] for call in calls if call[0] == "candy")
    assert any("memory=hard" in note for note in side_notes)


def test_hermesprobe_huffman_oracle_consumed_still_returns_seeds(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    before = fixit_felix_runtime.idat.analyze_idat_stream(data)
    _chunks, stream = fixit_felix_runtime.idat_bruteforce._all_chunks_and_idat_stream(data)
    seed = fixit_felix_runtime.idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(),
        before=before,
        after=before,
        state_id=17,
        parent_id=0,
        source_offsets=(),
        score=(1,),
    )

    def progress_state(_data, _progress_path=""):
        return fixit_felix_runtime.idat_bruteforce.IdatFrontierProgressState(
            available=True,
            source_matches=True,
            exhausted=True,
            tested=456,
            budget=fixit_felix_runtime.idat_bruteforce.HUFFMAN_ORACLE_DEFAULT_BUDGET,
            reason="frontier exhausted",
        )

    def oracle_probe(probe_data, **kwargs):
        calls.append(("oracle_probe_kwargs", kwargs, {}))
        before_analysis = fixit_felix_runtime.idat.analyze_idat_stream(probe_data)
        return fixit_felix_runtime.idat_bruteforce.IdatHuffmanOracleSolverResult(
            before_analysis,
            None,
            (seed,),
            456,
            True,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            reason="huffman oracle already exhausted for this source/budget",
        )

    def forbidden_artifacts(*_args, **_kwargs):
        raise AssertionError("consumed huffman-oracle seeds must not rewrite debug artifacts")

    monkeypatch.setattr(fixit_felix_runtime, "_block_deep_beam_if_chunk_names_are_stale", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "huffman_oracle_progress_state", progress_state)
    monkeypatch.setattr(
        fixit_felix_runtime.idat_bruteforce,
        "probe_idat_dynamic_huffman_png_oracle_solver",
        oracle_probe,
    )
    monkeypatch.setattr(fixit_felix_runtime, "_write_idat_deep_beam_debug_artifacts", forbidden_artifacts)
    runtime = wrong_crc_runtime(
        calls,
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
    )

    result = fixit_felix_runtime._run_idat_huffman_oracle_runtime(runtime, data, before)

    assert result is not None
    assert result.top_candidates == (seed,)
    assert any(note.startswith("-IDAT huffman-oracle already consumed") for note in side_notes)
    assert any(note.startswith("-IDAT huffman-oracle: tested=456;") for note in side_notes)
    assert any(call[0] == "oracle_probe_kwargs" for call in calls)
    assert not any(call[0] == "candy" and call[1][0] == "Title" for call in calls)


def test_hermesprobe_consumed_frontier_routes_still_return_checkpoint_seeds(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    data = bytes.fromhex(data_hex)
    before = fixit_felix_runtime.idat.analyze_idat_stream(data)
    seed = idat_deep_beam_seed(data, state_id=21, kind="consumed-frontier-seed")

    def frontier_state(_data, _progress_path=""):
        return fixit_felix_runtime.idat_bruteforce.IdatFrontierProgressState(
            available=True,
            source_matches=True,
            exhausted=True,
            tested=123,
            budget=999999,
            reason="frontier exhausted",
        )

    def periodic_state(_data, _progress_path=""):
        return fixit_felix_runtime.idat_bruteforce.IdatPeriodicProgressState(
            available=True,
            source_matches=True,
            exhausted=True,
            tested=123,
            reason="frontier exhausted",
        )

    def periodic_probe(probe_data, **kwargs):
        calls.append(("periodic_probe", kwargs))
        return fixit_felix_runtime.idat_bruteforce.IdatPeriodicCorruptionModelResult(
            fixit_felix_runtime.idat.analyze_idat_stream(probe_data),
            None,
            (seed,),
            123,
            True,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            reason="periodic model already exhausted for this source",
        )

    def affine_probe(probe_data, **kwargs):
        calls.append(("affine_probe", kwargs))
        return fixit_felix_runtime.idat_bruteforce.IdatAffineCorruptionModelResult(
            fixit_felix_runtime.idat.analyze_idat_stream(probe_data),
            None,
            (seed,),
            123,
            True,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            reason="affine corruption model already exhausted for this source/budget",
        )

    def crc_periodic_probe(probe_data, **kwargs):
        calls.append(("crc_periodic_probe", kwargs))
        return fixit_felix_runtime.idat_bruteforce.IdatCrcPeriodicPayloadSolverResult(
            fixit_felix_runtime.idat.analyze_idat_stream(probe_data),
            None,
            (seed,),
            123,
            True,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            reason="crc-periodic solver already exhausted for this source/budget",
        )

    def global_crc_probe(probe_data, **kwargs):
        calls.append(("global_crc_probe", kwargs))
        return fixit_felix_runtime.idat_bruteforce.IdatGlobalCrcResidueSolverResult(
            fixit_felix_runtime.idat.analyze_idat_stream(probe_data),
            None,
            (seed,),
            123,
            True,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            reason="global CRC residue solver already exhausted for this source/budget",
        )

    def forbidden_artifacts(*_args, **_kwargs):
        raise AssertionError("consumed frontier seeds must not rewrite debug artifacts")

    monkeypatch.setattr(fixit_felix_runtime, "_block_deep_beam_if_chunk_names_are_stale", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(fixit_felix_runtime, "_write_idat_deep_beam_debug_artifacts", forbidden_artifacts)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "periodic_model_progress_state", periodic_state)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "affine_corruption_progress_state", frontier_state)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "crc_periodic_progress_state", frontier_state)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "global_crc_residue_progress_state", frontier_state)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_periodic_corruption_model", periodic_probe)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_affine_corruption_model", affine_probe)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_crc_periodic_payload_solver", crc_periodic_probe)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_global_crc_residue_solver", global_crc_probe)
    runtime = wrong_crc_runtime(
        calls,
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
    )

    results = (
        fixit_felix_runtime._run_idat_periodic_model_runtime(runtime, data, before),
        fixit_felix_runtime._run_idat_affine_corruption_runtime(runtime, data, before),
        fixit_felix_runtime._run_idat_crc_periodic_runtime(runtime, data, before),
        fixit_felix_runtime._run_idat_global_crc_residue_runtime(runtime, data, before),
    )

    assert all(result is not None and result.top_candidates == (seed,) for result in results)
    assert any(note.startswith("-IDAT periodic corruption model already consumed") for note in side_notes)
    assert any(note.startswith("-IDAT affine-corruption already consumed") for note in side_notes)
    assert any(note.startswith("-IDAT crc-periodic already consumed") for note in side_notes)
    assert any(note.startswith("-IDAT global-crc-residue already consumed") for note in side_notes)
    assert {call[0] for call in calls if call[0].endswith("_probe")} == {
        "periodic_probe",
        "affine_probe",
        "crc_periodic_probe",
        "global_crc_probe",
    }
    assert not any(call[0] == "candy" and call[1][0] == "Title" for call in calls)


def test_hermesprobe_affine_corruption_uses_global_workers_and_gpu(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    gpu_config = fixit_felix_runtime.gpu_runtime.GpuRuntimeConfig(enabled=True, backend="opengl")

    def affine_probe(probe_data, **kwargs):
        calls.append(("affine_probe_kwargs", kwargs, {}))
        before = fixit_felix_runtime.idat.analyze_idat_stream(probe_data)
        return fixit_felix_runtime.idat_bruteforce.IdatAffineCorruptionModelResult(
            before,
            None,
            (),
            5,
            False,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            model_path=kwargs["convoy_model_path"],
            workers=int(kwargs["workers"]),
            gpu_status="opengl-active" if kwargs["gpu"] else "off",
            cpu_batches=2,
            reason="mocked",
        )

    monkeypatch.setattr(fixit_felix_runtime, "_block_deep_beam_if_chunk_names_are_stale", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_affine_corruption_model", affine_probe)
    runtime = wrong_crc_runtime(
        calls,
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        deep_beam_workers="9",
        huffman_kraft_gpu_config=gpu_config,
    )
    data = bytes.fromhex(data_hex)
    analysis = idat.analyze_idat_stream(data)

    result = fixit_felix_runtime._run_idat_affine_corruption_runtime(runtime, data, analysis)

    assert result is not None
    affine_call = next(call for call in calls if call[0] == "affine_probe_kwargs")
    assert affine_call[1]["workers"] == "9"
    assert affine_call[1]["gpu"] is True
    assert affine_call[1]["gpu_config"] == gpu_config
    assert any("workers=9" in note and "gpu=opengl-active" in note for note in side_notes)


def test_hermesprobe_kraft_backref_uses_kraft_checkpoint_seed(tmp_path, monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()

    def backref_probe(probe_data, **kwargs):
        calls.append(("backref_probe_kwargs", kwargs, {}))
        before = fixit_felix_runtime.idat.analyze_idat_stream(probe_data)
        return fixit_felix_runtime.idat_bruteforce.IdatKraftBackrefRepairResult(
            before,
            None,
            (),
            3,
            False,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            seed_checkpoint_path=kwargs["seed_checkpoint_path"],
            repaired_backrefs=1,
            png_prefix_hits=0,
            reason="mocked",
        )

    monkeypatch.setattr(fixit_felix_runtime, "_block_deep_beam_if_chunk_names_are_stale", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_kraft_backref_repair", backref_probe)
    runtime = wrong_crc_runtime(
        calls,
        side_notes=side_notes,
        data_hex=data_hex,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        kraft_backref_budget="77",
    )
    data = bytes.fromhex(data_hex)
    analysis = idat.analyze_idat_stream(data)

    result = fixit_felix_runtime._run_idat_kraft_backref_runtime(runtime, data, analysis)

    assert result is not None
    backref_call = next(call for call in calls if call[0] == "backref_probe_kwargs")
    kraft_checkpoint_path, _kraft_progress_path = fixit_felix_runtime._idat_huffman_kraft_paths(runtime)
    assert backref_call[1]["budget"] == 77
    assert backref_call[1]["seed_checkpoint_path"] == kraft_checkpoint_path
    assert any(note.startswith("-IDAT kraft-backref: tested=3;") for note in side_notes)


def test_hermesprobe_writes_deep_beam_candidate_after_short_probes_stall(monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    original_probe = fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates
    original_lf = fixit_felix_runtime._probe_idat_lf_route_for_diagnostics
    original_deep = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam

    def no_candidate_probe(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            1,
            7,
            False,
            "deflate-header",
            "mocked",
        )

    def deep_candidate_probe(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        repaired = valid_png_bytes()
        _chunks, stream = fixit_felix_runtime.idat_bruteforce._idat_chunks_and_stream(repaired)
        after = fixit_felix_runtime.idat.analyze_idat_stream(repaired)
        candidate = fixit_felix_runtime.idat_bruteforce.IdatDeepBeamCandidate(
            data=repaired,
            stream=stream,
            operations=(
                fixit_felix_runtime.idat_bruteforce.IdatDeepBeamOperation(
                    "replace",
                    2,
                    b"\x00",
                    b"\x01",
                ),
            ),
            before=before,
            after=after,
            state_id=9,
            parent_id=0,
            source_offsets=(2,),
            score=(1, 1, 1, 2, 8, 5, 1, 0, 0, 0, 0, 0, 0, -1, 0),
        )
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            candidate,
            (candidate,),
            0,
            1,
            11,
            False,
            1,
            2,
            2,
            workers=1,
            reason="mocked",
        )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = no_candidate_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = lambda *_args, **_kwargs: False
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = deep_candidate_probe
        mock_frontier_routes_empty(monkeypatch)
        runtime = wrong_crc_runtime(
            calls,
            answers=(),
            side_notes=side_notes,
            data_hex=data_hex,
        )
        analysis = idat.analyze_idat_stream(bytes.fromhex(data_hex))

        result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = original_probe
        fixit_felix_runtime._probe_idat_lf_route_for_diagnostics = original_lf
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = original_deep

    assert result == (True, "written")
    assert ("candy", ("Title", "probe_idat_deflate_deep_beam"), {}) in calls
    assert [call for call in calls if call[0] == "write_clone"]
    assert "-Repair hypothesis tried: aggressive IDAT deflate deep beam." in calls[-1][1][1]
    assert any(note.startswith("-IDAT deep beam candidate:") for note in side_notes)


def test_apply_wrong_crc_uses_focused_idat_crc_forge_before_blackfill():
    sample = ROOT / "png_to_check" / "color_plte2_sample.png"
    if not sample.exists():
        return

    data = sample.read_bytes()
    analysis = fixit_felix_runtime.idat.analyze_idat_stream(data)
    bad_idat = next(
        chunk
        for chunk in iter_chunks(data)
        if chunk.chunk_type == b"IDAT" and chunk.crc != chunk.computed_crc
    )
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": bad_idat.computed_crc.to_bytes(4, "big").hex()}},
        data_hex=data.hex(),
        side_notes=side_notes,
        preview_repair_image=lambda *args: calls.append(("preview", args, {})),
        minibar=lambda *args: calls.append(("minibar", args, {})),
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(
            chunk=b"IDAT",
            replacement_crc=bad_idat.computed_crc.to_bytes(4, "big").hex(),
            start=(bad_idat.offset + 8 + bad_idat.length) * 2,
            end=(bad_idat.offset + 12 + bad_idat.length) * 2,
        ),
    )

    assert analysis.error_file_offset == 0x20F
    assert result == (True, "written")
    cowsay = [call[1][1] for call in calls if call[0] == "candy" and call[1][0] == "Cowsay"]
    assert "HermesProbe localized a deflate error near file offset 0x20f." in cowsay
    assert "Trying focused 4-byte IDAT CRC repair around 0x20c before blackfill." in cowsay
    writes = [call for call in calls if call[0] == "write_clone"]
    previews = [call for call in calls if call[0] == "preview"]
    questions = [call for call in calls if call[0] == "question"]
    assert len(writes) == 1
    assert len(previews) == 1
    assert len(questions) == 1
    assert calls.index(writes[0]) < calls.index(questions[0])
    assert calls.index(writes[0]) < calls.index(previews[0]) < calls.index(questions[0])
    assert questions[0][1] == ()
    assert questions[0][2]["skipauto"] is True
    repaired = writes[0][1][0]
    assert validate_png_structure(repaired).ok
    assert fixit_felix_runtime.idat.analyze_idat_stream(repaired).complete is True
    repaired_plte = next(chunk for chunk in iter_chunks(repaired) if chunk.chunk_type == b"PLTE")
    repaired_indices = fixit_felix_runtime.png.indexed_png_indices(repaired)
    assert repaired_indices is not None
    assert max(repaired_indices) < repaired_plte.length // 3
    assert "-Repair hypothesis tried: focused 4-byte IDAT CRC forge." in writes[0][1][1]
    assert "Follow-up repair: then rebuilt undersized indexed PLTE as grayscale palette." in writes[0][1][1]


def test_apply_wrong_crc_uses_heavy_probe_loadingbar_after_quick_probe_fails():
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    original_quick = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue
    original_heavy = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates

    def loadingbar(*args):
        calls.append(("loadingbar", args, {}))

    def quick_no_candidate(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            "strategy-queue",
        )

    def heavy_candidate(data, *, progress=None):
        return original_heavy(
            data,
            backtrack=8,
            forward=8,
            budget=5000,
            progress=progress,
        )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = quick_no_candidate
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates = heavy_candidate
        runtime = wrong_crc_runtime(
            calls,
            answers=(True,),
            pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
            data_hex=bad_adler_png_hex(),
            side_notes=side_notes,
            loadingbar=loadingbar,
        )

        result = fixit_felix_runtime.apply_wrong_crc(
            runtime,
            fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
            chkd,
            wrong_crc_tools(chunk=b"IDAT", replacement_crc="00000000", start=12, end=20),
        )
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = original_quick
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates = original_heavy

    assert result == (True, "written")
    assert any(call[0] == "question" for call in calls)
    assert ("candy", ("Title", "probe_idat_deflate_strategy_queue"), {}) in calls
    assert ("candy", ("Title", "probe_idat_deflate_heavy_candidates"), {}) in calls
    assert any(call == ("loadingbar", (5000, 4, 0, True), {}) for call in calls)
    assert any(call[0] == "write_clone" for call in calls)
    assert any(note.startswith("-IDAT deflate probe: strategy=heavy-byte") for note in side_notes)


def test_try_idat_deflate_uses_longer_strategy_queue_after_usable_scanline(monkeypatch):
    calls = []
    side_notes = []
    data_hex = semantic_token_corrupt_deflate_png_hex()
    analysis = fixit_felix_runtime.idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        decompressed_size=4925,
        usable_scanlines=1,
        error_offset=1011,
    )

    def strategy_probe(data, **kwargs):
        calls.append(("strategy_probe", kwargs))
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            analysis,
            None,
            0,
            0,
            0,
            False,
            "strategy-queue",
        )

    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_prefix_frontier_routes_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_strategy_queue", strategy_probe)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_heavy_candidates", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("heavy probe should be declined before launch")))
    runtime = wrong_crc_runtime(
        calls,
        answers=(False,),
        side_notes=side_notes,
        data_hex=data_hex,
    )

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result is None
    strategy_call = next(call for call in calls if call[0] == "strategy_probe")
    assert strategy_call[1]["max_steps"] == 16


def test_apply_wrong_crc_declines_heavy_probe_without_loadingbar_or_clone():
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    original_quick = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue
    original_heavy = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates

    def quick_no_candidate(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            "strategy-queue",
        )

    def fail_heavy(*args, **kwargs):
        raise AssertionError("heavy probe should not run when user declines")

    try:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = quick_no_candidate
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates = fail_heavy
        runtime = wrong_crc_runtime(
            calls,
            answers=(False,),
            pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
            data_hex=bad_adler_png_hex(),
            side_notes=side_notes,
            loadingbar=lambda *args: calls.append(("loadingbar", args, {})),
        )

        result = fixit_felix_runtime.apply_wrong_crc(
            runtime,
            fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
            chkd,
            wrong_crc_tools(chunk=b"IDAT", replacement_crc="00000000", start=12, end=20),
        )
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = original_quick
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates = original_heavy

    assert result == (False, None)
    assert any(call[0] == "question" for call in calls)
    assert ("candy", ("Title", "probe_idat_deflate_strategy_queue"), {}) in calls
    assert ("candy", ("Title", "probe_idat_deflate_heavy_candidates"), {}) not in calls
    assert not any(call[0] == "loadingbar" for call in calls)
    assert not any(call[0] == "write_clone" for call in calls)
    assert "-IDAT heavy probe declined by user." in side_notes
    assert "-IDAT deflate heavy probe skipped: user declined." in side_notes


def test_apply_wrong_crc_other_errors_defers_to_chunk_story():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_other_errors_first", finding, 2),
        chkd,
        wrong_crc_tools(),
    )

    assert result == (False, None)
    assert calls[-3:] == [
        ("chunk_story", ("add", b"IDAT", 33, 109, 13), {}),
        ("set_old_bad_crc", ("old-crc",), {}),
        ("set_skip_bad_crc", (True,), {}),
    ]


def test_apply_wrong_crc_other_errors_defers_invalid_idat_crc_only_without_question():
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(),
        pandora_box={
            finding: {chkd + "0": "fixed-crc-data"},
            "CheckLength_Error_0:-No NextChunk": {},
        },
        data_hex="00112233445566778899",
        side_notes=side_notes,
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_other_errors_first", finding, 1),
        chkd,
        wrong_crc_tools(),
    )

    assert result == (False, None)
    assert not any(call[0] == "question" for call in calls)
    assert ("set_idat_crc_patch_failed", (True,), {}) in calls
    assert ("set_idat_crc_patch_failed_finding", (finding,), {}) in calls
    assert any(call[0] == "remember_deferred_idat_crc_route" for call in calls)
    assert any(note.startswith("-Deferred IDAT CRC-only patch: zlib stream still invalid:") for note in side_notes)
    assert calls[-3:] == [
        ("chunk_story", ("add", b"IDAT", 33, 109, 13), {}),
        ("set_old_bad_crc", ("old-crc",), {}),
        ("set_skip_bad_crc", (True,), {}),
    ]


def test_apply_wrong_crc_other_errors_saves_clean_idat_crc_only_patch():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    fixture = (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "xcsn0g01.png").read_bytes()
    idat_chunk = next(chunk for chunk in iter_chunks(fixture) if chunk.chunk_type == b"IDAT")
    crc_start = (idat_chunk.offset + 8 + idat_chunk.length) * 2
    crc_end = crc_start + 8
    replacement_crc = idat_chunk.computed_crc.to_bytes(4, "big").hex()
    old_crc = idat_chunk.crc.to_bytes(4, "big").hex()
    runtime = wrong_crc_runtime(
        calls,
        pandora_box={
            finding: {chkd + "0": replacement_crc},
            "CheckLength_Error_0:-No NextChunk": {},
        },
        data_hex=fixture.hex(),
    )
    tools = wrong_crc_tools(
        chunk=b"IDAT",
        offset=hex(idat_chunk.offset + 8 + idat_chunk.length),
        start=crc_start,
        end=crc_end,
        replacement_crc=replacement_crc,
    )
    tools.old_crc = old_crc

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_other_errors_first", finding, 1),
        chkd,
        tools,
    )

    assert result == (True, "saved")
    assert not [call for call in calls if call[0] == "question"]
    save_calls = [call for call in calls if call[0] == "save_clone"]
    assert save_calls == [
        (
            "save_clone",
            (
                replacement_crc,
                crc_start,
                crc_end,
                "-Found Chunk[b'IDAT'] has Wrong Crc at offset: %s\n"
                "-Replaced with: %s old value was: %s"
                % (hex(idat_chunk.offset + 8 + idat_chunk.length), replacement_crc, old_crc),
            ),
            {},
        )
    ]


def test_apply_wrong_crc_already_in_cornucopia_uses_debug_emit_without_tools():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    runtime = wrong_crc_runtime(calls, debug=True, pause_debug=True)

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("already_in_cornucopia", finding, 0),
        "IDAT_Tool_",
        None,
    )

    assert result == (False, None)
    assert calls == [
        ("emit", ("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding,), {}),
        ("emit", ("-Cornucopia is True",), {}),
    ]


def test_apply_wrong_crc_rejects_missing_tools_for_action():
    runtime = wrong_crc_runtime([])

    try:
        fixit_felix_runtime.apply_wrong_crc(
            runtime,
            fixit_felix.WrongCrcDecision("ask_easy_crc_fix", "finding", 0),
            "IDAT_Tool_",
            None,
        )
    except ValueError as exc:
        assert str(exc) == "FixItFelix wrong-CRC action needs CRC tools: ask_easy_crc_fix"
    else:
        raise AssertionError("Expected ValueError for missing wrong-CRC tools")


def test_apply_wrong_crc_rejects_unknown_action():
    runtime = wrong_crc_runtime([])

    try:
        fixit_felix_runtime.apply_wrong_crc(
            runtime,
            SimpleNamespace(action="unknown", finding="finding"),
            "IDAT_Tool_",
            wrong_crc_tools(),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix wrong-CRC action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown wrong-CRC action")


def wrong_chunk_name_tools():
    return SimpleNamespace(
        chunk_type=b"zzzz",
        chunk_length="13",
        chunk_type_offset=128,
        previous_chunk=b"IHDR",
    )


def raw_png_chunk(declared_length, chunk_type, payload):
    return declared_length.to_bytes(4, "big") + chunk_type + payload + b"\x00\x00\x00\x00"


def png_with_wrong_idat_like_name(chunk_type=b"IDA^", payload=b"abcd", *, crc_type=b"IDAT"):
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00",
    )
    first_idat = build_png_chunk(b"IDAT", b"first")
    stored_crc = zlib.crc32(crc_type + payload) & 0xFFFFFFFF
    wrong_chunk = (
        len(payload).to_bytes(4, "big")
        + chunk_type
        + payload
        + stored_crc.to_bytes(4, "big")
    )
    bad_chunk_offset = len(PNG_SIGNATURE) + len(ihdr) + len(first_idat)
    type_index = (bad_chunk_offset + 4) * 2
    data = PNG_SIGNATURE + ihdr + first_idat + wrong_chunk + IEND_CHUNK
    return data, type_index


def idat_chain_candidate_hex():
    data = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", b"\x00" * 13)
        + raw_png_chunk(4, b"IDAT", b"aaaa")
        + raw_png_chunk(4, b"IDAT", b"0000")
        + raw_png_chunk(5, b"@DAT", b"bbbb")
        + raw_png_chunk(4, b"IDAT", b"cccc")
        + IEND_CHUNK
    )
    return data.hex()


def idat_chain_aligned_bad_deflate_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00",
    )
    data = (
        PNG_SIGNATURE
        + ihdr
        + raw_png_chunk(2, b"IDAT", b"\x78\x9c")
        + raw_png_chunk(2, b"IDAT", b"\xff\xff")
        + IEND_CHUNK
    )
    return data.hex()


def idat_chain_repairable_bad_deflate_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00",
    )
    data = (
        PNG_SIGNATURE
        + ihdr
        + raw_png_chunk(2, b"IDAT", b"\x78\x9c")
        + raw_png_chunk(2, b"IDAT", b"\xff\xff")
        + raw_png_chunk(2, b"@DAT", b"\x00\x00")
        + IEND_CHUNK
    )
    return data.hex()


def wrong_chunk_name_before_first_idat_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00",
    )
    data = (
        PNG_SIGNATURE
        + ihdr
        + raw_png_chunk(4, b"zzzz", b"aaaa")
        + raw_png_chunk(4, b"IDAT", b"bbbb")
        + IEND_CHUNK
    )
    return data.hex(), len(PNG_SIGNATURE) + len(ihdr) + 4


def test_wrong_chunk_name_route_key_ignores_error_counter():
    first = fixit_felix_runtime.wrong_chunk_name_route_key(
        "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        wrong_chunk_name_tools(),
        "bruteforce",
    )
    second = fixit_felix_runtime.wrong_chunk_name_route_key(
        "CheckChunkName_Error_1:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        wrong_chunk_name_tools(),
        "bruteforce",
    )
    other = fixit_felix_runtime.wrong_chunk_name_route_key(
        "CheckChunkName_Error_1:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        SimpleNamespace(
            chunk_type=b"IDA^",
            chunk_length="13",
            chunk_type_offset=128,
            previous_chunk=b"IHDR",
        ),
        "bruteforce",
    )

    assert first == second
    assert first != other


def test_wrong_chunk_name_route_records_structural_state():
    namespace = {}
    tools = wrong_chunk_name_tools()
    key = fixit_felix_runtime.wrong_chunk_name_route_key(
        "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        tools,
        "bruteforce",
    )

    fixit_felix_runtime.remember_wrong_chunk_name_route(
        namespace,
        "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        tools,
        "bruteforce",
    )

    assert namespace["REPAIR_ROUTE_STATES"][key] == "tried"
    assert fixit_felix_runtime.is_wrong_chunk_name_route_tried(
        namespace,
        "CheckChunkName_Error_1:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        tools,
        "bruteforce",
    ) is True
    assert namespace["REPAIR_ROUTE_STATES"][key] == "skipped_duplicate"


def test_wrong_chunk_name_before_first_idat_does_not_block_name_repair():
    data_hex, chunk_type_offset = wrong_chunk_name_before_first_idat_hex()
    tools = SimpleNamespace(
        chunk_type=b"zzzz",
        chunk_length="4",
        chunk_type_offset=chunk_type_offset,
        previous_chunk=b"pHYs",
    )

    assert fixit_felix_runtime.wrong_chunk_name_precedes_first_parsed_idat(data_hex, tools) is True


def wrong_chunk_name_runtime(
    calls,
    *,
    answers=(),
    bad_ancillary=False,
    nearby_result="nearby-result",
    pandora_box=None,
    cornucopia=None,
    side_notes=None,
    tried_routes=None,
    data_hex="00112233445566778899",
):
    answer_iter = iter(answers)
    if side_notes is None:
        side_notes = []
    if tried_routes is None:
        tried_routes = set()

    def record(name, result=None):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return callback

    def question(*args, **kwargs):
        calls.append(("question", args, kwargs))
        return next(answer_iter)

    return fixit_felix_runtime.WrongChunkNameRuntime(
        emit=record("emit"),
        candy=record("candy"),
        question=question,
        ancillary=record("ancillary"),
        nearby_chunk=record("nearby_chunk", nearby_result),
        brute_chunk=record("brute_chunk", "brute-result"),
        save_clone=record("save_clone", "saved"),
        write_clone=record("write_clone", "written"),
        set_skip_bad_next_name=record("set_skip_bad_next_name"),
        set_skip_bad_current_name=record("set_skip_bad_current_name"),
        bad_ancillary=lambda: bad_ancillary,
        pandora_box=pandora_box if pandora_box is not None else {},
        cornucopia=cornucopia if cornucopia is not None else {},
        data_hex=data_hex,
        side_notes=side_notes,
        remember_wrong_chunk_name_route=lambda finding, chkd, tools, action: tried_routes.add(
            fixit_felix_runtime.wrong_chunk_name_route_key(finding, chkd, tools, action)
        ),
        is_wrong_chunk_name_route_tried=lambda finding, chkd, tools, action: (
            fixit_felix_runtime.wrong_chunk_name_route_key(finding, chkd, tools, action)
            in tried_routes
        ),
    )


def test_apply_wrong_chunk_name_length_probe_accepts_nearby_chunk():
    calls = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42 and length is not the same than before."
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(True,),
        bad_ancillary=True,
        pandora_box={finding: {chkd + "0": b"zzzz"}},
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_length_probe", finding, True),
        chkd,
        wrong_chunk_name_tools(),
    )

    assert result == (True, "nearby-result")
    assert ("ancillary", (b"zzzz",), {}) in calls
    assert calls[-1] == (
        "nearby_chunk",
        (b"zzzz", "13", 128, False, finding),
        {},
    )


def test_apply_wrong_chunk_name_length_probe_without_repair_skips_bruteforce_question():
    calls = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42 and length is not the same than before."
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(),
        nearby_result=None,
        pandora_box={finding: {chkd + "0": b"zzzz"}},
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_length_probe", finding, True),
        chkd,
        wrong_chunk_name_tools(),
    )

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "question"]
    assert not [call for call in calls if call[0] == "brute_chunk"]
    assert ("nearby_chunk", (b"zzzz", "13", 128, False, finding), {}) in calls
    assert ("set_skip_bad_next_name", (True,), {}) in calls
    assert calls[-1] == ("set_skip_bad_current_name", (True,), {})


def test_apply_wrong_chunk_name_length_probe_deja_vu_skips_bruteforce_question():
    calls = []
    finding = "CheckChunkName_Error_1:has Wrong Chunk name at offset: 42 and length is not the same than before."
    chkd = "zzzz_Tool_"
    tools = wrong_chunk_name_tools()
    tried_routes = {
        fixit_felix_runtime.wrong_chunk_name_route_key(
            "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42 and length is not the same than before.",
            chkd,
            tools,
            "length_probe",
        )
    }
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(),
        nearby_result="nearby-result",
        pandora_box={finding: {chkd + "0": b"zzzz"}},
        tried_routes=tried_routes,
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_length_probe", finding, True),
        chkd,
        tools,
    )

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "emit"]
    assert not [call for call in calls if call[0] == "ancillary"]
    assert not [call for call in calls if call[0] == "candy"]
    assert not [call for call in calls if call[0] == "question"]
    assert not [call for call in calls if call[0] == "nearby_chunk"]
    assert not [call for call in calls if call[0] == "brute_chunk"]
    assert ("set_skip_bad_next_name", (True,), {}) in calls
    assert calls[-1] == ("set_skip_bad_current_name", (True,), {})


def test_apply_wrong_chunk_name_bruteforce_accepts_brute_chunk():
    calls = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    side_notes = []
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
        side_notes=side_notes,
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
        chkd,
        wrong_chunk_name_tools(),
    )

    assert result == (True, "brute-result")
    assert calls[-1] == (
        "brute_chunk",
        (b"zzzz", b"IHDR", "13", finding),
        {},
    )
    assert side_notes == ["-Repair hypothesis tried: chunk-name recovery for zzzz at 0x80."]


def test_apply_wrong_chunk_name_repairs_idat_typo_at_recorded_offset_without_question():
    calls = []
    side_notes = []
    data, type_index = png_with_wrong_idat_like_name(b"IDA^", crc_type=b"IDAT")
    type_offset = type_index // 2
    finding = "CheckChunkName_Error_0:Found Chunk[b'IDA^'] has Wrong Chunk name after Chunk[b'IDAT']"
    chkd = "IDA^_Tool_"
    tools = SimpleNamespace(
        chunk_type=b"IDA^",
        chunk_length="4",
        chunk_type_offset=type_index,
        previous_chunk=b"IDAT",
    )
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(),
        pandora_box={finding: {chkd + "0": b"IDA^"}},
        side_notes=side_notes,
        data_hex=data.hex(),
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
        chkd,
        tools,
    )

    assert result == (True, "written")
    assert not [call for call in calls if call[0] == "question"]
    assert not [call for call in calls if call[0] == "brute_chunk"]
    assert not [call for call in calls if call[0] == "nearby_chunk"]
    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert len(write_calls) == 1
    fixed = write_calls[0][1][0]
    assert fixed[type_offset : type_offset + 4] == b"IDAT"
    assert any("direct chunk-name recovery for IDA^" in note for note in side_notes)
    assert any("stored CRC matches after renaming to IDAT" in note for note in side_notes)


def test_apply_wrong_chunk_name_keeps_idat_typo_repair_when_crc_still_mismatches():
    calls = []
    side_notes = []
    data, type_index = png_with_wrong_idat_like_name(b"@DAT", crc_type=b"JUNK")
    finding = (
        "CheckChunkName_Error_0:Found Chunk[b'@DAT'] has Wrong Chunk name after Chunk[b'IDAT'] "
        "and length is not the same than before."
    )
    chkd = "@DAT_Tool_"
    tools = SimpleNamespace(
        chunk_type=b"@DAT",
        chunk_length="4",
        chunk_type_offset=type_index,
        previous_chunk=b"IDAT",
    )
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(),
        pandora_box={finding: {chkd + "0": b"@DAT"}},
        side_notes=side_notes,
        data_hex=data.hex(),
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_length_probe", finding, True),
        chkd,
        tools,
    )

    assert result == (True, "written")
    assert not [call for call in calls if call[0] == "question"]
    assert not [call for call in calls if call[0] == "nearby_chunk"]
    assert any("direct chunk-name recovery for @DAT" in note for note in side_notes)
    assert any("stored CRC still mismatches" in note for note in side_notes)


def test_apply_wrong_chunk_name_bruteforce_skips_known_route_without_question():
    calls = []
    finding = "CheckChunkName_Error_1:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    tools = wrong_chunk_name_tools()
    side_notes = []
    tried_routes = {
        fixit_felix_runtime.wrong_chunk_name_route_key(
            "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
            chkd,
            tools,
            "bruteforce",
        )
    }
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
        side_notes=side_notes,
        tried_routes=tried_routes,
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
        chkd,
        tools,
    )

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "question"]
    assert ("set_skip_bad_current_name", (True,), {}) in calls
    assert (
        "-Repair hypothesis skipped: chunk-name recovery for zzzz at 0x80; "
        "reason: route was already tried."
    ) in side_notes


def test_apply_wrong_chunk_name_uses_idat_chain_batch_after_bruteforce_decline():
    calls = []
    side_notes = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(False,),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
        side_notes=side_notes,
        data_hex=idat_chain_candidate_hex(),
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
        chkd,
        wrong_chunk_name_tools(),
    )

    assert result == (True, "written")
    assert [call for call in calls if call[0] == "question"]
    assert [call for call in calls if call[0] == "ancillary"]
    assert not [call for call in calls if call[0] == "brute_chunk"]
    assert any(call[0] == "write_clone" for call in calls)
    assert any("chunk-name recovery" in note and "declined" in note for note in side_notes)
    assert any(note.startswith("-IDAT convoy chunk-name gate: current parser") for note in side_notes)
    assert any(note.startswith("-IDAT convoy chunk-name gate: after proposed realignment") for note in side_notes)
    assert "-Repair hypothesis tried: IDAT chain header repair." in side_notes
    assert any("type @DAT -> IDAT" in note for note in side_notes)


def test_idat_chain_chunk_name_gate_blocks_unclean_realign_candidate():
    calls = []
    side_notes = []

    def record(name, result=None):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return callback

    runtime = SimpleNamespace(
        candy=record("candy"),
        side_notes=side_notes,
    )
    original = PNG_SIGNATURE + build_png_chunk(b"IHDR", b"\x00" * 13) + IEND_CHUNK
    fixed = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", b"\x00" * 13)
        + raw_png_chunk(0, b"BA\x00D", b"")
        + IEND_CHUNK
    )

    result = fixit_felix_runtime._confirm_chunk_names_for_idat_chain(runtime, original, fixed)

    assert result is False
    assert any(note.startswith("-IDAT convoy chunk-name gate: blocked") for note in side_notes)
    assert ("candy", ("Cowsay", "I am not launching the IDAT convoy because the realigned candidate still has bad chunk names.", "bad"), {}) in calls


def test_apply_wrong_chunk_name_stops_after_idat_chain_convoy_clone_boundary():
    calls = []
    side_notes = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    source = bytes.fromhex(idat_chain_repairable_bad_deflate_hex())
    fixed = fixit_felix_runtime.idat_chain.analyze_idat_chain_headers(source).fixed_data
    original_probe = fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates
    original_deep = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam

    def forbidden_probe(*_args, **_kwargs):
        raise AssertionError("deflate probing must wait for the next clone pass")

    try:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = forbidden_probe
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = forbidden_probe
        runtime = wrong_chunk_name_runtime(
            calls,
            answers=(False,),
            pandora_box={finding: {chkd + "0": b"zzzz"}},
            side_notes=side_notes,
            data_hex=source.hex(),
        )

        result = fixit_felix_runtime.apply_wrong_chunk_name(
            runtime,
            fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
            chkd,
            wrong_chunk_name_tools(),
        )
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_deflate_header_candidates = original_probe
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = original_deep

    assert result == (True, "written")
    assert ("candy", ("Title", "probe_deflate_header_candidates"), {}) not in calls
    assert ("candy", ("Title", "probe_idat_deflate_deep_beam"), {}) not in calls
    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert write_calls
    assert write_calls[0][1][0] == fixed
    assert "-IDAT convoy clone written after clean chunk-name gate." in side_notes
    assert "-IDAT convoy clone boundary: deep-beam deferred until the next pass from this clone." in side_notes
    assert runtime.data_hex == source.hex()


def test_idat_chain_header_repair_writes_convoy_model_sidecar(tmp_path):
    calls = []
    side_notes = []
    source = bytes.fromhex(idat_chain_repairable_bad_deflate_hex())
    runtime = SimpleNamespace(
        data_hex=source.hex(),
        side_notes=side_notes,
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *_args: "written",
    )

    result = fixit_felix_runtime.try_idat_chain_header_repair(runtime)

    model_path = (
        Path(fixit_felix_runtime.output.ensure_clone_folder("Flag.png", str(tmp_path)))
        / "Debug_Payloads"
        / "Flag_idat_convoy_model.json"
    )
    payload = json.loads(model_path.read_text())
    assert result == (True, "written")
    assert model_path.exists()
    assert payload["version"] == 1
    assert payload["convoy_stream_hash"]
    assert payload["byte_repairs"]
    assert payload["xors"]
    assert any(note.startswith("-IDAT convoy model written:") for note in side_notes)


def test_idat_convoy_clone_reuses_existing_fixed_file(tmp_path):
    calls = []
    side_notes = []
    data = b"convoy-working-data"
    folder = Path(fixit_felix_runtime.output.ensure_clone_folder("Flag.png", str(tmp_path)))
    existing = folder / "Flag.0_Fixed.png"
    existing.write_bytes(data)
    queued = []
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=side_notes,
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *_args: calls.append(("write_clone",)),
        queue_existing_clone=lambda path: queued.append(path) or path,
    )

    result, reused = fixit_felix_runtime._write_or_reuse_idat_convoy_clone(
        runtime,
        data,
        "summary",
    )

    assert reused is True
    assert result == str(existing)
    assert queued == [str(existing)]
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any(note.startswith("-IDAT convoy clone reused:") for note in side_notes)


def test_idat_deep_beam_debug_artifacts_replace_previous_rank_files(tmp_path):
    side_notes = []
    folder = Path(fixit_felix_runtime.output.ensure_clone_folder("Flag.png", str(tmp_path)))
    payload = folder / "Debug_Payloads"
    payload.mkdir(parents=True, exist_ok=True)
    stale_png = payload / "Flag_idat_deep_beam_rank01_stateold_deadbeef.png"
    stale_bin = payload / "Flag_idat_deep_beam_rank01_stateold_deadbeef_idat.bin"
    stale_raw = payload / "Flag_idat_deep_beam_rank01_stateold_deadbeef_raw_prefix.bin"
    stale_trace = payload / "Flag_idat_deep_beam_rank01_stateold_deadbeef_dynamic_trace.json"
    stale_png.write_bytes(b"old")
    stale_bin.write_bytes(b"old")
    stale_raw.write_bytes(b"old")
    stale_trace.write_text("{}")
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=side_notes,
    )
    result = SimpleNamespace(
        top_candidates=(
            SimpleNamespace(data=b"new-png", stream=zlib.compress(b"\x00abc"), state_id=7),
        )
    )

    saved = fixit_felix_runtime._write_idat_deep_beam_debug_artifacts(
        runtime,
        result,
        include_dynamic_trace=True,
    )

    assert saved
    assert not stale_png.exists()
    assert not stale_bin.exists()
    assert not stale_trace.exists()
    assert sorted(path.name for path in payload.iterdir()) == [
        "Flag_idat_deep_beam_rank01_state7_74e584d7.png",
        "Flag_idat_deep_beam_rank01_state7_74e584d7_dynamic_trace.json",
        "Flag_idat_deep_beam_rank01_state7_74e584d7_idat.bin",
        "Flag_idat_deep_beam_rank01_state7_74e584d7_raw_prefix.bin",
    ]
    trace = json.loads((payload / "Flag_idat_deep_beam_rank01_state7_74e584d7_dynamic_trace.json").read_text())
    assert "status" in trace


def _stored_block_candidate_result(*, complete: bool) -> idat_bruteforce.IdatStoredBlockLengthRepairResult:
    before = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=20,
        compressed_size=8,
        decompressed_size=4,
        usable_scanlines=0,
        error_offset=6,
    )
    after = idat.IdatStreamAnalysis(
        supported=True,
        complete=complete,
        status="ok" if complete else "incomplete_stream",
        height=4,
        expected_size=20,
        compressed_size=8,
        decompressed_size=20 if complete else 12,
        usable_scanlines=4 if complete else 2,
        error_offset=None if complete else 12,
    )
    candidate = idat_bruteforce.IdatDeepBeamCandidate(
        data=valid_png_bytes() if complete else b"partial-idat-diagnostic",
        stream=zlib.compress(b"\x00\x00") if complete else b"\x78\x9c\x03\x00",
        operations=(
            idat_bruteforce.IdatDeepBeamOperation(
                "stored-block-length",
                1,
                b"\x00",
                b"\x01",
            ),
        ),
        before=before,
        after=after,
        state_id=42,
        score=(1, 2, 3),
    )
    return idat_bruteforce.IdatStoredBlockLengthRepairResult(
        before=before,
        best=candidate,
        top_candidates=(candidate,),
        tested_candidates=1,
        budget_exhausted=False,
        repaired_blocks=1,
        png_prefix_hits=1,
        best_prefix_rows=after.usable_scanlines,
    )


def test_stored_block_incomplete_candidate_stays_diagnostic_not_clone():
    calls = []
    side_notes = []
    result = _stored_block_candidate_result(complete=False)
    runtime = SimpleNamespace(
        side_notes=side_notes,
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *args: calls.append(("write_clone", args)) or "written",
    )

    written = fixit_felix_runtime._write_stored_block_best_clone(
        runtime,
        result.before,
        result,
    )

    assert written is None
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any("not promoted as clone" in note for note in side_notes)
    assert any("diagnostic evidence" in call[1][1] for call in calls if call[0] == "candy")


def test_stored_block_complete_candidate_writes_final_clone():
    calls = []
    side_notes = []
    result = _stored_block_candidate_result(complete=True)
    runtime = SimpleNamespace(
        side_notes=side_notes,
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *args: calls.append(("write_clone", args)) or "written",
    )

    written = fixit_felix_runtime._write_stored_block_best_clone(
        runtime,
        result.before,
        result,
    )

    assert written == (True, "written")
    assert [call for call in calls if call[0] == "write_clone"]
    assert not any("not promoted as clone" in note for note in side_notes)


def test_seed_local_continuation_keeps_incomplete_progress_as_seed(monkeypatch):
    data = valid_png_bytes()
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=80,
        usable_scanlines=1,
        error_offset=40,
    )
    improved_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="bad_adler",
        height=4,
        expected_size=200,
        decompressed_size=96,
        usable_scanlines=1,
        error_offset=48,
    )
    seed = idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(idat_bruteforce.IdatDeepBeamOperation("stored-block", 1, b"\x00", b"\x01"),),
        before=analysis,
        after=seed_after,
        state_id=10,
        score=(1,),
    )
    calls = []

    def fake_local_probe(probe_data, **_kwargs):
        calls.append(probe_data)
        return idat_bruteforce.IdatDeflateProbeResult(
            before=seed_after,
            best=idat_bruteforce.IdatDeflateCandidate(
                data=data,
                stream_offset=2,
                file_offset=3,
                idat_index=1,
                idat_offset=2,
                old_byte=0,
                new_byte=0,
                before=seed_after,
                after=improved_after,
                edit_kind="insert",
                new_bytes=b"\x00",
            ),
            window_start=40,
            window_end=60,
            tested_candidates=1,
            budget_exhausted=False,
            strategy="deflate-local",
            reason="mocked",
        )

    monkeypatch.setattr(idat_bruteforce, "probe_idat_deflate_local_candidates", fake_local_probe)
    monkeypatch.setattr(fixit_felix_runtime, "_write_idat_deep_beam_debug_artifacts", lambda *_args, **_kwargs: ())
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        write_clone=lambda *_args, **_kwargs: "written",
        minibar=None,
        loadingbar=None,
        seed_local_continuation_rounds=1,
    )

    written, seeds = fixit_felix_runtime._run_idat_seed_local_continuation_runtime(
        runtime,
        data,
        analysis,
        (seed,),
    )

    assert written is None
    assert seeds
    assert seeds[0].after.decompressed_size == 96
    assert seeds[0].operations[-1].kind == "seed-local-deflate"
    assert calls
    assert not any(
        fixit_felix_runtime.FINAL_INVESTIGATION_LABEL in note
        and "produced no final clone" in note
        for note in runtime.side_notes
    )


def test_seed_local_continuation_keeps_diagnostic_branch_as_seed(monkeypatch):
    data = valid_png_bytes()
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=80,
        usable_scanlines=1,
        error_offset=40,
    )
    best_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=84,
        usable_scanlines=1,
        error_offset=42,
    )
    diagnostic_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=96,
        usable_scanlines=1,
        error_offset=48,
    )
    seed = idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(idat_bruteforce.IdatDeepBeamOperation("stored-block", 1, b"\x00", b"\x01"),),
        before=analysis,
        after=seed_after,
        state_id=10,
        score=(1,),
    )
    best_mutation = idat_bruteforce.mutate_idat_stream_byte(
        data,
        2,
        stream[2] ^ 0x01,
        before_analysis=seed_after,
    )
    diagnostic_mutation = idat_bruteforce.mutate_idat_stream_byte(
        data,
        2,
        stream[2] ^ 0x02,
        before_analysis=seed_after,
    )
    assert best_mutation is not None
    assert diagnostic_mutation is not None

    def fake_local_probe(_probe_data, **_kwargs):
        return idat_bruteforce.IdatDeflateProbeResult(
            before=seed_after,
            best=idat_bruteforce.IdatDeflateCandidate(
                data=best_mutation.data,
                stream_offset=2,
                file_offset=3,
                idat_index=1,
                idat_offset=2,
                old_byte=stream[2],
                new_byte=stream[2] ^ 0x01,
                before=seed_after,
                after=best_after,
                edit_kind="replace",
                old_bytes=bytes((stream[2],)),
                new_bytes=bytes((stream[2] ^ 0x01,)),
            ),
            window_start=40,
            window_end=60,
            tested_candidates=2,
            budget_exhausted=False,
            strategy="deflate-local",
            reason="mocked",
            diagnostic_best=idat_bruteforce.IdatDeflateCandidate(
                data=diagnostic_mutation.data,
                stream_offset=2,
                file_offset=3,
                idat_index=1,
                idat_offset=2,
                old_byte=stream[2],
                new_byte=stream[2] ^ 0x02,
                before=seed_after,
                after=diagnostic_after,
                edit_kind="replace",
                old_bytes=bytes((stream[2],)),
                new_bytes=bytes((stream[2] ^ 0x02,)),
            ),
        )

    monkeypatch.setattr(idat_bruteforce, "probe_idat_deflate_local_candidates", fake_local_probe)
    monkeypatch.setattr(fixit_felix_runtime, "_write_idat_deep_beam_debug_artifacts", lambda *_args, **_kwargs: ())
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        write_clone=lambda *_args, **_kwargs: "written",
        minibar=None,
        loadingbar=None,
        seed_local_continuation_rounds=1,
        seed_local_continuation_limit=2,
    )

    written, seeds = fixit_felix_runtime._run_idat_seed_local_continuation_runtime(
        runtime,
        data,
        analysis,
        (seed,),
    )

    assert written is None
    assert {candidate.operations[-1].kind for candidate in seeds} == {
        "seed-local-deflate",
        "seed-local-deflate-diagnostic",
    }
    assert max(candidate.after.decompressed_size for candidate in seeds) == 96


def test_filter_alignment_keeps_png_filter_progress_as_seed(monkeypatch):
    data = valid_png_bytes()
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=80,
        usable_scanlines=1,
        error_offset=40,
    )
    improved_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=84,
        usable_scanlines=1,
        error_offset=42,
    )
    seed = idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(idat_bruteforce.IdatDeepBeamOperation("stored-block", 1, b"\x00", b"\x01"),),
        before=analysis,
        after=seed_after,
        state_id=10,
        score=(1,),
    )
    calls = []

    def fake_local_probe(probe_data, **kwargs):
        calls.append((probe_data, kwargs))
        return idat_bruteforce.IdatDeflateProbeResult(
            before=seed_after,
            best=idat_bruteforce.IdatDeflateCandidate(
                data=data,
                stream_offset=3,
                file_offset=4,
                idat_index=1,
                idat_offset=3,
                old_byte=0,
                new_byte=4,
                before=seed_after,
                after=improved_after,
                edit_kind="insert",
                new_bytes=b"\x04",
            ),
            window_start=40,
            window_end=60,
            tested_candidates=1,
            budget_exhausted=False,
            strategy="deflate-local-png-filter",
            reason="mocked",
        )

    artifact_labels = []
    monkeypatch.setattr(idat_bruteforce, "probe_idat_deflate_local_candidates", fake_local_probe)
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_write_idat_deep_beam_debug_artifacts",
        lambda *_args, **kwargs: artifact_labels.append(kwargs.get("label")) or (),
    )
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        write_clone=lambda *_args, **_kwargs: "written",
        minibar=None,
        loadingbar=None,
        seed_local_continuation_budget=17,
        seed_local_continuation_limit=1,
    )

    written, seeds = fixit_felix_runtime._run_idat_filter_alignment_runtime(
        runtime,
        data,
        analysis,
        (seed,),
    )

    assert written is None
    assert seeds
    assert seeds[0].operations[-1].kind == "seed-local-png-filter"
    assert calls[0][1]["score_mode"] == "png-filter"
    assert artifact_labels == ["idat_filter_alignment"]


def test_filter_seed_stored_block_returns_incomplete_progress_as_seed(monkeypatch):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=80,
        usable_scanlines=1,
        error_offset=40,
    )
    seed = idat_deep_beam_seed(data, state_id=12, kind="png-filter-seed")
    stored_result = _stored_block_candidate_result(complete=False)
    calls = []

    def fake_stored(_runtime, _data, _analysis, **kwargs):
        calls.append(kwargs)
        return stored_result

    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_stored_block_runtime", fake_stored)
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        write_clone=lambda *_args, **_kwargs: "written",
        minibar=None,
        loadingbar=None,
        seed_local_continuation_limit=1,
    )

    written, seeds = fixit_felix_runtime._run_idat_filter_seed_stored_block_runtime(
        runtime,
        data,
        analysis,
        (seed,),
    )

    assert written is None
    assert seeds == stored_result.top_candidates
    assert calls
    assert calls[0]["path_label"] == "stored_block_filter_seed"
    assert calls[0]["seed_candidates"] == (seed,)
    assert any("stored-block filter-seed route produced" in note for note in runtime.side_notes)


def test_seed_local_continuation_uses_runtime_round_configuration(monkeypatch):
    data = valid_png_bytes()
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=80,
        usable_scanlines=1,
        error_offset=40,
    )
    seed = idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(idat_bruteforce.IdatDeepBeamOperation("stored-block", 1, b"\x00", b"\x01"),),
        before=analysis,
        after=seed_after,
        state_id=10,
        score=(1,),
    )
    calls = []

    def fake_local_probe(probe_data, **_kwargs):
        calls.append(probe_data)
        improved_after = idat.IdatStreamAnalysis(
            supported=True,
            complete=False,
            status="corrupt_deflate",
            height=4,
            expected_size=200,
            decompressed_size=80 + len(calls),
            usable_scanlines=1,
            error_offset=40 + len(calls),
        )
        return idat_bruteforce.IdatDeflateProbeResult(
            before=seed_after,
            best=idat_bruteforce.IdatDeflateCandidate(
                data=data,
                stream_offset=len(calls),
                file_offset=len(calls),
                idat_index=1,
                idat_offset=len(calls),
                old_byte=0,
                new_byte=len(calls),
                before=seed_after,
                after=improved_after,
                edit_kind="insert",
                new_bytes=bytes((len(calls),)),
            ),
            window_start=40,
            window_end=60,
            tested_candidates=1,
            budget_exhausted=False,
            strategy="deflate-local",
            reason="mocked",
        )

    monkeypatch.setattr(idat_bruteforce, "probe_idat_deflate_local_candidates", fake_local_probe)
    monkeypatch.setattr(fixit_felix_runtime, "_write_idat_deep_beam_debug_artifacts", lambda *_args, **_kwargs: ())
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        write_clone=lambda *_args, **_kwargs: "written",
        minibar=None,
        loadingbar=None,
        seed_local_continuation_rounds=3,
        seed_local_continuation_budget=17,
        seed_local_continuation_limit=1,
    )

    written, seeds = fixit_felix_runtime._run_idat_seed_local_continuation_runtime(
        runtime,
        data,
        analysis,
        (seed,),
    )

    assert written is None
    assert len(calls) == 3
    assert seeds
    assert "budget=17" in runtime.side_notes[0]
    assert "3 round" in runtime.side_notes[0]


def test_seed_local_continuation_prefers_artifact_seeds_before_checkpoints(monkeypatch):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed = idat_deep_beam_seed(data, state_id=7, kind="artifact-seed")
    calls = []

    def artifact_loader(_runtime, _data, _analysis, *, limit):
        calls.append(("artifact", limit))
        return (seed,)

    def checkpoint_loader(*_args, **_kwargs):
        raise AssertionError("checkpoint loader should not run when artifact seeds exist")

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_load_idat_artifact_seed_candidates",
        artifact_loader,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_load_final_investigation_seed_candidates",
        checkpoint_loader,
    )
    monkeypatch.setattr(
        idat_bruteforce,
        "probe_idat_deflate_local_candidates",
        lambda *_args, **_kwargs: idat_bruteforce.IdatDeflateProbeResult(
            seed.after,
            None,
            0,
            0,
            0,
            False,
            strategy="deflate-local",
            reason="mocked",
        ),
    )
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        write_clone=lambda *_args, **_kwargs: "written",
        minibar=None,
        loadingbar=None,
        seed_local_continuation_limit=1,
    )

    result, seeds = fixit_felix_runtime._run_idat_seed_local_continuation_runtime(
        runtime,
        data,
        analysis,
    )

    assert result is None
    assert seeds == ()
    assert calls == [("artifact", 1)]


def test_GroundHogDay_repair_prioritizes_local_before_row_filter_unlock(monkeypatch):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    initial = idat_progress_seed(
        data,
        state_id=1,
        usable_scanlines=0,
        decompressed_size=100,
        kind="initial",
    )
    local_one = idat_progress_seed(
        data,
        state_id=2,
        usable_scanlines=1,
        decompressed_size=200,
        kind="seed-local",
    )
    local_two = idat_progress_seed(
        data,
        state_id=3,
        usable_scanlines=2,
        decompressed_size=400,
        kind="seed-local",
    )
    row_unlock = idat_progress_seed(
        data,
        state_id=4,
        usable_scanlines=3,
        decompressed_size=600,
        kind="row-filter",
    )
    local_after_row = idat_progress_seed(
        data,
        state_id=5,
        usable_scanlines=4,
        decompressed_size=800,
        kind="seed-local",
    )
    calls = []
    row_outputs = [(None, (row_unlock,)), (None, ())]
    local_outputs = [
        (None, (local_one,)),
        (None, (local_two,)),
        (None, ()),
        (None, (local_after_row,)),
        (None, ()),
    ]
    candy_calls = []

    def fake_row_filter(_runtime, _data, _analysis, seed_candidates=()):
        _runtime.candy("Title", "probe_idat_png_filter_literal_repair")
        calls.append(("row", tuple(seed.state_id for seed in seed_candidates)))
        return row_outputs.pop(0)

    def fake_seed_local(_runtime, _data, _analysis, seed_candidates=()):
        _runtime.candy("Title", "probe_idat_seed_local_continuation")
        calls.append(
            (
                "local",
                tuple(seed.state_id for seed in seed_candidates),
                _runtime.seed_local_continuation_rounds,
            )
        )
        return local_outputs.pop(0)

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_row_filter_literal_repair_runtime",
        fake_row_filter,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_seed_local_continuation_runtime",
        fake_seed_local,
    )
    runtime = SimpleNamespace(
        side_notes=[],
        candy=lambda *args, **_kwargs: candy_calls.append(args),
        prefinal_repair_cycles=4,
        seed_local_continuation_limit=1,
    )

    result, seeds = fixit_felix_runtime._GroundHogDay_run_idat_prefinal_alternating_repair_runtime(
        runtime,
        data,
        analysis,
        (initial,),
    )

    assert result is None
    assert seeds == (local_after_row,)
    assert calls == [
        ("local", (1,), 1),
        ("local", (2,), 1),
        ("local", (3,), 1),
        ("row", (3,)),
        ("local", (4,), 1),
        ("local", (5,), 1),
        ("row", (5,)),
    ]
    assert any("GroundHogDay cycle 2/4 accepted local seed" in note for note in runtime.side_notes)
    assert any("GroundHogDay cycle 3/4 accepted row-filter seed" in note for note in runtime.side_notes)
    assert any("GroundHogDay cycle 3/4 accepted local-after-row seed" in note for note in runtime.side_notes)
    assert any(
        "GroundHogDay starts before %s" % fixit_felix_runtime.FINAL_INVESTIGATION_LABEL
        in call[1]
        for call in candy_calls
    )
    assert any("not looping blindly" in call[1] for call in candy_calls)
    assert [call for call in candy_calls if call[0] == "Title"] == [
        ("Title", "GroundHogDay 1: probe_idat_seed_local_continuation"),
        ("Title", "GroundHogDay 2: probe_idat_seed_local_continuation"),
        ("Title", "GroundHogDay 3: probe_idat_seed_local_continuation"),
        ("Title", "GroundHogDay 3: probe_idat_png_filter_literal_repair"),
        ("Title", "GroundHogDay 3: probe_idat_seed_local_continuation"),
        ("Title", "GroundHogDay 4: probe_idat_seed_local_continuation"),
        ("Title", "GroundHogDay 4: probe_idat_png_filter_literal_repair"),
    ]


def test_GroundHogDay_row_filter_waits_until_local_stalls_with_unusable_rows(monkeypatch):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    initial = idat_progress_seed(
        data,
        state_id=1,
        usable_scanlines=1,
        complete_scanlines=1,
        decompressed_size=100,
        kind="initial",
    )
    local_unusable_rows = idat_progress_seed(
        data,
        state_id=2,
        usable_scanlines=1,
        complete_scanlines=3,
        decompressed_size=300,
        kind="seed-local",
    )
    row_fixed = idat_progress_seed(
        data,
        state_id=3,
        usable_scanlines=3,
        complete_scanlines=3,
        decompressed_size=300,
        kind="row-filter",
    )
    calls = []
    local_outputs = [(None, (local_unusable_rows,)), (None, ()), (None, ())]
    row_outputs = [(None, (row_fixed,))]
    candy_calls = []

    def fake_seed_local(_runtime, _data, _analysis, seed_candidates=()):
        _runtime.candy("Title", "probe_idat_seed_local_continuation")
        calls.append(
            (
                "local",
                tuple(seed.state_id for seed in seed_candidates),
                _runtime.seed_local_continuation_rounds,
            )
        )
        return local_outputs.pop(0)

    def fake_row_filter(_runtime, _data, _analysis, seed_candidates=()):
        _runtime.candy("Title", "probe_idat_png_filter_literal_repair")
        calls.append(("row", tuple(seed.state_id for seed in seed_candidates)))
        return row_outputs.pop(0)

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_seed_local_continuation_runtime",
        fake_seed_local,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_row_filter_literal_repair_runtime",
        fake_row_filter,
    )
    runtime = SimpleNamespace(
        side_notes=[],
        candy=lambda *args, **_kwargs: candy_calls.append(args),
        prefinal_repair_cycles=2,
        seed_local_continuation_limit=1,
    )

    result, seeds = fixit_felix_runtime._GroundHogDay_run_idat_prefinal_alternating_repair_runtime(
        runtime,
        data,
        analysis,
        (initial,),
    )

    assert result is None
    assert seeds == (row_fixed,)
    assert calls == [
        ("local", (1,), 1),
        ("local", (2,), 1),
        ("row", (2,)),
        ("local", (3,), 1),
    ]
    assert any("postponed row-filter repair" in note for note in runtime.side_notes)
    assert any("PNG filters are still dirty" in call[1] for call in candy_calls)
    assert [call for call in candy_calls if call[0] == "Title"] == [
        ("Title", "GroundHogDay 1: probe_idat_seed_local_continuation"),
        ("Title", "GroundHogDay 2: probe_idat_seed_local_continuation"),
        ("Title", "GroundHogDay 2: probe_idat_png_filter_literal_repair"),
        ("Title", "GroundHogDay 2: probe_idat_seed_local_continuation"),
    ]


def test_row_filter_literal_repair_tries_fast_pass_before_wide_fallback(monkeypatch):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed = idat_progress_seed(
        data,
        state_id=8,
        usable_scanlines=1,
        complete_scanlines=2,
        decompressed_size=300,
        kind="row-filter-seed",
    )
    calls = []

    def fake_probe(_data, **kwargs):
        calls.append(kwargs)
        return idat_bruteforce.IdatDeflateProbeResult(
            analysis,
            None,
            0,
            0,
            11,
            False,
            "png-filter-literal-repair",
            "mocked",
        )

    monkeypatch.setattr(
        fixit_felix_runtime.idat_bruteforce,
        "probe_idat_png_filter_literal_repair",
        fake_probe,
    )
    runtime = SimpleNamespace(
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        seed_local_continuation_limit=1,
        ultimate_linefeed_budget=0,
        loadingbar=None,
        minibar=None,
    )

    result, seeds = fixit_felix_runtime._run_idat_row_filter_literal_repair_runtime(
        runtime,
        data,
        analysis,
        (seed,),
    )

    assert result is None
    assert seeds == ()
    assert len(calls) == 2
    assert calls[0]["max_rows"] == 32
    assert calls[0]["max_repairs"] == 4
    assert calls[0]["search_radius"] == 4
    assert calls[0]["candidate_budget"] == 4000
    assert calls[1]["max_rows"] == 64
    assert calls[1]["max_repairs"] == 64
    assert "search_radius" not in calls[1]
    assert "candidate_budget" not in calls[1]
    assert any("fast pass produced no stronger seed" in note for note in runtime.side_notes)


def test_GroundHogDay_scanline_recovery_update_reports_only_line_gains():
    data = valid_png_bytes()
    old_seed = idat_progress_seed(
        data,
        state_id=1,
        usable_scanlines=2,
        decompressed_size=200,
        kind="old",
    )
    same_line_seed = idat_progress_seed(
        data,
        state_id=2,
        usable_scanlines=2,
        decompressed_size=260,
        kind="same-line",
    )
    new_seed = idat_progress_seed(
        data,
        state_id=3,
        usable_scanlines=4,
        decompressed_size=420,
        kind="line-gain",
    )
    calls = []
    runtime = SimpleNamespace(
        side_notes=[],
        candy=lambda *args, **_kwargs: calls.append(args),
    )

    fixit_felix_runtime._GroundHogDay_emit_scanline_recovery_update(
        runtime,
        (old_seed,),
        (same_line_seed,),
        "local deflate",
    )
    assert calls == []
    assert runtime.side_notes == []

    fixit_felix_runtime._GroundHogDay_emit_scanline_recovery_update(
        runtime,
        (old_seed,),
        (new_seed,),
        "local deflate",
    )

    assert calls == [
        (
            "Cowsay",
            "GroundHogDay local deflate recovered more scanlines: usable 4/10 (was 2/10), complete rows 4/10 (was 2/10).",
            "good",
        )
    ]
    assert runtime.side_notes == [
        "-IDAT GroundHogDay scanline gain via local deflate: usable 2->4/10; complete 2->4/10."
    ]


def test_GroundHogDay_visual_guard_scores_noise_by_profile():
    smooth_seed = idat_deep_beam_seed(smooth_gray_png(), state_id=1)
    noisy_seed = idat_deep_beam_seed(noisy_gray_png(), state_id=2)

    smooth = fixit_felix_runtime._GroundHogDay_visual_score(smooth_seed, "strict")
    noisy_strict = fixit_felix_runtime._GroundHogDay_visual_score(noisy_seed, "strict")
    noisy_structure = fixit_felix_runtime._GroundHogDay_visual_score(noisy_seed, "structure")

    assert smooth.passed is True
    assert noisy_strict.passed is False
    assert any("high entropy" in reason or "weak row continuity" in reason for reason in noisy_strict.reasons)
    assert noisy_structure.passed is True


def test_GroundHogDay_visual_guard_prompt_can_allow_noisy_structure():
    calls = []
    runtime = SimpleNamespace(
        interactive=True,
        input_func=lambda _prompt: "structure",
        deep_beam_prompt_cache={},
        side_notes=[],
        candy=lambda *args, **_kwargs: calls.append(args),
    )

    profile = fixit_felix_runtime._GroundHogDay_visual_guard_profile(runtime)

    assert profile == "structure"
    assert runtime.deep_beam_prompt_cache["groundhogday_visual_guard"] == "structure"
    assert any("GroundHogDay visual guard:" in call[1] for call in calls)


def test_GroundHogDay_visual_guard_rejects_noisy_linefeed_after_cleanup(monkeypatch, tmp_path):
    previous = idat_deep_beam_seed(smooth_gray_png(), state_id=11, kind="groundhogday-seed")
    noisy = idat_deep_beam_seed(noisy_gray_png(), state_id=12, kind="groundhogday-linefeed")
    cleanup_calls = []

    def fake_row_filter(_runtime, _data, _analysis, seed_candidates=()):
        cleanup_calls.append("row")
        return None, ()

    def fake_filter_alignment(_runtime, _data, _analysis, seed_candidates=()):
        cleanup_calls.append("filter")
        return None, ()

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_row_filter_literal_repair_runtime",
        fake_row_filter,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_filter_alignment_runtime",
        fake_filter_alignment,
    )
    candy_calls = []
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=[],
        candy=lambda *args, **_kwargs: candy_calls.append(args),
        seed_local_continuation_limit=1,
        groundhogday_visual_guard="strict",
        deep_beam_prompt_cache={},
    )
    analysis = idat.analyze_idat_stream(previous.data)
    title_counter = [205]

    result, accepted = fixit_felix_runtime._GroundHogDay_guard_linefeed_progress_runtime(
        runtime,
        previous.data,
        analysis,
        (previous,),
        (noisy,),
        title_counter,
    )

    assert result is None
    assert accepted == ()
    assert cleanup_calls == ["row", "filter"]
    assert any("complete stream, visual score failed" in call[1] for call in candy_calls)
    assert any("kept structural-only" in note for note in runtime.side_notes)


def test_GroundHogDay_mini_ultimate_progress_label():
    messages = []
    runtime = SimpleNamespace(minibar=lambda message: messages.append(message))
    progress = fixit_felix_runtime._runtime_groundhogday_ultimate_linefeed_progress(runtime)

    progress("UltimateMegaSuperLineFeedBruteForce", 7, 50)

    assert messages
    assert "MiniUltimateMegaSuperLineFeedBruteForce" in messages[0]
    assert "IDAT UltimateMegaSuperLineFeedBruteForce" not in messages[0]


def test_GroundHogDay_resume_uses_seed_pool_limit(monkeypatch):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.analyze_idat_stream(data)
    seed_a = idat_progress_seed(
        data,
        state_id=57,
        usable_scanlines=4,
        decompressed_size=100,
        kind="groundhogday-best",
    )
    seed_b = idat_progress_seed(
        data,
        state_id=36,
        usable_scanlines=3,
        decompressed_size=90,
        kind="groundhogday-side-branch",
    )
    calls = []

    def fake_artifact_loader(_runtime, _data, _analysis, *, limit):
        calls.append(limit)
        return (seed_a, seed_b)

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_load_idat_artifact_seed_candidates",
        fake_artifact_loader,
    )
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir="",
        side_notes=[],
        seed_local_continuation_limit=1,
        groundhogday_seed_pool_limit=7,
    )

    seeds = fixit_felix_runtime._GroundHogDay_resume_seed_candidates(
        runtime,
        data,
        analysis,
    )

    assert calls == [7]
    assert {seed.state_id for seed in seeds} == {57, 36}


def test_GroundHogDay_mini_ultimate_auto_budget_keeps_route_open(tmp_path, monkeypatch):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    seed = idat_progress_seed(
        data,
        state_id=36,
        usable_scanlines=3,
        decompressed_size=90,
        kind="groundhogday-linefeed",
    )
    progress_path = tmp_path / "Flag_groundhogday_ultimate_linefeed.progress.json"
    progress_path.write_text("{}\n", encoding="utf-8")
    calls = []
    side_notes = []
    progress = idat_bruteforce.UltimateLinefeedProgress(
        path=str(progress_path),
        source_hash="seed",
        target_adler=None,
        start_offset=12,
        max_depth=2,
        max_offsets=256,
        operation_pool_hash="pool",
        focused_operation_pool_hash="focused",
        broad_operation_pool_hash="broad",
        phase="complete",
        depth=2,
        pool_index=0,
        combination_rank=0,
        combination_indices=None,
        tested_candidates=50_000,
        pruned_candidates=0,
        state_count=50_001,
        budget=50_000,
        timestamp=0.0,
        attempted_candidates=50_000,
    )

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_idat_groundhogday_ultimate_linefeed_paths",
        lambda _runtime: ("", str(progress_path)),
    )
    monkeypatch.setattr(
        idat_bruteforce,
        "load_ultimate_progress_for_source",
        lambda *_args, **_kwargs: (progress, ""),
    )
    runtime = SimpleNamespace(
        side_notes=side_notes,
        candy=lambda *args, **kwargs: calls.append((args, kwargs)),
        seed_local_continuation_limit=1,
        groundhogday_seed_pool_limit=4,
        ultimate_linefeed_budget=None,
        ultimate_linefeed_unbounded=False,
        ultimate_linefeed_max_depth=None,
        ultimate_linefeed_max_offsets=None,
    )

    open_route = fixit_felix_runtime._GroundHogDay_ultimate_linefeed_route_open(
        runtime,
        (seed,),
    )

    assert open_route is True
    assert any("next budget=100000" in note for note in side_notes)
    assert any("attempted=50000; budget=100000" in note for note in side_notes)
    assert any("raising that checkpointed budget to 100000" in call[0][1] for call in calls)


def test_GroundHogDay_mini_ultimate_prioritizes_matching_resume_seed(tmp_path, monkeypatch):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.analyze_idat_stream(data)
    best_seed = idat_progress_seed(
        data,
        state_id=57,
        usable_scanlines=47,
        decompressed_size=771658,
        kind="groundhogday-best",
    )
    resume_seed = idat_progress_seed(
        data,
        state_id=36,
        usable_scanlines=47,
        decompressed_size=757362,
        kind="groundhogday-linefeed-resume",
    )
    progress_path = tmp_path / "Flag_groundhogday_ultimate_linefeed.progress.json"
    progress_path.write_text("{}\n", encoding="utf-8")
    progress = idat_bruteforce.UltimateLinefeedProgress(
        path=str(progress_path),
        source_hash="resume-seed",
        target_adler=None,
        start_offset=12,
        max_depth=2,
        max_offsets=256,
        operation_pool_hash="pool",
        focused_operation_pool_hash="focused",
        broad_operation_pool_hash="broad",
        phase="complete",
        depth=2,
        pool_index=0,
        combination_rank=0,
        combination_indices=None,
        tested_candidates=50_000,
        pruned_candidates=0,
        state_count=50_001,
        budget=50_000,
        timestamp=0.0,
        attempted_candidates=50_000,
    )
    probed: list[bytes] = []
    side_notes: list[str] = []

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_idat_groundhogday_ultimate_linefeed_paths",
        lambda _runtime: (str(tmp_path / "Flag_groundhogday_ultimate_linefeed.checkpoint.jsonl"), str(progress_path)),
    )

    def fake_load(progress_data, *_args, **_kwargs):
        if progress_data == resume_seed.data:
            return progress, ""
        return None, "source_hash mismatch"

    def fake_probe(probe_data, **kwargs):
        probed.append(probe_data)
        before = resume_seed.after if probe_data == resume_seed.data else best_seed.after
        return idat_bruteforce.UltimateLinefeedProbeResult(
            before=before,
            best=None,
            target_adler=None,
            start_offset=kwargs.get("start_offset"),
            reached_depth=0,
            max_depth=kwargs["max_depth"],
            suspect_offsets=(),
            tested_candidates=0,
            state_count=0,
            visited_count=0,
            pruned_candidates=0,
            resumed_states=0,
            checkpoint_path=kwargs.get("checkpoint_path", ""),
            budget_exhausted=False,
            progress_path=kwargs.get("progress_path", ""),
            reason="mocked",
        )

    monkeypatch.setattr(idat_bruteforce, "load_ultimate_progress_for_source", fake_load)
    monkeypatch.setattr(idat_bruteforce, "probe_ultimate_mega_super_linefeed_bruteforce", fake_probe)
    runtime = SimpleNamespace(
        side_notes=side_notes,
        candy=lambda *_args, **_kwargs: None,
        seed_local_continuation_limit=1,
        groundhogday_seed_pool_limit=4,
        ultimate_linefeed_budget=None,
        ultimate_linefeed_unbounded=False,
        ultimate_linefeed_workers=None,
        ultimate_linefeed_max_depth=None,
        ultimate_linefeed_max_offsets=None,
        file_origin="Flag.png",
    )

    _result, seeds, _next_state = fixit_felix_runtime._run_idat_groundhogday_ultimate_linefeed_runtime(
        runtime,
        data,
        analysis,
        (best_seed, resume_seed),
        next_state_id=58,
        original_idat_count=1,
    )

    assert seeds == ()
    assert probed == [resume_seed.data]
    assert any("resume priority: 1 seed" in note for note in side_notes)


def test_GroundHogDay_linefeed_route_promotes_insert_candidate(monkeypatch):
    data = valid_png_bytes()
    initial = idat_progress_seed(
        data,
        state_id=8,
        usable_scanlines=1,
        decompressed_size=100,
        kind="groundhogday-seed",
    )
    candidate_data = bad_adler_three_scanline_png_bytes()
    candidate_analysis = idat.analyze_idat_stream(candidate_data)
    candidate = idat_bruteforce.IdatLinefeedInsertCandidate(
        data=candidate_data,
        stream_offset=3,
        inserted_byte=0x0A,
        before=initial.after,
        after=candidate_analysis,
    )
    calls = []

    def fake_lf(_data, **kwargs):
        calls.append(("lf", _data, kwargs))
        return idat_bruteforce.IdatLinefeedInsertProbeResult(
            initial.after,
            candidate,
            0,
            12,
            1,
            False,
            strategy="linefeed-lf-insert",
            reason="mocked",
        )

    def fake_cr(_data, **kwargs):
        calls.append(("cr", _data, kwargs))
        return idat_bruteforce.IdatLinefeedInsertProbeResult(
            initial.after,
            None,
            0,
            12,
            1,
            False,
            strategy="linefeed-cr-insert",
            reason="mocked",
        )

    def fake_super(_data, **kwargs):
        calls.append(("super", _data, kwargs))
        return idat_bruteforce.SuperMegaLinefeedProbeResult(
            initial.after,
            None,
            None,
            0,
            0,
            12,
            1,
            False,
            reason="mocked",
        )

    monkeypatch.setattr(idat_bruteforce, "probe_idat_linefeed_lf_insertions", fake_lf)
    monkeypatch.setattr(idat_bruteforce, "probe_idat_linefeed_cr_insertions", fake_cr)
    monkeypatch.setattr(idat_bruteforce, "probe_super_mega_linefeed_force_of_death", fake_super)
    monkeypatch.setattr(fixit_felix_runtime, "_write_idat_deep_beam_debug_artifacts", lambda *_args, **_kwargs: ())
    candy_calls = []
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=[],
        candy=lambda *args, **_kwargs: candy_calls.append(args),
        seed_local_continuation_limit=1,
        loadingbar=None,
        minibar=None,
    )
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )

    result, seeds = fixit_felix_runtime._run_idat_groundhogday_linefeed_runtime(
        runtime,
        data,
        analysis,
        (initial,),
    )

    assert result is None
    assert len(seeds) == 1
    assert seeds[0].data == candidate_data
    assert seeds[0].parent_id == 8
    assert seeds[0].after.usable_scanlines == 3
    assert seeds[0].operations[-1].kind == "groundhogday-linefeed-insert-0a"
    assert [call[0] for call in calls] == ["lf", "cr", "super"]
    assert any("decompressed rows are the scoreboard" in call[1] for call in candy_calls)
    assert ("Title", "probe_idat_groundhogday_linefeed_seed_repair") in candy_calls
    assert any("GroundHogDay linefeed route" in note for note in runtime.side_notes)


def test_GroundHogDay_linefeed_route_promotes_ultimate_candidate(monkeypatch):
    data = valid_png_bytes()
    initial = idat_progress_seed(
        data,
        state_id=8,
        usable_scanlines=1,
        decompressed_size=100,
        kind="groundhogday-seed",
    )
    candidate_data = bad_adler_three_scanline_png_bytes()
    candidate_analysis = idat.analyze_idat_stream(candidate_data)
    ultimate_candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        data=candidate_data,
        operations=(
            idat_bruteforce.SuperMegaLinefeedOperation(
                "ultimate-insert-cr-before-lf",
                5,
                b"",
                b"\r",
            ),
        ),
        before=initial.after,
        after=candidate_analysis,
        state_id=91,
        parent_id=8,
        source_offsets=(5,),
        score=idat_bruteforce.super_mega_linefeed_score(candidate_analysis, 1),
    )
    calls = []

    monkeypatch.setattr(
        idat_bruteforce,
        "probe_idat_linefeed_lf_insertions",
        lambda *_args, **_kwargs: idat_bruteforce.IdatLinefeedInsertProbeResult(
            initial.after,
            None,
            0,
            12,
            1,
            False,
            strategy="linefeed-lf-insert",
        ),
    )
    monkeypatch.setattr(
        idat_bruteforce,
        "probe_idat_linefeed_cr_insertions",
        lambda *_args, **_kwargs: idat_bruteforce.IdatLinefeedInsertProbeResult(
            initial.after,
            None,
            0,
            12,
            1,
            False,
            strategy="linefeed-cr-insert",
        ),
    )
    monkeypatch.setattr(
        idat_bruteforce,
        "probe_super_mega_linefeed_force_of_death",
        lambda *_args, **_kwargs: idat_bruteforce.SuperMegaLinefeedProbeResult(
            initial.after,
            None,
            None,
            0,
            0,
            12,
            1,
            False,
            reason="mocked",
        ),
    )

    def fake_ultimate(_data, **kwargs):
        calls.append(kwargs)
        return idat_bruteforce.UltimateLinefeedProbeResult(
            before=initial.after,
            best=ultimate_candidate,
            target_adler=None,
            start_offset=kwargs.get("start_offset"),
            reached_depth=1,
            max_depth=kwargs.get("max_depth"),
            suspect_offsets=(5,),
            tested_candidates=7,
            state_count=2,
            visited_count=2,
            pruned_candidates=0,
            resumed_states=0,
            checkpoint_path=kwargs.get("checkpoint_path", ""),
            budget_exhausted=False,
            top_candidates=(ultimate_candidate,),
            progress_path=kwargs.get("progress_path", ""),
        )

    monkeypatch.setattr(idat_bruteforce, "probe_ultimate_mega_super_linefeed_bruteforce", fake_ultimate)
    monkeypatch.setattr(fixit_felix_runtime, "_write_idat_deep_beam_debug_artifacts", lambda *_args, **_kwargs: ())
    candy_calls = []
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=[],
        candy=lambda *args, **_kwargs: candy_calls.append(args),
        seed_local_continuation_limit=1,
        ultimate_linefeed_budget=1234,
        ultimate_linefeed_workers=0,
        ultimate_linefeed_max_depth=2,
        ultimate_linefeed_max_offsets=64,
        loadingbar=None,
        minibar=None,
    )
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )

    result, seeds = fixit_felix_runtime._run_idat_groundhogday_linefeed_runtime(
        runtime,
        data,
        analysis,
        (initial,),
    )

    assert result is None
    assert len(seeds) == 1
    assert seeds[0].data == candidate_data
    assert seeds[0].parent_id == 8
    assert seeds[0].operations[-1].kind == "groundhogday-linefeed-ultimate-insert-cr-before-lf"
    assert calls[0]["budget"] == 1234
    assert calls[0]["max_depth"] == 2
    assert calls[0]["max_offsets"] == 64
    assert any("UltimateLineFeed" in note for note in runtime.side_notes)
    assert ("Title", "IDAT MiniUltimateMegaSuperLineFeedBruteForce") in candy_calls


def test_GroundHogDay_seed_routes_checkpoint_progress_then_stop_on_plateau(monkeypatch, tmp_path):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    initial = idat_progress_seed(
        data,
        state_id=1,
        usable_scanlines=0,
        decompressed_size=100,
        kind="initial",
    )
    stored_seed = idat_progress_seed(
        data,
        state_id=2,
        usable_scanlines=1,
        decompressed_size=250,
        kind="stored-block-filter-seed",
    )
    calls = []

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_GroundHogDay_run_idat_prefinal_alternating_repair_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_filter_alignment_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_groundhogday_linefeed_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )

    def fake_stored(_runtime, _data, _analysis, seed_candidates=()):
        _runtime.candy("Title", "probe_idat_stored_block_length_repair")
        calls.append(("stored", tuple(seed.state_id for seed in seed_candidates)))
        return None, (stored_seed,)

    def fake_row_after_stored(_runtime, _data, _analysis, seed_candidates=()):
        _runtime.candy("Title", "probe_idat_png_filter_literal_repair")
        calls.append(("row-after-stored", tuple(seed.state_id for seed in seed_candidates)))
        return None, ()

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_filter_seed_stored_block_runtime",
        fake_stored,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_row_filter_literal_repair_runtime",
        fake_row_after_stored,
    )
    candy_calls = []
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=[],
        candy=lambda *args, **_kwargs: candy_calls.append(args),
        prefinal_repair_batches=1,
    )

    result, seeds, deferred = fixit_felix_runtime._GroundHogDay_run_idat_prefinal_seed_routes_runtime(
        runtime,
        data,
        analysis,
        (initial,),
    )

    assert result is None
    assert seeds == (stored_seed,)
    assert deferred is False
    assert calls == [("stored", (1,)), ("row-after-stored", (2,)), ("stored", (2,))]
    assert any("checkpoint interval reached after batch 1" in note for note in runtime.side_notes)
    assert any("stopped after batch 2: no stronger seed" in note for note in runtime.side_notes)
    assert any("plateau checkpoint saved" in note for note in runtime.side_notes)
    assert any("true plateau" in note for note in runtime.side_notes)
    resume_path = tmp_path / "Folder_Flag" / "Debug_Payloads" / "Flag_groundhogday.resume.json"
    assert resume_path.is_file()
    assert json.loads(resume_path.read_text(encoding="utf-8"))["best"]["state_id"] == 2
    assert any("saved preview/resume artifacts" in call[1] for call in candy_calls)
    assert any("last-resort handoff" in call[1] for call in candy_calls)
    assert [call for call in candy_calls if call[0] == "Title"] == [
        ("Title", "GroundHogDay 1: probe_idat_stored_block_length_repair"),
        ("Title", "GroundHogDay 1: probe_idat_png_filter_literal_repair"),
        ("Title", "GroundHogDay 2: probe_idat_stored_block_length_repair"),
    ]


def test_GroundHogDay_seed_routes_handoff_to_final_after_batch_plateau(monkeypatch):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    initial = idat_progress_seed(
        data,
        state_id=1,
        usable_scanlines=0,
        decompressed_size=100,
        kind="initial",
    )
    first = idat_progress_seed(
        data,
        state_id=2,
        usable_scanlines=1,
        decompressed_size=200,
        kind="first-batch",
    )
    second = idat_progress_seed(
        data,
        state_id=3,
        usable_scanlines=2,
        decompressed_size=300,
        kind="second-batch",
    )
    calls = []
    alternating_outputs = [(None, (first,)), (None, (second,)), (None, ())]

    def fake_alternating(_runtime, _data, _analysis, seed_candidates=(), _title_counter=None):
        calls.append(("alternating", tuple(seed.state_id for seed in seed_candidates)))
        return alternating_outputs.pop(0)

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_GroundHogDay_run_idat_prefinal_alternating_repair_runtime",
        fake_alternating,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_filter_alignment_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_filter_seed_stored_block_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_groundhogday_linefeed_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    candy_calls = []
    runtime = SimpleNamespace(
        side_notes=[],
        candy=lambda *args, **_kwargs: candy_calls.append(args),
        prefinal_repair_batches=1,
        prefinal_repair_cycles=2,
    )

    result, seeds, deferred = fixit_felix_runtime._GroundHogDay_run_idat_prefinal_seed_routes_runtime(
        runtime,
        data,
        analysis,
        (initial,),
    )

    assert result is None
    assert seeds == (second,)
    assert deferred is False
    assert calls == [
        ("alternating", (1,)),
        ("alternating", (2,)),
        ("alternating", (3,)),
    ]
    assert any("batch 2 continuing" in note for note in runtime.side_notes)
    assert any("batch 3 continuing" in note for note in runtime.side_notes)
    assert any("checkpoint interval reached after batch 1" in note for note in runtime.side_notes)
    assert any("checkpoint interval reached after batch 2" in note for note in runtime.side_notes)
    assert any("stopped after batch 3: no stronger seed" in note for note in runtime.side_notes)
    assert any("true plateau" in note for note in runtime.side_notes)
    assert any(
        call[0] == "Cowsay" and "continuing batch 2" in call[1]
        for call in candy_calls
    )
    assert any(
        call[0] == "Cowsay" and "checkpoint batch 1" in call[1]
        for call in candy_calls
    )
    assert any(
        call[0] == "Cowsay" and "last-resort handoff" in call[1]
        for call in candy_calls
    )


def test_GroundHogDay_seed_routes_continue_while_checkpointed_route_is_open(monkeypatch):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    initial = idat_progress_seed(
        data,
        state_id=1,
        usable_scanlines=0,
        decompressed_size=100,
        kind="initial",
    )
    calls = []

    def fake_alternating(_runtime, _data, _analysis, seed_candidates=(), _title_counter=None):
        calls.append(("alternating", tuple(seed.state_id for seed in seed_candidates)))
        return None, ()

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_GroundHogDay_run_idat_prefinal_alternating_repair_runtime",
        fake_alternating,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_filter_alignment_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_filter_seed_stored_block_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_groundhogday_linefeed_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_GroundHogDay_open_route_reasons",
        lambda *_args, **_kwargs: ("MiniUltimate linefeed checkpoint",),
    )
    candy_calls = []
    runtime = SimpleNamespace(
        side_notes=[],
        candy=lambda *args, **_kwargs: candy_calls.append(args),
        prefinal_repair_batches=2,
        prefinal_repair_cycles=1,
        deep_beam_prompt_cache={},
    )

    result, seeds, deferred = fixit_felix_runtime._GroundHogDay_run_idat_prefinal_seed_routes_runtime(
        runtime,
        data,
        analysis,
        (initial,),
    )

    assert result is None
    assert seeds == (initial,)
    assert deferred is True
    assert calls == [
        ("alternating", (1,)),
        ("alternating", (1,)),
        ("alternating", (1,)),
    ]
    assert any("route(s) remain open" in note for note in runtime.side_notes)
    assert any("paused with open route" in note for note in runtime.side_notes)
    assert any(
        call[0] == "Cowsay" and "continuing instead of handing off" in call[1]
        for call in candy_calls
    )
    assert any(
        call[0] == "Cowsay" and "leaving the checkpoint active" in call[1]
        for call in candy_calls
    )


def test_GroundHogDay_title_runtime_prefixes_and_preserves_existing_titles():
    calls = []
    runtime = SimpleNamespace(
        candy=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    title_counter = [1]
    wrapped = fixit_felix_runtime._GroundHogDay_next_title_runtime(
        runtime,
        title_counter,
        seed_local_continuation_rounds=1,
    )

    wrapped.candy("Title", "probe_one")
    wrapped.candy("Title", "GroundHogDay 9: already_prefixed")
    wrapped.candy("Title", "probe_two")
    fixit_felix_runtime._GroundHogDay_advance_day(title_counter)
    wrapped.candy("Title", "probe_three")

    assert wrapped.seed_local_continuation_rounds == 1
    quote_one_mood, quote_one_text = fixit_felix_runtime.GROUNDHOGDAY_QUOTES[0]
    quote_two_mood, quote_two_text = fixit_felix_runtime.GROUNDHOGDAY_QUOTES[1]
    assert calls == [
        (("Cowsay", "GroundHog Day part 1:\n\n%s" % quote_one_text, quote_one_mood), {}),
        (("Title", "GroundHogDay 1: probe_one"), {}),
        (("Title", "GroundHogDay 9: already_prefixed"), {}),
        (("Title", "GroundHogDay 1: probe_two"), {}),
        (("Cowsay", "GroundHog Day part 2:\n\n%s" % quote_two_text, quote_two_mood), {}),
        (("Title", "GroundHogDay 2: probe_three"), {}),
    ]


def test_GroundHogDay_day_quote_uses_hardcoded_table_once_per_day():
    calls = []
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir="",
        side_notes=[],
        candy=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    title_counter = [1]

    fixit_felix_runtime._GroundHogDay_emit_day_quote(runtime, title_counter)
    fixit_felix_runtime._GroundHogDay_emit_day_quote(runtime, title_counter)
    fixit_felix_runtime._GroundHogDay_advance_day(title_counter)
    fixit_felix_runtime._GroundHogDay_emit_day_quote(runtime, title_counter)
    fixit_felix_runtime._GroundHogDay_advance_day(title_counter)
    fixit_felix_runtime._GroundHogDay_emit_day_quote(runtime, title_counter)

    quote_one_mood, quote_one_text = fixit_felix_runtime.GROUNDHOGDAY_QUOTES[0]
    quote_two_mood, quote_two_text = fixit_felix_runtime.GROUNDHOGDAY_QUOTES[1]
    quote_three_mood, quote_three_text = fixit_felix_runtime.GROUNDHOGDAY_QUOTES[2]
    assert calls == [
        (("Cowsay", "GroundHog Day part 1:\n\n%s" % quote_one_text, quote_one_mood), {}),
        (("Cowsay", "GroundHog Day part 2:\n\n%s" % quote_two_text, quote_two_mood), {}),
        (("Cowsay", "GroundHog Day part 3:\n\n%s" % quote_three_text, quote_three_mood), {}),
    ]


def test_GroundHogDay_day_quote_label_uses_day_number_after_quote_wrap():
    calls = []
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir="",
        side_notes=[],
        candy=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    title_counter = [68]

    fixit_felix_runtime._GroundHogDay_emit_day_quote(runtime, title_counter)

    quote_index = ((68 - 1) % len(fixit_felix_runtime.GROUNDHOGDAY_QUOTES))
    quote_mood, quote_text = fixit_felix_runtime.GROUNDHOGDAY_QUOTES[quote_index]
    assert calls == [
        (("Cowsay", "GroundHog Day part 68:\n\n%s" % quote_text, quote_mood), {}),
    ]


def test_GroundHogDay_day_quote_is_emitted_after_intro_before_first_title():
    calls = []
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir="",
        side_notes=[],
        candy=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    title_counter = [4]

    wrapped = fixit_felix_runtime._GroundHogDay_next_title_runtime(runtime, title_counter)
    wrapped.candy(
        "Cowsay",
        "I have stronger IDAT seeds now, so I am probing locally around their current deflate wound before Punxsutawney Phil's shadow finder.",
        "bad",
    )
    fixit_felix_runtime._GroundHogDay_emit_quote_before_title(wrapped)
    wrapped.candy("Title", "probe_idat_seed_local_continuation")

    quote_mood, quote_text = fixit_felix_runtime.GROUNDHOGDAY_QUOTES[3]
    assert calls == [
        (
            (
                "Cowsay",
                "I have stronger IDAT seeds now, so I am probing locally around their current deflate wound before Punxsutawney Phil's shadow finder.",
                "bad",
            ),
            {},
        ),
        (("Cowsay", "GroundHog Day part 4:\n\n%s" % quote_text, quote_mood), {}),
        (("Title", "GroundHogDay 4: probe_idat_seed_local_continuation"), {}),
    ]


def test_shadow_finder_ready_when_groundhogday_seed_exists_without_final_config():
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed = idat_progress_seed(
        data,
        state_id=32,
        usable_scanlines=2,
        decompressed_size=300,
        kind="groundhogday-seed",
    )
    runtime = SimpleNamespace(
        file_origin="",
        file_dir="",
        side_notes=[],
    )

    assert fixit_felix_runtime._should_run_final_investigation(
        runtime,
        analysis,
        (seed,),
        evidence_ready=False,
    )


def test_GroundHogDay_defer_writes_resume_state(tmp_path):
    data = bad_adler_three_scanline_png_bytes()
    seed = idat_deep_beam_seed(
        data,
        state_id=17,
        kind="groundhogday-resume",
    )
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
    )

    result = fixit_felix_runtime._GroundHogDay_defer_final_investigation_after_local_progress(
        runtime,
        (seed,),
        data=data,
    )

    assert result is True
    resume_path = tmp_path / "Folder_Flag" / "Debug_Payloads" / "Flag_groundhogday.resume.json"
    payload = json.loads(resume_path.read_text(encoding="utf-8"))
    assert payload["route"] == "GroundHogDay"
    assert payload["source_hash"] == fixit_felix_runtime._GroundHogDay_source_hash(data)
    assert payload["next_day"] == 1
    assert payload["best"]["usable_scanlines"] == 3
    assert payload["best"]["complete_scanlines"] == 3
    assert any("GroundHogDay resume state saved" in note for note in runtime.side_notes)
    payload_folder = tmp_path / "Folder_Flag" / "Debug_Payloads"
    preview_folder = payload_folder / fixit_felix_runtime.GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER
    seed_paths = tuple(payload_folder.glob("Flag_groundhogday_seed_state17_*.png"))
    preview_paths = tuple(preview_folder.glob("Flag_groundhogday_scanline_preview_state17_*_3_of_3.png"))
    metadata_paths = tuple(payload_folder.glob("Flag_groundhogday_preview_state17_*.json"))
    assert len(seed_paths) == 1
    assert len(preview_paths) == 1
    assert len(metadata_paths) == 1
    assert seed_paths[0].read_bytes() == data
    preview_data = preview_paths[0].read_bytes()
    assert validate_png_structure(preview_data).ok
    preview_analysis = idat.analyze_idat_stream(preview_data)
    assert preview_analysis.complete is True
    metadata = json.loads(metadata_paths[0].read_text(encoding="utf-8"))
    assert metadata["route"] == "GroundHogDay"
    assert metadata["seed_artifact"] == seed_paths[0].name
    assert metadata["scanline_preview"] == "%s/%s" % (
        fixit_felix_runtime.GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER,
        preview_paths[0].name,
    )
    assert metadata["best"]["usable_scanlines"] == 3
    assert any("GroundHogDay preview artifacts" in note for note in runtime.side_notes)


def test_GroundHogDay_preview_artifacts_include_tolerant_complete_rows(tmp_path):
    data = bad_adler_three_scanline_one_bad_filter_png_bytes()
    seed = idat_deep_beam_seed(
        data,
        state_id=19,
        kind="groundhogday-resume",
    )
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
    )

    fixit_felix_runtime._GroundHogDay_write_resume_state(runtime, data, (seed,))

    payload_folder = tmp_path / "Folder_Flag" / "Debug_Payloads"
    preview_folder = payload_folder / fixit_felix_runtime.GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER
    preview_paths = tuple(preview_folder.glob("Flag_groundhogday_scanline_preview_state19_*_2_of_3.png"))
    tolerant_paths = tuple(preview_folder.glob("Flag_groundhogday_tolerant_preview_state19_*_3_complete_of_3.png"))
    metadata_paths = tuple(payload_folder.glob("Flag_groundhogday_preview_state19_*.json"))
    assert len(preview_paths) == 1
    assert len(tolerant_paths) == 1
    assert len(metadata_paths) == 1
    assert validate_png_structure(preview_paths[0].read_bytes()).ok
    assert validate_png_structure(tolerant_paths[0].read_bytes()).ok
    metadata = json.loads(metadata_paths[0].read_text(encoding="utf-8"))
    assert metadata["scanline_preview"] == "%s/%s" % (
        fixit_felix_runtime.GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER,
        preview_paths[0].name,
    )
    assert metadata["tolerant_preview"] == "%s/%s" % (
        fixit_felix_runtime.GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER,
        tolerant_paths[0].name,
    )
    assert metadata["best"]["usable_scanlines"] == 2
    assert metadata["best"]["complete_scanlines"] == 3


def test_GroundHogDay_seed_artifact_is_resume_artifact_path(tmp_path):
    data = bad_adler_three_scanline_png_bytes()
    seed = idat_deep_beam_seed(data, state_id=18, kind="groundhogday-resume")
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
    )

    fixit_felix_runtime._GroundHogDay_write_resume_state(runtime, data, (seed,))

    artifact_paths = fixit_felix_runtime._final_investigation_artifact_paths(runtime)
    names = {path.name for path in artifact_paths}
    assert any(name.startswith("Flag_groundhogday_seed_state18_") for name in names)
    assert not any("scanline_preview" in name for name in names)


def test_GroundHogDay_resume_state_next_day_keeps_title_counter(monkeypatch, tmp_path):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=10,
        expected_size=1000,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed = idat_progress_seed(
        data,
        state_id=68,
        usable_scanlines=3,
        decompressed_size=400,
        kind="groundhogday-resume",
    )
    payload_folder = tmp_path / "Folder_Flag" / "Debug_Payloads"
    payload_folder.mkdir(parents=True)
    resume_path = payload_folder / "Flag_groundhogday.resume.json"
    resume_path.write_text(
        json.dumps(
            {
                "route": "GroundHogDay",
                "version": 1,
                "source_hash": fixit_felix_runtime._GroundHogDay_source_hash(data),
                "next_day": 68,
                "seed_count": 1,
                "best": {},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    calls = []

    def fake_seed_local(_runtime, _data, _analysis, seed_candidates=()):
        _runtime.candy("Title", "probe_idat_seed_local_continuation")
        return None, ()

    def fake_row_filter(_runtime, _data, _analysis, seed_candidates=()):
        _runtime.candy("Title", "probe_idat_png_filter_literal_repair")
        return None, ()

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_seed_local_continuation_runtime",
        fake_seed_local,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_row_filter_literal_repair_runtime",
        fake_row_filter,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_filter_alignment_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_groundhogday_linefeed_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_filter_seed_stored_block_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=[],
        candy=lambda *args, **_kwargs: calls.append(args),
        prefinal_repair_cycles=1,
        prefinal_repair_batches=1,
        seed_local_continuation_limit=1,
    )

    result, seeds, deferred = fixit_felix_runtime._GroundHogDay_run_idat_prefinal_seed_routes_runtime(
        runtime,
        data,
        analysis,
        (seed,),
    )

    assert result is None
    assert seeds == (seed,)
    assert deferred is False
    assert [call for call in calls if call[0] == "Title"][:2] == [
        ("Title", "GroundHogDay 68: probe_idat_seed_local_continuation"),
        ("Title", "GroundHogDay 68: probe_idat_png_filter_literal_repair"),
    ]
    updated = json.loads(resume_path.read_text(encoding="utf-8"))
    assert updated["next_day"] >= 68


def test_GroundHogDay_resume_next_day_infers_from_debug_payloads(tmp_path):
    data = valid_png_bytes()
    payload_folder = tmp_path / "Folder_Flag" / "Debug_Payloads"
    payload_folder.mkdir(parents=True)
    resume_path = payload_folder / "Flag_groundhogday.resume.json"
    resume_path.write_text(
        json.dumps(
            {
                "route": "GroundHogDay",
                "version": 1,
                "source_hash": fixit_felix_runtime._GroundHogDay_source_hash(data),
                "seed_count": 1,
                "best": {},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for index in range(3):
        (payload_folder / ("Flag_groundhogday_preview_state%s_deadbeef.json" % index)).write_text(
            "{}\n",
            encoding="utf-8",
        )
    for index in range(5):
        (payload_folder / ("Flag_groundhogday_state99_linefeed_chain_round%s.png" % index)).write_bytes(
            b""
        )
    preview_folder = payload_folder / fixit_felix_runtime.GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER
    preview_folder.mkdir()
    for index in range(2):
        (
            preview_folder
            / (
                "Flag_groundhogday_scanline_preview_state%s_deadbeef_%s_of_850.png"
                % (index, index)
            )
        ).write_bytes(b"")
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=[],
    )

    assert fixit_felix_runtime._GroundHogDay_resume_next_day(runtime, data) == 6
    assert any(
        "linefeed_chain_artifacts=5" in note and "next_day=6" in note
        for note in runtime.side_notes
    )


def test_GroundHogDay_resume_next_day_infers_from_debug_payloads_when_resume_source_is_stale(tmp_path):
    data = valid_png_bytes()
    payload_folder = tmp_path / "Folder_Flag" / "Debug_Payloads"
    payload_folder.mkdir(parents=True)
    resume_path = payload_folder / "Flag_groundhogday.resume.json"
    resume_path.write_text(
        json.dumps(
            {
                "route": "GroundHogDay",
                "version": 1,
                "source_hash": "stale-source",
                "next_day": 1,
                "seed_count": 1,
                "best": {},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for index in range(8):
        (payload_folder / ("Flag_groundhogday_seed_state%s_deadbeef.png" % index)).write_bytes(
            b""
        )
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=[],
    )

    assert fixit_felix_runtime._GroundHogDay_resume_next_day(runtime, data) == 9
    assert any(
        "despite missing/stale resume source marker" in note and "next_day=9" in note
        for note in runtime.side_notes
    )


def test_GroundHogDay_resume_next_day_raises_stale_saved_counter(tmp_path):
    data = valid_png_bytes()
    payload_folder = tmp_path / "Folder_Flag" / "Debug_Payloads"
    payload_folder.mkdir(parents=True)
    resume_path = payload_folder / "Flag_groundhogday.resume.json"
    resume_path.write_text(
        json.dumps(
            {
                "route": "GroundHogDay",
                "version": 1,
                "source_hash": fixit_felix_runtime._GroundHogDay_source_hash(data),
                "next_day": 2,
                "seed_count": 1,
                "best": {},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for index in range(5):
        (payload_folder / ("Flag_groundhogday_seed_state%s_deadbeef.png" % index)).write_bytes(
            b""
        )
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        side_notes=[],
    )

    assert fixit_felix_runtime._GroundHogDay_resume_next_day(runtime, data) == 6
    assert any(
        "raised from saved next_day=2 to inferred next_day=6" in note
        for note in runtime.side_notes
    )


def test_post_deep_runs_seed_local_after_incomplete_stored_block(monkeypatch):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed = idat_deep_beam_seed(data, state_id=7, kind="post-deep")
    stored_result = _stored_block_candidate_result(complete=False)
    calls = []

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_kraft_backref_runtime",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_stored_block_runtime",
        lambda *_args, **_kwargs: stored_result,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_row_filter_literal_repair_runtime",
        lambda *_args, **_kwargs: (None, ()),
    )

    def fake_seed_local(_runtime, _data, _analysis, seed_candidates=()):
        calls.append(tuple(seed_candidates))
        return (True, "seed-local-written"), ()

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_seed_local_continuation_runtime",
        fake_seed_local,
    )
    runtime = SimpleNamespace(
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        write_clone=lambda *_args, **_kwargs: "written",
    )

    result = fixit_felix_runtime._run_idat_post_deep_frontier_routes_runtime(
        runtime,
        data,
        analysis,
        (seed,),
    )

    assert result == (True, "seed-local-written")
    assert calls
    assert calls[-1] == stored_result.top_candidates


def test_post_deep_runs_seed_local_after_direct_row_filter_progress(monkeypatch):
    data = valid_png_bytes()
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=4,
        expected_size=200,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=5,
    )
    seed = idat_progress_seed(
        data,
        state_id=7,
        usable_scanlines=0,
        decompressed_size=100,
        kind="post-deep",
    )
    row_seed = idat_progress_seed(
        data,
        state_id=8,
        usable_scanlines=1,
        decompressed_size=200,
        kind="png-filter-literal-repair",
    )
    calls = []

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_kraft_backref_runtime",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_stored_block_runtime",
        lambda *_args, **_kwargs: None,
    )

    def fake_row_filter(_runtime, _data, _analysis, seed_candidates=()):
        calls.append(("row-filter", tuple(seed_candidates)))
        return None, (row_seed,)

    seed_local_outputs = [(None, ()), ((True, "seed-local-written"), ())]

    def fake_seed_local(_runtime, _data, _analysis, seed_candidates=()):
        calls.append(("seed-local", tuple(seed_candidates)))
        return seed_local_outputs.pop(0)

    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_row_filter_literal_repair_runtime",
        fake_row_filter,
    )
    monkeypatch.setattr(
        fixit_felix_runtime,
        "_run_idat_seed_local_continuation_runtime",
        fake_seed_local,
    )
    runtime = SimpleNamespace(
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        write_clone=lambda *_args, **_kwargs: "written",
    )

    result = fixit_felix_runtime._run_idat_post_deep_frontier_routes_runtime(
        runtime,
        data,
        analysis,
        (seed,),
    )

    assert result == (True, "seed-local-written")
    assert calls[0] == ("seed-local", (seed,))
    assert calls[1] == ("row-filter", (seed,))
    assert calls[2] == ("seed-local", (row_seed,))


def test_final_investigation_paths_reuse_existing_repair_folder_for_debug_artifact_origin(tmp_path):
    payload = tmp_path / "Folder_Flag" / "Debug_Payloads"
    payload.mkdir(parents=True)
    artifact = payload / "Flag_idat_kraft_backref_deep2_rank01_state1_deadbeef.png"
    artifact.write_bytes(valid_png_bytes())
    runtime = SimpleNamespace(
        file_origin=str(artifact),
        file_dir=str(tmp_path),
        side_notes=[],
    )

    checkpoint_path, progress_path = fixit_felix_runtime._idat_final_investigation_paths(runtime)

    assert Path(checkpoint_path).parent == payload
    assert Path(progress_path).parent == payload
    assert Path(checkpoint_path).name == "Flag_final_investigation.checkpoint.jsonl"
    assert Path(progress_path).name == "Flag_final_investigation.progress.json"
    assert not [path for path in tmp_path.iterdir() if path.name.startswith("Folder_Flag_idat_")]


def test_artifact_seed_candidate_rejects_incompatible_png_geometry(tmp_path):
    artifact = tmp_path / "Flag_groundhogday_seed_state12_deadbeef.png"
    artifact.write_bytes(smooth_gray_png(width=32, height=16))
    before = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        width=640,
        height=850,
        bit_depth=8,
        color_type=0,
        expected_size=640 * 850 + 850,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=110,
    )

    candidate = fixit_felix_runtime._artifact_idat_seed_candidate(
        artifact,
        before,
        original_idat_count=25,
        state_id=12,
    )

    assert candidate is None


def test_final_investigation_paths_normalize_misnamed_fixed_clone_folder(tmp_path):
    payload = tmp_path / "Folder_Flag.3_Fixed" / "Debug_Payloads"
    payload.mkdir(parents=True)
    artifact = payload / "Flag_idat_kraft_backref_deep2_rank01_state1_deadbeef.png"
    artifact.write_bytes(valid_png_bytes())
    runtime = SimpleNamespace(
        file_origin=str(artifact),
        file_dir=str(tmp_path),
        side_notes=[],
    )

    checkpoint_path, progress_path = fixit_felix_runtime._idat_final_investigation_paths(runtime)

    assert Path(checkpoint_path).parent == tmp_path / "Folder_Flag" / "Debug_Payloads"
    assert Path(progress_path).parent == tmp_path / "Folder_Flag" / "Debug_Payloads"
    assert Path(checkpoint_path).name == "Flag_final_investigation.checkpoint.jsonl"
    assert Path(progress_path).name == "Flag_final_investigation.progress.json"


def test_final_investigation_uses_workers_gpu_checkpoint_and_minibar_eta(tmp_path):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.analyze_idat_stream(data)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    seed = idat_bruteforce._frontier_root_candidate(
        data=data,
        stream=stream,
        before=analysis,
        original_idat_count=sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT"),
    )
    calls = []
    side_notes = []
    captured = {}
    gpu_config = fixit_felix_runtime.gpu_runtime.GpuRuntimeConfig(
        enabled=True,
        backend="opengl",
    )
    original_probe = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam

    def fake_probe(data_arg, **kwargs):
        captured["data"] = data_arg
        captured.update(kwargs)
        kwargs["progress"]("final-investigation", 50, 100)
        return idat_bruteforce.IdatDeepBeamProbeResult(
            before=analysis,
            best=None,
            top_candidates=(),
            window_start=0,
            window_end=len(stream),
            tested_candidates=100,
            budget_exhausted=True,
            reached_depth=4,
            state_count=5,
            visited_count=6,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            workers=3,
            gpu_requested=True,
            gpu_backend="opengl",
            reason="budget exhausted",
        )

    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        data_hex=data.hex(),
        side_notes=side_notes,
        candy=lambda *args, **kwargs: calls.append(("candy", args, kwargs)),
        write_clone=lambda *_args: "written",
        minibar=lambda *args, **kwargs: calls.append(("minibar", args, kwargs)),
        loadingbar=None,
        preview_repair_image=None,
        interactive=False,
        input_func=None,
        deep_beam_workers="3",
        deep_beam_gpu=True,
        deep_beam_gpu_config=gpu_config,
        deep_beam_budget="9",
        final_investigation_budget="77",
        final_investigation_max_depth="11",
        final_investigation_seed_limit="5",
        deep_beam_gpu_shard_size="13",
        deep_beam_cpu_batch_size="17",
        deep_beam_prompt_cache={},
    )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = fake_probe
        result = fixit_felix_runtime._run_idat_final_investigation_runtime(
            runtime,
            data,
            analysis,
            seed_candidates=(seed,),
        )
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = original_probe

    assert result is None
    assert captured["data"] == data
    assert captured["budget"] == 77
    assert captured["max_depth"] == 11
    assert captured["workers"] == 3
    assert captured["gpu"] is True
    assert captured["gpu_config"] == gpu_config
    assert captured["gpu_shard_size"] == 13
    assert captured["cpu_batch_size"] == 17
    assert captured["overlap_gpu_cpu"] is True
    assert Path(captured["checkpoint_path"]).parent == tmp_path / "Folder_Flag" / "Debug_Payloads"
    assert Path(captured["checkpoint_path"]).name == "Flag_final_investigation.checkpoint.jsonl"
    minibar_calls = [call for call in calls if call[0] == "minibar"]
    assert minibar_calls
    assert "IDAT %s" % fixit_felix_runtime.FINAL_INVESTIGATION_LABEL in minibar_calls[0][2]["Indication"]
    assert "eta=" in minibar_calls[0][2]["Indication"]
    assert any("route left open" in note for note in side_notes)


def test_final_investigation_eta_formats_days_hours_minutes_seconds():
    assert fixit_felix_runtime._format_eta_seconds(None) == "--j --h --m --s"
    assert fixit_felix_runtime._format_eta_seconds(5) == "0j 00h 00m 05s"
    assert fixit_felix_runtime._format_eta_seconds(90061) == "1j 01h 01m 01s"


def test_final_investigation_hands_partial_candidates_back_to_groundhogday(tmp_path, monkeypatch):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.analyze_idat_stream(data)
    seed = idat_progress_seed(
        data,
        state_id=42,
        usable_scanlines=1,
        decompressed_size=30,
        kind="final-partial",
    )
    calls = []
    side_notes = []

    def fake_probe(_data, **kwargs):
        return idat_bruteforce.IdatDeepBeamProbeResult(
            before=analysis,
            best=None,
            top_candidates=(seed,),
            window_start=0,
            window_end=1,
            tested_candidates=10,
            budget_exhausted=False,
            reached_depth=1,
            state_count=2,
            visited_count=1,
            checkpoint_path=kwargs["checkpoint_path"],
            progress_path=kwargs["progress_path"],
            reason="partial evidence",
        )

    monkeypatch.setattr(
        fixit_felix_runtime.idat_bruteforce,
        "probe_idat_deflate_deep_beam",
        fake_probe,
    )
    runtime = SimpleNamespace(
        file_origin="Flag.png",
        file_dir=str(tmp_path),
        data_hex=data.hex(),
        side_notes=side_notes,
        candy=lambda *args, **kwargs: calls.append(("candy", args, kwargs)),
        write_clone=lambda *_args: "written",
        minibar=None,
        loadingbar=None,
        preview_repair_image=None,
        interactive=False,
        input_func=None,
        deep_beam_workers="1",
        deep_beam_gpu=False,
        deep_beam_gpu_config=None,
        final_investigation_budget="77",
        final_investigation_max_depth="11",
        final_investigation_seed_limit="5",
        deep_beam_prompt_cache={},
    )

    result = fixit_felix_runtime._run_idat_final_investigation_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=(seed,),
    )

    resume_path = tmp_path / "Folder_Flag" / "Debug_Payloads" / "Flag_groundhogday.resume.json"
    assert result is None
    assert resume_path.is_file()
    payload = json.loads(resume_path.read_text(encoding="utf-8"))
    assert payload["route"] == "GroundHogDay"
    assert payload["best"]["state_id"] == 42
    assert any("handed checkpointed candidate" in note for note in side_notes)
    assert any(
        call[0] == "candy" and "GroundHogDay will use those saved seeds" in call[1][1]
        for call in calls
    )


def test_try_idat_deflate_runs_final_investigation_after_strategy_queue_stalls():
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=2,
        decompressed_size=12,
        usable_scanlines=1,
        error_offset=6,
    )
    calls = []
    original_prefix = fixit_felix_runtime._run_idat_prefix_frontier_routes_runtime
    original_queue = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue
    original_final = fixit_felix_runtime._run_idat_final_investigation_runtime

    def fake_queue(*_args, **kwargs):
        calls.append(("queue", kwargs))
        return SimpleNamespace(
            best=None,
            strategy="strategy-queue",
            window_start=0,
            window_end=1,
            tested_candidates=0,
            budget_exhausted=False,
            reason="none",
        )

    def fake_final(runtime_arg, data_arg, analysis_arg, *, seed_candidates=()):
        calls.append(("final", data_arg, analysis_arg, seed_candidates))
        return True, "final-written"

    runtime = SimpleNamespace(
        data_hex=data.hex(),
        side_notes=[],
        candy=lambda *_args, **_kwargs: None,
        question=lambda *_args, **_kwargs: False,
        write_clone=lambda *_args, **_kwargs: "written",
        remember_idat_deflate_probe=lambda _analysis: True,
        file_origin="",
        file_dir="",
        loadingbar=None,
        minibar=None,
        deep_beam_workers=None,
        deep_beam_gpu=None,
        deep_beam_gpu_config=None,
        deep_beam_budget=None,
        final_investigation_budget="100",
        deep_beam_prompt_cache={},
    )

    try:
        fixit_felix_runtime._run_idat_prefix_frontier_routes_runtime = lambda *_args, **_kwargs: None
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = fake_queue
        fixit_felix_runtime._run_idat_final_investigation_runtime = fake_final
        result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)
    finally:
        fixit_felix_runtime._run_idat_prefix_frontier_routes_runtime = original_prefix
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = original_queue
        fixit_felix_runtime._run_idat_final_investigation_runtime = original_final

    assert result == (True, "final-written")
    assert calls[0][0] == "queue"
    assert calls[0][1]["max_steps"] == 16
    assert calls[1][0] == "final"


def test_try_idat_deflate_defers_final_when_prefinal_routes_progress(monkeypatch):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=2,
        decompressed_size=12,
        usable_scanlines=1,
        error_offset=6,
    )
    seed = idat_deep_beam_seed(data, state_id=9, kind="local-progress")
    calls = []
    side_notes = []

    def fake_queue(*_args, **kwargs):
        calls.append(("queue", kwargs))
        return SimpleNamespace(
            best=None,
            strategy="strategy-queue",
            window_start=0,
            window_end=1,
            tested_candidates=0,
            budget_exhausted=False,
            reason="none",
        )

    def fake_prefinal(*_args, **_kwargs):
        calls.append(("prefinal",))
        side_notes.append(
            "-IDAT %s deferred: mocked prefinal progress."
            % fixit_felix_runtime.FINAL_INVESTIGATION_LABEL
        )
        return None, (seed,), True

    def fake_final(*_args, **_kwargs):
        calls.append(("final",))
        return True, "final-written"

    runtime = SimpleNamespace(
        data_hex=data.hex(),
        side_notes=side_notes,
        candy=lambda *args, **kwargs: calls.append(("candy", args, kwargs)),
        question=lambda *_args, **_kwargs: False,
        write_clone=lambda *_args, **_kwargs: "written",
        remember_idat_deflate_probe=lambda _analysis: True,
        file_origin="",
        file_dir="",
        loadingbar=None,
        minibar=None,
        deep_beam_workers=None,
        deep_beam_gpu=None,
        deep_beam_gpu_config=None,
        deep_beam_budget=None,
        final_investigation_budget="100",
        deep_beam_prompt_cache={},
    )

    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_prefix_frontier_routes_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_strategy_queue", fake_queue)
    monkeypatch.setattr(fixit_felix_runtime, "_GroundHogDay_run_idat_prefinal_seed_routes_runtime", fake_prefinal)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_final_investigation_runtime", fake_final)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result is None
    assert [call[0] for call in calls if call[0] in {"queue", "prefinal", "final"}] == ["queue", "prefinal"]
    assert any(fixit_felix_runtime.FINAL_INVESTIGATION_LABEL in note and "deferred" in note for note in side_notes)


def test_try_idat_deflate_resumes_groundhogday_before_replaying_idat_probes(monkeypatch):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=2,
        decompressed_size=12,
        usable_scanlines=1,
        error_offset=6,
    )
    seed = idat_progress_seed(
        data,
        state_id=23,
        usable_scanlines=2,
        decompressed_size=40,
        kind="groundhogday-resume",
    )
    calls = []
    side_notes = []

    def fake_resume_seeds(_runtime, _data, _analysis):
        calls.append(("resume-seeds",))
        return (seed,)

    def fake_prefinal(_runtime, _data, _analysis, seed_candidates=()):
        calls.append(("prefinal", tuple(candidate.state_id for candidate in seed_candidates)))
        side_notes.append(
            "-IDAT %s deferred: mocked GroundHogDay resume progress."
            % fixit_felix_runtime.FINAL_INVESTIGATION_LABEL
        )
        return None, (seed,), True

    def fail_if_replayed(*_args, **_kwargs):
        raise AssertionError("older IDAT probes should not replay before GroundHogDay resume")

    def fail_if_remembered(_analysis):
        raise AssertionError("exact wound guard should not block GroundHogDay resume")

    runtime = SimpleNamespace(
        data_hex=data.hex(),
        side_notes=side_notes,
        candy=lambda *args, **kwargs: calls.append(("candy", args, kwargs)),
        question=lambda *_args, **_kwargs: False,
        write_clone=lambda *_args, **_kwargs: "written",
        remember_idat_deflate_probe=fail_if_remembered,
        file_origin="",
        file_dir="",
        loadingbar=None,
        minibar=None,
        deep_beam_workers=None,
        deep_beam_gpu=None,
        deep_beam_gpu_config=None,
        deep_beam_budget=None,
        final_investigation_budget=None,
        deep_beam_prompt_cache={},
    )

    monkeypatch.setattr(fixit_felix_runtime, "_GroundHogDay_resume_seed_candidates", fake_resume_seeds)
    monkeypatch.setattr(fixit_felix_runtime, "_GroundHogDay_run_idat_prefinal_seed_routes_runtime", fake_prefinal)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_frontier_routes_runtime", fail_if_replayed)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_prefix_frontier_routes_runtime", fail_if_replayed)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_strategy_queue", fail_if_replayed)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result is None
    assert [call[0] for call in calls if call[0] in {"resume-seeds", "prefinal"}] == [
        "resume-seeds",
        "prefinal",
    ]
    assert [call for call in calls if call[0] == "prefinal"] == [("prefinal", (23,))]
    assert any("GroundHogDay resume-first" in note for note in side_notes)
    assert any(
        call[0] == "candy" and "jumping back to that loop" in call[1][1]
        for call in calls
    )
    assert any(fixit_felix_runtime.FINAL_INVESTIGATION_LABEL in note and "deferred" in note for note in side_notes)


def test_try_idat_deflate_groundhogday_resume_no_progress_runs_shadow_finder(monkeypatch):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=2,
        decompressed_size=12,
        usable_scanlines=1,
        error_offset=6,
    )
    seed = idat_progress_seed(
        data,
        state_id=24,
        usable_scanlines=2,
        decompressed_size=40,
        kind="groundhogday-resume",
    )
    calls = []
    side_notes = []

    def fake_prefinal(_runtime, _data, _analysis, seed_candidates=()):
        calls.append(("prefinal", tuple(candidate.state_id for candidate in seed_candidates)))
        return None, seed_candidates, False

    def fake_final(_runtime, _data, _analysis, seed_candidates=()):
        calls.append(("final", tuple(candidate.state_id for candidate in seed_candidates)))
        return True, "shadow-written"

    def fail_if_replayed(*_args, **_kwargs):
        raise AssertionError("older IDAT probes should not replay after GroundHogDay resume stalls")

    runtime = SimpleNamespace(
        data_hex=data.hex(),
        side_notes=side_notes,
        candy=lambda *args, **kwargs: calls.append(("candy", args, kwargs)),
        question=lambda *_args, **_kwargs: False,
        write_clone=lambda *_args, **_kwargs: "written",
        remember_idat_deflate_probe=lambda _analysis: True,
        file_origin="",
        file_dir="",
        loadingbar=None,
        minibar=None,
        deep_beam_workers=None,
        deep_beam_gpu=None,
        deep_beam_gpu_config=None,
        deep_beam_budget=None,
        final_investigation_budget=None,
        deep_beam_prompt_cache={},
    )

    monkeypatch.setattr(fixit_felix_runtime, "_GroundHogDay_resume_seed_candidates", lambda *_args: (seed,))
    monkeypatch.setattr(fixit_felix_runtime, "_GroundHogDay_run_idat_prefinal_seed_routes_runtime", fake_prefinal)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_final_investigation_runtime", fake_final)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_frontier_routes_runtime", fail_if_replayed)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_prefix_frontier_routes_runtime", fail_if_replayed)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_strategy_queue", fail_if_replayed)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result == (True, "shadow-written")
    assert [call for call in calls if call[0] in {"prefinal", "final"}] == [
        ("prefinal", (24,)),
        ("final", (24,)),
    ]
    assert any("resume plateau reached" in note for note in side_notes)
    assert any(
        call[0] == "candy" and "last resort" in call[1][1]
        for call in calls
    )


def test_try_idat_deflate_groundhogday_resume_plateau_runs_final_when_ready(monkeypatch):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=2,
        decompressed_size=12,
        usable_scanlines=1,
        error_offset=6,
    )
    seed = idat_progress_seed(
        data,
        state_id=25,
        usable_scanlines=2,
        decompressed_size=40,
        kind="groundhogday-resume",
    )
    calls = []
    side_notes = []

    def fake_prefinal(_runtime, _data, _analysis, seed_candidates=()):
        calls.append(("prefinal", tuple(candidate.state_id for candidate in seed_candidates)))
        return None, seed_candidates, False

    def fake_final(_runtime, _data, _analysis, seed_candidates=()):
        calls.append(("final", tuple(candidate.state_id for candidate in seed_candidates)))
        return True, "final-written"

    def fail_if_replayed(*_args, **_kwargs):
        raise AssertionError("older IDAT probes should not replay after GroundHogDay resume plateau")

    runtime = SimpleNamespace(
        data_hex=data.hex(),
        side_notes=side_notes,
        candy=lambda *args, **kwargs: calls.append(("candy", args, kwargs)),
        question=lambda *_args, **_kwargs: False,
        write_clone=lambda *_args, **_kwargs: "written",
        remember_idat_deflate_probe=lambda _analysis: True,
        file_origin="",
        file_dir="",
        loadingbar=None,
        minibar=None,
        deep_beam_workers=None,
        deep_beam_gpu=None,
        deep_beam_gpu_config=None,
        deep_beam_budget=None,
        final_investigation_budget="100",
        deep_beam_prompt_cache={},
    )

    monkeypatch.setattr(fixit_felix_runtime, "_GroundHogDay_resume_seed_candidates", lambda *_args: (seed,))
    monkeypatch.setattr(fixit_felix_runtime, "_GroundHogDay_run_idat_prefinal_seed_routes_runtime", fake_prefinal)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_final_investigation_runtime", fake_final)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_frontier_routes_runtime", fail_if_replayed)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_prefix_frontier_routes_runtime", fail_if_replayed)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_strategy_queue", fail_if_replayed)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result == (True, "final-written")
    assert [call for call in calls if call[0] in {"prefinal", "final"}] == [
        ("prefinal", (25,)),
        ("final", (25,)),
    ]
    assert any("resume plateau reached" in note for note in side_notes)
    assert any(
        call[0] == "candy" and "last resort" in call[1][1]
        for call in calls
    )


def test_try_idat_deflate_defers_final_when_prefinal_stored_progresses(monkeypatch):
    data = bytes.fromhex(one_byte_corrupt_deflate_png_hex())
    analysis = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        height=2,
        decompressed_size=12,
        usable_scanlines=1,
        error_offset=6,
    )
    seed = idat_deep_beam_seed(data, state_id=11, kind="stored-block-filter-seed")
    calls = []
    side_notes = []

    def fake_queue(*_args, **kwargs):
        calls.append(("queue", kwargs))
        return SimpleNamespace(
            best=None,
            strategy="strategy-queue",
            window_start=0,
            window_end=1,
            tested_candidates=0,
            budget_exhausted=False,
            reason="none",
        )

    def fake_prefinal(*_args, **_kwargs):
        calls.append(("prefinal-stored",))
        side_notes.append(
            "-IDAT %s deferred: mocked stored prefinal progress."
            % fixit_felix_runtime.FINAL_INVESTIGATION_LABEL
        )
        return None, (seed,), True

    def fake_final(*_args, **_kwargs):
        calls.append(("final",))
        return True, "final-written"

    runtime = SimpleNamespace(
        data_hex=data.hex(),
        side_notes=side_notes,
        candy=lambda *args, **kwargs: calls.append(("candy", args, kwargs)),
        question=lambda *_args, **_kwargs: False,
        write_clone=lambda *_args, **_kwargs: "written",
        remember_idat_deflate_probe=lambda _analysis: True,
        file_origin="",
        file_dir="",
        loadingbar=None,
        minibar=None,
        deep_beam_workers=None,
        deep_beam_gpu=None,
        deep_beam_gpu_config=None,
        deep_beam_budget=None,
        final_investigation_budget="100",
        deep_beam_prompt_cache={},
    )

    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_prefix_frontier_routes_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fixit_felix_runtime.idat_bruteforce, "probe_idat_deflate_strategy_queue", fake_queue)
    monkeypatch.setattr(fixit_felix_runtime, "_GroundHogDay_run_idat_prefinal_seed_routes_runtime", fake_prefinal)
    monkeypatch.setattr(fixit_felix_runtime, "_run_idat_final_investigation_runtime", fake_final)

    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)

    assert result is None
    assert [call[0] for call in calls if call[0] in {"queue", "prefinal-stored", "final"}] == [
        "queue",
        "prefinal-stored",
    ]
    assert any(fixit_felix_runtime.FINAL_INVESTIGATION_LABEL in note and "deferred" in note for note in side_notes)


def test_apply_wrong_chunk_name_uses_deflate_probe_when_aligned_stream_is_bad():
    calls = []
    side_notes = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    original_deep = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam

    def no_candidate_deep(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (),
            0,
            1,
            0,
            False,
            0,
            1,
            1,
            strategy="deep-beam",
            reason="mocked",
        )

    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(False,),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
        side_notes=side_notes,
        data_hex=idat_chain_aligned_bad_deflate_hex(),
    )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = no_candidate_deep
        result = fixit_felix_runtime.apply_wrong_chunk_name(
            runtime,
            fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
            chkd,
            wrong_chunk_name_tools(),
        )
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = original_deep

    assert result == (False, None)
    assert [call for call in calls if call[0] == "question"]
    assert [call for call in calls if call[0] == "ancillary"]
    assert not [call for call in calls if call[0] == "brute_chunk"]
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any(note.startswith("-IDAT stream diagnosis: status=corrupt_deflate") for note in side_notes)
    assert "-IDAT deflate header probe found no clone-worthy scanline progress." in side_notes
    assert "-IDAT diagnostic LF route found no clone-worthy scanline progress." in side_notes


def test_apply_wrong_chunk_name_saves_existing_solution():
    calls = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        cornucopia={
            finding: {
                chkd + "0": "fixed-data",
                chkd + "1": 12,
                chkd + "2": 20,
                chkd + "3": "legacy note",
                chkd + "4": "solved label",
            }
        },
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("save_existing_solution", finding, True),
        chkd,
        None,
    )

    assert result == (True, "saved")
    assert calls == [
        ("emit", ("\n-\033[1;32;49mSolved\033[m: solved label",), {}),
        ("save_clone", ("fixed-data", 12, 20, "legacy note"), {}),
    ]


def test_apply_wrong_chunk_name_rejects_missing_tools_for_action():
    runtime = wrong_chunk_name_runtime([])

    try:
        fixit_felix_runtime.apply_wrong_chunk_name(
            runtime,
            fixit_felix.WrongChunkNameDecision("ask_bruteforce", "finding", True),
            "zzzz_Tool_",
            None,
        )
    except ValueError as exc:
        assert str(exc) == "FixItFelix wrong-chunk-name action needs chunk tools: ask_bruteforce"
    else:
        raise AssertionError("Expected ValueError for missing wrong-chunk-name tools")


def test_apply_wrong_chunk_name_rejects_unknown_action():
    runtime = wrong_chunk_name_runtime([])

    try:
        fixit_felix_runtime.apply_wrong_chunk_name(
            runtime,
            SimpleNamespace(action="unknown", finding="finding", bad_crc=True),
            "zzzz_Tool_",
            wrong_chunk_name_tools(),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix wrong-chunk-name action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown wrong-chunk-name action")


def no_next_tools(chunk_type=b"IDAT", chunk_length="12", previous_chunk=b"IDAT"):
    return SimpleNamespace(
        chunk_type=chunk_type,
        chunk_length=chunk_length,
        previous_chunk=previous_chunk,
    )


def no_next_runtime(
    calls,
    *,
    pandora_box=None,
    data_hex="",
    question_result=True,
    crc_offset=0,
    bad_missplaced=False,
    eof=False,
    chunks_history=(),
    deferred_linefeed=False,
):
    state = {"eof": eof}
    side_notes = []

    def record(name, result=None):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return callback

    def set_eof(value):
        calls.append(("set_eof", (value,), {}))
        state["eof"] = value

    return (
        fixit_felix_runtime.NoNextChunkRuntime(
            emit=record("emit"),
            candy=record("candy", "colored"),
            question=record("question", question_result),
            side_notes=side_notes,
            pandora_box=pandora_box if pandora_box is not None else {},
            sample="sample.png",
            data_hex=data_hex,
            cl_offset=33,
            crc_offset=crc_offset,
            original_chunk_length_hex="0d",
            raw_crc="raw-crc",
            debug=False,
            pause_debug=False,
            pause_error=False,
            bad_missplaced=bad_missplaced,
            set_skip_bad_no_next_chunk=record("set_skip_bad_no_next_chunk"),
            set_eof=set_eof,
            eof=lambda: state["eof"],
            chunk_story=record("chunk_story"),
            check_chunk_order=record("check_chunk_order"),
            libpng_check=record("libpng_check", "libpng-result"),
            run_relics=record("relics", "relics-result"),
            the_good_place=record("the_good_place", "good-place-result"),
            write_clone=record("write_clone", "write-result"),
            the_end=record("the_end"),
            pause=record("pause"),
            debug_print=record("debug_print"),
            dummy_chunk=record("dummy_chunk", "dummy-result"),
            nearby_chunk=record("nearby_chunk", "nearby-result"),
            nearby_found_later_iend=lambda: state.get("nearby_found_later_iend"),
            chunks_history=tuple(chunks_history),
            has_deferred_linefeed_repair=lambda: deferred_linefeed,
            apply_deferred_linefeed_repair=record(
                "apply_deferred_linefeed_repair",
                "deferred-result",
            ),
        ),
        side_notes,
        state,
    )


def test_stop_before_libpng_repairs_splt_invalid_sample_depth():
    calls = []
    original = splt_sample_depth_fixture_bytes()
    runtime, side_notes, _state = no_next_runtime(calls, data_hex=original.hex())

    should_return, result = fixit_felix_runtime.stop_before_libpng_for_unresolved_findings(
        runtime,
        ("GetInfo_Error_0:-Sample depth is not correct it must be 8 or 16",),
    )

    assert should_return is True
    assert result == "write-result"
    question_calls = [call for call in calls if call[0] == "question"]
    assert question_calls == [
        (
            "question",
            (),
            {
                "id": "sPLT Payload Repair:-Try to repair malformed/duplicate sPLT chunk(s)?",
                "idhash": "sPLT-payload:sPLT",
            },
        )
    ]
    write_call = next(call for call in calls if call[0] == "write_clone")
    fixed_data = bytes.fromhex(write_call[1][0])
    assert validate_png_structure(fixed_data).ok
    assert [chunk.data for chunk in iter_chunks(fixed_data) if chunk.chunk_type == b"sPLT"] == [
        b"Bad suggestion\x00\x08\x00\x00\x00\xff\x00\x00"
    ]
    assert side_notes == [
        "-Stopped before libpng: unresolved findings remain: GetInfo_Error_0:-Sample depth is not correct it must be 8 or 16.",
        "-FixItFelix:repaired malformed/duplicate sPLT chunk(s).",
    ]


def test_stop_before_libpng_prompts_to_remove_all_transparent_overlong_trns_alpha_table():
    calls = []
    original = trns_too_many_entries_fixture_bytes()
    runtime, side_notes, _state = no_next_runtime(calls, data_hex=original.hex())

    should_return, result = fixit_felix_runtime.stop_before_libpng_for_unresolved_findings(
        runtime,
        ("GetInfo_Error_0:-tRNS Alpha indexes palettes entries must not be superior to PLTE entries",),
    )

    assert should_return is True
    assert result == "write-result"
    question_calls = [call for call in calls if call[0] == "question"]
    assert question_calls == [
        (
            "question",
            (),
            {
                "id": (
                    "tRNS Indexed Alpha Removal:-Trimmed tRNS would make every PLTE entry "
                    "transparent. Remove tRNS instead?"
                ),
                "idhash": "tRNS-transparency:tRNS",
            },
        )
    ]
    write_call = next(call for call in calls if call[0] == "write_clone")
    fixed_data = bytes.fromhex(write_call[1][0])
    assert validate_png_structure(fixed_data).ok
    assert b"tRNS" not in [chunk.chunk_type for chunk in iter_chunks(fixed_data)]
    assert side_notes == [
        "-Stopped before libpng: unresolved findings remain: GetInfo_Error_0:-tRNS Alpha indexes palettes entries must not be superior to PLTE entries.",
        "-FixItFelix:removed overlong indexed tRNS chunk.",
    ]


def test_stop_before_libpng_repairs_ster_invalid_mode():
    calls = []
    original = ster_mode_fixture_bytes()
    runtime, side_notes, _state = no_next_runtime(calls, data_hex=original.hex())

    should_return, result = fixit_felix_runtime.stop_before_libpng_for_unresolved_findings(
        runtime,
        ("GetInfo_Error_0:-sTER should be 0 or 1",),
    )

    assert should_return is True
    assert result == "write-result"
    write_call = next(call for call in calls if call[0] == "write_clone")
    fixed_data = bytes.fromhex(write_call[1][0])
    assert validate_png_structure(fixed_data).ok
    ster = next(chunk for chunk in iter_chunks(fixed_data) if chunk.chunk_type == b"sTER")
    assert ster.data == b"\x00"
    assert side_notes == [
        "-Stopped before libpng: unresolved findings remain: GetInfo_Error_0:-sTER should be 0 or 1.",
        "-FixItFelix:normalized sTER mode from 02 to 00 and rebuilt CRC.",
    ]


def test_stop_before_libpng_repairs_text_null_bytes():
    calls = []
    original = text_trailing_null_fixture_bytes()
    runtime, side_notes, _state = no_next_runtime(calls, data_hex=original.hex())

    should_return, result = fixit_felix_runtime.stop_before_libpng_for_unresolved_findings(
        runtime,
        ("GetInfo_Error_0:-tEXt text must not contain null bytes",),
    )

    assert should_return is True
    assert result == "write-result"
    write_call = next(call for call in calls if call[0] == "write_clone")
    fixed_data = bytes.fromhex(write_call[1][0])
    assert validate_png_structure(fixed_data).ok
    text = next(chunk for chunk in iter_chunks(fixed_data) if chunk.chunk_type == b"tEXt")
    assert text.data == b"Title\x00PngSuite"
    assert side_notes == [
        "-Stopped before libpng: unresolved findings remain: GetInfo_Error_0:-tEXt text must not contain null bytes.",
        "-FixItFelix:removed 1 null byte(s) from tEXt text payload and rebuilt CRC.",
    ]


def test_stop_before_libpng_repairs_time_value_range():
    calls = []
    original = time_value_range_fixture_bytes()
    runtime, side_notes, _state = no_next_runtime(calls, data_hex=original.hex())

    should_return, result = fixit_felix_runtime.stop_before_libpng_for_unresolved_findings(
        runtime,
        ("GetInfo_Error_0:-Month value is not valid 0",),
    )

    assert should_return is True
    assert result == "write-result"
    write_call = next(call for call in calls if call[0] == "write_clone")
    fixed_data = bytes.fromhex(write_call[1][0])
    assert validate_png_structure(fixed_data).ok
    time = next(chunk for chunk in iter_chunks(fixed_data) if chunk.chunk_type == b"tIME")
    assert time.data == bytes.fromhex("07d001010c2238")
    assert time.crc_ok
    assert side_notes == [
        "-Stopped before libpng: unresolved findings remain: GetInfo_Error_0:-Month value is not valid 0.",
        "-FixItFelix:normalized tIME from 2000-00-01 12:34:56 to 2000-01-01 12:34:56 and rebuilt CRC.",
    ]


def test_apply_no_next_false_positive_iend_runs_libpng_after_marking_eof():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    pandora_box = {finding: {"IEND_Tool_0": b"IEND"}}
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box=pandora_box,
        data_hex="aabbccdd" + fixit_felix.GOOD_IEND_HEX,
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("false_positive_iend", b"IEND", b"IEND", "0"),
        finding,
        "IEND_Tool_",
        no_next_tools(chunk_type=b"IEND", chunk_length="0"),
    )

    assert result == (True, "libpng-result")
    assert pandora_box == {}
    assert state["eof"] is True
    assert side_notes == [
        "-Found False-Positive :[Error:-No NextChunk].",
        "-Reached the end of file.",
    ]
    assert (
        "candy",
        ("Cowsay", "That No NextChunk is a false positive im removing it ..", "good"),
        {},
    ) in calls
    assert ("chunk_story", ("add", b"IEND", 33, 8, 13), {}) in calls
    assert calls[-1] == ("libpng_check", ("sample.png",), {})


def test_apply_no_next_false_positive_iend_applies_deferred_linefeed_before_libpng():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    pandora_box = {finding: {"IEND_Tool_0": b"IEND"}}
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box=pandora_box,
        data_hex="aabbccdd" + fixit_felix.GOOD_IEND_HEX,
        deferred_linefeed=True,
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("false_positive_iend", b"IEND", b"IEND", "0"),
        finding,
        "IEND_Tool_",
        no_next_tools(chunk_type=b"IEND", chunk_length="0"),
    )

    assert result == (True, "deferred-result")
    assert pandora_box == {}
    assert state["eof"] is True
    assert side_notes == [
        "-Found False-Positive :[Error:-No NextChunk].",
        "-Reached the end of file.",
        "-Deferred line-feed repair applied after full chunk tour.",
    ]
    assert ("apply_deferred_linefeed_repair", (), {}) in calls
    assert not [call for call in calls if call[0] in ("libpng_check", "the_end")]


def test_apply_no_next_false_positive_iend_writes_clean_cut():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    data_hex = "aabbccdd" + fixit_felix.GOOD_IEND_HEX + "ffee"
    runtime, side_notes, _state = no_next_runtime(
        calls,
        pandora_box={finding: {"IEND_Tool_0": b"IEND"}},
        data_hex=data_hex,
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("false_positive_iend", b"IEND", b"IEND", "0"),
        finding,
        "IEND_Tool_",
        no_next_tools(chunk_type=b"IEND", chunk_length="0"),
    )

    assert result == (True, "write-result")
    assert side_notes == [
        "-Found False-Positive :[Error:-No NextChunk].",
        "-FixitFelix:Removing extra bytes after IEND chunk.",
    ]
    assert calls[-1] == (
        "write_clone",
        (bytes.fromhex("aabbccdd" + fixit_felix.GOOD_IEND_HEX), "-Saved"),
        {},
    )


def test_apply_no_next_false_positive_iend_falls_back_when_missplaced_tools_are_incomplete():
    calls = []
    runtime, side_notes, state = no_next_runtime(
        calls,
        bad_missplaced=True,
        pandora_box={"ChunkOrder_Error_0:-Missplaced": {"Only_One_Tool": b"gAMA"}},
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("the_good_place"),
    )

    assert result == (False, None)
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved misplaced chunk remains after IDAT.",
    ]
    assert all(call[0] != "the_good_place" for call in calls)
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert (
        "candy",
        (
            "Cowsay",
            "I still have an unrepaired misplaced chunk on the table. No Kraken snack until that mess is handled.",
            "bad",
        ),
        {},
    ) in calls
    assert calls[-1] == ("the_end", (), {})


def test_apply_no_next_false_positive_iend_infers_before_idat_repair_from_history():
    calls = []
    runtime, side_notes, state = no_next_runtime(
        calls,
        bad_missplaced=True,
        pandora_box={"ChunkOrder_Error_0:-Missplaced": {"Only_One_Tool": ["-Missplaced"]}},
        chunks_history=(b"PNG", b"IHDR", b"gAMA", b"IDAT", b"bKGD"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("the_good_place"),
    )

    assert result == (True, "good-place-result")
    assert state["eof"] is True
    assert side_notes == ["-Reached the end of file."]
    assert ("the_good_place", (b"IDAT", 3, b"bKGD"), {}) in calls
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert not [call for call in calls if call[0] == "the_end"]


def test_apply_no_next_false_positive_iend_infers_before_plte_repair_from_lowercase_missplaced():
    calls = []
    runtime, side_notes, state = no_next_runtime(
        calls,
        bad_missplaced=True,
        pandora_box={
            "CheckChunkOrder_Error_0:-cHRM is missplaced must appears before PLTE Chunk": {
                "Only_One_Tool": ["-cHRM is missplaced must appears before PLTE Chunk"]
            }
        },
        chunks_history=(b"PNG", b"IHDR", b"gAMA", b"PLTE", b"cHRM", b"IDAT"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("the_good_place"),
    )

    assert result == (True, "good-place-result")
    assert state["eof"] is True
    assert side_notes == ["-Reached the end of file."]
    assert ("the_good_place", (b"PLTE", 3, b"cHRM"), {}) in calls
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert not [call for call in calls if call[0] == "the_end"]


def test_apply_no_next_false_positive_iend_repairs_hist_before_plte_before_libpng():
    calls = []
    finding = "GetInfo_Error_0:-PLTE Chunk sPLT is missing.(hIST must be used after one of them)"
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {}},
        chunks_history=(b"PNG", b"IHDR", b"gAMA", b"sBIT", b"hIST", b"PLTE", b"IDAT"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (True, "good-place-result")
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: %s." % finding,
    ]
    assert (
        "candy",
        (
            "Cowsay",
            "Libpng might smile at the pixels, but Pandora still has unpaid invoices. No Kraken snack yet.",
            "bad",
        ),
        {},
    ) in calls
    assert (
        "candy",
        (
            "Cowsay",
            "I found a chunk-order repair path, so I am trying TheGoodPlace before calling this perfect.",
            "com",
        ),
        {},
    ) in calls
    assert ("the_good_place", (b"hIST", 4, b"PLTE"), {}) in calls
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert not [call for call in calls if call[0] == "the_end"]


def test_apply_no_next_false_positive_iend_routes_missing_plte_to_relics():
    calls = []
    finding = "GetInfo_Error_0:-PLTE Chunk or sPLT is missing.(tRNS must be used after one of them)"
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {}},
        chunks_history=(b"PNG", b"IHDR", b"gAMA", b"tRNS", b"bKGD", b"IDAT"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (True, "relics-result")
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: %s." % finding,
    ]
    assert (
        "candy",
        (
            "Cowsay",
            "I found a missing PLTE repair path, so I am opening the Ark before calling this unsupported.",
            "com",
        ),
        {},
    ) in calls
    assert ("relics", (finding,), {}) in calls
    assert not [call for call in calls if call[0] in ("libpng_check", "the_good_place", "the_end")]


def test_apply_no_next_false_positive_iend_repairs_duplicate_iccp_before_libpng():
    calls = []
    finding = "CheckChunkOrder_Error_0:-Multiple iCCP chunk"
    duplicate_iccp = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00")
        + build_png_chunk(b"iCCP", b"profile\x00\x00x\x9c\x03\x00\x00\x00\x00\x01")
        + build_png_chunk(b"iCCP", b"profile\x00\x00x\x9c\x03\x00\x00\x00\x00\x01")
        + build_png_chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff")
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + IEND_CHUNK
    )
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {}},
        data_hex=duplicate_iccp.hex(),
        chunks_history=(b"PNG", b"IHDR", b"iCCP", b"iCCP", b"PLTE", b"IDAT"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (True, "write-result")
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: %s." % finding,
        "-FixItFelix:removed duplicate singleton chunk(s): iCCP.",
    ]
    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert len(write_calls) == 1
    fixed_data = bytes.fromhex(write_calls[0][1][0])
    assert fixed_data.count(b"iCCP") == 1
    assert not [call for call in calls if call[0] in ("libpng_check", "the_good_place", "the_end")]


def test_apply_no_next_false_positive_iend_repairs_duplicate_ihdr_before_libpng():
    calls = []
    finding = "CheckChunkOrder_Error_0:-Multiple IHDR chunk"
    ihdr = build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00")
    duplicate_ihdr = (
        PNG_SIGNATURE
        + ihdr
        + ihdr
        + build_png_chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff")
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + IEND_CHUNK
    )
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {}},
        data_hex=duplicate_ihdr.hex(),
        chunks_history=(b"PNG", b"IHDR", b"IHDR", b"PLTE", b"IDAT"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (True, "write-result")
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: %s." % finding,
        "-FixItFelix:removed duplicate IHDR chunk(s) after first header.",
    ]
    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert len(write_calls) == 1
    fixed_data = bytes.fromhex(write_calls[0][1][0])
    assert fixed_data.count(b"IHDR") == 1
    assert not [call for call in calls if call[0] in ("libpng_check", "the_good_place", "the_end")]


def test_apply_no_next_false_positive_iend_repairs_duplicate_pcal_before_libpng():
    calls = []
    finding = "CheckChunkOrder_Error_0:-Multiple pCAL chunk"
    pcal = build_png_chunk(
        b"pCAL",
        bytes.fromhex(
            "626f67757320756e69747300000000000000ffff0002666f6f2f626172"
            "00312e3065300036352e3533356533"
        ),
    )
    duplicate_pcal = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00")
        + pcal
        + pcal
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + IEND_CHUNK
    )
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {}},
        data_hex=duplicate_pcal.hex(),
        chunks_history=(b"PNG", b"IHDR", b"pCAL", b"pCAL", b"IDAT"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (True, "write-result")
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: %s." % finding,
        "-FixItFelix:removed duplicate singleton chunk(s): pCAL.",
    ]
    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert len(write_calls) == 1
    fixed_data = bytes.fromhex(write_calls[0][1][0])
    assert fixed_data.count(b"pCAL") == 1
    assert not [call for call in calls if call[0] in ("libpng_check", "the_good_place", "the_end")]


def test_apply_no_next_false_positive_iend_refuses_libpng_when_other_errors_remain():
    calls = []
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={"CheckChunkOrder_Error_0:-cHRM is missplaced must appears before PLTE Chunk": {}},
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (False, None)
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: "
        "CheckChunkOrder_Error_0:-cHRM is missplaced must appears before PLTE Chunk.",
    ]
    assert (
        "candy",
        ("Cowsay", messages.UNIMPLEMENTED_REPAIR_ROUTE_MESSAGE, "bad"),
        {},
    ) in calls
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert calls[-1] == ("the_end", (), {})


def test_apply_no_next_false_positive_iend_allows_libpng_for_benign_chrm_override():
    calls = []
    finding = "GetInfo_Error_0:-cHRM is overided by sRGB chunk and iCCP"
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {"cHRM_Tool_0": finding}},
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (True, "libpng-result")
    assert state["eof"] is True
    assert finding not in runtime.pandora_box
    assert side_notes == [
        "-Reached the end of file.",
        "-Found benign metadata advisory before libpng: %s." % finding,
        "-LibpngCheck allowed after filtering benign metadata advisories.",
    ]
    assert ("libpng_check", ("sample.png",), {}) in calls
    assert not [call for call in calls if call[0] == "the_end"]


def test_apply_no_next_false_positive_iend_allows_libpng_for_benign_iccp_warning():
    calls = []
    finding = "LibpngCheck_Warning_0:-iCCP: profile is noisy"
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {"iCCP_Tool_0": finding}},
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (True, "libpng-result")
    assert state["eof"] is True
    assert finding not in runtime.pandora_box
    assert side_notes == [
        "-Reached the end of file.",
        "-Found benign metadata advisory before libpng: %s." % finding,
        "-LibpngCheck allowed after filtering benign metadata advisories.",
    ]
    assert ("libpng_check", ("sample.png",), {}) in calls
    assert not [call for call in calls if call[0] == "the_end"]


def test_apply_no_next_false_positive_iend_reports_unimplemented_non_order_error():
    calls = []
    finding = "GetInfo_Error_0:-iTXt Compression Flag must be 0 or 1"
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {}},
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (False, None)
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: %s." % finding,
    ]
    assert (
        "candy",
        (
            "Cowsay",
            "Libpng might smile at the pixels, but Pandora still has unpaid invoices. No Kraken snack yet.",
            "bad",
        ),
        {},
    ) in calls
    assert (
        "candy",
        ("Cowsay", messages.UNIMPLEMENTED_REPAIR_ROUTE_MESSAGE, "bad"),
        {},
    ) in calls
    assert not [call for call in calls if call[0] in ("libpng_check", "the_good_place")]
    assert calls[-1] == ("the_end", (), {})


def test_apply_no_next_wrong_iend_length_rebuilds_canonical_iend():
    calls = []
    prefix = valid_png_bytes()[: -len(IEND_CHUNK)]
    broken = prefix + bytes.fromhex("0000000149454e44aad11a4fe1")
    expected = prefix + IEND_CHUNK
    runtime, side_notes, _state = no_next_runtime(calls, data_hex=broken.hex())

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("wrong_iend_length", b"IDAT", b"IEND", "1"),
        "CheckLength_Error_0:-No NextChunk",
        "IEND_Tool_",
        no_next_tools(chunk_type=b"IEND", chunk_length="1"),
    )

    assert result == (True, "write-result")
    assert side_notes == ["-FixItFelix:rebuilt IEND with zero length and canonical CRC."]
    assert calls[-1] == (
        "write_clone",
        (
            expected,
            "-FixItFelix:rebuilt IEND with zero length and canonical CRC.",
        ),
        {},
    )


def test_apply_no_next_append_missing_iend_uses_dummy_at_crc_tail():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, _state = no_next_runtime(calls, data_hex="aabbccddff")

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("append_missing_iend", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (True, "dummy-result")
    assert side_notes == ["-Extra bits detected:ff"]
    assert calls[-1] == ("dummy_chunk", (b"IEND", 8, 8, 8, finding), {})


def test_apply_no_next_append_missing_iend_replaces_partial_iend_tail():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    partial_iend = fixit_felix.GOOD_IEND_HEX[:4]
    runtime, side_notes, _state = no_next_runtime(
        calls,
        data_hex="aabbccdd" + partial_iend,
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("append_missing_iend", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (True, "write-result")
    assert side_notes == [
        "-Extra bits detected:%s" % partial_iend,
        "-Part or full IEND chunk detected:%s" % partial_iend,
        "-FixItFelix:replaced partial IEND tail with canonical IEND chunk.",
    ]
    assert calls[-1] == (
        "write_clone",
        (
            bytes.fromhex("aabbccdd" + fixit_felix.GOOD_IEND_HEX),
            "-FixItFelix:replaced partial IEND tail with canonical IEND chunk.",
        ),
        {},
    )


def test_apply_no_next_length_probe_replaces_partial_iend_tail_before_nearby():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    partial_iend = fixit_felix.GOOD_IEND_HEX[:2]
    runtime, side_notes, _state = no_next_runtime(
        calls,
        data_hex="aabbccdd" + partial_iend,
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("ask_length_probe", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (True, "write-result")
    assert side_notes == [
        "-Extra bits detected:%s" % partial_iend,
        "-Part or full IEND chunk detected:%s" % partial_iend,
        "-FixItFelix:replaced partial IEND tail with canonical IEND chunk.",
    ]
    assert not [call for call in calls if call[0] in ("question", "nearby_chunk")]
    assert calls[-1] == (
        "write_clone",
        (
            bytes.fromhex("aabbccdd" + fixit_felix.GOOD_IEND_HEX),
            "-FixItFelix:replaced partial IEND tail with canonical IEND chunk.",
        ),
        {},
    )


def test_apply_no_next_uses_idat_chain_batch_before_iend_append():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, _state = no_next_runtime(
        calls,
        data_hex=idat_chain_candidate_hex(),
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("append_missing_iend", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (True, "write-result")
    assert not [call for call in calls if call[0] == "dummy_chunk"]
    assert any(call[0] == "write_clone" for call in calls)
    assert "-Repair hypothesis tried: IDAT chain header repair." in side_notes


def test_apply_no_next_uses_deflate_probe_when_idat_chain_is_aligned_but_stream_is_bad():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    original_deep = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam

    def no_candidate_deep(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeepBeamProbeResult(
            before,
            None,
            (),
            0,
            1,
            0,
            False,
            0,
            1,
            1,
            strategy="deep-beam",
            reason="mocked",
        )

    runtime, side_notes, _state = no_next_runtime(
        calls,
        data_hex=idat_chain_aligned_bad_deflate_hex(),
    )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = no_candidate_deep
        result = fixit_felix_runtime.apply_no_next_chunk(
            runtime,
            fixit_felix.NoNextChunkDecision("append_missing_iend", b"IDAT", b"IDAT", "12"),
            finding,
            "IDAT_Tool_",
            no_next_tools(),
        )
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_deep_beam = original_deep

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "dummy_chunk"]
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any(note.startswith("-IDAT stream diagnosis: status=corrupt_deflate") for note in side_notes)
    assert "-IDAT deflate header probe found no clone-worthy scanline progress." in side_notes
    assert "-IDAT diagnostic LF route found no clone-worthy scanline progress." in side_notes


def test_apply_no_next_does_not_append_iend_when_nearby_already_found_one():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, state = no_next_runtime(calls, data_hex="aabbccddff")
    state["nearby_found_later_iend"] = {
        "sample_name": "sample.png",
        "idat_count": 2,
        "double_check": True,
    }

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("append_missing_iend", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (False, None)
    assert side_notes == [
        "-Skipped adding IEND chunk: NearbyChunk already found an IEND later."
    ]
    assert ("set_skip_bad_no_next_chunk", (True,), {}) in calls
    assert not [call for call in calls if call[0] == "dummy_chunk"]


def test_apply_no_next_ask_length_probe_routes_to_nearby_chunk():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, _state = no_next_runtime(
        calls,
        pandora_box={finding: {"IDAT_Tool_0": b"IDAT"}},
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("ask_length_probe", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (True, "nearby-result")
    assert side_notes == ["-End of File Reached but IEND Chunk is missing"]
    assert calls[-1] == ("nearby_chunk", (b"IDAT", "12", b"IDAT", False, finding), {})


def test_apply_no_next_without_idat_evidence_stops_terminally():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {"gAMA_Tool_0": b"gAMA"}},
        chunks_history=(b"IHDR", b"gAMA"),
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("ask_length_probe", b"gAMA", b"gAMA", "4"),
        finding,
        "gAMA_Tool_",
        no_next_tools(chunk_type=b"gAMA", chunk_length="4", previous_chunk=b"IHDR"),
    )

    assert result == (False, None)
    assert side_notes == [
        "-Critical Chunk b'IDAT' is Missing",
        "-Terminal PNG error: no IDAT chunk found; no image data to repair.",
    ]
    assert state["eof"] is True
    assert ("set_skip_bad_no_next_chunk", (True,), {}) in calls
    assert ("set_eof", (True,), {}) in calls
    assert calls[-1] == ("the_end", (), {})
    assert not [call for call in calls if call[0] == "question"]
    assert not [call for call in calls if call[0] == "nearby_chunk"]
    assert any(
        call[0] == "candy"
        and call[1][0] == "Cowsay"
        and "No IDAT chunk, no image stream" in call[1][1]
        for call in calls
    )


def test_apply_no_next_zero_dimension_missing_idat_stops_terminally():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, state = no_next_runtime(
        calls,
        data_hex=zero_dimension_missing_idat_bytes().hex(),
        pandora_box={finding: {"gAMA_Tool_0": b"gAMA"}},
        chunks_history=(b"IHDR", b"gAMA"),
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("ask_length_probe", b"gAMA", b"gAMA", "4"),
        finding,
        "gAMA_Tool_",
        no_next_tools(chunk_type=b"gAMA", chunk_length="4", previous_chunk=b"IHDR"),
    )

    assert result == (False, None)
    assert side_notes == [
        "-Critical Chunk b'IDAT' is Missing",
        "-Terminal PNG error: no IDAT chunk found; no image data to repair.",
    ]
    assert state["eof"] is True
    assert ("set_skip_bad_no_next_chunk", (True,), {}) in calls
    assert ("set_eof", (True,), {}) in calls
    assert calls[-1] == ("the_end", (), {})
    assert not [call for call in calls if call[0] == "question"]
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any(
        call[0] == "candy"
        and call[1][0] == "Cowsay"
        and "No IDAT chunk, no image stream" in call[1][1]
        for call in calls
    )


def test_apply_no_next_raw_idat_bytes_keep_length_probe_available():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, _state = no_next_runtime(
        calls,
        data_hex="89504e470d0a1a0a0000000467414d410000000049444154",
        chunks_history=(b"IHDR", b"gAMA"),
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("ask_length_probe", b"gAMA", b"gAMA", "4"),
        finding,
        "gAMA_Tool_",
        no_next_tools(chunk_type=b"gAMA", chunk_length="4", previous_chunk=b"IHDR"),
    )

    assert result == (True, "nearby-result")
    assert side_notes == ["-End of File Reached but IEND Chunk is missing"]
    assert calls[-1] == ("nearby_chunk", (b"gAMA", "4", b"IHDR", False, finding), {})


def test_apply_no_next_chunk_rejects_unknown_action():
    runtime, _side_notes, _state = no_next_runtime([])

    try:
        fixit_felix_runtime.apply_no_next_chunk(
            runtime,
            SimpleNamespace(action="unknown"),
            "finding",
            "IDAT_Tool_",
            no_next_tools(),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix no-next-chunk action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown no-next action")


def libpng_runtime(
    calls,
    *,
    answer=True,
    pandora_box=None,
    cornucopia=None,
    sample="sample.png",
    try_idat_decision_gate=None,
):
    def record(name, result=None):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return callback

    return fixit_felix_runtime.LibpngErrorRuntime(
        emit=record("emit"),
        candy=record("candy", "colored"),
        question=record("question", answer),
        the_end=record("the_end"),
        run_relics=record("run_relics", "relics-result"),
        save_clone=record("save_clone", "saved"),
        groundhog_day=record("groundhog_day", "groundhog-result"),
        set_skip_bad_libpng=record("set_skip_bad_libpng"),
        pandora_box=pandora_box if pandora_box is not None else {},
        cornucopia=cornucopia if cornucopia is not None else {},
        sample=sample,
        try_idat_decision_gate=try_idat_decision_gate,
    )


def test_apply_libpng_error_saves_existing_solution():
    calls = []
    finding = "Libpng_Error_0:libpng error: bad adaptive filter"
    chkd = "LibpngCheck_Tool_"
    runtime = libpng_runtime(
        calls,
        cornucopia={
            finding: {
                chkd + "0": "fixed-data",
                chkd + "1": 12,
                chkd + "2": 20,
                chkd + "3": "legacy save note",
            }
        },
    )

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("save_existing_solution", finding),
        chkd,
    )

    assert result == (True, "groundhog-result")
    assert calls == [
        ("emit", ("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding,), {}),
        ("emit", ("\n-\033[1;32;49mSolved\033[m: legacy save note",), {}),
        ("save_clone", ("fixed-data", 12, 20, "legacy save note"), {}),
        ("groundhog_day", ("sample.png",), {}),
    ]


def test_apply_libpng_error_accepts_relics_prompt_and_sets_skip():
    calls = []
    finding = "Libpng_Error_0:libpng error: bad adaptive filter"
    chkd = "LibpngCheck_Tool_"
    pandora_box = {
        finding: {
            chkd + "0": "candidate",
            chkd + "1": 12,
            chkd + "2": 20,
        }
    }
    runtime = libpng_runtime(calls, pandora_box=pandora_box)

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("ask_relics", finding),
        chkd,
    )

    assert result == (True, "relics-result")
    assert calls[0] == ("emit", ("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding,), {})
    assert calls[-2:] == [
        ("set_skip_bad_libpng", (True,), {}),
        ("run_relics", (finding,), {}),
    ]
    question_calls = [call for call in calls if call[0] == "question"]
    assert question_calls == [
        (
            "question",
            (),
            {
                "id": finding,
                "idhash": hash("candidate1220"),
            },
        )
    ]


def test_apply_libpng_error_declines_relics_prompt_and_ends():
    calls = []
    finding = "Libpng_Error_0:libpng error: bad adaptive filter"
    runtime = libpng_runtime(calls, answer=False)

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("ask_relics", finding),
        "LibpngCheck_Tool_",
    )

    assert result is None
    assert calls[-1] == ("the_end", (), {})


def test_apply_libpng_error_not_enough_image_data_ends_after_todo():
    calls = []
    finding = "Libpng_Error_0:libpng error: Not enough image data"
    runtime = libpng_runtime(calls)

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("idat_decision_gate", finding),
        "LibpngCheck_Tool_",
    )

    assert result is None
    assert calls[-2:] == [
        ("emit", ("colored",), {}),
        ("the_end", (), {}),
    ]


def test_apply_libpng_error_idat_gate_uses_partial_blackfill_decision():
    calls = []
    finding = "Libpng_Error_0:libpng error: Not enough image data"

    def gate(gated_finding):
        calls.append(("idat_gate", (gated_finding,), {}))
        return True

    runtime = libpng_runtime(calls, try_idat_decision_gate=gate)

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("idat_decision_gate", finding),
        "LibpngCheck_Tool_",
    )

    assert result is True
    assert ("idat_gate", (finding,), {}) in calls
    assert not any(call[0] == "the_end" for call in calls)


def test_apply_libpng_error_skip_only_reports_critical_hit():
    calls = []
    finding = "Libpng_Error_0:libpng error: bad adaptive filter"
    runtime = libpng_runtime(calls)

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("skip", finding),
        "LibpngCheck_Tool_",
    )

    assert result == (False, None)
    assert calls == [
        ("emit", ("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding,), {})
    ]


def test_apply_libpng_error_rejects_unknown_action():
    runtime = libpng_runtime([])

    try:
        fixit_felix_runtime.apply_libpng_error(
            runtime,
            SimpleNamespace(action="unknown", finding="Libpng_Error_0:bad"),
            "LibpngCheck_Tool_",
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix libpng action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown libpng action")


def recording_callbacks(calls):
    return fixit_felix_runtime.LegacyFixItFelixHandlers(
        wrong_crc=lambda finding, chkd, pandora_len: calls.append(
            ("wrong_crc", finding, chkd, pandora_len)
        )
        or (True, "wrong-crc"),
        libpng_error=lambda finding, chkd: calls.append(
            ("libpng_error", finding, chkd)
        )
        or (True, "libpng"),
        wrong_chunk_name=lambda finding, chkd: calls.append(
            ("wrong_chunk_name", finding, chkd)
        )
        or (True, "wrong-name"),
        no_next_chunk=lambda finding, chkd, chunk: calls.append(
            ("no_next_chunk", finding, chkd, chunk)
        )
        or (True, "no-next"),
        gama_zero=lambda finding: calls.append(("gama_zero", finding))
        or (True, "gama"),
        critical_miss=lambda finding: calls.append(("critical_miss", finding))
        or (False, None),
    )


def test_finding_handlers_route_legacy_callback_arguments():
    cases = [
        ("wrong_crc", ("wrong_crc", "finding", "IDAT_Tool_", 2), (True, "wrong-crc")),
        ("libpng_error", ("libpng_error", "finding", "IDAT_Tool_"), (True, "libpng")),
        ("wrong_chunk_name", ("wrong_chunk_name", "finding", "IDAT_Tool_"), (True, "wrong-name")),
        ("no_next_chunk", ("no_next_chunk", "finding", "IDAT_Tool_", b"IDAT"), (True, "no-next")),
        ("gama_zero", ("gama_zero", "finding"), (True, "gama")),
        ("critical_miss", ("critical_miss", "finding"), (False, None)),
    ]

    for handler_name, expected_call, expected_result in cases:
        calls = []
        handlers = fixit_felix_runtime.finding_handlers(recording_callbacks(calls))
        work_item = fixit_felix.FixItFelixWorkItem("finding", handler_name, "finding")

        result = handlers[handler_name](work_item, "IDAT_Tool_", 2, b"IDAT")

        assert result == expected_result
        assert calls == [expected_call]


def test_apply_finding_work_item_dispatches_through_fixit_felix_dispatch():
    calls = []
    work_item = fixit_felix.FixItFelixWorkItem("finding", "wrong_crc", "finding")

    result = fixit_felix_runtime.apply_finding_work_item(
        recording_callbacks(calls),
        work_item,
        "IDAT_Tool_",
        3,
        b"IDAT",
    )

    assert result == (True, "wrong-crc")
    assert calls == [("wrong_crc", "finding", "IDAT_Tool_", 3)]


def test_runtime_uses_automatic_repair_and_legacy_callbacks():
    calls = []
    runtime = fixit_felix_runtime.runtime(
        try_automatic_repair=lambda handler: calls.append(("auto", handler)) or None,
        callbacks=recording_callbacks(calls),
    )

    result = fixit_felix.run_repair_work_items(
        runtime,
        (
            fixit_felix.FixItFelixWorkItem("automatic_repair", "plte_cleanup"),
            fixit_felix.FixItFelixWorkItem("finding", "no_next_chunk", "finding"),
        ),
        chkd="IDAT_Tool_",
        pandora_box_len=4,
        chunk=b"IDAT",
    )

    assert result == fixit_felix.FixItFelixRunResult(True, "no-next")
    assert calls == [
        ("auto", "plte_cleanup"),
        ("no_next_chunk", "finding", "IDAT_Tool_", b"IDAT"),
    ]


def test_namespace_runtime_builders_preserve_legacy_wiring():
    calls = []
    side_notes = []
    pandora_box = {}
    cornucopia = {}

    def callback(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return name

        return inner

    namespace = {
        "PRINT": callback("PRINT"),
        "Candy": callback("Candy"),
        "Question": callback("Question"),
        "SaveClone": callback("SaveClone"),
        "ChunkStory": callback("ChunkStory"),
        "FixItFelix_Set_Skip_Bad_Crc": callback("set_skip_bad_crc"),
        "FixItFelix_Set_Old_Bad_Crc": callback("set_old_bad_crc"),
        "FixItFelix_Set_Skip_Bad_Libpng": callback("set_skip_bad_libpng"),
        "FixItFelix_Set_Skip_Bad_Next_Name": callback("set_skip_bad_next_name"),
        "FixItFelix_Set_Skip_Bad_Current_Name": callback("set_skip_bad_current_name"),
        "FixItFelix_Set_Skip_Bad_No_Next_Chunk": callback("set_skip_bad_no_next_chunk"),
        "FixItFelix_Set_EOF": callback("set_eof"),
        "Relics": callback("Relics"),
        "GroundhogDay": callback("GroundhogDay"),
        "Ancillary": callback("Ancillary"),
        "NearbyChunk": callback("NearbyChunk"),
        "BruteChunk": callback("BruteChunk"),
        "CheckChunkOrder": callback("CheckChunkOrder"),
        "LibpngCheck": callback("LibpngCheck"),
        "TheGoodPlace": callback("TheGoodPlace"),
        "WriteClone": callback("WriteClone"),
        "Preview_Repair_Image": callback("Preview_Repair_Image"),
        "Tk_Manual_Plte": callback("Tk_Manual_Plte"),
        "SmashBruteBrawl": callback("SmashBruteBrawl"),
        "GetSpec": callback("GetSpec"),
        "Product": callback("Product"),
        "Loadingbar": callback("Loadingbar"),
        "Minibar": callback("Minibar"),
        "TheEnd": callback("TheEnd"),
        "Pause": callback("Pause"),
        "DummyChunk": callback("DummyChunk"),
        "FixItFelix": callback("FixItFelix"),
        "PandoraBox": pandora_box,
        "Cornucopia": cornucopia,
        "SideNotes": side_notes,
        "CLoffI": 12,
        "CrcoffI": 40,
        "Orig_CL": "0000000d",
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": True,
        "Sample": "sample.png",
        "FILE_Origin": "source.png",
        "FILE_DIR": "/tmp/out/",
        "SMASH_BRUTE_BRAWL_FORCE_LEVEL": "2",
        "DATAX": "001122",
        "IDAT_PREFINAL_REPAIR_CYCLES": "6",
        "IDAT_PREFINAL_REPAIR_BATCHES": "5",
        "ULTIMATE_LINEFEED_BUDGET": "1234",
        "ULTIMATE_LINEFEED_UNBOUNDED": False,
        "ULTIMATE_LINEFEED_WORKERS": "2",
        "IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_DEPTH": "3",
        "IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_OFFSETS": "70",
        "IDAT_GROUNDHOGDAY_VISUAL_GUARD": "strict",
        "Raw_Crc": "deadbeef",
        "Bad_Missplaced": True,
        "Bad_Ancillary": False,
        "EOF": True,
    }

    wrong_crc = fixit_felix_runtime.build_wrong_crc_runtime_from_namespace(namespace)
    assert wrong_crc.emit is namespace["PRINT"]
    assert wrong_crc.candy is namespace["Candy"]
    assert wrong_crc.question is namespace["Question"]
    assert wrong_crc.save_clone is namespace["SaveClone"]
    assert wrong_crc.chunk_story is namespace["ChunkStory"]
    assert wrong_crc.set_skip_bad_crc is namespace["FixItFelix_Set_Skip_Bad_Crc"]
    assert wrong_crc.set_old_bad_crc is namespace["FixItFelix_Set_Old_Bad_Crc"]
    assert wrong_crc.side_notes is side_notes
    assert wrong_crc.pandora_box is pandora_box
    assert wrong_crc.cl_offset == 12
    assert wrong_crc.crc_offset == 40
    assert wrong_crc.original_chunk_length_hex == "0000000d"
    assert wrong_crc.debug is True
    assert wrong_crc.pause_debug is False
    assert wrong_crc.file_origin == "source.png"
    assert wrong_crc.file_dir == "/tmp/out/"
    assert wrong_crc.preview_repair_image is namespace["Preview_Repair_Image"]
    assert wrong_crc.prefinal_repair_cycles == "6"
    assert wrong_crc.prefinal_repair_batches == "5"
    assert wrong_crc.ultimate_linefeed_budget == "1234"
    assert wrong_crc.ultimate_linefeed_workers == "2"
    assert wrong_crc.ultimate_linefeed_max_depth == "3"
    assert wrong_crc.ultimate_linefeed_max_offsets == "70"
    assert wrong_crc.groundhogday_visual_guard == "strict"

    libpng = fixit_felix_runtime.build_libpng_error_runtime_from_namespace(namespace)
    assert libpng.emit is namespace["PRINT"]
    assert libpng.candy is namespace["Candy"]
    assert libpng.question is namespace["Question"]
    assert libpng.the_end is namespace["TheEnd"]
    assert libpng.run_relics is namespace["Relics"]
    assert libpng.save_clone is namespace["SaveClone"]
    assert libpng.groundhog_day is namespace["GroundhogDay"]
    assert libpng.set_skip_bad_libpng is namespace["FixItFelix_Set_Skip_Bad_Libpng"]
    assert libpng.pandora_box is pandora_box
    assert libpng.cornucopia is cornucopia
    assert libpng.sample == "sample.png"

    wrong_name = fixit_felix_runtime.build_wrong_chunk_name_runtime_from_namespace(namespace)
    assert wrong_name.emit is namespace["PRINT"]
    assert wrong_name.candy is namespace["Candy"]
    assert wrong_name.question is namespace["Question"]
    assert wrong_name.ancillary is namespace["Ancillary"]
    assert wrong_name.nearby_chunk is namespace["NearbyChunk"]
    assert wrong_name.brute_chunk is namespace["BruteChunk"]
    assert wrong_name.save_clone is namespace["SaveClone"]
    assert wrong_name.write_clone is namespace["WriteClone"]
    assert wrong_name.set_skip_bad_next_name is namespace["FixItFelix_Set_Skip_Bad_Next_Name"]
    assert wrong_name.set_skip_bad_current_name is namespace["FixItFelix_Set_Skip_Bad_Current_Name"]
    assert wrong_name.bad_ancillary() is False
    namespace["Bad_Ancillary"] = True
    assert wrong_name.bad_ancillary() is True
    assert wrong_name.pandora_box is pandora_box
    assert wrong_name.cornucopia is cornucopia
    assert wrong_name.data_hex == "001122"
    assert wrong_name.file_origin == "source.png"
    assert wrong_name.file_dir == "/tmp/out/"
    assert wrong_name.prefinal_repair_cycles == "6"
    assert wrong_name.prefinal_repair_batches == "5"
    assert wrong_name.ultimate_linefeed_budget == "1234"
    assert wrong_name.ultimate_linefeed_workers == "2"
    assert wrong_name.ultimate_linefeed_max_depth == "3"
    assert wrong_name.ultimate_linefeed_max_offsets == "70"
    assert wrong_name.groundhogday_visual_guard == "strict"

    no_next = fixit_felix_runtime.build_no_next_chunk_runtime_from_namespace(namespace)
    assert no_next.emit is namespace["PRINT"]
    assert no_next.candy is namespace["Candy"]
    assert no_next.question is namespace["Question"]
    assert no_next.side_notes is side_notes
    assert no_next.pandora_box is pandora_box
    assert no_next.sample == "sample.png"
    assert no_next.data_hex == "001122"
    assert no_next.cl_offset == 12
    assert no_next.crc_offset == 40
    assert no_next.original_chunk_length_hex == "0000000d"
    assert no_next.raw_crc == "deadbeef"
    assert no_next.debug is True
    assert no_next.pause_debug is False
    assert no_next.pause_error is True
    assert no_next.file_origin == "source.png"
    assert no_next.file_dir == "/tmp/out/"
    assert no_next.prefinal_repair_cycles == "6"
    assert no_next.prefinal_repair_batches == "5"
    assert no_next.ultimate_linefeed_budget == "1234"
    assert no_next.ultimate_linefeed_workers == "2"
    assert no_next.ultimate_linefeed_max_depth == "3"
    assert no_next.ultimate_linefeed_max_offsets == "70"
    assert no_next.groundhogday_visual_guard == "strict"
    assert no_next.bad_missplaced is True
    assert no_next.set_skip_bad_no_next_chunk is namespace["FixItFelix_Set_Skip_Bad_No_Next_Chunk"]
    assert no_next.set_eof is namespace["FixItFelix_Set_EOF"]
    assert no_next.eof() is True
    namespace["EOF"] = False
    assert no_next.eof() is False
    assert no_next.chunk_story is namespace["ChunkStory"]
    assert no_next.check_chunk_order is namespace["CheckChunkOrder"]
    assert no_next.libpng_check is namespace["LibpngCheck"]
    assert no_next.run_relics is namespace["Relics"]
    assert no_next.the_good_place is namespace["TheGoodPlace"]
    assert no_next.write_clone is namespace["WriteClone"]
    assert no_next.the_end is namespace["TheEnd"]
    assert no_next.pause is namespace["Pause"]
    assert no_next.debug_print is print
    assert no_next.dummy_chunk is namespace["DummyChunk"]
    assert no_next.nearby_chunk is namespace["NearbyChunk"]

    gama = fixit_felix_runtime.build_gama_zero_runtime_from_namespace(namespace)
    assert gama.candy is namespace["Candy"]
    assert gama.pandora_box is pandora_box
    assert gama.side_notes is side_notes
    assert gama.return_value is namespace["FixItFelix"]

    critical = fixit_felix_runtime.build_critical_miss_runtime_from_namespace(namespace)
    assert critical.emit is namespace["PRINT"]
    assert critical.pause is namespace["Pause"]

    automatic = fixit_felix_runtime.build_automatic_repair_runtime_from_namespace(namespace)
    assert automatic.side_notes is side_notes
    assert automatic.write_clone is namespace["WriteClone"]
    assert automatic.question is namespace["Question"]
    assert automatic.preview_repair_image is namespace["Preview_Repair_Image"]
    assert automatic.tk_manual_plte is namespace["Tk_Manual_Plte"]
    assert automatic.smash_brute_brawl is namespace["SmashBruteBrawl"]
    assert automatic.data_hex == "001122"
    assert automatic.pandora_box is pandora_box
    assert automatic.get_spec is namespace["GetSpec"]
    assert automatic.product is namespace["Product"]
    assert automatic.loadingbar is namespace["Loadingbar"]
    assert automatic.minibar is namespace["Minibar"]
    assert automatic.file_origin == "source.png"
    assert automatic.file_dir == "/tmp/out/"
    assert automatic.interactive is False
    assert automatic.smash_brute_brawl_force_level == 2


def test_namespace_interactive_prompts_uses_stdin_not_captured_stdout():
    namespace = {
        "AUTO": False,
        "NODIALOGUE": False,
        "sys": SimpleNamespace(
            stdin=SimpleNamespace(isatty=lambda: True),
            stdout=SimpleNamespace(isatty=lambda: False),
        ),
    }

    assert fixit_felix_runtime.namespace_interactive_prompts(namespace) is True

    namespace["NODIALOGUE"] = True
    assert fixit_felix_runtime.namespace_interactive_prompts(namespace) is False


def test_namespace_idat_convoy_runtimes_preserve_deep_beam_prompt_options():
    calls = []
    side_notes = []
    pandora_box = {}
    cornucopia = {}
    gpu_config = fixit_felix_runtime.gpu_runtime.GpuRuntimeConfig(enabled=False)

    def callback(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return name

        return inner

    def transcript_input(prompt):
        calls.append(("Transcript_Input", (prompt,), {}))
        return "1"

    namespace = {
        "PRINT": callback("PRINT"),
        "Candy": callback("Candy"),
        "Question": callback("Question"),
        "SaveClone": callback("SaveClone"),
        "WriteClone": callback("WriteClone"),
        "ChunkStory": callback("ChunkStory"),
        "FixItFelix_Set_Skip_Bad_Next_Name": callback("set_skip_bad_next_name"),
        "FixItFelix_Set_Skip_Bad_Current_Name": callback("set_skip_bad_current_name"),
        "FixItFelix_Set_Skip_Bad_No_Next_Chunk": callback("set_skip_bad_no_next_chunk"),
        "FixItFelix_Set_EOF": callback("set_eof"),
        "Ancillary": callback("Ancillary"),
        "NearbyChunk": callback("NearbyChunk"),
        "BruteChunk": callback("BruteChunk"),
        "CheckChunkOrder": callback("CheckChunkOrder"),
        "LibpngCheck": callback("LibpngCheck"),
        "Relics": callback("Relics"),
        "TheGoodPlace": callback("TheGoodPlace"),
        "TheEnd": callback("TheEnd"),
        "Pause": callback("Pause"),
        "DummyChunk": callback("DummyChunk"),
        "PandoraBox": pandora_box,
        "Cornucopia": cornucopia,
        "SideNotes": side_notes,
        "DATAX": "001122",
        "Bad_Ancillary": False,
        "Sample": "sample.png",
        "FILE_Origin": "source.png",
        "FILE_DIR": "/tmp/out/",
        "CLoffI": 12,
        "CrcoffI": 40,
        "Orig_CL": "0000000d",
        "Raw_Crc": "deadbeef",
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": False,
        "Bad_Missplaced": False,
        "EOF": False,
        "AUTO": False,
        "NODIALOGUE": False,
        "sys": SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True)),
        "Transcript_Input": transcript_input,
        "IDAT_DEEP_BEAM_WORKERS": None,
        "IDAT_DEEP_BEAM_GPU": None,
        "IDAT_DEEP_BEAM_BUDGET": "123456",
        "IDAT_FINAL_INVESTIGATION_BUDGET": "9999999",
        "IDAT_FINAL_INVESTIGATION_MAX_DEPTH": "41",
        "IDAT_FINAL_INVESTIGATION_SEED_LIMIT": "23",
        "IDAT_HUFFMAN_KRAFT_BUDGET": "1000001",
        "IDAT_HUFFMAN_KRAFT_WORKERS": "7",
        "IDAT_KRAFT_BACKREF_BUDGET": "250003",
        "IDAT_GLOBAL_CRC_RESIDUE_BUDGET": "750001",
        "IDAT_AFFINE_CORRUPTION_BUDGET": "250001",
        "IDAT_DEFLATE_SALVAGE_BUDGET": "250002",
        "IDAT_PREFINAL_REPAIR_CYCLES": "9",
        "IDAT_PREFINAL_REPAIR_BATCHES": "3",
        "GPU_CONFIG": gpu_config,
    }

    wrong_name = fixit_felix_runtime.build_wrong_chunk_name_runtime_from_namespace(namespace)
    no_next = fixit_felix_runtime.build_no_next_chunk_runtime_from_namespace(namespace)

    assert wrong_name.interactive is True
    assert wrong_name.input_func is transcript_input
    assert wrong_name.deep_beam_workers == "7"
    assert wrong_name.deep_beam_budget == "123456"
    assert wrong_name.deep_beam_gpu_config == gpu_config
    assert wrong_name.final_investigation_budget == "9999999"
    assert wrong_name.final_investigation_max_depth == "41"
    assert wrong_name.final_investigation_seed_limit == "23"
    assert wrong_name.huffman_kraft_budget == "1000001"
    assert wrong_name.huffman_kraft_workers == "7"
    assert wrong_name.huffman_kraft_gpu_config == gpu_config
    assert wrong_name.kraft_backref_budget == "250003"
    assert wrong_name.global_crc_residue_budget == "750001"
    assert wrong_name.affine_corruption_budget == "250001"
    assert wrong_name.deflate_salvage_budget == "250002"
    assert wrong_name.prefinal_repair_cycles == "9"
    assert wrong_name.prefinal_repair_batches == "3"
    assert no_next.interactive is True
    assert no_next.input_func is transcript_input
    assert no_next.deep_beam_workers == "7"
    assert no_next.deep_beam_budget == "123456"
    assert no_next.deep_beam_gpu_config == gpu_config
    assert no_next.final_investigation_budget == "9999999"
    assert no_next.final_investigation_max_depth == "41"
    assert no_next.final_investigation_seed_limit == "23"
    assert no_next.huffman_kraft_budget == "1000001"
    assert no_next.huffman_kraft_workers == "7"
    assert no_next.huffman_kraft_gpu_config == gpu_config
    assert no_next.kraft_backref_budget == "250003"
    assert no_next.global_crc_residue_budget == "750001"
    assert no_next.affine_corruption_budget == "250001"
    assert no_next.deflate_salvage_budget == "250002"
    assert no_next.prefinal_repair_cycles == "9"
    assert no_next.prefinal_repair_batches == "3"


def test_namespace_pipeline_builder_preserves_debug_and_repair_wiring():
    calls = []
    pandora_box = {"finding": {"IDAT_Tool_0": "tool-data"}}
    cornucopia = {}

    def callback(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return name

        return inner

    namespace = {
        "PRINT": callback("PRINT"),
        "Pause": callback("Pause"),
        "FixItFelix_Try_Automatic_Repair": callback("automatic_repair"),
        "FixItFelix_Wrong_Crc": callback("wrong_crc"),
        "FixItFelix_Libpng_Error": callback("libpng_error"),
        "FixItFelix_Wrong_Chunk_Name": callback("wrong_chunk_name"),
        "FixItFelix_No_NextChunk": callback("no_next_chunk"),
        "FixItFelix_Gama_Zero": callback("gama_zero"),
        "FixItFelix_Critical_Miss": callback("critical_miss"),
        "PandoraBox": pandora_box,
        "Cornucopia": cornucopia,
        "Skip_Bad_Crc": False,
        "Bad_Next_Name": False,
        "DEBUG": True,
        "PAUSEDEBUG": True,
    }
    for name in fixit_felix.DEBUG_FLAG_NAMES:
        namespace.setdefault(name, False)

    handlers = fixit_felix_runtime.build_legacy_fixit_felix_handlers_from_namespace(namespace)
    assert handlers.wrong_crc is namespace["FixItFelix_Wrong_Crc"]
    assert handlers.libpng_error is namespace["FixItFelix_Libpng_Error"]
    assert handlers.wrong_chunk_name is namespace["FixItFelix_Wrong_Chunk_Name"]
    assert handlers.no_next_chunk is namespace["FixItFelix_No_NextChunk"]
    assert handlers.gama_zero is namespace["FixItFelix_Gama_Zero"]
    assert handlers.critical_miss is namespace["FixItFelix_Critical_Miss"]

    fix_runtime = fixit_felix_runtime.build_fixit_felix_runtime_from_namespace(namespace)
    assert fix_runtime.try_automatic_repair("plte_cleanup") == "automatic_repair"
    assert fix_runtime.apply_finding_work_item(
        fixit_felix.FixItFelixWorkItem("finding", "wrong_crc", "finding"),
        "IDAT_Tool_",
        3,
        b"IDAT",
    ) == "wrong_crc"

    def runner(runtime, findings, *, skip_bad_crc, bad_next_name, chkd, chunk):
        calls.append(
            (
                "runner",
                (findings, skip_bad_crc, bad_next_name, chkd, chunk),
                {},
            )
        )
        assert runtime.try_automatic_repair("known_chunk_type_case") == "automatic_repair"
        assert runtime.apply_finding_work_item(
            fixit_felix.FixItFelixWorkItem("finding", "critical_miss", "finding"),
            chkd,
            1,
            chunk,
        ) == "critical_miss"
        return fixit_felix.FixItFelixRunResult(True, "pipeline-result")

    result = fixit_felix_runtime.run_fixit_felix_pipeline_from_namespace(
        namespace,
        b"IDAT",
        "IDAT_Tool_",
        runner=runner,
    )

    assert result == fixit_felix.FixItFelixRunResult(True, "pipeline-result")
    assert ("Pause", ("FixItFelix Debug Pause:",), {}) in calls
    assert (
        "runner",
        (pandora_box, False, False, "IDAT_Tool_", b"IDAT"),
        {},
    ) in calls
    assert any(call[0] == "PRINT" and str(call[1][0]).startswith("EOF:") for call in calls)


def main():
    checks = [
        ("Apply repair records note and writes clone", test_apply_repair_records_note_and_writes_clone),
        (
            "Automatic repair success explains private compression",
            test_automatic_repair_success_message_explains_private_compression,
        ),
        (
            "Automatic repair success prefers tRNS wording",
            test_automatic_repair_success_message_prefers_trns_over_plte_wording,
        ),
        (
            "Apply repair moves IDAT interruption after prompt",
            test_apply_repair_prompts_to_move_idat_interruption_before_writing_clone,
        ),
        (
            "Apply repair removes safe IDAT interruption when move declined",
            test_apply_repair_can_remove_safe_to_copy_idat_interruption_when_move_declined,
        ),
        (
            "Apply repair offers PLTE Tkinter controls",
            test_apply_repair_offers_tkinter_controls_after_empty_plte_preview,
        ),
        (
            "Apply repair keeps PLTE auto path without TTY",
            test_apply_repair_keeps_empty_plte_auto_path_without_interactive_tty,
        ),
        (
            "Apply repair offers malformed PLTE Tkinter controls",
            test_apply_repair_offers_tkinter_controls_after_malformed_plte_preview,
        ),
        (
            "Apply repair offers oversized black PLTE Tkinter controls",
            test_apply_repair_offers_tkinter_controls_after_oversized_black_plte_preview,
        ),
        (
            "Apply repair prompts to repair malformed duplicate sPLT",
            test_apply_repair_prompts_to_repair_malformed_duplicate_splt,
        ),
        (
            "Apply repair removes malformed duplicate sPLT when declined",
            test_apply_repair_can_remove_malformed_duplicate_splt_when_repair_declined,
        ),
        (
            "Apply repair prompts to remove all-transparent overlong tRNS",
            test_apply_repair_prompts_to_remove_all_transparent_overlong_trns_alpha_table,
        ),
        (
            "Apply repair trims overlong tRNS when removal declined",
            test_apply_repair_can_trim_overlong_trns_when_removal_declined,
        ),
        (
            "Apply repair declines zero-scanline blackfill",
            test_apply_repair_prompts_before_zero_scanline_blackfill_and_declines_placeholder,
        ),
        (
            "Apply repair confirms zero-scanline blackfill",
            test_apply_repair_can_write_zero_scanline_blackfill_when_confirmed,
        ),
        (
            "Apply repair offers SmashBruteBrawl after partial blackfill",
            test_apply_repair_parks_partial_blackfill_preview_before_source_idat_bruteforce,
        ),
        (
            "Partial blackfill low chance opens HephaestusForge",
            test_partial_blackfill_low_chance_opens_hephaestusforge,
        ),
        (
            "Partial blackfill Hephaestus prepares visual ROI",
            test_partial_blackfill_hephaestus_can_prepare_visual_reference_roi,
        ),
        (
            "Partial blackfill cheap missing uses Insert",
            test_partial_blackfill_cheap_missing_uses_insert,
        ),
        (
            "Partial blackfill cheap extra uses Remove",
            test_partial_blackfill_cheap_extra_uses_remove,
        ),
        (
            "Partial blackfill focus prompt default",
            test_partial_blackfill_focus_prompt_defaults_to_recommendation,
        ),
        (
            "Partial blackfill focus prompt override",
            test_partial_blackfill_focus_prompt_can_override_recommendation,
        ),
        (
            "Partial blackfill uses stored CRC only when useful",
            test_partial_blackfill_bruteforce_uses_stored_crc_only_when_it_targets_original,
        ),
        (
            "IDAT brute force target prefers bad CRC",
            test_idat_bruteforce_target_prefers_crc_bad_idat_chunk,
        ),
        (
            "Apply repair offers local IDAT donor",
            test_apply_repair_offers_local_idat_donor_before_black_placeholder,
        ),
        (
            "Apply repair offers synthetic IDAT without donor",
            test_apply_repair_offers_synthetic_idat_when_no_local_donor_exists,
        ),
        (
            "Apply repair prompts before unproven cHRM inference",
            test_apply_repair_prompts_before_unproven_chrm_inference,
        ),
        (
            "Apply repair removes short cHRM when inference declined",
            test_apply_repair_removes_short_chrm_when_inference_declined,
        ),
        (
            "Apply repair explains IHDR rebuild",
            test_apply_repair_explains_ihdr_rebuild_before_writing_clone,
        ),
        (
            "Apply repair explains IHDR value rebuild without CRC noise",
            test_apply_repair_explains_ihdr_value_rebuild_without_crc_noise,
        ),
        (
            "Automatic repair success message describes focused IDAT CRC forge",
            test_automatic_repair_success_message_describes_focused_idat_crc_forge,
        ),
        (
            "Apply repair rejects invalid IHDR rebuild",
            test_apply_repair_rejects_invalid_ihdr_rebuild_before_clone,
        ),
        (
            "Apply repair explains duplicate IHDR cut",
            test_apply_repair_explains_duplicate_ihdr_cut_without_rebuild_noise,
        ),
        (
            "IHDR stored CRC brute force uses loader",
            test_try_ihdr_stored_crc_bruteforce_uses_loader_and_writes_valid_candidate,
        ),
        (
            "IHDR stored CRC brute force decline",
            test_try_ihdr_stored_crc_bruteforce_decline_falls_back_to_rebuild,
        ),
        ("Apply gAMA zero discards false positive", test_apply_gama_zero_discards_false_positive_and_returns_legacy_target),
        ("Apply gAMA zero rejects unknown action", test_apply_gama_zero_rejects_unknown_action),
        ("Apply critical miss emits and pauses", test_apply_critical_miss_emits_and_pauses_on_debug_action),
        ("Apply critical miss continue skips pause", test_apply_critical_miss_continue_does_not_pause),
        ("Apply critical miss rejects unknown action", test_apply_critical_miss_rejects_unknown_action),
        (
            "Repeated deferred repair message templates",
            test_repeated_deferred_repair_message_templates_are_adaptable,
        ),
        ("Apply wrong CRC easy answer saves clone", test_apply_wrong_crc_easy_answer_saves_clone),
        (
            "Apply wrong CRC easy decline keeps skip none",
            test_apply_wrong_crc_easy_decline_then_final_decline_keeps_skip_none_and_saves,
        ),
        ("Deferred IDAT CRC route ignores error counter", test_deferred_idat_crc_route_key_ignores_error_counter),
        (
            "Deferred IDAT CRC route records structural state",
            test_deferred_idat_crc_route_records_structural_state,
        ),
        ("Apply wrong CRC skips deferred IDAT route", test_apply_wrong_crc_skips_question_for_deferred_idat_route),
        (
            "Apply wrong CRC records failed IDAT route",
            test_apply_wrong_crc_records_failed_idat_crc_route_when_patch_still_breaks,
        ),
        (
            "Apply wrong CRC defers invalid IDAT stream",
            test_apply_wrong_crc_defers_crc_only_when_idat_stream_stays_invalid,
        ),
        (
            "Apply wrong CRC writes improved IDAT deflate probe",
            test_apply_wrong_crc_writes_improved_deflate_probe_instead_of_crc_clone,
        ),
        (
            "HermesProbe logs deep beam diagnostic",
            test_hermesprobe_logs_dynamic_huffman_semantic_diagnostic_without_clone,
        ),
        (
            "HermesProbe interrupted deep beam stops",
            test_hermesprobe_interrupted_deep_beam_stops_instead_of_relaunching,
        ),
        (
            "HermesProbe resume deep beam skips short probes",
            test_hermesprobe_resume_deep_beam_skips_short_probes,
        ),
        (
            "HermesProbe resume mismatch runs short probes",
            test_hermesprobe_resume_mismatch_runs_short_probes,
        ),
        (
            "IDAT queue progress pads counters",
            test_runtime_idat_queue_progress_pads_counter_to_budget_width,
        ),
        (
            "HermesProbe prompts deep beam resources",
            test_hermesprobe_prompts_deep_beam_workers_and_gpu_when_unconfigured,
        ),
        (
            "HermesProbe prompts GPU with disabled default config",
            test_hermesprobe_deep_beam_options_prompt_gpu_when_disabled_config_default,
        ),
        (
            "HermesProbe deep GPU false overrides global config",
            test_hermesprobe_deep_beam_gpu_argument_overrides_enabled_global_config,
        ),
        (
            "HermesProbe deep beam advanced sizes",
            test_hermesprobe_deep_beam_advanced_sizes_are_runtime_options_not_prompts,
        ),
        (
            "HermesProbe deep beam invalid budget",
            test_hermesprobe_deep_beam_invalid_budget_falls_back_to_default,
        ),
        (
            "HermesProbe uses explicit deep beam config",
            test_hermesprobe_uses_explicit_deep_beam_workers_and_gpu_config_without_prompts,
        ),
        (
            "HermesProbe writes deep beam candidate",
            test_hermesprobe_writes_deep_beam_candidate_after_short_probes_stall,
        ),
        (
            "Apply wrong CRC focused IDAT CRC forge before blackfill",
            test_apply_wrong_crc_uses_focused_idat_crc_forge_before_blackfill,
        ),
        (
            "Apply wrong CRC heavy IDAT deflate probe loadingbar",
            test_apply_wrong_crc_uses_heavy_probe_loadingbar_after_quick_probe_fails,
        ),
        (
            "Apply wrong CRC heavy IDAT deflate probe decline",
            test_apply_wrong_crc_declines_heavy_probe_without_loadingbar_or_clone,
        ),
        ("Apply wrong CRC other errors defers", test_apply_wrong_crc_other_errors_defers_to_chunk_story),
        (
            "Apply wrong CRC saves clean IDAT CRC with other errors",
            test_apply_wrong_crc_other_errors_saves_clean_idat_crc_only_patch,
        ),
        (
            "Apply wrong CRC Cornucopia debug path",
            test_apply_wrong_crc_already_in_cornucopia_uses_debug_emit_without_tools,
        ),
        ("Apply wrong CRC rejects missing tools", test_apply_wrong_crc_rejects_missing_tools_for_action),
        ("Apply wrong CRC rejects unknown action", test_apply_wrong_crc_rejects_unknown_action),
        ("Wrong chunk name route ignores error counter", test_wrong_chunk_name_route_key_ignores_error_counter),
        (
            "Wrong chunk name route records structural state",
            test_wrong_chunk_name_route_records_structural_state,
        ),
        (
            "Wrong chunk name before first IDAT stays available",
            test_wrong_chunk_name_before_first_idat_does_not_block_name_repair,
        ),
        (
            "Apply wrong chunk name length probe accepts",
            test_apply_wrong_chunk_name_length_probe_accepts_nearby_chunk,
        ),
        (
            "Apply wrong chunk name length probe skips brute question",
            test_apply_wrong_chunk_name_length_probe_without_repair_skips_bruteforce_question,
        ),
        (
            "Apply wrong chunk name length probe deja-vu skips brute question",
            test_apply_wrong_chunk_name_length_probe_deja_vu_skips_bruteforce_question,
        ),
        ("Apply wrong chunk name bruteforce accepts", test_apply_wrong_chunk_name_bruteforce_accepts_brute_chunk),
        (
            "Apply wrong chunk name skips known route",
            test_apply_wrong_chunk_name_bruteforce_skips_known_route_without_question,
        ),
        (
            "Apply wrong chunk name IDAT chain fallback",
            test_apply_wrong_chunk_name_uses_idat_chain_batch_after_bruteforce_decline,
        ),
        (
            "IDAT chain chunk-name gate blocks dirty candidate",
            test_idat_chain_chunk_name_gate_blocks_unclean_realign_candidate,
        ),
        (
            "Apply wrong chunk name stops at IDAT convoy boundary",
            test_apply_wrong_chunk_name_stops_after_idat_chain_convoy_clone_boundary,
        ),
        (
            "IDAT convoy clone reuses existing Fixed file",
            test_idat_convoy_clone_reuses_existing_fixed_file,
        ),
        (
            "IDAT deep beam artifacts replace previous ranks",
            test_idat_deep_beam_debug_artifacts_replace_previous_rank_files,
        ),
        (
            "Apply wrong chunk name probes after aligned bad stream",
            test_apply_wrong_chunk_name_uses_deflate_probe_when_aligned_stream_is_bad,
        ),
        ("Apply wrong chunk name saves existing", test_apply_wrong_chunk_name_saves_existing_solution),
        (
            "Apply wrong chunk name rejects missing tools",
            test_apply_wrong_chunk_name_rejects_missing_tools_for_action,
        ),
        ("Apply wrong chunk name rejects unknown action", test_apply_wrong_chunk_name_rejects_unknown_action),
        (
            "Stop before libpng repairs sPLT invalid sample depth",
            test_stop_before_libpng_repairs_splt_invalid_sample_depth,
        ),
        (
            "Stop before libpng prompts to remove all-transparent overlong tRNS",
            test_stop_before_libpng_prompts_to_remove_all_transparent_overlong_trns_alpha_table,
        ),
        (
            "Stop before libpng repairs sTER invalid mode",
            test_stop_before_libpng_repairs_ster_invalid_mode,
        ),
        (
            "Stop before libpng repairs tEXt null bytes",
            test_stop_before_libpng_repairs_text_null_bytes,
        ),
        (
            "Stop before libpng repairs tIME value range",
            test_stop_before_libpng_repairs_time_value_range,
        ),
        (
            "Apply no-next false positive runs libpng",
            test_apply_no_next_false_positive_iend_runs_libpng_after_marking_eof,
        ),
        ("Apply no-next false positive clean cut", test_apply_no_next_false_positive_iend_writes_clean_cut),
        (
            "Apply no-next false positive infers before-IDAT repair",
            test_apply_no_next_false_positive_iend_infers_before_idat_repair_from_history,
        ),
        (
            "Apply no-next false positive infers before-PLTE repair",
            test_apply_no_next_false_positive_iend_infers_before_plte_repair_from_lowercase_missplaced,
        ),
        (
            "Apply no-next false positive repairs hIST before PLTE",
            test_apply_no_next_false_positive_iend_repairs_hist_before_plte_before_libpng,
        ),
        (
            "Apply no-next false positive repairs duplicate iCCP",
            test_apply_no_next_false_positive_iend_repairs_duplicate_iccp_before_libpng,
        ),
        (
            "Apply no-next false positive repairs duplicate IHDR",
            test_apply_no_next_false_positive_iend_repairs_duplicate_ihdr_before_libpng,
        ),
        (
            "Apply no-next false positive repairs duplicate pCAL",
            test_apply_no_next_false_positive_iend_repairs_duplicate_pcal_before_libpng,
        ),
        (
            "Apply no-next false positive blocks libpng with pending errors",
            test_apply_no_next_false_positive_iend_refuses_libpng_when_other_errors_remain,
        ),
        ("Apply no-next wrong IEND length rebuilds IEND", test_apply_no_next_wrong_iend_length_rebuilds_canonical_iend),
        ("Apply no-next appends dummy at CRC tail", test_apply_no_next_append_missing_iend_uses_dummy_at_crc_tail),
        (
            "Apply no-next replaces partial IEND tail",
            test_apply_no_next_append_missing_iend_replaces_partial_iend_tail,
        ),
        (
            "Apply no-next length probe replaces partial IEND tail",
            test_apply_no_next_length_probe_replaces_partial_iend_tail_before_nearby,
        ),
        (
            "Apply no-next IDAT chain batch",
            test_apply_no_next_uses_idat_chain_batch_before_iend_append,
        ),
        (
            "Apply no-next probes after aligned bad stream",
            test_apply_no_next_uses_deflate_probe_when_idat_chain_is_aligned_but_stream_is_bad,
        ),
        (
            "Apply no-next skips append after nearby IEND",
            test_apply_no_next_does_not_append_iend_when_nearby_already_found_one,
        ),
        ("Apply no-next length probe routes nearby", test_apply_no_next_ask_length_probe_routes_to_nearby_chunk),
        ("Apply no-next without IDAT evidence ends", test_apply_no_next_without_idat_evidence_stops_terminally),
        (
            "Apply no-next zero-dimension missing IDAT ends",
            test_apply_no_next_zero_dimension_missing_idat_stops_terminally,
        ),
        (
            "Apply no-next raw IDAT keeps probe",
            test_apply_no_next_raw_idat_bytes_keep_length_probe_available,
        ),
        ("Apply no-next rejects unknown action", test_apply_no_next_chunk_rejects_unknown_action),
        ("Apply libpng saves existing solution", test_apply_libpng_error_saves_existing_solution),
        ("Apply libpng accepts Relics prompt", test_apply_libpng_error_accepts_relics_prompt_and_sets_skip),
        ("Apply libpng declines Relics prompt", test_apply_libpng_error_declines_relics_prompt_and_ends),
        ("Apply libpng not enough image data ends", test_apply_libpng_error_not_enough_image_data_ends_after_todo),
        ("Apply libpng IDAT decision gate", test_apply_libpng_error_idat_gate_uses_partial_blackfill_decision),
        ("Apply libpng skip reports critical", test_apply_libpng_error_skip_only_reports_critical_hit),
        ("Apply libpng rejects unknown action", test_apply_libpng_error_rejects_unknown_action),
        ("Finding handlers route callback arguments", test_finding_handlers_route_legacy_callback_arguments),
        ("Apply finding work item dispatches", test_apply_finding_work_item_dispatches_through_fixit_felix_dispatch),
        ("Runtime uses automatic repair and callbacks", test_runtime_uses_automatic_repair_and_legacy_callbacks),
        ("Namespace runtime builders", test_namespace_runtime_builders_preserve_legacy_wiring),
        ("Namespace interactive prompts use stdin", test_namespace_interactive_prompts_uses_stdin_not_captured_stdout),
        (
            "Namespace convoy runtimes preserve deep beam options",
            test_namespace_idat_convoy_runtimes_preserve_deep_beam_prompt_options,
        ),
        ("Namespace pipeline builder", test_namespace_pipeline_builder_preserves_debug_and_repair_wiring),
    ]

    print("Running FixItFelix runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"FixItFelix runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
