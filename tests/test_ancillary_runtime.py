#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import ancillary_runtime


def build_runtime(calls):
    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    return ancillary_runtime.AncillaryRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
    )


def test_run_ancillary_check_reports_valid_semantics_and_returns_true():
    calls = []

    result = ancillary_runtime.run_ancillary_check(build_runtime(calls), b"gAMa")

    assert result is True
    assert ("candy", ("Title", "Ancillary Check:", "<white:b'gAMa'>")) in calls
    assert ("emit", "-[gAMa] <green:Seems to be Following> Chunks's naming conventions") in calls
    assert ("candy", ("Cowsay", "If this is a real Chunk this means that gAMa is :", "good")) in calls
    assert ("emit", "-<green:g>:<yellow:Not Critical>") in calls
    assert ("emit", "-<green:A>:<yellow:Private>") in calls
    assert ("emit", "-<green:M>:<yellow:Conform to PNG specifications>") in calls
    assert ("emit", "-<green:a>:<yellow:Safe to Copy>") in calls


def test_run_ancillary_check_reports_invalid_name_and_returns_false():
    calls = []

    result = ancillary_runtime.run_ancillary_check(build_runtime(calls), "AB1D")

    assert result is False
    assert ("betterror", "'str' object has no attribute 'decode'", "Ancillary") in calls
    assert ("emit", "-[AB1D] is <red:Not Following> Chunks's naming conventions") in calls
    assert (
        "candy",
        (
            "Cowsay",
            "Meaning that could be an unknown private chunk that got corrupt .....Or a Known chunk that got corrupt ...",
            "com",
        ),
    ) in calls
    assert ("candy", ("Cowsay", "..Or Not even a chunk's name at all ...", "bad")) in calls


def main():
    checks = [
        ("valid semantics", test_run_ancillary_check_reports_valid_semantics_and_returns_true),
        ("invalid semantics", test_run_ancillary_check_reports_invalid_name_and_returns_false),
    ]

    print("Running ancillary runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"ancillary runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
