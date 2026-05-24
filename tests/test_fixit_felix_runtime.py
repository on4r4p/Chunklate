#!/usr/bin/env python3
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import fixit_felix
from chunklate import fixit_felix_runtime


def test_apply_repair_records_note_and_writes_clone():
    side_notes = []
    writes = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
    )
    repair = SimpleNamespace(
        data=b"fixed",
        strategy="unit-test-repair",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert side_notes == ["-FixItFelix:unit-test-repair."]
    assert writes == [("6669786564", "-unit-test-repair.")]


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


def main():
    checks = [
        ("Apply repair records note and writes clone", test_apply_repair_records_note_and_writes_clone),
        ("Finding handlers route callback arguments", test_finding_handlers_route_legacy_callback_arguments),
        ("Apply finding work item dispatches", test_apply_finding_work_item_dispatches_through_fixit_felix_dispatch),
        ("Runtime uses automatic repair and callbacks", test_runtime_uses_automatic_repair_and_legacy_callbacks),
    ]

    print("Running FixItFelix runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"FixItFelix runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
