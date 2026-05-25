#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import getspec_runtime, specs


class FakeDateTime:
    @classmethod
    def now(cls):
        return type("Now", (), {"year": 2030})()


def build_runtime(calls, *, idat_count=640, max_resolution=100):
    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    return getspec_runtime.GetSpecRuntime(
        emit=lambda message: calls.append(("emit", message)),
        candy=candy,
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        pause=lambda message: calls.append(("pause", message)),
        end=lambda: calls.append(("end",)),
        max_resolution=lambda: calls.append(("max_resolution",)) or max_resolution,
        refresh_idat_byte_count=lambda: calls.append(("refresh_idat_byte_count",)) or idat_count,
        current_year=lambda: 2026,
    )


def base_context(**updates):
    values = {
        "idat_byte_count": 640,
        "brute_level": 0,
        "ihdr_color": "2",
        "ihdr_height": 10,
        "ihdr_width": 10,
        "pandora_box": {},
        "cornucopia": {},
        "pandemonium": {},
        "allchunks": (b"IHDR", b"IDAT", b"IEND"),
        "skip_bad_crc": False,
    }
    values.update(updates)
    return getspec_runtime.GetSpecContext(**values)


def test_getspec_runtime_returns_resolved_spec_fields():
    calls = []

    result = getspec_runtime.run_getspec(
        build_runtime(calls),
        base_context(),
        b"IHDR",
        "Spec",
        ["Length"],
    )

    assert result == (26,)
    assert ("max_resolution",) in calls
    assert ("refresh_idat_byte_count",) not in calls


def test_getspec_runtime_refreshes_empty_idat_byte_count():
    calls = []

    result = getspec_runtime.run_getspec(
        build_runtime(calls, idat_count=640),
        base_context(idat_byte_count=0),
        b"IHDR",
        "Spec",
        ["Length"],
    )

    assert result == (26,)
    assert ("refresh_idat_byte_count",) in calls


def test_getspec_runtime_preserves_debug_output():
    calls = []

    result = getspec_runtime.run_getspec(
        build_runtime(calls),
        base_context(debug=True),
        b"IHDR",
        "Spec",
        ["Length"],
    )

    assert result == (26,)
    assert ("emit", "GetChunk:b'IHDR'") in calls
    assert ("emit", "Mode:Spec") in calls
    assert ("emit", "Fields:['Length']") in calls
    assert ("emit", "-ColorType set to:colortype:2:minres") in calls
    assert ("emit", "-Smalest resolution estimation based on file size: 10*10") in calls


def test_getspec_runtime_missing_spec_emits_legacy_todo():
    calls = []

    result = getspec_runtime.run_getspec(
        build_runtime(calls),
        base_context(),
        b"NOPE",
        "Spec",
        ["Length"],
    )

    assert result is None
    assert ("emit", "-Error in GetSpec: Didnt Found matching result") in calls
    assert ("emit", "GetColor:nocolortype") in calls
    assert ("emit", "GetChunk:b'NOPE'") in calls
    assert ("emit", "<yellow:\n-ToDo>") in calls


def test_getspec_runtime_resolve_error_routes_legacy_debug_pause_and_end():
    calls = []
    original = specs.resolve_getspec

    def boom(*args, **kwargs):
        raise ValueError("bad spec")

    specs.resolve_getspec = boom
    try:
        result = getspec_runtime.run_getspec(
            build_runtime(calls),
            base_context(debug=True, pause_error=True),
            b"IHDR",
            "Spec",
            ["Length"],
        )
    finally:
        specs.resolve_getspec = original

    assert result is None
    assert ("betterror", "bad spec", "GetSpec") in calls
    assert ("pause", "Pause Debug") in calls
    assert ("end",) in calls


def test_getspec_namespace_helper_builds_runtime_context_and_preserves_args():
    calls = []
    namespace = {
        "PRINT": lambda message: calls.append(("emit", message)),
        "Candy": lambda *args: calls.append(("candy", args)) or "candy",
        "Betterror": lambda *args: calls.append(("betterror", args)),
        "Pause": lambda message: calls.append(("pause", message)),
        "TheEnd": lambda: calls.append(("end",)),
        "Max_Res": lambda: calls.append(("max_resolution",)) or 500,
        "IDAT_Bytes_Nbr": lambda: calls.append(("idat_bytes",)) or 640,
        "datetime": FakeDateTime,
        "IBN": 123,
        "Brute_LvL": 4,
        "IHDR_Color": "3",
        "IHDR_Height": 20,
        "IHDR_Width": 30,
        "PandoraBox": {"pandora": True},
        "Cornucopia": {"corn": True},
        "Pandemonium": {"panic": True},
        "ALLCHUNKS": [b"IHDR", b"IDAT"],
        "Skip_Bad_Crc": True,
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": True,
    }

    def runner(runtime, context, get_chunk, mode, fields, struct_index, iter_count):
        assert runtime.emit is namespace["PRINT"]
        assert runtime.candy is namespace["Candy"]
        assert runtime.betterror is namespace["Betterror"]
        assert runtime.pause is namespace["Pause"]
        assert runtime.end is namespace["TheEnd"]
        assert runtime.max_resolution() == 500
        assert runtime.refresh_idat_byte_count() == 640
        assert runtime.current_year() == 2030
        assert context.idat_byte_count == 123
        assert context.brute_level == 4
        assert context.ihdr_color == "3"
        assert context.ihdr_height == 20
        assert context.ihdr_width == 30
        assert context.pandora_box == {"pandora": True}
        assert context.cornucopia == {"corn": True}
        assert context.pandemonium == {"panic": True}
        assert context.allchunks == (b"IHDR", b"IDAT")
        assert context.skip_bad_crc is True
        assert context.debug is True
        assert context.pause_debug is False
        assert context.pause_error is True
        assert (get_chunk, mode, fields, struct_index, iter_count) == (
            b"IHDR",
            "Spec",
            ["Length"],
            1,
            2,
        )
        return "spec"

    result = getspec_runtime.run_getspec_from_namespace(
        namespace,
        b"IHDR",
        "Spec",
        ["Length"],
        1,
        2,
        runner=runner,
    )

    assert result == "spec"
    assert ("max_resolution",) in calls
    assert ("idat_bytes",) in calls


def main():
    checks = [
        ("Resolved spec", test_getspec_runtime_returns_resolved_spec_fields),
        ("Refresh IDAT byte count", test_getspec_runtime_refreshes_empty_idat_byte_count),
        ("Debug output", test_getspec_runtime_preserves_debug_output),
        ("Missing spec", test_getspec_runtime_missing_spec_emits_legacy_todo),
        ("Resolve error", test_getspec_runtime_resolve_error_routes_legacy_debug_pause_and_end),
        ("Namespace bridge", test_getspec_namespace_helper_builds_runtime_context_and_preserves_args),
    ]

    print("Running GetSpec runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"GetSpec runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
