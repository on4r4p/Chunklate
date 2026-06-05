#!/usr/bin/env python3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import bruteforce, bruteforce_runtime, bruteforce_viewer


@dataclass
class FakeClock:
    value: datetime = datetime(2026, 5, 25, 10, 0, 0)

    def __call__(self):
        current = self.value
        self.value = self.value + timedelta(seconds=1)
        return current


def build_runtime(calls, *, specs, product_values, viewer_results=None, side_notes=None):
    side_notes = [] if side_notes is None else side_notes
    viewer_results = [] if viewer_results is None else list(viewer_results)

    def load_spec(request):
        calls.append(("load_spec", request))
        return specs(request)

    def product(chunk_data, color_type):
        calls.append(("product", tuple(chunk_data), color_type))
        return list(product_values)

    def loadingbar(max_iter, len_iter, current, start):
        calls.append(("loadingbar", max_iter, len_iter, current, start))

    def minibar(**kwargs):
        calls.append(("minibar", kwargs))

    def show_candidate(png_bytes, full_new_data, loop_index, debug_bytes):
        calls.append(("show_candidate", png_bytes, full_new_data, loop_index, debug_bytes))
        if viewer_results:
            return viewer_results.pop(0)
        return bruteforce_viewer.BruteForceViewerResult(False)

    def emit(message):
        calls.append(("emit", message))

    def pause(message):
        calls.append(("pause", message))

    return bruteforce_runtime.SmashBruteBrawlRuntime(
        load_spec=load_spec,
        product=product,
        loadingbar=loadingbar,
        minibar=minibar,
        show_candidate=show_candidate,
        emit=emit,
        pause=pause,
        side_notes=side_notes,
        raw_print=lambda *args, **kwargs: calls.append(("raw_print", args, kwargs)),
        now=FakeClock(),
    )


def base_context(**updates):
    context = {
        "file": "broken.png",
        "chunk_name": b"gAMA",
        "chunk_length": 1,
        "data_offset": 8,
        "from_error": "Relics",
        "data_hex": "00112233445566778899aabbccddeeff00112233445566778899",
        "pandora_box": {},
        "edit_mode": "Replace",
        "bf_mode": "Brutus",
        "brute_crc": True,
        "brute_length": True,
        "old_crc": False,
        "brute_level": 0,
        "crash": False,
        "debug": False,
        "pause_debug": False,
    }
    context.update(updates)
    return bruteforce_runtime.SmashBruteBrawlContext(**context)


def simple_specs(request):
    if request.fields:
        return (2, ("B",))
    return (2, 1, 2, ("B",), [(7,)], "color")


def test_run_scan_preserves_oldcrc_path_without_viewer():
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    runtime = build_runtime(calls, specs=simple_specs, product_values=[(7,)])

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(chunk_name=chunk_name, old_crc=old_crc),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.old_crc == bytes.fromhex(old_crc)
    assert result.full_new_data == (
        b"\x00\x00\x00\x01" + chunk_name + b"\x07" + bytes.fromhex(old_crc)
    )
    assert result.to_brute == "cc"
    assert result.bf_mode == "Brutus"
    assert result.crash is False
    assert not [call for call in calls if call[0] == "show_candidate"]
    assert ("loadingbar", 2, 1, None, True) in calls
    assert ("loadingbar", 2, 1, 0, False) in calls


def test_run_scan_preserves_viewer_acceptance_gate_and_diff():
    calls = []

    def specs(request):
        if request.fields:
            return (2, ("B",))
        return (2, 2, 2, ("B",), [(1,), (2,)], "color")

    runtime = build_runtime(
        calls,
        specs=specs,
        product_values=[(1,), (2,)],
        viewer_results=[
            bruteforce_viewer.BruteForceViewerResult(False),
            bruteforce_viewer.BruteForceViewerResult(True, "accepted-diff"),
        ],
    )

    result = bruteforce_runtime.run_scan(runtime, base_context())

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.diff == "accepted-diff"
    assert result.full_new_data.startswith(b"\x00\x00\x00\x01gAMA\x02")
    assert [call[0] for call in calls].count("show_candidate") == 2
    assert ("loadingbar", 2, 2, 0, False) in calls
    assert ("loadingbar", 2, 2, 1, False) in calls


def test_run_scan_preserves_twobytes_oldcrc_path():
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    runtime = build_runtime(calls, specs=simple_specs, product_values=[(7,)])

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(
            chunk_name=chunk_name,
            chunk_length=1,
            data_hex="0011223300aabbccddeeff",
            bf_mode="TwoBytes",
            old_crc=old_crc,
        ),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.full_new_data == (
        b"\x00\x00\x00\x01" + chunk_name + b"\x07" + bytes.fromhex(old_crc)
    )
    assert result.to_brute == "00"
    assert [call[0] for call in calls].count("show_candidate") == 0
    assert ("minibar", {"Indication": "0/2"}) not in calls
    assert (
        "raw_print",
        ("0/2 byte 1/1 .\033[K",),
        {"end": "\r", "flush": True},
    ) in calls


def test_twobytes_progress_dots_line_fills_and_returns():
    prefix = "0/256 byte 1/149210 "
    start = bruteforce_runtime.twobytes_progress_dots_line(
        prefix,
        position=0,
        terminal_width=len(prefix) + 6,
    )
    filled = bruteforce_runtime.twobytes_progress_dots_line(
        prefix,
        position=4 * 1024,
        terminal_width=len(prefix) + 6,
    )
    returning = bruteforce_runtime.twobytes_progress_dots_line(
        prefix,
        position=7 * 1024,
        terminal_width=len(prefix) + 6,
    )

    assert start == prefix + ".\033[K"
    assert filled == prefix + ".....\033[K"
    assert returning == prefix + "...\033[K"


def test_twobytes_progress_dots_line_clamps_to_short_terminal_width():
    assert bruteforce_runtime.twobytes_progress_dots_line(
        "0/256 byte 1/149210 ",
        position=0,
        terminal_width=5,
    ) == "0/256 byte 1/149210 \033[K"


def test_run_scan_preserves_crash_resume_skip_and_reset():
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x08").hex()
    runtime = build_runtime(calls, specs=simple_specs, product_values=[(7,), (8,)])

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(chunk_name=chunk_name, old_crc=old_crc, crash=1),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.crash is False
    assert result.full_new_data == (
        b"\x00\x00\x00\x01" + chunk_name + b"\x08" + bytes.fromhex(old_crc)
    )
    assert ("loadingbar", 2, 1, 0, False) not in calls
    assert ("loadingbar", 2, 1, 1, False) in calls


def main():
    checks = [
        ("OldCrc scan", test_run_scan_preserves_oldcrc_path_without_viewer),
        ("Viewer scan", test_run_scan_preserves_viewer_acceptance_gate_and_diff),
        ("TwoBytes scan", test_run_scan_preserves_twobytes_oldcrc_path),
        ("TwoBytes dots", test_twobytes_progress_dots_line_fills_and_returns),
        ("TwoBytes short terminal", test_twobytes_progress_dots_line_clamps_to_short_terminal_width),
        ("Crash resume", test_run_scan_preserves_crash_resume_skip_and_reset),
    ]

    print("Running bruteforce runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"bruteforce runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
