#!/usr/bin/env python3
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import cli, main_runtime, runtime_state


class ExitReached(Exception):
    def __init__(self, code):
        self.code = code


class FakeParser:
    def __init__(self, calls):
        self.calls = calls

    def print_help(self, stream):
        self.calls.append(("print_help", stream))


def args(**updates):
    values = {
        "FILENAME": "sample.png",
        "OUTPUT_DIR": None,
        "MAX_SAVES": None,
        "CLEAR": False,
        "PAUSE": False,
        "PAUSEDEBUG": False,
        "PAUSEERROR": False,
        "PAUSEDIALOGUE": False,
        "NODIALOGUE": False,
        "DEBUG": False,
        "AUTO": False,
    }
    values.update(updates)
    return SimpleNamespace(**values)


def build_runtime(calls, *, exit_raises=True):
    def exit_process(code):
        calls.append(("exit", code))
        if exit_raises:
            raise ExitReached(code)

    return main_runtime.MainCliOptionsRuntime(
        print_error=lambda message: calls.append(("print", message)),
        exit_process=exit_process,
        make_dirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        abspath=lambda path: "/abs/" + path,
        join=lambda *parts: "/".join(parts),
        stderr="stderr",
    )


def apply_options(calls, parsed_args=None, unknown=(), argv_len=2):
    if parsed_args is None:
        parsed_args = args()
    return main_runtime.apply_main_cli_options(
        build_runtime(calls),
        parsed_args,
        unknown,
        argv_len=argv_len,
        parser=FakeParser(calls),
        current_cloneswar=False,
        current_crash=False,
    )


def test_apply_main_cli_options_builds_initial_state():
    calls = []

    state = apply_options(
        calls,
        args(OUTPUT_DIR="out", MAX_SAVES=2, PAUSEDEBUG=True),
    )

    assert state == main_runtime.MainCliOptionsState(
        file_origin="sample.png",
        file_dir="/abs/out/",
        runtime_flags=cli.RuntimeFlags(
            clear=False,
            pause=False,
            pause_debug=True,
            pause_error=False,
            pause_dialogue=False,
            nodialogue=False,
            debug=True,
            auto=False,
        ),
        max_saves=2,
        save_count=0,
        sample="sample.png",
        cloneswar=False,
        crash=False,
    )
    assert ("makedirs", "/abs/out/", {"exist_ok": True}) in calls


def test_apply_main_cli_options_preserves_legacy_unknown_clone_and_crash():
    calls = []

    state = apply_options(calls, unknown=["--CLONE", "Folder/sample.png", "--crash", "3"])

    assert state.cloneswar == "Folder/sample.png --crash 3"
    assert state.crash == 3


def test_apply_main_cli_options_exits_on_invalid_crash():
    calls = []

    try:
        apply_options(calls, unknown=["--crash", "nope"])
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("invalid crash should exit")

    assert ("print", "--crash arguments must be a number.") in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_prints_help_without_args():
    calls = []

    try:
        apply_options(calls, argv_len=1)
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("missing argv should exit")

    assert ("print_help", "stderr") in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_without_filename():
    calls = []

    try:
        apply_options(calls, args(FILENAME=None))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("missing filename should exit")

    assert ("print", "-f,--filename arguments is missing.") in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_on_bad_max_saves():
    calls = []

    try:
        apply_options(calls, args(MAX_SAVES=0))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad max saves should exit")

    assert ("print", "--max-saves arguments must be greater than zero.") in calls
    assert ("exit", 1) in calls


def test_legacy_globals_from_main_cli_options_maps_runtime_flags():
    state = main_runtime.MainCliOptionsState(
        file_origin="sample.png",
        file_dir="/tmp/",
        runtime_flags=cli.RuntimeFlags(
            clear=True,
            pause=True,
            pause_debug=False,
            pause_error=True,
            pause_dialogue=False,
            nodialogue=False,
            debug=True,
            auto=False,
        ),
        max_saves=4,
        save_count=0,
        sample="sample.png",
        cloneswar="clone.png",
        crash=9,
    )

    assert main_runtime.legacy_globals_from_main_cli_options(state) == {
        "FILE_Origin": "sample.png",
        "FILE_DIR": "/tmp/",
        "CLEAR": True,
        "PAUSE": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": True,
        "PAUSEDIALOGUE": False,
        "NODIALOGUE": False,
        "DEBUG": True,
        "AUTO": False,
        "MAX_SAVES": 4,
        "SAVE_COUNT": 0,
        "Sample": "sample.png",
        "CLONESWAR": "clone.png",
        "CRASH": 9,
    }


def test_reset_main_loop_state_updates_legacy_globals_and_preserves_local_tmp_fixihdr():
    calls = []
    namespace = {"TmpFixIHDR": "global value"}

    reset_state = main_runtime.reset_main_loop_state(
        main_runtime.MainLoopResetRuntime(
            namespace=namespace,
            reset_chunk_info_idat=lambda: calls.append(("reset_idat",)),
            sync_chunk_info_legacy_state=lambda section: calls.append(("sync", section)),
            banner=lambda mode: calls.append(("banner", mode)),
        )
    )

    assert reset_state == main_runtime.MainLoopResetState(tmp_fix_ihdr=False)
    assert namespace["IBN"] == 0
    assert namespace["IDAT_Datastream"] == ""
    assert namespace["Bad_Crc"] is False
    assert namespace["EOF"] is False
    assert namespace["Chunks_History"] == []
    assert namespace["PandoraBox"] == {}
    assert namespace["TmpFixIHDR"] == "global value"
    assert calls == [
        ("reset_idat",),
        ("sync", "idat"),
        ("reset_idat",),
        ("sync", "idat"),
        ("banner", 1),
    ]


def test_reset_main_loop_state_uses_fresh_history_containers_each_time():
    namespace = {}
    runtime = main_runtime.MainLoopResetRuntime(
        namespace=namespace,
        reset_chunk_info_idat=lambda: None,
        sync_chunk_info_legacy_state=lambda section: None,
        banner=lambda mode: None,
    )

    main_runtime.reset_main_loop_state(runtime)
    first_history = namespace["Chunks_History"]
    first_pandora = namespace["PandoraBox"]
    first_history.append(b"IHDR")
    first_pandora["error"] = "value"

    main_runtime.reset_main_loop_state(runtime)

    assert namespace["Chunks_History"] == []
    assert namespace["Chunks_History"] is not first_history
    assert namespace["PandoraBox"] == {}
    assert namespace["PandoraBox"] is not first_pandora


def build_sample_runtime(calls, *, data=b"png", load_error=None):
    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    def load_sample_data(sample):
        calls.append(("load", sample))
        if load_error is not None:
            raise load_error
        return runtime_state.sample_data_from_bytes(data)

    return main_runtime.MainSampleRuntime(
        basename=lambda sample: "base-" + str(sample),
        load_sample_data=load_sample_data,
        raw_print=lambda *args: calls.append(("raw_print", args)),
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        exit_process=lambda code: calls.append(("exit", code)),
    )


def test_load_main_sample_selects_current_sample_and_loads_data():
    calls = []

    state = main_runtime.load_main_sample(
        build_sample_runtime(calls, data=b"\x89PNG"),
        main_runtime.MainSampleContext(sample="sample.png", cloneswar=False),
    )

    assert state == main_runtime.MainSampleState(
        sample="sample.png",
        sample_name="base-sample.png",
        cloneswar=False,
        data_bytes=b"\x89PNG",
        data_hex="89504e47",
    )
    assert ("raw_print", ("-Proceeding with: <white:base-sample.png>",)) in calls
    assert ("load", "sample.png") in calls
    assert ("candy", ("Cowsay", " <green:base-sample.png> is loaded!", "good")) in calls


def test_load_main_sample_uses_cloneswar_then_resets_it():
    calls = []

    state = main_runtime.load_main_sample(
        build_sample_runtime(calls),
        main_runtime.MainSampleContext(sample="origin.png", cloneswar="clone.png"),
    )

    assert state.sample == "clone.png"
    assert state.sample_name == "base-clone.png"
    assert state.cloneswar is False
    assert ("load", "clone.png") in calls


def test_load_main_sample_routes_load_error_to_legacy_error_path():
    calls = []

    state = main_runtime.load_main_sample(
        build_sample_runtime(calls, load_error=OSError("missing")),
        main_runtime.MainSampleContext(sample="missing.png", cloneswar=False),
    )

    assert state is None
    assert ("betterror", "missing", "main") in calls
    assert ("emit", "<red:Error:<yellow:missing>>") in calls
    assert ("exit", 1) in calls


def chunk_namespace(**updates):
    values = {
        "Orig_CD": "orig-data",
        "Orig_CL": "orig-len",
        "Orig_CT": b"IHDR",
        "Chunks_History": [b"IHDR"],
        "Raw_Data": b"data",
        "Raw_Type": b"IHDR",
        "Raw_Crc": b"crc!",
        "Raw_Length": b"len!",
        "Show_Must_Go_On": False,
        "Have_A_KitKat": False,
    }
    values.update(updates)
    return values


def build_chunk_walk_runtime(calls, namespace):
    def callback(name):
        def inner(*args):
            calls.append((name, args))
            if name == "fix_it_felix":
                namespace["Show_Must_Go_On"] = True

        return inner

    return main_runtime.MainChunkWalkRuntime(
        namespace=namespace,
        chunk_by_chunk=callback("chunk_by_chunk"),
        check_length=callback("check_length"),
        check_chunk_name=callback("check_chunk_name"),
        get_info=callback("get_info"),
        checksum=callback("checksum"),
        fix_it_felix=callback("fix_it_felix"),
    )


def test_run_main_chunk_walk_returns_without_offset():
    calls = []
    namespace = chunk_namespace()

    state = main_runtime.run_main_chunk_walk(
        build_chunk_walk_runtime(calls, namespace),
        main_runtime.MainChunkWalkContext(offset=None, data_hex="001122"),
    )

    assert state == main_runtime.MainChunkWalkState(offset=None)
    assert calls == []


def test_run_main_chunk_walk_runs_legacy_callback_order_and_updates_offset():
    calls = []
    namespace = chunk_namespace()

    state = main_runtime.run_main_chunk_walk(
        build_chunk_walk_runtime(calls, namespace),
        main_runtime.MainChunkWalkContext(offset=0, data_hex="0" * 10),
    )

    assert state == main_runtime.MainChunkWalkState(offset=16)
    assert calls == [
        ("chunk_by_chunk", (0,)),
        ("check_length", ("orig-data", "orig-len", b"IHDR")),
        ("check_chunk_name", (b"IHDR", "orig-len", b"IHDR")),
        ("get_info", (b"IHDR", b"data")),
        ("checksum", (b"IHDR", b"data", b"crc!")),
        ("fix_it_felix", (b"IHDR",)),
    ]
    assert namespace["Have_A_KitKat"] is False


def test_run_main_chunk_walk_stops_when_kitkat_breaks():
    calls = []
    namespace = chunk_namespace(Have_A_KitKat=True)

    state = main_runtime.run_main_chunk_walk(
        build_chunk_walk_runtime(calls, namespace),
        main_runtime.MainChunkWalkContext(offset=0, data_hex="0" * 40),
    )

    assert state == main_runtime.MainChunkWalkState(offset=16)
    assert [call[0] for call in calls].count("chunk_by_chunk") == 1
    assert namespace["Have_A_KitKat"] is False


def main():
    checks = [
        ("main options state", test_apply_main_cli_options_builds_initial_state),
        ("legacy clone/crash", test_apply_main_cli_options_preserves_legacy_unknown_clone_and_crash),
        ("invalid crash", test_apply_main_cli_options_exits_on_invalid_crash),
        ("help without args", test_apply_main_cli_options_prints_help_without_args),
        ("missing filename", test_apply_main_cli_options_exits_without_filename),
        ("bad max saves", test_apply_main_cli_options_exits_on_bad_max_saves),
        ("legacy globals", test_legacy_globals_from_main_cli_options_maps_runtime_flags),
        ("loop reset state", test_reset_main_loop_state_updates_legacy_globals_and_preserves_local_tmp_fixihdr),
        ("loop reset fresh containers", test_reset_main_loop_state_uses_fresh_history_containers_each_time),
        ("load sample", test_load_main_sample_selects_current_sample_and_loads_data),
        ("load clone sample", test_load_main_sample_uses_cloneswar_then_resets_it),
        ("load sample error", test_load_main_sample_routes_load_error_to_legacy_error_path),
        ("chunk walk no offset", test_run_main_chunk_walk_returns_without_offset),
        ("chunk walk order", test_run_main_chunk_walk_runs_legacy_callback_order_and_updates_offset),
        ("chunk walk kitkat", test_run_main_chunk_walk_stops_when_kitkat_breaks),
    ]

    print("Running main runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"main runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
