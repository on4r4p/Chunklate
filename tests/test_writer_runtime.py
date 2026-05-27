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


def clone_patch_runtime(calls, *, data_hex="0011223344556677"):
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
    assert ("write_clone", "0011aabb556677", "infos") in calls


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
    assert ("write_clone", "0011494441546677", b"IDA^") in calls


def test_run_save_clone_preserves_bad_hex_error_path_before_write():
    calls = []
    runtime, state = clone_patch_runtime(calls)

    result = writer_runtime.run_save_clone(runtime, "not-hex", 4, 10, "infos")

    assert result == "written"
    assert state == {"show_must_go_on": True}
    assert any(call[0] == "betterror" and call[2] == "SaveClone" for call in calls)
    assert ("write_clone", "0011not-hex556677", "infos") in calls


def main():
    checks = [
        ("Write builders", test_write_clone_builders_wire_namespace_and_context),
        ("Write namespace bridge", test_write_clone_namespace_bridge_builds_runtime_and_context),
        ("Write and state", test_write_clone_runtime_writes_updates_state_and_summarises),
        ("Pause and max saves", test_write_clone_runtime_preserves_pause_and_max_saves_exit),
        ("Prepare error", test_write_clone_runtime_prepare_error_routes_betterror_and_end),
        ("Write error", test_write_clone_runtime_write_error_routes_betterror_emit_and_end),
        ("Remove chunk", test_run_remove_chunk_builds_fixed_data_and_writes_clone),
        ("Save clone", test_run_save_clone_builds_fixed_data_sets_flag_and_writes_clone),
        ("Save clone named patch", test_run_save_clone_explains_named_patch_when_source_is_bytes),
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
