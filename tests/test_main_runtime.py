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

from chunklate import (
    cli,
    chunk_state,
    chunk_state_runtime,
    main_runtime,
    messages,
    output,
    runtime_state,
)


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
        "DEBUGFILE": False,
        "AUTO": False,
        "COLOR_MODE": "auto",
        "ULTIMATE_LINEFEED_BUDGET": None,
        "ULTIMATE_LINEFEED_UNBOUNDED": False,
        "ULTIMATE_LINEFEED_REFERENCE": None,
        "ULTIMATE_LINEFEED_REFERENCE_MODE": "exact",
        "ULTIMATE_LINEFEED_REFERENCE_REGIONS": None,
        "ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR": False,
        "ULTIMATE_LINEFEED_PREVIEW_TIMEOUT": 5.0,
        "ULTIMATE_LINEFEED_SHOW_PREVIEWS": False,
        "ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT": 100,
        "ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE": 0.95,
        "ULTIMATE_LINEFEED_RESUME": "ask",
        "ULTIMATE_LINEFEED_WORKERS": None,
        "SMASH_BRUTE_BRAWL_RESUME": "ask",
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
        remove_file=lambda path: calls.append(("remove_file", path)),
        abspath=lambda path: "/abs/" + path,
        join=lambda *parts: "/".join(parts),
        stderr="stderr",
        asker=lambda prompt: "no",
        candy=lambda *args: calls.append(("candy", args)),
        emit=lambda message: calls.append(("emit", message)),
        clear_dialogue_pause=lambda: calls.append(("clear_dialogue_pause",)),
    )


def test_ultimate_linefeed_paths_use_short_names_with_legacy_resume_fallback():
    calls = []
    existing: set[str] = set()
    folder = "/out/Folder_sample"
    runtime = main_runtime.MainCliOptionsRuntime(
        **{
            **build_runtime(calls).__dict__,
            "path_exists": lambda path: path in existing,
            "join": lambda *parts: "/".join(parts),
            "clone_folder": lambda file_origin, file_dir: folder,
        }
    )
    legacy_checkpoint = folder + "/" + main_runtime.LEGACY_ULTIMATE_LINEFEED_CHECKPOINT_NAMES[0]
    legacy_progress = folder + "/" + main_runtime.LEGACY_ULTIMATE_LINEFEED_PROGRESS_NAMES[0]
    short_checkpoint = folder + "/" + main_runtime.ULTIMATE_LINEFEED_CHECKPOINT_NAME

    existing.update({legacy_checkpoint, legacy_progress})
    paths = main_runtime.ultimate_linefeed_folder_paths(
        runtime,
        file_origin="sample.png",
        file_dir="/out",
    )

    assert paths == (
        folder,
        legacy_checkpoint,
        legacy_progress,
        folder + "/" + main_runtime.ULTIMATE_LINEFEED_SOURCE_NAME,
    )

    existing.add(short_checkpoint)
    paths = main_runtime.ultimate_linefeed_folder_paths(
        runtime,
        file_origin="sample.png",
        file_dir="/out",
    )

    assert paths[1] == short_checkpoint


def test_reset_ultimate_linefeed_resume_files_removes_short_and_legacy_names():
    calls = []
    folder = "/out/Folder_sample"
    names = main_runtime._ultimate_linefeed_resume_names()
    assert main_runtime.ULTIMATE_LINEFEED_SOURCE_RAW_NAME in names
    existing = {folder + "/" + name for name in names}
    runtime = main_runtime.MainCliOptionsRuntime(
        **{
            **build_runtime(calls).__dict__,
            "path_exists": lambda path: path in existing,
            "remove_file": lambda path: calls.append(("remove_file", path)),
            "join": lambda *parts: "/".join(parts),
            "clone_folder": lambda file_origin, file_dir: folder,
        }
    )

    main_runtime.reset_ultimate_linefeed_resume_files(
        runtime,
        file_origin="sample.png",
        file_dir="/out",
    )

    assert [call[1] for call in calls if call[0] == "remove_file"] == [
        folder + "/" + name for name in names
    ]


def test_reset_smash_brute_brawl_resume_files_removes_short_names():
    calls = []
    folder = "/out/Folder_sample"
    names = main_runtime._smash_brute_brawl_resume_names()
    assert main_runtime.SMASH_BRUTE_BRAWL_SOURCE_RAW_NAME in names
    existing = {folder + "/" + name for name in names}
    runtime = main_runtime.MainCliOptionsRuntime(
        **{
            **build_runtime(calls).__dict__,
            "path_exists": lambda path: path in existing,
            "remove_file": lambda path: calls.append(("remove_file", path)),
            "join": lambda *parts: "/".join(parts),
            "clone_folder": lambda file_origin, file_dir: folder,
        }
    )

    main_runtime.reset_smash_brute_brawl_resume_files(
        runtime,
        file_origin="sample.png",
        file_dir="/out",
    )

    assert [call[1] for call in calls if call[0] == "remove_file"] == [
        folder + "/" + name for name in names
    ]


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
    module = ast.parse((ROOT / "Chunklate.py").read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError("Chunklate.main not found")


def test_chunklate_main_has_no_direct_global_wiring_and_no_dead_reached_end_comment():
    source = (ROOT / "Chunklate.py").read_text(encoding="utf-8")
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
        remove_file=lambda path: calls.append(("remove_file", path)),
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
            debug_file=False,
            auto=False,
            color_mode="auto",
        ),
        max_saves=2,
        save_count=0,
        sample="sample.png",
        cloneswar=False,
        crash=False,
        ultimate_linefeed_budget=None,
        ultimate_linefeed_unbounded=False,
        ultimate_linefeed_reference=None,
        ultimate_linefeed_reference_mode="exact",
        ultimate_linefeed_reference_regions=None,
        ultimate_linefeed_reference_region_editor=False,
        ultimate_linefeed_preview_timeout=5.0,
        ultimate_linefeed_show_previews=False,
        ultimate_linefeed_visual_gallery_limit=100,
        ultimate_linefeed_visual_min_coverage=0.95,
        ultimate_linefeed_resume="ask",
        ultimate_linefeed_workers=None,
        smash_brute_brawl_resume="ask",
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


def test_apply_main_cli_options_exits_on_bad_ultimate_preview_timeout():
    calls = []

    try:
        apply_options(calls, args(ULTIMATE_LINEFEED_PREVIEW_TIMEOUT=-0.1))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad ultimate preview timeout should exit")

    assert (
        "print",
        "--ultimate-linefeed-preview-timeout arguments must be zero or greater.",
    ) in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_on_bad_ultimate_resume_mode():
    calls = []

    try:
        apply_options(calls, args(ULTIMATE_LINEFEED_RESUME="bad"))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad ultimate resume mode should exit")

    assert (
        "print",
        "--ultimate-linefeed-resume must be one of: ask, auto, never, reset.",
    ) in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_on_bad_ultimate_workers():
    calls = []

    try:
        apply_options(calls, args(ULTIMATE_LINEFEED_WORKERS="-1"))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad ultimate workers should exit")

    assert (
        "print",
        "--ultimate-linefeed-workers must be a non-negative integer, min, normal, or max.",
    ) in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_on_bad_smash_brute_brawl_resume_mode():
    calls = []

    try:
        apply_options(calls, args(SMASH_BRUTE_BRAWL_RESUME="bad"))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad SmashBruteBrawl resume mode should exit")

    assert (
        "print",
        "--smashbrutebrawl-resume must be one of: ask, auto, never, reset.",
    ) in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_on_bad_smash_workers():
    calls = []

    try:
        apply_options(calls, args(SMASH_BRUTE_BRAWL_WORKERS="-1"))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad SmashBruteBrawl workers should exit")

    assert (
        "print",
        "--smashbrutebrawl-workers must be a non-negative integer, min, normal, max, or auto.",
    ) in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_on_bad_ultimate_reference_mode():
    calls = []

    try:
        apply_options(calls, args(ULTIMATE_LINEFEED_REFERENCE_MODE="bad"))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad ultimate reference mode should exit")

    assert (
        "print",
        "--ultimate-linefeed-reference-mode must be one of: exact, similar.",
    ) in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_on_bad_ultimate_visual_gallery_limit():
    calls = []

    try:
        apply_options(calls, args(ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT=-1))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad ultimate visual gallery limit should exit")

    assert (
        "print",
        "--ultimate-linefeed-visual-gallery-limit arguments must be zero or greater.",
    ) in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_on_bad_ultimate_visual_min_coverage():
    calls = []

    try:
        apply_options(calls, args(ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE=1.5))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad ultimate visual min coverage should exit")

    assert (
        "print",
        "--ultimate-linefeed-visual-min-coverage arguments must be between 0 and 1.",
    ) in calls
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
            debug_file=True,
            auto=False,
            color_mode="never",
        ),
        max_saves=4,
        save_count=0,
        sample="sample.png",
        cloneswar="clone.png",
        crash=9,
        ultimate_linefeed_budget=1234,
        ultimate_linefeed_unbounded=True,
        ultimate_linefeed_reference="ref.png",
        ultimate_linefeed_reference_mode="similar",
        ultimate_linefeed_reference_regions="regions.json",
        ultimate_linefeed_reference_region_editor=True,
        ultimate_linefeed_preview_timeout=1.5,
        ultimate_linefeed_show_previews=True,
        ultimate_linefeed_visual_gallery_limit=77,
        ultimate_linefeed_visual_min_coverage=0.8,
        ultimate_linefeed_resume="auto",
        ultimate_linefeed_workers="auto",
        smash_brute_brawl_resume="auto",
        smash_brute_brawl_workers="normal",
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
        "DEBUGFILE": True,
        "AUTO": False,
        "COLOR_MODE": "never",
        "MAX_SAVES": 4,
        "SAVE_COUNT": 0,
        "Sample": "sample.png",
        "CLONESWAR": "clone.png",
        "CRASH": 9,
        "ULTIMATE_LINEFEED_BUDGET": 1234,
        "ULTIMATE_LINEFEED_UNBOUNDED": True,
        "ULTIMATE_LINEFEED_REFERENCE": "ref.png",
        "ULTIMATE_LINEFEED_REFERENCE_MODE": "similar",
        "ULTIMATE_LINEFEED_REFERENCE_REGIONS": "regions.json",
        "ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR": True,
        "ULTIMATE_LINEFEED_PREVIEW_TIMEOUT": 1.5,
        "ULTIMATE_LINEFEED_SHOW_PREVIEWS": True,
        "ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT": 77,
        "ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE": 0.8,
        "ULTIMATE_LINEFEED_RESUME": "auto",
        "ULTIMATE_LINEFEED_WORKERS": "auto",
        "SMASH_BRUTE_BRAWL_RESUME": "auto",
        "SMASH_BRUTE_BRAWL_WORKERS": "normal",
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
    assert namespace["DEBUGFILE"] is False
    assert namespace["MAX_SAVES"] == 3
    assert namespace["SAVE_COUNT"] == 0
    assert namespace["Sample"] == "sample.png"
    assert namespace["CLONESWAR"] is False
    assert namespace["CRASH"] is False
    assert namespace["ULTIMATE_LINEFEED_BUDGET"] is None
    assert namespace["ULTIMATE_LINEFEED_UNBOUNDED"] is False
    assert namespace["ULTIMATE_LINEFEED_REFERENCE"] is None
    assert namespace["ULTIMATE_LINEFEED_REFERENCE_MODE"] == "exact"
    assert namespace["ULTIMATE_LINEFEED_REFERENCE_REGIONS"] is None
    assert namespace["ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR"] is False
    assert namespace["ULTIMATE_LINEFEED_PREVIEW_TIMEOUT"] == 5.0
    assert namespace["ULTIMATE_LINEFEED_SHOW_PREVIEWS"] is False
    assert namespace["ULTIMATE_LINEFEED_RESUME"] == "ask"
    assert namespace["SMASH_BRUTE_BRAWL_RESUME"] == "ask"
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


def test_reset_main_loop_state_clears_splt_state_between_repair_passes():
    state = chunk_state.ChunkInfoState()
    state.set_splt_legacy(
        names=["7369782d63756265"],
        depths=["16"],
        red=["00"],
        green=["00"],
        blue=["00"],
        alpha=["ff"],
        freq=["00"],
    )
    namespace = {}

    def sync(section):
        chunk_state_runtime.sync_state_to_legacy(namespace, state, section)

    main_runtime.reset_main_loop_state(
        main_runtime.MainLoopResetRuntime(
            namespace=namespace,
            reset_chunk_info_idat=state.reset_idat,
            sync_chunk_info_legacy_state=sync,
            banner=lambda mode: None,
            reset_chunk_info_splt=state.reset_splt,
        )
    )

    assert state.splt_name == []
    assert state.splt_entry_count() == 0
    assert namespace["sPLT_Name"] == []
    assert namespace["sPLT_Red"] == []


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
    assert (
        "candy",
        ("Cowsay", main_runtime.clone_study_phrase("base-clone.png"), "com"),
    ) in calls


def test_load_main_sample_announces_fixed_clone_even_without_cloneswar_flag():
    calls = []

    state = main_runtime.load_main_sample(
        build_sample_runtime(calls),
        main_runtime.MainSampleContext(sample="sample.0_Fixed.png", cloneswar=False),
    )

    assert state.sample_name == "base-sample.0_Fixed.png"
    assert (
        "candy",
        ("Cowsay", main_runtime.clone_study_phrase("base-sample.0_Fixed.png"), "com"),
    ) in calls


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


def build_sequence_chunk_walk_runtime(calls, namespace, sequence):
    offsets = sorted(sequence)
    next_offsets = {
        offset: offsets[index + 1] if index + 1 < len(offsets) else offset + 16
        for index, offset in enumerate(offsets)
    }

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

    return main_runtime.MainChunkWalkRuntime(
        namespace=namespace,
        chunk_by_chunk=chunk_by_chunk,
        check_length=callback("check_length"),
        check_chunk_name=callback("check_chunk_name"),
        get_info=callback("get_info"),
        checksum=callback("checksum"),
        fix_it_felix=callback("fix_it_felix"),
        next_chunk_offset=lambda offset, *_args: next_offsets[offset],
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
            "I found repairable problems, but the chunk road is still walkable. I am finishing the file tour before Felix touches it.",
            "com",
        ),
    ) in calls


def test_run_main_chunk_walk_defers_generic_findings_until_iend_even_with_immediate_flags():
    scenarios = [
        (
            "crc",
            {"Checksum_Error_0:-Wrong Crc b'IDAT'": {}},
            {"Bad_Crc": True},
        ),
        (
            "bad-current-name",
            {"CheckChunkName_Error_0:-Bad Current Name b'BDAT'": {}},
            {"Bad_Current_Name": True},
        ),
        (
            "plte-order",
            {"CheckChunkOrder_Error_0:-PLTE is misplaced and must appear before IDAT": {}},
            {"Bad_Missplaced": True},
        ),
    ]

    for label, pandora_box, flags in scenarios:
        calls = []
        namespace = chunk_namespace(
            PandoraBox=pandora_box,
            Candy=lambda *args: calls.append(("candy", args)),
            **flags,
        )
        runtime = build_sequence_chunk_walk_runtime(
            calls,
            namespace,
            {
                0: b"IHDR",
                16: b"IDAT",
                32: b"IEND",
            },
        )

        state = main_runtime.run_main_chunk_walk(
            runtime,
            main_runtime.MainChunkWalkContext(offset=0, data_hex="0" * 48),
        )

        assert state == main_runtime.MainChunkWalkState(offset=48), label
        assert [call for call in calls if call[0] == "fix_it_felix"] == [
            ("fix_it_felix", (b"IEND",))
        ], label
        iend_checksum_index = calls.index(("checksum", (b"IEND", b"data", b"crc!")))
        fix_index = calls.index(("fix_it_felix", (b"IEND",)))
        assert iend_checksum_index < fix_index, label
        assert [call for call in calls if call[0] == "candy"] == [
            (
                "candy",
                (
                    "Cowsay",
                    "I found repairable problems, but the chunk road is still walkable. I am finishing the file tour before Felix touches it.",
                    "com",
                ),
            )
        ], label


def test_run_main_chunk_walk_allows_felix_on_non_iend_no_next_chunk_boundary():
    calls = []
    namespace = chunk_namespace(
        PandoraBox={"CheckLength_Error_0:-No NextChunk after IDAT": {}},
        Bad_No_Next_Chunk=True,
        Candy=lambda *args: calls.append(("candy", args)),
    )
    runtime = build_sequence_chunk_walk_runtime(
        calls,
        namespace,
        {
            0: b"IDAT",
        },
    )

    state = main_runtime.run_main_chunk_walk(
        runtime,
        main_runtime.MainChunkWalkContext(offset=0, data_hex="0" * 16),
    )

    assert state == main_runtime.MainChunkWalkState(offset=16)
    assert [call for call in calls if call[0] == "fix_it_felix"] == [
        ("fix_it_felix", (b"IDAT",))
    ]
    assert [call for call in calls if call[0] == "candy"] == []


def test_run_main_chunk_walk_allows_no_next_route_when_deferred_has_no_visible_iend():
    calls = []
    namespace = chunk_namespace(
        PandoraBox={"CheckLength_Error_0:-No NextChunk": {}},
        Bad_No_Next_Chunk=True,
        DEFERRED_LINEFEED_SIGNATURE_REPAIR={"data_bytes": b"png"},
        Candy=lambda *args: calls.append(("candy", args)),
    )
    runtime = build_sequence_chunk_walk_runtime(
        calls,
        namespace,
        {
            0: b"IDAT",
        },
    )

    state = main_runtime.run_main_chunk_walk(
        runtime,
        main_runtime.MainChunkWalkContext(offset=0, data_hex="0" * 16),
    )

    assert state == main_runtime.MainChunkWalkState(offset=16)
    assert [call for call in calls if call[0] == "fix_it_felix"] == [
        ("fix_it_felix", (b"IDAT",))
    ]


def test_run_main_chunk_walk_defers_no_next_when_visible_linefeed_tour_finds_iend():
    calls = []
    sample_bytes = (
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png"
    ).read_bytes()
    namespace = chunk_namespace(
        PandoraBox={"CheckLength_Error_0:-No NextChunk": {}},
        Bad_No_Next_Chunk=True,
        DEFERRED_LINEFEED_SIGNATURE_REPAIR={"data_bytes": sample_bytes},
        Candy=lambda *args: calls.append(("candy", args)),
    )
    runtime = build_sequence_chunk_walk_runtime(
        calls,
        namespace,
        {
            0: b"IDAT",
        },
    )

    state = main_runtime.run_main_chunk_walk(
        runtime,
        main_runtime.MainChunkWalkContext(offset=0, data_hex="0" * 16),
    )

    assert state == main_runtime.MainChunkWalkState(offset=16)
    assert [call for call in calls if call[0] == "fix_it_felix"] == []
    assert namespace["DEFERRED_LINEFEED_VISIBLE_TOUR_SHOWN"] is True
    assert namespace["SideNotes"] == [
        "-FindMagic: visible line-feed marker tour reached IEND before deferred repair."
    ]


def test_run_main_chunk_walk_defers_private_compression_repair_until_after_idat():
    calls = []
    sequence = {
        0: b"IHDR",
        16: b"IDAT",
        32: b"IEND",
    }
    namespace = chunk_namespace(
        PandoraBox={
            "GetInfo_Error_0:-IHDR Compression Algorithms : Wrong value must be 0. StructIndex:5": {}
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
        next_chunk_offset=lambda offset, *_args: {0: 16, 16: 32, 32: 48}[offset],
    )

    state = main_runtime.run_main_chunk_walk(
        runtime,
        main_runtime.MainChunkWalkContext(offset=0, data_hex="0" * 48),
    )

    assert state == main_runtime.MainChunkWalkState(offset=48)
    assert [call for call in calls if call[0] == "fix_it_felix"] == [
        ("fix_it_felix", (b"IEND",))
    ]
    idat_checksum_index = calls.index(("checksum", (b"IDAT", b"data", b"crc!")))
    iend_checksum_index = calls.index(("checksum", (b"IEND", b"data", b"crc!")))
    fix_index = calls.index(("fix_it_felix", (b"IEND",)))
    assert idat_checksum_index < fix_index
    assert iend_checksum_index < fix_index


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


def test_run_main_loop_once_applies_deferred_find_magic_repair_after_chunk_walk():
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

    def apply_deferred():
        calls.append(("apply_deferred",))
        namespace["SAVE_COUNT"] += 1

    def fix_it_felix(chunk):
        calls.append(("fix_it_felix", chunk))
        namespace["Show_Must_Go_On"] = True

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
            "Apply_Deferred_FindMagic_Repair": apply_deferred,
            "Clear_Deferred_FindMagic_Repair": lambda: calls.append(("clear_deferred",)),
        }
    )

    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        os.unlink(sample_path)

    assert state == main_runtime.MainLoopIterationState()
    assert calls.index(("chunk_by_chunk", 0)) < calls.index(("apply_deferred",))
    assert calls.index(("checksum", ("raw-type", "raw-data", "raw-crc"))) < calls.index(("apply_deferred",))
    assert ("clear_deferred",) not in calls
    assert namespace["SAVE_COUNT"] == 1


def test_run_main_loop_once_does_not_apply_deferred_find_magic_before_walk_end():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNGstill-walking")
        sample_path = handle.name

    namespace = {}

    def chunk_by_chunk(offset):
        calls.append(("chunk_by_chunk", offset))
        namespace.update(
            {
                "Orig_CD": "orig-data",
                "Orig_CL": "orig-len",
                "Orig_CT": b"IDAT",
                "Chunks_History": [b"PNG", b"IHDR", b"IDAT"],
                "Raw_Data": "raw-data",
                "Raw_Type": "raw-type",
                "Raw_Crc": "raw-crc",
                "Raw_Length": "raw-len",
                "Show_Must_Go_On": False,
                "Have_A_KitKat": False,
            }
        )

    def checksum(*args):
        calls.append(("checksum", args))
        namespace["Have_A_KitKat"] = True

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
            "Checksum": checksum,
            "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
            "Apply_Deferred_FindMagic_Repair": lambda: calls.append(("apply_deferred",)),
            "Clear_Deferred_FindMagic_Repair": lambda: calls.append(("clear_deferred",)),
            "Open_Current_Final_Image_If_Valid": lambda: calls.append(("open_final",)),
        }
    )

    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        os.unlink(sample_path)

    assert state == main_runtime.MainLoopIterationState(should_return=True)
    assert ("apply_deferred",) not in calls
    assert ("clear_deferred",) not in calls
    assert ("fix_it_felix", b"IDAT") not in calls


def test_run_main_loop_once_does_not_apply_deferred_without_visible_iend():
    calls = []
    sample_bytes = b"\x89PNGstill-drifting"
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(sample_bytes)
        sample_path = handle.name

    namespace = {}

    def chunk_by_chunk(offset):
        calls.append(("chunk_by_chunk", offset))
        namespace.update(
            {
                "Orig_CD": "orig-data",
                "Orig_CL": "orig-len",
                "Orig_CT": b"IDAT",
                "Chunks_History": [b"PNG", b"IHDR", b"IDAT"],
                "Raw_Data": "x" * 200,
                "Raw_Type": "raw-type",
                "Raw_Crc": "raw-crc",
                "Raw_Length": "raw-len",
                "Show_Must_Go_On": False,
                "Have_A_KitKat": False,
            }
        )

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
            "DEFERRED_LINEFEED_SIGNATURE_REPAIR": {"data_bytes": sample_bytes},
            "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
            "PRINT": lambda message: calls.append(("emit", message)),
            "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
            "FindMagic": lambda: calls.append(("find_magic",)) or 0,
            "ChunkbyChunk": chunk_by_chunk,
            "CheckLength": lambda *args: calls.append(("check_length", args)),
            "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
            "GetInfo": lambda *args: calls.append(("get_info", args)),
            "Checksum": lambda *args: calls.append(("checksum", args)),
            "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
            "Apply_Deferred_FindMagic_Repair": lambda: calls.append(("apply_deferred",)),
            "Clear_Deferred_FindMagic_Repair": lambda: calls.append(("clear_deferred",)),
            "Open_Current_Final_Image_If_Valid": lambda: calls.append(("open_final",)),
        }
    )

    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        os.unlink(sample_path)

    assert state == main_runtime.MainLoopIterationState(should_return=True)
    assert ("apply_deferred",) not in calls
    assert ("clear_deferred",) not in calls


def test_run_main_loop_once_applies_deferred_after_visible_linefeed_marker_tour():
    calls = []
    sample_bytes = (
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png"
    ).read_bytes()
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(sample_bytes)
        sample_path = handle.name

    namespace = {}

    def chunk_by_chunk(offset):
        calls.append(("chunk_by_chunk", offset))
        namespace.update(
            {
                "Orig_CD": "orig-data",
                "Orig_CL": "orig-len",
                "Orig_CT": b"XBt\xd3",
                "Chunks_History": [b"PNG", b"IHDR", b"IDAT", b"IDAT"],
                "Raw_Data": "x" * len(sample_bytes.hex()),
                "Raw_Type": "raw-type",
                "Raw_Crc": "raw-crc",
                "Raw_Length": "raw-len",
                "Show_Must_Go_On": False,
                "Have_A_KitKat": False,
            }
        )

    def apply_deferred():
        calls.append(("apply_deferred",))
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
            "DEFERRED_LINEFEED_SIGNATURE_REPAIR": {"data_bytes": sample_bytes},
            "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
            "PRINT": lambda message: calls.append(("emit", message)),
            "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
            "FindMagic": lambda: calls.append(("find_magic",)) or 0,
            "ChunkbyChunk": chunk_by_chunk,
            "CheckLength": lambda *args: calls.append(("check_length", args)),
            "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
            "GetInfo": lambda *args: calls.append(("get_info", args)),
            "Checksum": lambda *args: calls.append(("checksum", args)),
            "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
            "Apply_Deferred_FindMagic_Repair": apply_deferred,
            "Clear_Deferred_FindMagic_Repair": lambda: calls.append(("clear_deferred",)),
            "Open_Current_Final_Image_If_Valid": lambda: calls.append(("open_final",)),
        }
    )

    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        os.unlink(sample_path)

    assert state == main_runtime.MainLoopIterationState()
    assert ("apply_deferred",) in calls
    assert (
        "-FindMagic: visible line-feed marker tour reached IEND before deferred repair."
        in namespace["SideNotes"]
    )


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
        "Clear_Terminal_Dialogue_Pause": lambda: calls.append(("clear_dialogue_pause",)),
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
    assert ("candy", ("Cowsay", "See you Space Cowboy...", "good")) in calls
    assert calls.index(("open_final",)) < calls.index(("emit", "-No new clone produced, stopping main loop."))
    assert calls.index(("emit", "-No new clone produced, stopping main loop.")) < calls.index(
        ("candy", ("Cowsay", "See you Space Cowboy...", "good"))
    )
    assert calls[-1] == ("candy", ("Cowsay", "See you Space Cowboy...", "good"))
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
        "Clear_Terminal_Dialogue_Pause": lambda: calls.append(("clear_dialogue_pause",)),
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


def test_run_main_loop_once_skips_output_cleanup_when_ultimate_resume_is_accepted():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    original_input = builtins.input

    def answer_resume(prompt):
        calls.append(("input", prompt))
        return "1"

    def find_magic():
        calls.append(("find_magic",))
        namespace["SAVE_COUNT"] += 1
        return None

    progress_name = main_runtime.ULTIMATE_LINEFEED_PROGRESS_NAME
    fake_os = SimpleNamespace(
        name="posix",
        system=lambda command: calls.append(("system", command)),
        makedirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        listdir=lambda path: calls.append(("listdir", path)) or [progress_name, "old.png"],
        path=SimpleNamespace(
            basename=os.path.basename,
            exists=lambda path: calls.append(("exists", path)) or True,
            isdir=lambda path: calls.append(("isdir", path)) or True,
            abspath=lambda path: "/abs/" + path,
            join=lambda *parts: "/".join(parts),
        ),
        remove=lambda path: calls.append(("remove_file", path)),
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
        "ULTIMATE_LINEFEED_RESUME": "ask",
        "Sample": sample_path,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Clear_Terminal_Dialogue_Pause": lambda: calls.append(("clear_dialogue_pause",)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "FindMagic": find_magic,
        "ChunkbyChunk": lambda offset: calls.append(("chunk_by_chunk", offset)),
        "CheckLength": lambda *args: calls.append(("check_length", args)),
        "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
        "GetInfo": lambda *args: calls.append(("get_info", args)),
        "Checksum": lambda *args: calls.append(("checksum", args)),
        "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
    }

    builtins.input = answer_resume
    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        builtins.input = original_input
        os.unlink(sample_path)

    folder = "/out/Folder_%s" % os.path.basename(sample_path)
    assert state == main_runtime.MainLoopIterationState()
    assert namespace["ULTIMATE_LINEFEED_RESUME_DECISION"] == "resume"
    assert namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] is False
    assert ("remove_tree", folder) not in calls
    assert ("input", "-Delete existing output folder '%s'? (yes/no): " % folder) not in calls
    assert ("input", "-Ultimate line-feed resume choice [1 resume]: ") in calls
    assert ("clear_dialogue_pause",) in calls
    resume_prompt_calls = [
        call
        for call in calls
        if call[0] == "candy"
        and call[1][0] == "Cowsay"
        and (
            "UltimateMegaSuperLineFeedBruteForce checkpoint" in str(call[1][1])
            or "clean Ultimate source snapshot" in str(call[1][1])
            or "1. resume\n2. ignore once" in str(call[1][1])
        )
    ]
    assert resume_prompt_calls == [
        (
            "candy",
            (
                "Cowsay",
                "I found an UltimateMegaSuperLineFeedBruteForce checkpoint in this folder. I can resume from it instead of wiping the output.",
                "good",
            ),
        ),
        (
            "candy",
            (
                "Cowsay",
                "If a clean Ultimate source snapshot exists, I can jump straight back; otherwise I will finish the file tour first.",
                "com",
            ),
        ),
        (
            "candy",
            (
                "Cowsay",
                "1. resume\n2. ignore once\n3. reset checkpoints\n4. abort",
                "com",
            ),
        ),
    ]
    assert ("find_magic",) in calls


def test_run_main_loop_once_skips_output_cleanup_for_candidate_checkpoint_only():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    original_input = builtins.input

    def answer_resume(prompt):
        calls.append(("input", prompt))
        return "1"

    checkpoint_name = main_runtime.ULTIMATE_LINEFEED_CHECKPOINT_NAME
    fake_os = SimpleNamespace(
        name="posix",
        system=lambda command: calls.append(("system", command)),
        makedirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        listdir=lambda path: calls.append(("listdir", path)) or [checkpoint_name, "old.png"],
        path=SimpleNamespace(
            basename=os.path.basename,
            exists=lambda path: calls.append(("exists", path)) or True,
            isdir=lambda path: calls.append(("isdir", path)) or True,
            abspath=lambda path: "/abs/" + path,
            join=lambda *parts: "/".join(parts),
        ),
        remove=lambda path: calls.append(("remove_file", path)),
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
        "ULTIMATE_LINEFEED_RESUME": "ask",
        "Sample": sample_path,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Clear_Terminal_Dialogue_Pause": lambda: calls.append(("clear_dialogue_pause",)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "FindMagic": lambda: calls.append(("find_magic",)) or None,
        "ChunkbyChunk": lambda offset: calls.append(("chunk_by_chunk", offset)),
        "CheckLength": lambda *args: calls.append(("check_length", args)),
        "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
        "GetInfo": lambda *args: calls.append(("get_info", args)),
        "Checksum": lambda *args: calls.append(("checksum", args)),
        "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
    }

    builtins.input = answer_resume
    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        builtins.input = original_input
        os.unlink(sample_path)

    folder = "/out/Folder_%s" % os.path.basename(sample_path)
    assert state == main_runtime.MainLoopIterationState(should_return=True)
    assert namespace["ULTIMATE_LINEFEED_RESUME_DECISION"] == "resume"
    assert namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] is False
    assert ("remove_tree", folder) not in calls
    assert ("input", "-Delete existing output folder '%s'? (yes/no): " % folder) not in calls
    assert ("input", "-Ultimate line-feed resume choice [1 resume]: ") in calls
    assert ("clear_dialogue_pause",) in calls


def test_run_main_loop_once_directly_resumes_ultimate_before_find_magic():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    checkpoint_name = main_runtime.ULTIMATE_LINEFEED_CHECKPOINT_NAME
    fake_os = SimpleNamespace(
        name="posix",
        system=lambda command: calls.append(("system", command)),
        makedirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        listdir=lambda path: calls.append(("listdir", path)) or [checkpoint_name],
        path=SimpleNamespace(
            basename=os.path.basename,
            exists=lambda path: calls.append(("exists", path)) or True,
            isdir=lambda path: calls.append(("isdir", path)) or True,
            abspath=lambda path: "/abs/" + path,
            join=lambda *parts: "/".join(parts),
        ),
        remove=lambda path: calls.append(("remove_file", path)),
    )

    def direct_resume():
        calls.append(("direct_resume",))
        namespace["SAVE_COUNT"] += 1
        return "direct-result"

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
        "ULTIMATE_LINEFEED_RESUME": "auto",
        "Sample": sample_path,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Clear_Terminal_Dialogue_Pause": lambda: calls.append(("clear_dialogue_pause",)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "Prepare_Immediate_Summary": lambda: calls.append(("prepare_summary",)),
        "Run_Ultimate_Linefeed_Direct_Resume": direct_resume,
        "FindMagic": lambda: calls.append(("find_magic",)) or 0,
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
    assert namespace["ULTIMATE_LINEFEED_RESUME_DECISION"] == "resume"
    assert namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] is False
    assert ("prepare_summary",) in calls
    assert ("direct_resume",) in calls
    assert ("find_magic",) not in calls
    assert not [call for call in calls if call[0] == "chunk_by_chunk"]


def test_run_main_loop_once_skips_output_cleanup_when_smash_resume_is_accepted():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    original_input = builtins.input

    def answer_resume(prompt):
        calls.append(("input", prompt))
        return "1"

    def find_magic():
        calls.append(("find_magic",))
        namespace["SAVE_COUNT"] += 1
        return None

    progress_name = main_runtime.SMASH_BRUTE_BRAWL_PROGRESS_NAME
    fake_os = SimpleNamespace(
        name="posix",
        system=lambda command: calls.append(("system", command)),
        makedirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        listdir=lambda path: calls.append(("listdir", path)) or [progress_name, "old.png"],
        path=SimpleNamespace(
            basename=os.path.basename,
            exists=lambda path: calls.append(("exists", path)) or True,
            isdir=lambda path: calls.append(("isdir", path)) or True,
            abspath=lambda path: "/abs/" + path,
            join=lambda *parts: "/".join(parts),
        ),
        remove=lambda path: calls.append(("remove_file", path)),
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
        "ULTIMATE_LINEFEED_RESUME": "ask",
        "SMASH_BRUTE_BRAWL_RESUME": "ask",
        "Sample": sample_path,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Clear_Terminal_Dialogue_Pause": lambda: calls.append(("clear_dialogue_pause",)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "FindMagic": find_magic,
        "ChunkbyChunk": lambda offset: calls.append(("chunk_by_chunk", offset)),
        "CheckLength": lambda *args: calls.append(("check_length", args)),
        "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
        "GetInfo": lambda *args: calls.append(("get_info", args)),
        "Checksum": lambda *args: calls.append(("checksum", args)),
        "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
    }

    builtins.input = answer_resume
    try:
        state = main_runtime.run_main_loop_once_from_namespace(namespace)
    finally:
        builtins.input = original_input
        os.unlink(sample_path)

    folder = "/out/Folder_%s" % os.path.basename(sample_path)
    assert state == main_runtime.MainLoopIterationState()
    assert namespace["SMASH_BRUTE_BRAWL_RESUME_DECISION"] == "resume"
    assert namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] is False
    assert ("remove_tree", folder) not in calls
    assert ("input", "-Delete existing output folder '%s'? (yes/no): " % folder) not in calls
    assert ("input", "-SmashBruteBrawl resume choice [1 resume]: ") in calls
    assert ("clear_dialogue_pause",) in calls
    assert ("find_magic",) in calls


def test_run_main_loop_once_directly_resumes_smash_before_find_magic():
    calls = []
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    progress_name = main_runtime.SMASH_BRUTE_BRAWL_PROGRESS_NAME
    fake_os = SimpleNamespace(
        name="posix",
        system=lambda command: calls.append(("system", command)),
        makedirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        listdir=lambda path: calls.append(("listdir", path)) or [progress_name],
        path=SimpleNamespace(
            basename=os.path.basename,
            exists=lambda path: calls.append(("exists", path)) or True,
            isdir=lambda path: calls.append(("isdir", path)) or True,
            abspath=lambda path: "/abs/" + path,
            join=lambda *parts: "/".join(parts),
        ),
        remove=lambda path: calls.append(("remove_file", path)),
    )

    def direct_resume():
        calls.append(("direct_resume",))
        namespace["SAVE_COUNT"] += 1
        return "direct-result"

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
        "ULTIMATE_LINEFEED_RESUME": "ask",
        "SMASH_BRUTE_BRAWL_RESUME": "auto",
        "Sample": sample_path,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Clear_Terminal_Dialogue_Pause": lambda: calls.append(("clear_dialogue_pause",)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "Prepare_Immediate_Summary": lambda: calls.append(("prepare_summary",)),
        "Run_Smash_Brute_Brawl_Direct_Resume": direct_resume,
        "FindMagic": lambda: calls.append(("find_magic",)) or 0,
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
    assert namespace["SMASH_BRUTE_BRAWL_RESUME_DECISION"] == "resume"
    assert namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] is False
    assert ("prepare_summary",) in calls
    assert ("direct_resume",) in calls
    assert ("find_magic",) not in calls
    assert not [call for call in calls if call[0] == "chunk_by_chunk"]


def test_run_main_loop_once_checks_existing_output_before_summary_preparation():
    calls = []
    folders = {}
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        handle.write(b"\x89PNG")
        sample_path = handle.name

    folder = output.clone_folder(sample_path, "/out/")

    def prepare_summary():
        calls.append(("prepare_summary",))
        folders[folder] = ["Summary_Of_%s" % Path(sample_path).stem]

    def find_magic():
        calls.append(("find_magic",))
        namespace["SAVE_COUNT"] += 1
        return None

    fake_os = SimpleNamespace(
        name="posix",
        system=lambda command: calls.append(("system", command)),
        makedirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        listdir=lambda path: calls.append(("listdir", path)) or list(folders.get(path, [])),
        path=SimpleNamespace(
            basename=os.path.basename,
            exists=lambda path: calls.append(("exists", path)) or path in folders,
            isdir=lambda path: calls.append(("isdir", path)) or path in folders,
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
        "Prepare_Immediate_Summary": prepare_summary,
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
    assert calls.index(("exists", folder)) < calls.index(("prepare_summary",))
    assert ("input", "-Delete existing output folder '%s'? (yes/no): " % folder) not in calls
    assert ("remove_tree", folder) not in calls
    assert folders[folder] == ["Summary_Of_%s" % Path(sample_path).stem]
    assert ("find_magic",) in calls


def assert_run_main_loop_once_does_not_prepare_summary_when_sample_load_fails(tmp_path):
    calls = []
    missing_sample = str(tmp_path / "missing.png")
    folder = output.clone_folder(missing_sample, "/out/")

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
        "FILE_Origin": missing_sample,
        "FILE_DIR": "/out/",
        "OUTPUT_FOLDER_CLEANUP_PENDING": False,
        "Sample": missing_sample,
        "CLONESWAR": False,
        "SAVE_COUNT": 0,
        "Candy": lambda *args: "<%s:%s>" % (args[1], args[2]) if args[0] == "Color" else calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "Prepare_Immediate_Summary": lambda: calls.append(("prepare_summary", folder)),
        "FindMagic": lambda: calls.append(("find_magic",)) or None,
        "ChunkbyChunk": lambda offset: calls.append(("chunk_by_chunk", offset)),
        "CheckLength": lambda *args: calls.append(("check_length", args)),
        "CheckChunkName": lambda *args: calls.append(("check_chunk_name", args)),
        "GetInfo": lambda *args: calls.append(("get_info", args)),
        "Checksum": lambda *args: calls.append(("checksum", args)),
        "FixItFelix": lambda chunk: calls.append(("fix_it_felix", chunk)),
    }

    state = main_runtime.run_main_loop_once_from_namespace(namespace)

    assert state == main_runtime.MainLoopIterationState(should_return=True)
    assert ("exit", 1) in calls
    assert ("prepare_summary", folder) not in calls
    assert ("find_magic",) not in calls


def test_run_main_loop_once_does_not_prepare_summary_when_sample_load_fails(tmp_path):
    assert_run_main_loop_once_does_not_prepare_summary_when_sample_load_fails(tmp_path)


def run_main_loop_once_missing_sample_summary_check():
    with tempfile.TemporaryDirectory() as directory:
        assert_run_main_loop_once_does_not_prepare_summary_when_sample_load_fails(
            Path(directory)
        )


def main():
    checks = [
        ("main cleanup boundary", test_chunklate_main_has_no_direct_global_wiring_and_no_dead_reached_end_comment),
        ("runtime builders", test_build_main_runtime_helpers_wire_callbacks),
        (
            "ultimate linefeed resume paths",
            test_ultimate_linefeed_paths_use_short_names_with_legacy_resume_fallback,
        ),
        (
            "ultimate linefeed reset files",
            test_reset_ultimate_linefeed_resume_files_removes_short_and_legacy_names,
        ),
        (
            "SmashBruteBrawl reset files",
            test_reset_smash_brute_brawl_resume_files_removes_short_names,
        ),
        ("main options state", test_apply_main_cli_options_builds_initial_state),
        ("legacy clone/crash", test_apply_main_cli_options_preserves_legacy_unknown_clone_and_crash),
        ("invalid crash", test_apply_main_cli_options_exits_on_invalid_crash),
        ("help without args", test_apply_main_cli_options_prints_help_without_args),
        ("missing filename", test_apply_main_cli_options_exits_without_filename),
        ("bad max saves", test_apply_main_cli_options_exits_on_bad_max_saves),
        ("bad ultimate budget", test_apply_main_cli_options_exits_on_bad_ultimate_linefeed_budget),
        (
            "bad ultimate preview timeout",
            test_apply_main_cli_options_exits_on_bad_ultimate_preview_timeout,
        ),
        (
            "bad ultimate resume mode",
            test_apply_main_cli_options_exits_on_bad_ultimate_resume_mode,
        ),
        (
            "bad SmashBruteBrawl resume mode",
            test_apply_main_cli_options_exits_on_bad_smash_brute_brawl_resume_mode,
        ),
        ("legacy globals", test_legacy_globals_from_main_cli_options_maps_runtime_flags),
        ("namespace CLI options", test_apply_main_cli_options_from_namespace_updates_legacy_globals),
        ("loop reset state", test_reset_main_loop_state_updates_legacy_globals_and_preserves_local_tmp_fixihdr),
        ("loop reset fresh containers", test_reset_main_loop_state_uses_fresh_history_containers_each_time),
        (
            "loop reset sPLT state",
            test_reset_main_loop_state_clears_splt_state_between_repair_passes,
        ),
        ("clear screen startup", test_run_main_clear_screen_preserves_startup_skip),
        ("clear screen posix", test_run_main_clear_screen_writes_ansi_reset_on_posix_after_startup),
        ("clear screen windows", test_run_main_clear_screen_calls_cls_on_windows_after_startup),
        ("load sample", test_load_main_sample_selects_current_sample_and_loads_data),
        ("load clone sample", test_load_main_sample_uses_cloneswar_then_resets_it),
        ("load fixed clone sample", test_load_main_sample_announces_fixed_clone_even_without_cloneswar_flag),
        ("load sample error", test_load_main_sample_routes_load_error_to_legacy_error_path),
        ("chunk walk no offset", test_run_main_chunk_walk_returns_without_offset),
        ("chunk walk order", test_run_main_chunk_walk_runs_legacy_callback_order_and_updates_offset),
        ("chunk walk defers IHDR value repair", test_run_main_chunk_walk_defers_ihdr_value_repair_until_file_tour_ends),
        (
            "chunk walk defers generic findings",
            test_run_main_chunk_walk_defers_generic_findings_until_iend_even_with_immediate_flags,
        ),
        (
            "chunk walk no-next boundary",
            test_run_main_chunk_walk_allows_felix_on_non_iend_no_next_chunk_boundary,
        ),
        (
            "chunk walk deferred FindMagic allows missing IEND route",
            test_run_main_chunk_walk_allows_no_next_route_when_deferred_has_no_visible_iend,
        ),
        (
            "chunk walk deferred FindMagic blocks Felix after visible IEND",
            test_run_main_chunk_walk_defers_no_next_when_visible_linefeed_tour_finds_iend,
        ),
        (
            "chunk walk defers private compression repair",
            test_run_main_chunk_walk_defers_private_compression_repair_until_after_idat,
        ),
        ("chunk walk kitkat", test_run_main_chunk_walk_stops_when_kitkat_breaks),
        ("main loop namespace", test_run_main_loop_once_from_namespace_resets_loads_and_walks_sample),
        (
            "main loop deferred FindMagic repair",
            test_run_main_loop_once_applies_deferred_find_magic_repair_after_chunk_walk,
        ),
        (
            "main loop deferred FindMagic waits for walk end",
            test_run_main_loop_once_does_not_apply_deferred_find_magic_before_walk_end,
        ),
        ("main loop counts FindMagic clone", test_run_main_loop_once_counts_clone_written_by_find_magic),
        ("main loop opens final image on clean no-clone exit", test_run_main_loop_once_opens_valid_final_image_when_no_clone_written),
        ("main loop cleanup after banner", test_run_main_loop_once_asks_output_cleanup_after_banner),
        (
            "main loop ultimate resume skips cleanup",
            test_run_main_loop_once_skips_output_cleanup_when_ultimate_resume_is_accepted,
        ),
        (
            "main loop ultimate candidate checkpoint skips cleanup",
            test_run_main_loop_once_skips_output_cleanup_for_candidate_checkpoint_only,
        ),
        (
            "main loop ultimate direct resume",
            test_run_main_loop_once_directly_resumes_ultimate_before_find_magic,
        ),
        (
            "main loop SmashBruteBrawl resume skips cleanup",
            test_run_main_loop_once_skips_output_cleanup_when_smash_resume_is_accepted,
        ),
        (
            "main loop SmashBruteBrawl direct resume",
            test_run_main_loop_once_directly_resumes_smash_before_find_magic,
        ),
        (
            "main loop cleanup before summary",
            test_run_main_loop_once_checks_existing_output_before_summary_preparation,
        ),
        (
            "main loop load failure before summary",
            run_main_loop_once_missing_sample_summary_check,
        ),
    ]

    print("Running main runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"main runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
