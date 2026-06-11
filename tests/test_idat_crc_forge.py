#!/usr/bin/env python3
import struct
import zlib
import random
from types import SimpleNamespace

from chunklate import idat, idat_crc_forge, png


def _png_with_idat(payload: bytes) -> bytes:
    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        png.PNG_SIGNATURE
        + png.build_png_chunk(b"IHDR", ihdr)
        + png.build_png_chunk(b"IDAT", payload)
        + png.IEND_CHUNK
    )


def _idat(data: bytes) -> png.PngChunk:
    return next(chunk for chunk in png.iter_chunks(data) if chunk.chunk_type == b"IDAT")


def _with_stored_crc(data: bytes, stored_crc: bytes) -> bytes:
    chunk = _idat(data)
    crc_start = chunk.offset + 8 + chunk.length
    return data[:crc_start] + stored_crc + data[crc_start + 4 :]


def _bad_adler_missing5_fixture():
    rng = random.Random(20)
    raw = bytearray()
    for row in range(80):
        raw.append(row % 5)
        raw.extend(rng.randrange(256) for _ in range(128 * 3))
    payload = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack("!IIBBBBB", 128, 80, 8, 2, 0, 0, 0)
    good = (
        png.PNG_SIGNATURE
        + png.build_png_chunk(b"IHDR", ihdr)
        + png.build_png_chunk(b"IDAT", payload)
        + png.IEND_CHUNK
    )
    old_crc = _idat(good).crc.to_bytes(4, "big")
    offset = 50
    broken_payload = payload[:offset] + payload[offset + 5 :]
    broken = _with_stored_crc(
        png.PNG_SIGNATURE
        + png.build_png_chunk(b"IHDR", ihdr)
        + png.build_png_chunk(b"IDAT", broken_payload)
        + png.IEND_CHUNK,
        old_crc,
    )
    return good, broken, old_crc, offset, payload[offset : offset + 5]


def _bad_adler_missing4_fixture():
    good, _broken, old_crc, offset, _missing = _bad_adler_missing5_fixture()
    ihdr = next(chunk for chunk in png.iter_chunks(good) if chunk.chunk_type == b"IHDR").data
    payload = _idat(good).data
    broken_payload = payload[:offset] + payload[offset + 4 :]
    broken = _with_stored_crc(
        png.PNG_SIGNATURE
        + png.build_png_chunk(b"IHDR", ihdr)
        + png.build_png_chunk(b"IDAT", broken_payload)
        + png.IEND_CHUNK,
        old_crc,
    )
    return good, broken, old_crc, offset, payload[offset : offset + 4]


def _bad_adler_missing3_fixture():
    good, _broken, old_crc, offset, _missing = _bad_adler_missing5_fixture()
    ihdr = next(chunk for chunk in png.iter_chunks(good) if chunk.chunk_type == b"IHDR").data
    payload = _idat(good).data
    broken_payload = payload[:offset] + payload[offset + 3 :]
    broken = _with_stored_crc(
        png.PNG_SIGNATURE
        + png.build_png_chunk(b"IHDR", ihdr)
        + png.build_png_chunk(b"IDAT", broken_payload)
        + png.IEND_CHUNK,
        old_crc,
    )
    return good, broken, old_crc, offset, payload[offset : offset + 3]


def _stored_crc_missing_payload_fixture(byte_count: int, missing: bytes):
    prefix = bytes(range(40))
    suffix = bytes(range(80, 140))
    offset = len(prefix)
    payload = prefix + missing + suffix
    good = _png_with_idat(payload)
    old_crc = _idat(good).crc.to_bytes(4, "big")
    broken = _with_stored_crc(_png_with_idat(prefix + suffix), old_crc)
    return good, broken, old_crc, offset, payload[offset : offset + byte_count]


def _stored_crc_changed_payload_fixture(byte_count: int, original: bytes, changed: bytes):
    prefix = bytes(range(40))
    suffix = bytes(range(80, 140))
    offset = len(prefix)
    payload = prefix + original + suffix
    good = _png_with_idat(payload)
    old_crc = _idat(good).crc.to_bytes(4, "big")
    broken = _with_stored_crc(_png_with_idat(prefix + changed + suffix), old_crc)
    return good, broken, old_crc, offset, payload[offset : offset + byte_count]



def _first_matching_candidate(data: bytes, old_crc: bytes, *, edit: str, byte_count: int, offset: int):
    chunk = _idat(data)
    for candidate in idat_crc_forge.iter_forge_candidates(
        data,
        chunk,
        old_crc,
        edit_order=(edit,),
        byte_counts=(byte_count,),
        window_spec="%s:%s" % (offset, offset + 1),
        mode="force",
    ):
        if candidate.hit.png_bytes == _GOOD_PNG:
            return candidate
    raise AssertionError("matching CRC-forge candidate not found")


_GOOD_PAYLOAD = zlib.compress(b"\x00\x01\x02\x03")
_GOOD_PNG = _png_with_idat(_GOOD_PAYLOAD)
_GOOD_CHUNK = _idat(_GOOD_PNG)
_GOOD_CRC = _GOOD_CHUNK.crc.to_bytes(4, "big")


def test_insert4_crc_forge_recovers_contiguous_missing_bytes():
    offset = 3
    broken_payload = _GOOD_PAYLOAD[:offset] + _GOOD_PAYLOAD[offset + 4 :]
    broken = _with_stored_crc(_png_with_idat(broken_payload), _GOOD_CRC)

    candidate = _first_matching_candidate(broken, _GOOD_CRC, edit="insert", byte_count=4, offset=offset)

    assert candidate.hit.edit_kind == "insert"
    assert candidate.hit.brute_bytes == _GOOD_PAYLOAD[offset : offset + 4]
    assert candidate.hit.old_crc_match is True


def test_insert5_crc_forge_recovers_contiguous_missing_bytes():
    offset = 3
    broken_payload = _GOOD_PAYLOAD[:offset] + _GOOD_PAYLOAD[offset + 5 :]
    broken = _with_stored_crc(_png_with_idat(broken_payload), _GOOD_CRC)

    candidate = _first_matching_candidate(broken, _GOOD_CRC, edit="insert", byte_count=5, offset=offset)

    assert candidate.hit.edit_kind == "insert"
    assert candidate.hit.brute_bytes == _GOOD_PAYLOAD[offset : offset + 5]
    assert candidate.hit.old_crc_match is True


def test_insert6_crc_forge_recovers_contiguous_missing_bytes():
    offset = 2
    broken_payload = _GOOD_PAYLOAD[:offset] + _GOOD_PAYLOAD[offset + 6 :]
    broken = _with_stored_crc(_png_with_idat(broken_payload), _GOOD_CRC)

    candidate = _first_matching_candidate(broken, _GOOD_CRC, edit="insert", byte_count=6, offset=offset)

    assert candidate.hit.edit_kind == "insert"
    assert candidate.hit.brute_bytes == _GOOD_PAYLOAD[offset : offset + 6]


def test_replace5_crc_forge_recovers_contiguous_changed_bytes():
    offset = 3
    broken_payload = _GOOD_PAYLOAD[:offset] + b"\xff" * 5 + _GOOD_PAYLOAD[offset + 5 :]
    broken = _with_stored_crc(_png_with_idat(broken_payload), _GOOD_CRC)

    candidate = _first_matching_candidate(broken, _GOOD_CRC, edit="replace", byte_count=5, offset=offset)

    assert candidate.hit.edit_kind == "replace"
    assert candidate.hit.brute_bytes == _GOOD_PAYLOAD[offset : offset + 5]


def test_replace6_crc_forge_recovers_contiguous_changed_bytes():
    offset = 2
    broken_payload = _GOOD_PAYLOAD[:offset] + b"\xee" * 6 + _GOOD_PAYLOAD[offset + 6 :]
    broken = _with_stored_crc(_png_with_idat(broken_payload), _GOOD_CRC)

    candidate = _first_matching_candidate(broken, _GOOD_CRC, edit="replace", byte_count=6, offset=offset)

    assert candidate.hit.edit_kind == "replace"
    assert candidate.hit.brute_bytes == _GOOD_PAYLOAD[offset : offset + 6]


def test_remove5_crc_forge_recovers_contiguous_extra_bytes():
    offset = 3
    extra = b"extra"
    broken_payload = _GOOD_PAYLOAD[:offset] + extra + _GOOD_PAYLOAD[offset:]
    broken = _with_stored_crc(_png_with_idat(broken_payload), _GOOD_CRC)

    candidate = _first_matching_candidate(broken, _GOOD_CRC, edit="remove", byte_count=5, offset=offset)

    assert candidate.hit.edit_kind == "remove"
    assert candidate.hit.brute_bytes == extra


def test_small_seed_pass_tries_remove_even_when_replace_is_focused():
    offset = 3
    extra = b"\x00"
    broken_payload = _GOOD_PAYLOAD[:offset] + extra + _GOOD_PAYLOAD[offset:]
    broken = _with_stored_crc(_png_with_idat(broken_payload), _GOOD_CRC)

    for candidate in idat_crc_forge.iter_forge_candidates(
        broken,
        _idat(broken),
        _GOOD_CRC,
        edit_order=("replace",),
        byte_counts=(1,),
        window_spec="%s:%s" % (offset, offset + 1),
        mode="force",
    ):
        if candidate.hit.png_bytes == _GOOD_PNG:
            break
    else:
        raise AssertionError("small seed pass did not try the remove repair")

    assert candidate.hit.edit_kind == "remove"
    assert candidate.hit.brute_bytes == extra


def test_crc_forge_refuses_large_7_byte_window_without_force_budget():
    broken_payload = b"x" * 128
    broken = _with_stored_crc(_png_with_idat(broken_payload), _GOOD_CRC)
    summary = idat_crc_forge.explain_scan(
        broken,
        _idat(broken),
        edit_order=("insert",),
        byte_counts=(7,),
        window_spec="0:2",
        mode="auto",
        max_candidates=1_000,
    )

    assert summary.runnable is False
    assert "budget" in summary.reason


def test_clip_windows_to_candidate_budget_keeps_scanline_anchor_offsets():
    windows = (idat_crc_forge.ForgeWindow(100, 200, "scanline-anomaly"),)

    clipped = idat_crc_forge._clip_windows_to_candidate_budget(
        windows,
        "replace",
        6,
        10 * (65_536 + idat_crc_forge.REPLACE_SEED_TRANSFORM_COUNT),
    )

    assert clipped == (idat_crc_forge.ForgeWindow(102, 112, "scanline-anomaly"),)


def test_clip_windows_to_candidate_budget_anchors_large_free_prefixes():
    windows = (idat_crc_forge.ForgeWindow(100, 165, "scanline-anomaly"),)

    clipped = idat_crc_forge._clip_windows_to_candidate_budget(
        windows,
        "insert",
        9,
        idat_crc_forge.DEFAULT_MAX_CANDIDATES,
        free_index_limit=idat_crc_forge._auto_free_index_limit(9, mode="auto", explicit_windows=False),
    )

    assert clipped
    assert any(window.start <= 109 < window.end for window in clipped)
    assert sum(window.length for window in clipped) <= 5


def test_rank_scanline_windows_by_deflate_orders_nearest_output_first():
    windows = (
        idat_crc_forge.ForgeWindow(100, 165, "scanline-anomaly"),
        idat_crc_forge.ForgeWindow(200, 265, "scanline-anomaly"),
        idat_crc_forge.ForgeWindow(300, 365, "scanline-anomaly"),
        idat_crc_forge.ForgeWindow(400, 465, "scanline-anomaly"),
    )
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    original_trace = idat_crc_forge.deflate_probe.cached_analyze_deflate_stream
    try:
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            supported=True,
            scanline_size=10,
            usable_scanlines=5,
            height=10,
        )
        idat_crc_forge.deflate_probe.cached_analyze_deflate_stream = lambda *_args, **_kwargs: (
            idat_crc_forge.deflate_probe.DeflateTrace(
                status="complete",
                compressed_size=500,
                decompressed_size=100,
                checkpoints=(
                    idat_crc_forge.deflate_probe.DeflateCheckpoint(100, 800, 10, 0, 2),
                    idat_crc_forge.deflate_probe.DeflateCheckpoint(200, 1600, 20, 0, 2),
                    idat_crc_forge.deflate_probe.DeflateCheckpoint(300, 2400, 30, 0, 2),
                    idat_crc_forge.deflate_probe.DeflateCheckpoint(400, 3200, 40, 0, 2),
                ),
            )
        )

        ranked = idat_crc_forge._rank_scanline_windows_by_deflate(
            _GOOD_PNG,
            _GOOD_CHUNK,
            windows,
        )
    finally:
        idat_crc_forge.idat.analyze_idat_stream = original_analyze
        idat_crc_forge.deflate_probe.cached_analyze_deflate_stream = original_trace

    assert [window.start for window in ranked] == [300, 200, 400, 100]


def test_clamp_windows_for_operation_preserves_ranked_order():
    windows = (
        idat_crc_forge.ForgeWindow(300, 320, "scanline-anomaly"),
        idat_crc_forge.ForgeWindow(100, 120, "scanline-anomaly"),
        idat_crc_forge.ForgeWindow(200, 220, "scanline-anomaly"),
    )

    clamped = idat_crc_forge.clamp_windows_for_operation(windows, 500, "insert", 9)

    assert [window.start for window in clamped] == [300, 100, 200]


def test_auto_free_index_limit_keeps_7_byte_crc_forge_bounded():
    windows = (idat_crc_forge.ForgeWindow(100, 115, "scanline-anomaly"),)
    limit = idat_crc_forge._auto_free_index_limit(7, mode="auto", explicit_windows=False)

    assert limit == 4096
    assert idat_crc_forge.candidate_count(windows, "replace", 7, free_index_limit=limit) == 15 * (
        4096 + idat_crc_forge.REPLACE_SEED_TRANSFORM_COUNT
    )


def test_seed_candidates_cover_local_insert_replace_and_direct_remove_counts():
    payload = bytes.fromhex("01020304aabbccdd10203040")

    insert_seeds = idat_crc_forge._seed_candidates(payload, 4, 4, "insert")
    replace_seeds = idat_crc_forge._seed_candidates(payload, 4, 4, "replace")

    assert b"\x00\x00\x00\x00" in insert_seeds
    assert bytes.fromhex("01020304") in insert_seeds
    assert bytes.fromhex("aabbccdd") in insert_seeds
    assert replace_seeds == (bytes.fromhex("55443322"),)


def test_ranked_auto_windows_include_scanline_anomaly_for_bad_adler():
    _good, broken, _old_crc, offset, _missing = _bad_adler_missing5_fixture()
    analysis = idat.analyze_idat_stream(broken)

    windows = idat_crc_forge.ranked_auto_windows(broken, _idat(broken))

    assert analysis.status == "bad_adler"
    assert any(window.source == "scanline-anomaly" for window in windows)
    assert any(window.start <= offset < window.end for window in windows)


def test_auto_insert5_crc_forge_uses_scanline_anomaly_without_manual_window():
    good, broken, old_crc, offset, missing = _bad_adler_missing5_fixture()

    for candidate in idat_crc_forge.iter_forge_candidates(
        broken,
        _idat(broken),
        old_crc,
        edit_order=("insert",),
        byte_counts=(5,),
        mode="auto",
        zlib_prefilter=True,
    ):
        if candidate.hit.png_bytes == good:
            break
    else:
        raise AssertionError("auto CRC-forge did not find the scanline-anomaly candidate")

    assert candidate.hit.byte_position == offset
    assert candidate.hit.brute_bytes == missing


def test_auto_insert4_crc_forge_uses_scanline_anomaly_without_manual_window():
    good, broken, old_crc, offset, missing = _bad_adler_missing4_fixture()
    original_ranked = idat_crc_forge.ranked_auto_windows
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset, offset + 1, "scanline-anomaly"),
        )
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=("insert",),
            byte_counts=(4,),
            mode="auto",
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("auto CRC-forge did not find the 4-byte scanline-anomaly candidate")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked

    assert candidate.hit.byte_position == offset
    assert candidate.hit.brute_bytes == missing


def test_auto_insert4_runs_before_large_replace_focus_passes():
    good, broken, old_crc, offset, missing = _bad_adler_missing4_fixture()
    original_ranked = idat_crc_forge.ranked_auto_windows
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset, offset + 1, "scanline-anomaly"),
        )
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=("replace",),
            byte_counts=idat_crc_forge.TARGET_BYTE_COUNTS,
            mode="auto",
            zlib_prefilter=True,
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("replace focus did not try the direct 4-byte insertion")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked

    assert candidate.hit.edit_kind == "insert"
    assert candidate.hit.byte_position == offset
    assert candidate.hit.brute_bytes == missing


def test_auto_insert5_runs_before_large_replace_focus_passes():
    good, broken, old_crc, offset, missing = _bad_adler_missing5_fixture()
    original_ranked = idat_crc_forge.ranked_auto_windows
    original_scanline = idat_crc_forge.scanline_anomaly_windows
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset, offset + 1, "scanline-anomaly"),
        )
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset, offset + 1, "scanline-anomaly"),
        )
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            expected_size=100,
            decompressed_size=91,
        )
        plan = idat_crc_forge.focused_auto_plan(
            broken,
            _idat(broken),
            edit_order=("replace", "insert", "remove"),
            byte_counts=idat_crc_forge.TARGET_BYTE_COUNTS,
            focus="replace",
            edit_mode="Replace",
        )
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=plan.edit_order,
            byte_counts=plan.byte_counts,
            mode="auto",
            zlib_prefilter=False,
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("replace focus did not try the 5-byte insertion")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked
        idat_crc_forge.scanline_anomaly_windows = original_scanline
        idat_crc_forge.idat.analyze_idat_stream = original_analyze

    assert plan.edit_order == ("insert", "replace", "remove")
    assert plan.byte_counts[0] == 5
    assert candidate.hit.edit_kind == "insert"
    assert candidate.hit.byte_position == offset
    assert candidate.hit.brute_bytes == missing


def test_auto_insert7_runs_before_replace_focus_when_idat_output_is_short():
    good, broken, old_crc, offset, missing = _stored_crc_missing_payload_fixture(
        7,
        bytes.fromhex("0000057f7d6687"),
    )
    original_ranked = idat_crc_forge.ranked_auto_windows
    original_scanline = idat_crc_forge.scanline_anomaly_windows
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset - 4, offset + 5, "scanline-anomaly"),
        )
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset - 4, offset + 5, "scanline-anomaly"),
        )
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            expected_size=100,
            decompressed_size=39,
        )
        plan = idat_crc_forge.focused_auto_plan(
            broken,
            _idat(broken),
            edit_order=("replace", "insert", "remove"),
            byte_counts=idat_crc_forge.TARGET_BYTE_COUNTS,
            focus="replace",
            edit_mode="Replace",
        )
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=plan.edit_order,
            byte_counts=plan.byte_counts,
            mode="auto",
            zlib_prefilter=False,
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("replace focus did not try the 7-byte insertion")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked
        idat_crc_forge.scanline_anomaly_windows = original_scanline
        idat_crc_forge.idat.analyze_idat_stream = original_analyze

    assert plan.edit_order == ("insert", "replace", "remove")
    assert plan.byte_counts[:4] == (7, 8, 9, 10)
    assert candidate.hit.edit_kind == "insert"
    assert candidate.hit.byte_position == offset
    assert candidate.hit.brute_bytes == missing


def test_auto_insert8_scanline_clip_keeps_missing_position():
    good, broken, old_crc, offset, missing = _stored_crc_missing_payload_fixture(
        8,
        bytes.fromhex("0000057f7d668724"),
    )
    original_ranked = idat_crc_forge.ranked_auto_windows
    original_scanline = idat_crc_forge.scanline_anomaly_windows
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset - 4, offset + 61, "scanline-anomaly"),
        )
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset - 4, offset + 61, "scanline-anomaly"),
        )
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            expected_size=100,
            decompressed_size=31,
        )
        plan = idat_crc_forge.focused_auto_plan(
            broken,
            _idat(broken),
            edit_order=("replace", "insert", "remove"),
            byte_counts=(8,),
            focus="replace",
            edit_mode="Replace",
        )
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=plan.edit_order,
            byte_counts=plan.byte_counts,
            mode="auto",
            zlib_prefilter=False,
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("scanline clipping dropped the 8-byte insertion position")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked
        idat_crc_forge.scanline_anomaly_windows = original_scanline
        idat_crc_forge.idat.analyze_idat_stream = original_analyze

    assert candidate.hit.edit_kind == "insert"
    assert candidate.hit.byte_position == offset
    assert candidate.hit.brute_bytes == missing


def test_auto_insert9_expands_free_prefix_on_short_scanline_gap():
    good, broken, old_crc, offset, missing = _stored_crc_missing_payload_fixture(
        9,
        bytes.fromhex("0000002000abcdef01"),
    )
    original_ranked = idat_crc_forge.ranked_auto_windows
    original_scanline = idat_crc_forge.scanline_anomaly_windows
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset - 9, offset + 56, "scanline-anomaly"),
        )
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset - 9, offset + 56, "scanline-anomaly"),
        )
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            expected_size=100,
            decompressed_size=82,
        )
        plan = idat_crc_forge.focused_auto_plan(
            broken,
            _idat(broken),
            edit_order=("replace", "insert", "remove"),
            byte_counts=(9,),
            focus="replace",
            edit_mode="Replace",
        )
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=plan.edit_order,
            byte_counts=plan.byte_counts,
            mode="auto",
            zlib_prefilter=False,
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("9-byte insertion with a high free prefix was not found")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked
        idat_crc_forge.scanline_anomaly_windows = original_scanline
        idat_crc_forge.idat.analyze_idat_stream = original_analyze

    assert candidate.hit.edit_kind == "insert"
    assert candidate.hit.byte_position == offset
    assert candidate.hit.brute_bytes == missing
    assert candidate.free_index > 4096


def test_explicit_auto_window_keeps_9_byte_search_bounded():
    good, broken, old_crc, offset, missing = _stored_crc_missing_payload_fixture(
        9,
        bytes.fromhex("0000057f7d668724c6"),
    )
    progress = {"count": 0, "last": None}

    summary = idat_crc_forge.explain_scan(
        broken,
        _idat(broken),
        edit_order=("insert",),
        byte_counts=(9,),
        window_spec="%s:%s" % (offset, offset + 1),
        mode="auto",
    )

    assert summary.runnable is True
    assert summary.estimated_candidates < idat_crc_forge.DEFAULT_MAX_CANDIDATES

    for candidate in idat_crc_forge.iter_forge_candidates(
        broken,
        _idat(broken),
        old_crc,
        edit_order=("insert",),
        byte_counts=(9,),
        window_spec="%s:%s" % (offset, offset + 1),
        mode="auto",
        zlib_prefilter=False,
        progress_callback=lambda *args: progress.update(count=progress["count"] + 1, last=args),
    ):
        if candidate.hit.png_bytes == good:
            break
    else:
        raise AssertionError("explicit auto window did not find bounded 9-byte insertion")

    assert candidate.hit.brute_bytes == missing
    assert candidate.free_index == int.from_bytes(missing[:-4], "big")
    assert progress["last"] == ("insert", 9, offset, candidate.free_index, progress["count"])


def test_guided_free_prefix_runs_before_limited_numeric_search():
    guided_prefix = bytes.fromhex("0100000000")
    good, broken, old_crc, offset, missing = _stored_crc_missing_payload_fixture(
        9,
        guided_prefix + bytes.fromhex("abcdef01"),
    )
    seen_progress: list[tuple[str, int, int, int, int]] = []
    original_ranked = idat_crc_forge.ranked_auto_windows
    original_guided = idat_crc_forge._guided_free_prefix_candidates
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset, offset + 1, "scanline-anomaly"),
        )

        def guided(payload, position, free_len, trace, target_output_delta=None):
            if position == offset and free_len == len(guided_prefix):
                return (guided_prefix,)
            return ()

        idat_crc_forge._guided_free_prefix_candidates = guided
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=("insert",),
            byte_counts=(9,),
            mode="auto",
            zlib_prefilter=False,
            progress_callback=lambda *args: seen_progress.append(args),
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("guided free prefix was not tried before the limited numeric search")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked
        idat_crc_forge._guided_free_prefix_candidates = original_guided

    assert candidate.hit.brute_bytes == missing
    assert candidate.free_index == int.from_bytes(guided_prefix, "big")
    assert any(
        progress[3] == idat_crc_forge.DEFLATE_GUIDED_FREE_INDEX_MARKER
        for progress in seen_progress
    )


def test_guided_full_insert_runs_before_limited_numeric_search():
    missing = bytes.fromhex("0100000000abcdef01")
    good, broken, old_crc, offset, _missing = _stored_crc_missing_payload_fixture(9, missing)
    seen_progress: list[tuple[str, int, int, int, int]] = []
    original_ranked = idat_crc_forge.ranked_auto_windows
    original_guided = idat_crc_forge._guided_full_byte_candidates
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset, offset + 1, "scanline-anomaly"),
        )

        def guided(payload, position, byte_count, trace, target_output_delta=None, known_suffix_position=None):
            if position == offset and byte_count == len(missing):
                return (missing,)
            return ()

        idat_crc_forge._guided_full_byte_candidates = guided
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=("insert",),
            byte_counts=(9,),
            mode="auto",
            zlib_prefilter=False,
            progress_callback=lambda *args: seen_progress.append(args),
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("guided full insert bytes were not tried before numeric search")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked
        idat_crc_forge._guided_full_byte_candidates = original_guided

    assert candidate.hit.brute_bytes == missing
    assert candidate.free_index == idat_crc_forge.DEFLATE_GUIDED_FULL_INDEX_MARKER
    assert any(
        progress[3] == idat_crc_forge.DEFLATE_GUIDED_FULL_INDEX_MARKER
        for progress in seen_progress
    )


def test_guided_full_replace_runs_before_limited_numeric_search():
    original = bytes.fromhex("0100000000abcdef01")
    changed = bytes.fromhex("101112131415161718")
    good, broken, old_crc, offset, _original = _stored_crc_changed_payload_fixture(
        9,
        original,
        changed,
    )
    seen_progress: list[tuple[str, int, int, int, int]] = []
    original_ranked = idat_crc_forge.ranked_auto_windows
    original_guided = idat_crc_forge._guided_full_byte_candidates
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset, offset + 1, "scanline-anomaly"),
        )

        def guided(payload, position, byte_count, trace, target_output_delta=None, known_suffix_position=None):
            if position == offset and byte_count == len(original):
                return (original,)
            return ()

        idat_crc_forge._guided_full_byte_candidates = guided
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=("replace",),
            byte_counts=(9,),
            mode="auto",
            zlib_prefilter=False,
            progress_callback=lambda *args: seen_progress.append(args),
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("guided full replace bytes were not tried before numeric search")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked
        idat_crc_forge._guided_full_byte_candidates = original_guided

    assert candidate.hit.brute_bytes == original
    assert candidate.free_index == idat_crc_forge.DEFLATE_GUIDED_FULL_INDEX_MARKER
    assert any(
        progress[3] == idat_crc_forge.DEFLATE_GUIDED_FULL_INDEX_MARKER
        for progress in seen_progress
    )


def test_auto_insert3_seed_solver_uses_crc_without_bruteforce():
    good, broken, old_crc, offset, missing = _bad_adler_missing3_fixture()
    seen_progress: list[tuple[str, int, int, int, int]] = []
    original_ranked = idat_crc_forge.ranked_auto_windows
    try:
        idat_crc_forge.ranked_auto_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(offset, offset + 1, "scanline-anomaly"),
        )
        for candidate in idat_crc_forge.iter_forge_candidates(
            broken,
            _idat(broken),
            old_crc,
            edit_order=("insert",),
            byte_counts=(3,),
            mode="auto",
            zlib_prefilter=True,
            progress_callback=lambda *args: seen_progress.append(args),
        ):
            if candidate.hit.png_bytes == good:
                break
        else:
            raise AssertionError("auto CRC seed solver did not find the 3-byte insertion")
    finally:
        idat_crc_forge.ranked_auto_windows = original_ranked

    assert candidate.hit.byte_position == offset
    assert candidate.hit.brute_bytes == missing
    assert candidate.free_index == -1
    assert seen_progress[-1] == ("insert", 3, offset, -1, 1)


def test_focused_auto_plan_prioritizes_insert5_for_scanline_anomaly():
    original_windows = idat_crc_forge.scanline_anomaly_windows
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    try:
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(10, 20, "scanline-anomaly"),
        )
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            expected_size=100,
            decompressed_size=91,
        )

        plan = idat_crc_forge.focused_auto_plan(
            _GOOD_PNG,
            _GOOD_CHUNK,
            edit_order=("replace", "insert", "remove"),
            byte_counts=(5, 6, 7, 8, 9),
        )
    finally:
        idat_crc_forge.scanline_anomaly_windows = original_windows
        idat_crc_forge.idat.analyze_idat_stream = original_analyze

    assert plan.edit_order == ("insert",)
    assert plan.byte_counts == (5,)
    assert plan.reset_resume is True


def test_focused_auto_plan_prioritizes_replace_for_large_shortfall_scanline_anomaly():
    original_windows = idat_crc_forge.scanline_anomaly_windows
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    try:
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(10, 20, "scanline-anomaly"),
        )
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            expected_size=100,
            decompressed_size=78,
        )

        plan = idat_crc_forge.focused_auto_plan(
            _GOOD_PNG,
            _GOOD_CHUNK,
            edit_order=("replace", "insert", "remove"),
            byte_counts=(4, 5, 6, 7, 8, 9),
        )
    finally:
        idat_crc_forge.scanline_anomaly_windows = original_windows
        idat_crc_forge.idat.analyze_idat_stream = original_analyze

    assert plan.edit_order == ("replace",)
    assert plan.byte_counts == (9, 8, 7, 6, 5, 4)
    assert plan.reset_resume is True


def test_focused_auto_plan_honors_explicit_insert_focus():
    original_windows = idat_crc_forge.scanline_anomaly_windows
    try:
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(10, 20, "scanline-anomaly"),
        )

        plan = idat_crc_forge.focused_auto_plan(
            _GOOD_PNG,
            _GOOD_CHUNK,
            edit_order=("replace", "insert", "remove"),
            byte_counts=(4, 5, 6, 7, 8, 9),
            focus="insert",
            edit_mode="Insert",
        )
    finally:
        idat_crc_forge.scanline_anomaly_windows = original_windows

    assert plan.edit_order == ("insert",)
    assert plan.byte_counts == (7, 8, 9, 6, 5, 4)
    assert "insert focus" in plan.reason
    assert plan.reset_resume is True


def test_focused_auto_plan_honors_explicit_remove_focus():
    original_windows = idat_crc_forge.scanline_anomaly_windows
    try:
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(10, 20, "scanline-anomaly"),
        )

        plan = idat_crc_forge.focused_auto_plan(
            _GOOD_PNG,
            _GOOD_CHUNK,
            edit_order=("replace", "insert", "remove"),
            byte_counts=(4, 5, 6, 7, 8, 9),
            focus="remove",
            edit_mode="Remove",
        )
    finally:
        idat_crc_forge.scanline_anomaly_windows = original_windows

    assert plan.edit_order == ("remove",)
    assert plan.byte_counts == (7, 8, 9, 6, 5, 4)
    assert "remove focus" in plan.reason
    assert plan.reset_resume is True


def test_focused_auto_plan_progressive_uses_current_edit_mode_without_filename_hint():
    original_windows = idat_crc_forge.scanline_anomaly_windows
    try:
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(10, 20, "scanline-anomaly"),
        )

        plan = idat_crc_forge.focused_auto_plan(
            _GOOD_PNG,
            _GOOD_CHUNK,
            edit_order=("replace", "insert", "remove"),
            byte_counts=(4, 5, 6, 7, 8, 9),
            focus="progressive",
            edit_mode="Replace",
        )
    finally:
        idat_crc_forge.scanline_anomaly_windows = original_windows

    assert plan.edit_order == ("replace",)
    assert plan.byte_counts == (7, 8, 9, 6, 5, 4)
    assert "progressive focus" in plan.reason
    assert plan.reset_resume is True


def test_focused_auto_plan_prioritizes_insert4_for_small_scanline_gap():
    original_windows = idat_crc_forge.scanline_anomaly_windows
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    try:
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(10, 20, "scanline-anomaly"),
        )
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            expected_size=100,
            decompressed_size=92,
        )

        plan = idat_crc_forge.focused_auto_plan(
            _GOOD_PNG,
            _GOOD_CHUNK,
            edit_order=("replace", "insert", "remove"),
            byte_counts=(4, 5, 6, 7, 8, 9),
        )
    finally:
        idat_crc_forge.scanline_anomaly_windows = original_windows
        idat_crc_forge.idat.analyze_idat_stream = original_analyze

    assert plan.edit_order == ("insert",)
    assert plan.byte_counts == (4,)
    assert plan.reset_resume is True


def test_focused_auto_plan_prioritizes_remove5_for_extra_scanline_anomaly():
    original_windows = idat_crc_forge.scanline_anomaly_windows
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    try:
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(10, 20, "scanline-anomaly"),
        )
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            expected_size=100,
            decompressed_size=109,
        )

        plan = idat_crc_forge.focused_auto_plan(
            _GOOD_PNG,
            _GOOD_CHUNK,
            edit_order=("replace", "insert", "remove"),
            byte_counts=(5, 6, 7, 8, 9),
        )
    finally:
        idat_crc_forge.scanline_anomaly_windows = original_windows
        idat_crc_forge.idat.analyze_idat_stream = original_analyze

    assert plan.edit_order == ("remove",)
    assert plan.byte_counts == (5, 6, 7, 8, 9)
    assert plan.reset_resume is True


def test_focused_auto_plan_skips_when_small_gap_size_is_not_requested():
    original_windows = idat_crc_forge.scanline_anomaly_windows
    original_analyze = idat_crc_forge.idat.analyze_idat_stream
    try:
        idat_crc_forge.scanline_anomaly_windows = lambda *_args, **_kwargs: (
            idat_crc_forge.ForgeWindow(10, 20, "scanline-anomaly"),
        )
        idat_crc_forge.idat.analyze_idat_stream = lambda *_args, **_kwargs: SimpleNamespace(
            expected_size=100,
            decompressed_size=92,
        )

        plan = idat_crc_forge.focused_auto_plan(
            _GOOD_PNG,
            _GOOD_CHUNK,
            edit_order=("replace", "insert", "remove"),
            byte_counts=(5, 6, 7, 8, 9),
        )
    finally:
        idat_crc_forge.scanline_anomaly_windows = original_windows
        idat_crc_forge.idat.analyze_idat_stream = original_analyze

    assert plan.edit_order == ()
    assert plan.byte_counts == ()
    assert "outside the requested CRC-forge range" in plan.reason
    assert plan.reset_resume is True


def main():
    test_insert4_crc_forge_recovers_contiguous_missing_bytes()
    test_insert5_crc_forge_recovers_contiguous_missing_bytes()
    test_insert6_crc_forge_recovers_contiguous_missing_bytes()
    test_replace5_crc_forge_recovers_contiguous_changed_bytes()
    test_replace6_crc_forge_recovers_contiguous_changed_bytes()
    test_remove5_crc_forge_recovers_contiguous_extra_bytes()
    test_small_seed_pass_tries_remove_even_when_replace_is_focused()
    test_crc_forge_refuses_large_7_byte_window_without_force_budget()
    test_clip_windows_to_candidate_budget_keeps_scanline_anchor_offsets()
    test_clip_windows_to_candidate_budget_anchors_large_free_prefixes()
    test_rank_scanline_windows_by_deflate_orders_nearest_output_first()
    test_clamp_windows_for_operation_preserves_ranked_order()
    test_auto_free_index_limit_keeps_7_byte_crc_forge_bounded()
    test_seed_candidates_cover_local_insert_replace_and_direct_remove_counts()
    test_ranked_auto_windows_include_scanline_anomaly_for_bad_adler()
    test_auto_insert5_crc_forge_uses_scanline_anomaly_without_manual_window()
    test_auto_insert4_crc_forge_uses_scanline_anomaly_without_manual_window()
    test_auto_insert4_runs_before_large_replace_focus_passes()
    test_auto_insert5_runs_before_large_replace_focus_passes()
    test_auto_insert7_runs_before_replace_focus_when_idat_output_is_short()
    test_auto_insert8_scanline_clip_keeps_missing_position()
    test_auto_insert9_expands_free_prefix_on_short_scanline_gap()
    test_explicit_auto_window_keeps_9_byte_search_bounded()
    test_guided_free_prefix_runs_before_limited_numeric_search()
    test_guided_full_insert_runs_before_limited_numeric_search()
    test_guided_full_replace_runs_before_limited_numeric_search()
    test_auto_insert3_seed_solver_uses_crc_without_bruteforce()
    test_focused_auto_plan_prioritizes_insert5_for_scanline_anomaly()
    test_focused_auto_plan_prioritizes_replace_for_large_shortfall_scanline_anomaly()
    test_focused_auto_plan_honors_explicit_insert_focus()
    test_focused_auto_plan_honors_explicit_remove_focus()
    test_focused_auto_plan_progressive_uses_current_edit_mode_without_filename_hint()
    test_focused_auto_plan_prioritizes_insert4_for_small_scanline_gap()
    test_focused_auto_plan_prioritizes_remove5_for_extra_scanline_anomaly()
    test_focused_auto_plan_skips_when_small_gap_size_is_not_requested()


if __name__ == "__main__":
    main()
