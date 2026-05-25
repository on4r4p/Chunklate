#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import output, writer, writer_runtime


def clone_plan(*, save_count=1, max_saves_reached=False):
    return writer.CloneWritePlan(
        target=output.CloneTarget(
            name="sample.0_Fixed.png",
            directory="/tmp/Folder_sample",
            path="/tmp/Folder_sample/sample.0_Fixed.png",
        ),
        data=b"fixed",
        save_count=save_count,
        max_saves_reached=max_saves_reached,
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


def test_write_clone_runtime_writes_updates_state_and_summarises():
    calls = []
    side_notes = []
    runtime, state = build_runtime(calls, side_notes)

    result = writer_runtime.run_write_clone(runtime, base_context(), "89504e47", "summary")

    assert result is None
    assert ("remember",) in calls
    assert ("prepare", ("sample.png", "/tmp", "89504e47", 0, None)) in calls
    assert ("write", clone_plan()) in calls
    assert ("emit", "<green:-Saving to : /tmp/Folder_sample/sample.0_Fixed.png>") in calls
    assert ("summarise", "summary") in calls
    assert side_notes == ["-Saving to : /tmp/Folder_sample/sample.0_Fixed.png"]
    assert state == {
        "sample": "/tmp/Folder_sample/sample.0_Fixed.png",
        "save_count": 1,
        "have_a_kitkat": True,
    }


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

    assert ("pause", "-Saved Press Return to continue:") in calls
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


def main():
    checks = [
        ("Write and state", test_write_clone_runtime_writes_updates_state_and_summarises),
        ("Pause and max saves", test_write_clone_runtime_preserves_pause_and_max_saves_exit),
        ("Prepare error", test_write_clone_runtime_prepare_error_routes_betterror_and_end),
        ("Write error", test_write_clone_runtime_write_error_routes_betterror_emit_and_end),
    ]

    print("Running writer runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"writer runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
