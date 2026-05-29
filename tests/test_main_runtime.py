#!/usr/bin/env python3
import ast
import builtins
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import cli, main_runtime, messages, runtime_state


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
        "ULTIMATE_LINEFEED_BUDGET": None,
        "ULTIMATE_LINEFEED_UNBOUNDED": False,
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
        path_exists=lambda path: False,
        path_is_dir=lambda path: False,
        list_dir=lambda path: [],
        remove_tree=lambda path: calls.append(("remove_tree", path)),
        abspath=lambda path: "/abs/" + path,
        join=lambda *parts: "/".join(parts),
        stderr="stderr",
        asker=lambda prompt: "no",
        candy=lambda *args: calls.append(("candy", args)),
        emit=lambda message: calls.append(("emit", message)),
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


def chunklate_main_node():
    module = ast.parse((ROOT / "Chunklate.py").read_text())
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError("Chunklate.main not found")


def test_chunklate_main_has_no_direct_global_wiring_and_no_dead_reached_end_comment():
    source = (ROOT / "Chunklate.py").read_text()
    main_node = chunklate_main_node()
    global_names = []
    for node in ast.walk(main_node):
        if isinstance(node, ast.Global):
            global_names.extend(node.names)
    attrs = {item.attr for item in ast.walk(main_node) if isinstance(item, ast.Attribute)}

    assert global_names == []
    assert "apply_main_cli_options_from_namespace" in attrs
    assert "run_main_loop_once_from_namespace" in attrs
    assert "Reached End" not in source
    assert "CheckChunkOrder(b'IEND',\"Critical\")" not in source


def test_build_main_runtime_helpers_wire_callbacks():
    calls = []
    namespace = {}

    cli_runtime = main_runtime.build_cli_options_runtime(
        print_error=lambda message: calls.append(("print", message)),
        exit_process=lambda code: calls.append(("exit", code)),
        make_dirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        path_exists=lambda path: False,
        path_is_dir=lambda path: False,
        list_dir=lambda path: [],
        remove_tree=lambda path: calls.append(("remove_tree", path)),
        abspath=lambda path: "/abs/" + path,
        join=lambda *parts: "/".join(parts),
        stderr="stderr",
        asker=lambda prompt: "no",
        candy=lambda *args: calls.append(("candy", args)),
        emit=lambda message: calls.append(("emit", message)),
    )
    clear_runtime = main_runtime.build_clear_screen_runtime(
        stderr_write=lambda value: calls.append(("stderr", value)),
        system=lambda value: calls.append(("system", value)),
        os_name="posix",
    )
    reset_runtime = main_runtime.build_loop_reset_runtime(
        namespace=namespace,
        reset_chunk_info_idat=lambda: calls.append(("reset",)),
        sync_chunk_info_legacy_state=lambda section: calls.append(("sync", section)),
        banner=lambda mode: calls.append(("banner", mode)),
    )
    sample_runtime = main_runtime.build_sample_runtime(
        basename=lambda value: "base-" + str(value),
        load_sample_data=lambda sample: runtime_state.sample_data_from_bytes(b"png"),
        raw_print=lambda *args: calls.append(("raw_print", args)),
        candy=lambda *args: "candy",
        emit=lambda message: calls.append(("emit", message)),
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        exit_process=lambda code: calls.append(("sample_exit", code)),
    )
    chunk_walk_runtime = main_runtime.build_chunk_walk_runtime(
        namespace=namespace,
        chunk_by_chunk=lambda offset: calls.append(("chunk_by_chunk", offset)),
        check_length=lambda *args: calls.append(("check_length", args)),
        check_chunk_name=lambda *args: calls.append(("check_chunk_name", args)),
        get_info=lambda *args: calls.append(("get_info", args)),
        checksum=lambda *args: calls.append(("checksum", args)),
        fix_it_felix=lambda chunk: calls.append(("fix_it_felix", chunk)),
    )

    assert cli_runtime.stderr == "stderr"
    assert cli_runtime.abspath("out") == "/abs/out"
    assert clear_runtime.os_name == "posix"
    assert reset_runtime.namespace is namespace
    assert sample_runtime.basename("sample.png") == "base-sample.png"
    assert chunk_walk_runtime.namespace is namespace


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
        ultimate_linefeed_budget=None,
        ultimate_linefeed_unbounded=False,
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


def test_apply_main_cli_options_exits_on_bad_ultimate_linefeed_budget():
    calls = []

    try:
        apply_options(calls, args(ULTIMATE_LINEFEED_BUDGET=0))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad ultimate linefeed budget should exit")

    assert ("print", "--ultimate-linefeed-budget arguments must be greater than zero.") in calls
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
        ultimate_linefeed_budget=1234,
        ultimate_linefeed_unbounded=True,
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
        "ULTIMATE_LINEFEED_BUDGET": 1234,
        "ULTIMATE_LINEFEED_UNBOUNDED": True,
        "OUTPUT_FOLDER_CLEANUP_PENDING": True,
    }


def test_apply_main_cli_options_from_namespace_updates_legacy_globals():
    calls = []
    fake_os = SimpleNamespace(
        makedirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        listdir=lambda path: [],
        path=SimpleNamespace(
            abspath=lambda path: "/abs/" + path,
            join=lambda *parts: "/".join(parts),
            exists=lambda path: False,
            isdir=lambda path: False,
        ),
    )
    namespace = {
        "sys": SimpleNamespace(exit=lambda code: calls.append(("exit", code)), stderr="stderr"),
        "os": fake_os,
        "shutil": SimpleNamespace(rmtree=lambda path: calls.append(("remove_tree", path))),
        "Candy": lambda *args: calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "CLONESWAR": False,
        "CRASH": False,
    }

    state = main_runtime.apply_main_cli_options_from_namespace(
        namespace,
        args(OUTPUT_DIR="out", MAX_SAVES=3, PAUSEERROR=True),
        (),
        argv_len=2,
        parser=FakeParser(calls),
    )

    assert state.file_origin == "sample.png"
    assert namespace["FILE_Origin"] == "sample.png"
    assert namespace["FILE_DIR"] == "/abs/out/"
    assert namespace["PAUSEERROR"] is True
    assert namespace["DEBUG"] is False
    assert namespace["MAX_SAVES"] == 3
    assert namespace["SAVE_COUNT"] == 0
    assert namespace["Sample"] == "sample.png"
    assert namespace["CLONESWAR"] is False
    assert namespace["CRASH"] is False
    assert namespace["ULTIMATE_LINEFEED_BUDGET"] is None
    assert namespace["ULTIMATE_LINEFEED_UNBOUNDED"] is False
    assert namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] is True
    assert calls == [("makedirs", "/abs/out/", {"exist_ok": True})]


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


def test_run_main_clear_screen_preserves_startup_skip():
    calls = []

    state = main_runtime.run_main_clear_screen(
        main_runtime.MainClearScreenRuntime(
            stderr_write=lambda value: calls.append(("stderr", value)),
            system=lambda value: calls.append(("system", value)),
            os_name="posix",
        ),
        main_runtime.MainClearScreenContext(clear=True, fir_start=True),
    )

    assert state == main_runtime.MainClearScreenState(fir_start=False, cleared=False)
    assert calls == []


def test_run_main_clear_screen_writes_ansi_reset_on_posix_after_startup():
    calls = []

    state = main_runtime.run_main_clear_screen(
        main_runtime.MainClearScreenRuntime(
            stderr_write=lambda value: calls.append(("stderr", value)),
            system=lambda value: calls.append(("system", value)),
            os_name="posix",
        ),
        main_runtime.MainClearScreenContext(clear=True, fir_start=False),
    )

    assert state == main_runtime.MainClearScreenState(fir_start=False, cleared=True)
    assert calls == [("stderr", "\033c")]


def test_run_main_clear_screen_calls_cls_on_windows_after_startup():
    calls = []

    state = main_runtime.run_main_clear_screen(
        main_runtime.MainClearScreenRuntime(
            stderr_write=lambda value: calls.append(("stderr", value)),
            system=lambda value: calls.append(("system", value)),
            os_name="nt",
        ),
        main_runtime.MainClearScreenContext(clear=True, fir_start=False),
    )

    assert state == main_runtime.MainClearScreenState(fir_start=False, cleared=True)
    assert calls == [("system", "cls")]


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


def test_run_main_chunk_walk_defers_ihdr_value_repair_until_file_tour_ends():
    calls = []
    sequence = {
        0: b"IHDR",
        16: b"IEND",
    }
    namespace = chunk_namespace(
        PandoraBox={
            "GetInfo_Error_0:-IHDR Color 3: Wrong bit depht with IHDR Color type 3": {}
        },
        Candy=lambda *args: calls.append(("candy", args)),
    )

    def chunk_by_chunk(offset):
        chunk = sequence[offset]
        namespace.update(
            {
                "Orig_CD": "orig-data",
                "Orig_CL": "orig-len",
                "Orig_CT": chunk,
                "Chunks_History": [chunk],
                "Raw_Data": b"data",
                "Raw_Type": chunk,
                "Raw_Crc": b"crc!",
                "Raw_Length": b"len!",
                "Show_Must_Go_On": False,
                "Have_A_KitKat": False,
            }
        )
        calls.append(("chunk_by_chunk", (offset,)))

    def callback(name):
        def inner(*args):
            calls.append((name, args))
            if name == "fix_it_felix":
                namespace["Show_Must_Go_On"] = True

        return inner

    runtime = main_runtime.MainChunkWalkRuntime(
        namespace=namespace,
        chunk_by_chunk=chunk_by_chunk,
        check_length=callback("check_length"),
        check_chunk_name=callback("check_chunk_name"),
        get_info=callback("get_info"),
        checksum=callback("checksum"),
        fix_it_felix=callback("fix_it_felix"),
        next_chunk_offset=lambda offset, *_args: 16 if offset == 0 else 32,
    )

    state = main_runtime.run_main_chunk_walk(
        runtime,
        main_runtime.MainChunkWalkContext(offset=0, data_hex="0" * 32),
    )

    assert state == main_runtime.MainChunkWalkState(offset=32)
    assert [call for call in calls if call[0] == "fix_it_felix"] == [
        ("fix_it_felix", (b"IEND",))
    ]
    assert (
        "candy",
        (
            "Cowsay",
            "I found an IHDR value problem, but the chunk road is still walkable. I am finishing the file tour before Felix touches it.",
            "com",
        ),
    ) in calls


def test_run_main_chunk_walk_stops_when_kitkat_breaks():
    calls = []
    namespace = chunk_namespace(Have_A_KitKat=True)

    state = main_runtime.run_main_chunk_walk(
        build_chunk_walk_runtime(calls, namespace),
        main_runtime.MainChunkWalkContext(offset=0, data_hex="0" * 40),
    )

    assert state == main_runtime.MainChunkWalkState(offset=0)
    assert [call[0] for call in calls].count("chunk_by_chunk") == 1
    assert namespace["Have_A_KitKat"] is False


def test_run_main_loop_once_from_namespace_resets_loads_and_walks_sample():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    namespace = {}

    def chunk_by_chunk(offset):
        calls.append(("chunk_by_chunk", offset))
        namespace.update(
            {
                "Orig_CD": "orig-data",
                "Orig_CL": "orig-len",
                "Orig_CT": b"IHDR",
                "Chunks_History": [b"PNG"],
                "Raw_Data": "raw-data",
                "Raw_Type": "raw-type",
                "Raw_Crc": "raw-crc",
                "Raw_Length": "raw-len",
                "Show_Must_Go_On": False,
                "Have_A_KitKat": False,
            }
        )

    def fix_it_felix(chunk):
        calls.append(("fix_it_felix", chunk))
        namespace["Show_Must_Go_On"] = True
        namespace["SAVE_COUNT"] += 1

    namespace.update(
        {
            "sys": SimpleNamespace(
                stderr=SimpleNamespace(write=lambda value: calls.append(("stderr", value))),
                exit=lambda code: calls.append(("exit", code)),
            ),
            "os": os,
            "CLEAR": False,
            "FirStart": True,
            "CHUNK_INFO_STATE": SimpleNamespace(
                reset_idat=lambda: calls.append(("reset_idat",))
            ),
            "Sync_Chunk_Info_Legacy_State": lambda section: calls.append(("sync", section)),
            "Chunklate": lambda mode: calls.append(("banner", mode)),
            "Sample": sample_path,
            "CLONESWAR": False,
            "SAVE_COUNT": 0,
            "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
            "PRINT": lambda message: calls.append(("emit", message)),
            "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
            "FindMagic": lambda: calls.append(("find_magic",)) or 0,
            "ChunkbyChunk": chunk_by_chunk,
            "CheckLength": lambda *args: calls.append(("check_length", args)),
            "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
            "GetInfo": lambda *args: calls.append(("get_info", args)),
            "Checksum": lambda *args: calls.append(("checksum", args)),
            "FixItFelix": fix_it_felix,
        }
    )

    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        os.unlink(sample_path)

    assert state == main_runtime.MainLoopIterationState()
    assert namespace["FirStart"] is True
    assert namespace["Sample"] == sample_path
    assert namespace["Sample_Name"] == os.path.basename(sample_path)
    assert namespace["CLONESWAR"] is False
    assert namespace["DATA_BYTES"] == b"\x89PNG"
    assert namespace["DATAX"] == "89504e47"
    assert ("reset_idat",) in calls
    assert ("sync", "idat") in calls
    assert ("banner", 1) in calls
    assert ("find_magic",) in calls
    assert ("chunk_by_chunk", 0) in calls
    assert ("check_length", ("orig-data", "orig-len", b"IHDR")) in calls
    assert ("check_chunk_name", (b"IHDR", "orig-len", b"PNG")) in calls
    assert ("get_info", (b"IHDR", "raw-data")) in calls
    assert ("checksum", ("raw-type", "raw-data", "raw-crc")) in calls
    assert ("fix_it_felix", b"IHDR") in calls
    assert namespace["Have_A_KitKat"] is False


def test_run_main_loop_once_counts_clone_written_by_find_magic():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    def find_magic():
        calls.append(("find_magic",))
        namespace["SAVE_COUNT"] += 1
        return None

    namespace = {
        "sys": SimpleNamespace(
            stderr=SimpleNamespace(write=lambda value: calls.append(("stderr", value))),
            exit=lambda code: calls.append(("exit", code)),
        ),
        "os": os,
        "CLEAR": False,
        "FirStart": True,
        "CHUNK_INFO_STATE": SimpleNamespace(reset_idat=lambda: calls.append(("reset_idat",))),
        "Sync_Chunk_Info_Legacy_State": lambda section: calls.append(("sync", section)),
        "Chunklate": lambda mode: calls.append(("banner", mode)),
        "Sample": sample_path,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "FindMagic": find_magic,
        "ChunkbyChunk": lambda offset: calls.append(("chunk_by_chunk", offset)),
        "CheckLength": lambda *args: calls.append(("check_length", args)),
        "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
        "GetInfo": lambda *args: calls.append(("get_info", args)),
        "Checksum": lambda *args: calls.append(("checksum", args)),
        "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
    }

    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        os.unlink(sample_path)

    assert state == main_runtime.MainLoopIterationState()
    assert ("find_magic",) in calls
    assert not any(call[0] == "chunk_by_chunk" for call in calls)
    assert namespace["SAVE_COUNT"] == 1


def test_run_main_loop_once_opens_valid_final_image_when_no_clone_written():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    namespace = {
        "sys": SimpleNamespace(
            stderr=SimpleNamespace(write=lambda value: calls.append(("stderr", value))),
            exit=lambda code: calls.append(("exit", code)),
        ),
        "os": os,
        "CLEAR": False,
        "FirStart": True,
        "CHUNK_INFO_STATE": SimpleNamespace(reset_idat=lambda: calls.append(("reset_idat",))),
        "Sync_Chunk_Info_Legacy_State": lambda section: calls.append(("sync", section)),
        "Chunklate": lambda mode: calls.append(("banner", mode)),
        "Sample": sample_path,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "FindMagic": lambda: calls.append(("find_magic",)) or None,
        "ChunkbyChunk": lambda offset: calls.append(("chunk_by_chunk", offset)),
        "CheckLength": lambda *args: calls.append(("check_length", args)),
        "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
        "GetInfo": lambda *args: calls.append(("get_info", args)),
        "Checksum": lambda *args: calls.append(("checksum", args)),
        "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
        "Open_Current_Final_Image_If_Valid": lambda: calls.append(("open_final",)),
    }

    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        os.unlink(sample_path)

    assert state == main_runtime.MainLoopIterationState(should_return=True)
    assert ("find_magic",) in calls
    assert ("open_final",) in calls
    assert calls.index(("open_final",)) < calls.index(("emit", "-No new clone produced, stopping main loop."))
    assert not any(call[0] == "chunk_by_chunk" for call in calls)


def test_run_main_loop_once_keeps_unresolved_file_closed_when_no_clone_written():
    calls = []
    finding = "GetInfo_Error_0:-iTXt Compression Flag must be 0 or 1"
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    def find_magic_with_unresolved_finding():
        calls.append(("find_magic",))
        namespace["PandoraBox"] = {finding: {}}
        return None

    namespace = {
        "sys": SimpleNamespace(
            stderr=SimpleNamespace(write=lambda value: calls.append(("stderr", value))),
            exit=lambda code: calls.append(("exit", code)),
        ),
        "os": os,
        "CLEAR": False,
        "FirStart": True,
        "CHUNK_INFO_STATE": SimpleNamespace(reset_idat=lambda: calls.append(("reset_idat",))),
        "Sync_Chunk_Info_Legacy_State": lambda section: calls.append(("sync", section)),
        "Chunklate": lambda mode: calls.append(("banner", mode)),
        "Sample": sample_path,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "PandoraBox": {},
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "FindMagic": find_magic_with_unresolved_finding,
        "ChunkbyChunk": lambda offset: calls.append(("chunk_by_chunk", offset)),
        "CheckLength": lambda *args: calls.append(("check_length", args)),
        "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
        "GetInfo": lambda *args: calls.append(("get_info", args)),
        "Checksum": lambda *args: calls.append(("checksum", args)),
        "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
        "Open_Current_Final_Image_If_Valid": lambda: calls.append(("open_final",)),
    }

    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        os.unlink(sample_path)

    assert state == main_runtime.MainLoopIterationState(should_return=True)
    assert ("find_magic",) in calls
    assert ("open_final",) not in calls
    assert ("candy", ("Cowsay", messages.UNIMPLEMENTED_REPAIR_ROUTE_MESSAGE, "bad")) in calls
    assert ("emit", "-No repair route implemented for remaining findings.") in calls
    assert ("emit", "-No new clone produced, stopping main loop.") in calls
    assert not any(call[0] == "chunk_by_chunk" for call in calls)


def test_run_main_loop_once_asks_output_cleanup_after_banner():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    original_input = builtins.input

    def answer_cleanup(prompt):
        calls.append(("input", prompt))
        return "yes"

    def find_magic():
        calls.append(("find_magic",))
        namespace["SAVE_COUNT"] += 1
        return None

    fake_os = SimpleNamespace(
        name="posix",
        system=lambda command: calls.append(("system", command)),
        makedirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        listdir=lambda path: calls.append(("listdir", path)) or ["old.png"],
        path=SimpleNamespace(
            basename=os.path.basename,
            exists=lambda path: calls.append(("exists", path)) or True,
            isdir=lambda path: calls.append(("isdir", path)) or True,
            abspath=lambda path: "/abs/" + path,
            join=lambda *parts: "/".join(parts),
        ),
    )

    namespace = {
        "sys": SimpleNamespace(
            stderr=SimpleNamespace(write=lambda value: calls.append(("stderr", value))),
            exit=lambda code: calls.append(("exit", code)),
        ),
        "os": fake_os,
        "shutil": SimpleNamespace(rmtree=lambda path: calls.append(("remove_tree", path))),
        "CLEAR": False,
        "FirStart": True,
        "CHUNK_INFO_STATE": SimpleNamespace(reset_idat=lambda: calls.append(("reset_idat",))),
        "Sync_Chunk_Info_Legacy_State": lambda section: calls.append(("sync", section)),
        "Chunklate": lambda mode: calls.append(("banner", mode)),
        "FILE_Origin": sample_path,
        "FILE_DIR": "/out/",
        "OUTPUT_FOLDER_CLEANUP_PENDING": True,
        "Sample": sample_path,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "FindMagic": find_magic,
        "ChunkbyChunk": lambda offset: calls.append(("chunk_by_chunk", offset)),
        "CheckLength": lambda *args: calls.append(("check_length", args)),
        "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
        "GetInfo": lambda *args: calls.append(("get_info", args)),
        "Checksum": lambda *args: calls.append(("checksum", args)),
        "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
    }

    builtins.input = answer_cleanup
    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        builtins.input = original_input
        os.unlink(sample_path)

    folder = "/out/Folder_%s" % os.path.basename(sample_path)
    assert state == main_runtime.MainLoopIterationState()
    assert namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] is False
    assert calls.index(("banner", 1)) < calls.index(
        (
            "candy",
            (
                "Cowsay",
                "Ok, the output folder already exists and there is stuff in it. I can wipe it, but I am asking first because this smells like evidence.",
                "com",
            ),
        )
    )
    assert ("input", "-Delete existing output folder '%s'? (yes/no): " % folder) in calls
    assert ("remove_tree", folder) in calls
    assert ("find_magic",) in calls


def main():
    checks = [
        ("main cleanup boundary", test_chunklate_main_has_no_direct_global_wiring_and_no_dead_reached_end_comment),
        ("runtime builders", test_build_main_runtime_helpers_wire_callbacks),
        ("main options state", test_apply_main_cli_options_builds_initial_state),
        ("legacy clone/crash", test_apply_main_cli_options_preserves_legacy_unknown_clone_and_crash),
        ("invalid crash", test_apply_main_cli_options_exits_on_invalid_crash),
        ("help without args", test_apply_main_cli_options_prints_help_without_args),
        ("missing filename", test_apply_main_cli_options_exits_without_filename),
        ("bad max saves", test_apply_main_cli_options_exits_on_bad_max_saves),
        ("legacy globals", test_legacy_globals_from_main_cli_options_maps_runtime_flags),
        ("namespace CLI options", test_apply_main_cli_options_from_namespace_updates_legacy_globals),
        ("loop reset state", test_reset_main_loop_state_updates_legacy_globals_and_preserves_local_tmp_fixihdr),
        ("loop reset fresh containers", test_reset_main_loop_state_uses_fresh_history_containers_each_time),
        ("clear screen startup", test_run_main_clear_screen_preserves_startup_skip),
        ("clear screen posix", test_run_main_clear_screen_writes_ansi_reset_on_posix_after_startup),
        ("clear screen windows", test_run_main_clear_screen_calls_cls_on_windows_after_startup),
        ("load sample", test_load_main_sample_selects_current_sample_and_loads_data),
        ("load clone sample", test_load_main_sample_uses_cloneswar_then_resets_it),
        ("load sample error", test_load_main_sample_routes_load_error_to_legacy_error_path),
        ("chunk walk no offset", test_run_main_chunk_walk_returns_without_offset),
        ("chunk walk order", test_run_main_chunk_walk_runs_legacy_callback_order_and_updates_offset),
        ("chunk walk defers IHDR value repair", test_run_main_chunk_walk_defers_ihdr_value_repair_until_file_tour_ends),
        ("chunk walk kitkat", test_run_main_chunk_walk_stops_when_kitkat_breaks),
        ("main loop namespace", test_run_main_loop_once_from_namespace_resets_loads_and_walks_sample),
        ("main loop counts FindMagic clone", test_run_main_loop_once_counts_clone_written_by_find_magic),
        ("main loop opens final image on clean no-clone exit", test_run_main_loop_once_opens_valid_final_image_when_no_clone_written),
        ("main loop cleanup after banner", test_run_main_loop_once_asks_output_cleanup_after_banner),
    ]

    print("Running main runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"main runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
