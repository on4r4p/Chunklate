#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import spec_length_runtime


def build_runtime(calls, side_notes=None, spec_value=26):
    if side_notes is None:
        side_notes = []

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    def get_spec(*args, **kwargs):
        calls.append(("get_spec", args, kwargs))
        return [spec_value]

    return spec_length_runtime.SpecLengthRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        end=lambda: calls.append(("end",)),
        get_spec=get_spec,
        side_notes=side_notes,
    )


def test_spec_length_runtime_returns_spec_length_without_input():
    calls = []
    runtime = build_runtime(calls)

    result = spec_length_runtime.run_spec_length(runtime, b"IHDR")

    assert result == "0000000d"
    assert ("get_spec", (b"IHDR", "Spec"), {"Fields": ["Length"]}) in calls
    assert not [call for call in calls if call[0] == "emit"]


def test_spec_length_runtime_records_matching_length():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)

    result = spec_length_runtime.run_spec_length(runtime, b"IHDR", "0000000d")

    assert result == "0000000d"
    assert ("candy", ("Title", "Get Length from Spec:")) in calls
    assert ("candy", ("Cowsay", "Looks good to me !", "good")) in calls
    assert ("emit", "-Real b'IHDR' Length: 0000000d ") in calls
    assert side_notes == ["-SpecLength:Giving correct length:  0000000d -"]


def test_spec_length_runtime_repairs_corrupted_length():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)

    result = spec_length_runtime.run_spec_length(runtime, b"IHDR", "ffffffff")

    assert result == "0000000d"
    assert ("candy", ("Cowsay", "Length part is corrupted!", "bad")) in calls
    assert ("emit", "-Given b'IHDR' Length was : ffffffff ") in calls
    assert ("emit", "\n-Returning correct fixed length :0000000d") in calls
    assert side_notes == ["-SpecLength:Giving correct length:  0000000d -"]


def test_spec_length_runtime_preserves_tuple_spec_fallback_when_end_returns():
    calls = []
    runtime = build_runtime(calls, spec_value=(1, 2))

    result = spec_length_runtime.run_spec_length(runtime, b"tEXt", "00000000")

    assert result is None
    assert ("emit", "<yellow:\n-ToDotuple>") in calls
    assert ("emit", "<yellow:\n-Requested Spec b'tEXt' has not been found.>") in calls
    assert ("emit", "<yellow:\n-ToDo>") in calls
    assert calls.count(("end",)) == 2


def main():
    checks = [
        ("No input", test_spec_length_runtime_returns_spec_length_without_input),
        ("Matching length", test_spec_length_runtime_records_matching_length),
        ("Repair length", test_spec_length_runtime_repairs_corrupted_length),
        ("Tuple fallback", test_spec_length_runtime_preserves_tuple_spec_fallback_when_end_returns),
    ]

    print("Running spec length runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"spec length runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
