#!/usr/bin/env python3
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Chunklate
from chunklate import checkpoint, checkpoint_runtime


@contextmanager
def patched_attrs(module, **attrs):
    old_values = {name: getattr(module, name) for name in attrs}
    try:
        for name, value in attrs.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in old_values.items():
            setattr(module, name, value)


def callback_runtime(calls):
    def callback(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return name

        return inner

    return checkpoint_runtime.CheckPointRuntime(
        write_clone=callback("write_clone"),
        dummy_chunk=callback("dummy_chunk"),
        summarise=callback("summarise"),
        find_fucking_magic=callback("find_fucking_magic"),
        check_chunk_name=callback("check_chunk_name"),
        save_clone=callback("save_clone"),
        fix_it_felix=callback("fix_it_felix"),
        relics=callback("relics"),
        smash_brute_brawl=callback("smash_brute_brawl"),
        candy=callback("candy"),
        emit=callback("emit"),
        end=callback("end"),
        question=callback("question"),
        print_libpng_critical=callback("print_libpng_critical"),
        discard_libpng_warning=callback("discard_libpng_warning"),
        libpng_end_success=callback("libpng_end_success"),
    )


def test_checkpoint_loop_runtime_records_finding_pauses_and_applies_action():
    calls = []

    def record_finding(registration):
        calls.append(("record_finding", registration))

    def apply_action(decision, chunk, info, toolkit):
        calls.append(("apply_action", decision, chunk, info, toolkit))
        return False, None

    def pause_error(prompt):
        calls.append(("pause_error", prompt))

    result = checkpoint_runtime.run_checkpoint_loop(
        checkpoint_runtime.CheckPointLoopRuntime(
            record_finding=record_finding,
            apply_action=apply_action,
            pause_error=pause_error,
        ),
        checkpoint_runtime.CheckPointLoopContext(
            error=True,
            fixed=False,
            function="Checksum",
            chunk=b"IDAT",
            infos=("-Wrong Crc b'IDAT'",),
            toolkit=("crc", 12, 20),
            brute_level=0,
            libpng_errors=(),
            libpng_finished_at_iend=False,
            pause_error_enabled=True,
        ),
    )

    assert result == ()
    registration = calls[0][1]
    assert calls[0][0] == "record_finding"
    assert registration.store == "pandora_box"
    assert registration.side_note == "Error:-Wrong Crc b'IDAT'"
    assert calls[1] == ("pause_error", "Pause:Error")
    assert calls[2] == (
        "apply_action",
        checkpoint.CheckPointActionDecision(flags={"Bad_Crc": True}),
        b"IDAT",
        "-Wrong Crc b'IDAT'",
        ("crc", 12, 20),
    )


def test_checkpoint_loop_runtime_returns_first_action_result():
    calls = []

    def apply_action(decision, chunk, info, toolkit):
        calls.append((decision, chunk, info, toolkit))
        return True, decision.return_value

    result = checkpoint_runtime.run_checkpoint_loop(
        checkpoint_runtime.CheckPointLoopRuntime(
            record_finding=lambda registration: calls.append(registration),
            apply_action=apply_action,
            pause_error=lambda prompt: calls.append(prompt),
        ),
        checkpoint_runtime.CheckPointLoopContext(
            error=False,
            fixed=False,
            function="FindMagic",
            chunk=b"PNG",
            infos=("-Found Magic",),
            toolkit=(16,),
            brute_level=0,
            libpng_errors=(),
            libpng_finished_at_iend=False,
            pause_error_enabled=False,
        ),
    )

    assert result == 16
    assert calls == [
        (
            checkpoint.CheckPointActionDecision(
                action="return_value",
                side_note="-CheckPoint: Returning next position based on Magic Offset 16",
                return_value=16,
            ),
            b"PNG",
            "-Found Magic",
            (16,),
        )
    ]


def test_checkpoint_entry_runtime_emits_header_and_routes_loop():
    calls = []

    def apply_action(decision, chunk, info, toolkit):
        calls.append(("apply_action", decision, chunk, info, toolkit))
        return True, "done"

    result = checkpoint_runtime.run_checkpoint(
        checkpoint_runtime.CheckPointEntryRuntime(
            candy=lambda *args: calls.append(("candy", args)),
            emit=lambda message: calls.append(("emit", message)),
            pause_debug=lambda prompt: calls.append(("pause_debug", prompt)),
            record_finding=lambda registration: calls.append(("record_finding", registration)),
            apply_action=apply_action,
            pause_error=lambda prompt: calls.append(("pause_error", prompt)),
        ),
        checkpoint_runtime.CheckPointEntryContext(
            error=False,
            fixed=False,
            function="FindMagic",
            chunk=b"PNG",
            infos=("-Found Magic",),
            toolkit=(16,),
            brute_level=0,
            libpng_errors=(),
            libpng_finished_at_iend=False,
            pandora_keys=(),
            debug=False,
            pause_debug_enabled=False,
            pause_error_enabled=False,
        ),
    )

    assert result == "done"
    assert calls[0] == ("candy", ("Title", "CheckPoint"))
    assert calls[1] == ("emit", checkpoint_runtime.CHECKPOINT_COFFEE)
    assert calls[2] == (
        "apply_action",
        checkpoint.CheckPointActionDecision(
            action="return_value",
            side_note="-CheckPoint: Returning next position based on Magic Offset 16",
            return_value=16,
        ),
        b"PNG",
        "-Found Magic",
        (16,),
    )


def test_checkpoint_entry_runtime_preserves_debug_and_pause():
    calls = []

    checkpoint_runtime.run_checkpoint(
        checkpoint_runtime.CheckPointEntryRuntime(
            candy=lambda *args: calls.append(("candy", args)),
            emit=lambda message: calls.append(("emit", message)),
            pause_debug=lambda prompt: calls.append(("pause_debug", prompt)),
            record_finding=lambda registration: calls.append(("record_finding", registration)),
            apply_action=lambda decision, chunk, info, toolkit: (False, None),
            pause_error=lambda prompt: calls.append(("pause_error", prompt)),
        ),
        checkpoint_runtime.CheckPointEntryContext(
            error=True,
            fixed=False,
            function="Checksum",
            chunk=b"IDAT",
            infos=("-Wrong Crc",),
            toolkit=("crc",),
            brute_level=0,
            libpng_errors=(),
            libpng_finished_at_iend=False,
            pandora_keys=("PandoraKey",),
            debug=True,
            pause_debug_enabled=True,
            pause_error_enabled=False,
        ),
    )

    assert ("emit", "error:True") in calls
    assert ("emit", "Pandora:") in calls
    assert ("emit", "key:PandoraKey") in calls
    assert ("pause_debug", "Checkpoint pause") in calls


def test_checkpoint_entry_builders_preserve_legacy_namespace_mapping():
    calls = []
    namespace = {
        "Brute_LvL": 2,
        "LIBPNG_ERR": ["libpng error:", "libpng warning:"],
        "Chunks_History": [b"IHDR", b"IEND"],
        "EOF": True,
        "PandoraBox": {"key": "value"},
        "DATAX": "001122",
        "CLoffI": 42,
        "Sample_Name": "sample.png",
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": True,
    }

    runtime = checkpoint_runtime.build_checkpoint_entry_runtime(
        candy=lambda *args: calls.append(("candy", args)),
        emit=lambda message: calls.append(("emit", message)),
        pause_debug=lambda prompt: calls.append(("pause_debug", prompt)),
        record_finding=lambda registration: calls.append(("record", registration)),
        apply_action=lambda decision, chunk, info, toolkit: (True, "result"),
        pause_error=lambda prompt: calls.append(("pause_error", prompt)),
    )
    context = checkpoint_runtime.build_checkpoint_entry_context(
        namespace,
        error=True,
        fixed=False,
        function="LibpngCheck",
        chunk="LibpngCheck",
        infos=["-error"],
        toolkit=("tool",),
    )

    assert isinstance(runtime, checkpoint_runtime.CheckPointEntryRuntime)
    assert context == checkpoint_runtime.CheckPointEntryContext(
        error=True,
        fixed=False,
        function="LibpngCheck",
        chunk="LibpngCheck",
        infos=("-error",),
        toolkit=("tool",),
        brute_level=2,
        libpng_errors=("libpng error:", "libpng warning:"),
        libpng_finished_at_iend=True,
        pandora_keys=("key",),
        chunks_history=(b"IHDR", b"IEND"),
        data_hex="001122",
        current_offset=42,
        sample_name="sample.png",
        debug=True,
        pause_debug_enabled=False,
        pause_error_enabled=True,
    )


def test_checkpoint_namespace_entry_bridge_builds_runtime_and_context():
    calls = []
    namespace = {
        "Candy": lambda *args: calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Pause": lambda prompt: calls.append(("pause", prompt)),
        "CheckPoint_Record_Finding": lambda registration: calls.append(("record", registration)),
        "CheckPoint_Apply_Action_Decision": lambda decision, chunk, info, toolkit: (
            calls.append(("apply", decision, chunk, info, toolkit)) or (True, "done")
        ),
        "Brute_LvL": 2,
        "LIBPNG_ERR": ["libpng error:"],
        "Chunks_History": [b"IHDR"],
        "EOF": False,
        "PandoraBox": {"key": "value"},
        "DATAX": "001122",
        "CLoffI": 42,
        "Sample_Name": "sample.png",
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": True,
    }

    def runner(runtime, context):
        assert runtime.candy is namespace["Candy"]
        assert runtime.emit is namespace["PRINT"]
        assert runtime.pause_debug is namespace["Pause"]
        assert runtime.record_finding is namespace["CheckPoint_Record_Finding"]
        assert runtime.apply_action is namespace["CheckPoint_Apply_Action_Decision"]
        assert runtime.pause_error is namespace["Pause"]
        assert context.error is True
        assert context.fixed is False
        assert context.function == "Checksum"
        assert context.chunk == b"IDAT"
        assert context.infos == ("-Wrong Crc",)
        assert context.toolkit == ("tool",)
        assert context.brute_level == 2
        assert context.libpng_errors == ("libpng error:",)
        assert context.libpng_finished_at_iend is False
        assert context.pandora_keys == ("key",)
        assert context.chunks_history == (b"IHDR",)
        assert context.data_hex == "001122"
        assert context.current_offset == 42
        assert context.sample_name == "sample.png"
        assert context.debug is True
        assert context.pause_error_enabled is True
        return "checkpoint"

    result = checkpoint_runtime.run_checkpoint_from_namespace(
        namespace,
        error=True,
        fixed=False,
        function="Checksum",
        chunk=b"IDAT",
        infos=["-Wrong Crc"],
        toolkit=("tool",),
        runner=runner,
    )

    assert result == "checkpoint"


def test_checkpoint_fog_of_war_counts_current_and_previous_idat_crc_errors():
    context = checkpoint_runtime.CheckPointEntryContext(
        error=True,
        fixed=False,
        function="Checksum",
        chunk=b"IDAT",
        infos=("-Wrong Crc b'IDAT'",),
        toolkit=("tool",),
        brute_level=0,
        libpng_errors=(),
        libpng_finished_at_iend=False,
        pandora_keys=(
            "Checksum_Error_0:-Wrong Crc b'IDAT'",
            "Checksum_Error_1:-Wrong Crc b'IDAT'",
            "Checksum_Error_0:-Wrong Crc b'PLTE'",
        ),
        chunks_history=(b"PNG", b"IHDR", b"IDAT", b"IDAT"),
        data_hex="00" * 128,
        current_offset=32,
        sample_name="sample.png",
    )

    rendered = checkpoint_runtime.render_fog_of_war_from_context(
        {
            "Candy": lambda mode, color, value: f"<{color}:{value}>",
            "FOG_OF_WAR_LAST_MAP": None,
            "FOG_OF_WAR_LAST_WIDTH": None,
        },
        context,
    )

    assert "<green:[IDAT><white::><red:3><green:/><yellow:3><green:]>" in rendered


def test_checkpoint_debug_lines_preserve_legacy_print_shape():
    long_bytes = b"x" * 120
    long_text = "y" * 120
    long_object = ["z" * 120]

    lines = checkpoint_runtime.checkpoint_debug_lines(
        error=True,
        fixed=False,
        function="Checksum",
        infos=["-Wrong Crc"],
        chunk=b"IDAT",
        toolkit=(long_bytes, long_text, long_object, 12),
        pandora_keys=("key1", b"key2"),
    )

    assert lines == (
        "error:True",
        "fixed:False",
        "function:Checksum",
        "infos:['-Wrong Crc']",
        "chunk:b'IDAT'",
        "ToolKit:",
        "Arg0:b'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx...To big to be displayed ...' type:<class 'bytes'>",
        "Arg1:yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy...To big to be displayed ... type:<class 'str'>",
        "Arg2:['zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz...To big to be displayed ... type:<class 'list'>",
        "Arg3:12 type:<class 'int'>",
        "Pandora:",
        "key:key1",
        "key:b'key2'",
    )


def test_emit_checkpoint_debug_uses_injected_emit_callback():
    emitted = []

    checkpoint_runtime.emit_checkpoint_debug(
        emitted.append,
        error=False,
        fixed=True,
        function="FindMagic",
        infos=("-Found Magic",),
        chunk=b"PNG",
        toolkit=(16,),
        pandora_keys=(),
    )

    assert emitted == [
        "error:False",
        "fixed:True",
        "function:FindMagic",
        "infos:-Found Magic",
        "chunk:b'PNG'",
        "ToolKit:",
        "Arg0:16 type:<class 'int'>",
        "Pandora:",
    ]


def test_checkpoint_runtime_keeps_legacy_callbacks():
    calls = []
    runtime = callback_runtime(calls)

    assert runtime.write_clone("data", "why") == "write_clone"
    assert runtime.dummy_chunk(b"IEND", 1, 2, 3, "info") == "dummy_chunk"
    assert runtime.save_clone("data", 1, 2, "info") == "save_clone"
    assert runtime.fix_it_felix("LibpngCheck") == "fix_it_felix"

    assert [call[0] for call in calls] == [
        "write_clone",
        "dummy_chunk",
        "save_clone",
        "fix_it_felix",
    ]


def test_checkpoint_runtime_runs_simple_actions():
    calls = []
    runtime = callback_runtime(calls)

    assert checkpoint_runtime.run_write_clone(runtime, ("data",)) == (True, "write_clone")
    assert checkpoint_runtime.run_dummy_chunk_from_the_good_place(
        runtime,
        (b"IEND", 10, 20, 30),
        "dummy info",
    ) == (True, "dummy_chunk")
    assert checkpoint_runtime.run_return_value("value") == (True, "value")
    assert checkpoint_runtime.run_summarise_and_write_clone(
        runtime,
        "summary",
        ("data",),
    ) == (True, "write_clone")
    assert checkpoint_runtime.run_find_fucking_magic(runtime) == (True, "find_fucking_magic")
    assert checkpoint_runtime.run_check_chunk_name(
        runtime,
        b"IDAT",
        b"bADR",
        ("0f",),
    ) == (True, "check_chunk_name")
    assert checkpoint_runtime.run_save_clone(
        runtime,
        ("data", 1, 2, "info"),
    ) == (True, "save_clone")
    assert checkpoint_runtime.run_save_clone_missing_bytes(
        runtime,
        (b"prefix", b"missing", b"suffix"),
    ) == (True, "save_clone")
    assert checkpoint_runtime.run_fix_it_felix_continue(runtime, "LibpngCheck") == (False, None)
    assert checkpoint_runtime.run_fix_it_felix_return(runtime, "LibpngCheck") == (
        True,
        "fix_it_felix",
    )

    assert calls == [
        ("write_clone", ("data", "-About to save."), {}),
        ("dummy_chunk", (b"IEND", 10, 20, 30, "dummy info"), {}),
        ("summarise", ("summary",), {}),
        ("write_clone", ("data", "-About to save."), {}),
        ("find_fucking_magic", (), {}),
        ("check_chunk_name", (b"IDAT", 15, b"bADR", True), {}),
        ("save_clone", ("data", 1, 2, "info"), {}),
        (
            "save_clone",
            (b"prefix", b"suffix", b"missingsuffix", "Fixing Missing bytes corruption"),
            {},
        ),
        ("fix_it_felix", ("LibpngCheck",), {}),
        ("fix_it_felix", ("LibpngCheck",), {}),
    ]


def test_checkpoint_runtime_runs_libpng_actions():
    calls = []
    runtime = callback_runtime(calls)

    assert checkpoint_runtime.run_libpng_warning_relics(
        runtime,
        "libpng warning: known issue",
    ) == (True, "relics")
    assert checkpoint_runtime.run_discard_libpng_warning(
        runtime,
        "discard_libpng_warning",
        "libpng warning: noisy profile",
    ) == (False, None)
    assert checkpoint_runtime.run_discard_libpng_warning(
        runtime,
        "discard_libpng_warning_and_end",
        "libpng warning: noisy profile",
    ) == (False, None)
    assert checkpoint_runtime.run_libpng_end_success(runtime) == (False, None)

    assert calls == [
        ("print_libpng_critical", ("libpng warning: known issue",), {}),
        ("candy", ("Cowsay", "Ah found something !", "good"), {}),
        ("relics", ("libpng warning: known issue",), {}),
        ("print_libpng_critical", ("libpng warning: noisy profile",), {}),
        ("candy", ("Cowsay", "Bah that's just a warning who cares ?! !", "good"), {}),
        ("candy", ("Cowsay", "im removing it ..", "good"), {}),
        ("discard_libpng_warning", (), {}),
        ("print_libpng_critical", ("libpng warning: noisy profile",), {}),
        ("candy", ("Cowsay", "Bah that's just a warning who cares ?! !", "good"), {}),
        ("candy", ("Cowsay", "im removing it ..", "good"), {}),
        ("discard_libpng_warning", (), {}),
        (
            "libpng_end_success",
            ("Well maybe i am missing something but as for my abilities my job is done here!",),
            {},
        ),
        (
            "libpng_end_success",
            (
                "Well maybe i am missing something but as far as my current abilities goes the job is done for me here!",
            ),
            {},
        ),
    ]


def test_checkpoint_runtime_runs_smash_brute_brawl_relaunches():
    calls = []
    runtime = callback_runtime(calls)
    toolkit = ("sample.png", b"IDAT", 4, 100, "Insert", "TwoBytes", "crc", "length")

    assert checkpoint_runtime.run_smash_brute_brawl_relaunch(
        runtime,
        toolkit,
        "from-error",
    ) == "smash_brute_brawl"
    assert checkpoint_runtime.run_smash_brute_brawl_relaunch(
        runtime,
        toolkit,
        "from-old-crc",
        bf_mode="Brutus",
        has_old_crc=True,
        old_crc="old-crc",
    ) == "smash_brute_brawl"

    assert calls == [
        (
            "smash_brute_brawl",
            ("sample.png", b"IDAT", 4, 100, "from-error"),
            {
                "EditMode": "Insert",
                "BfMode": "TwoBytes",
                "BruteCrc": "crc",
                "BruteLength": "length",
            },
        ),
        (
            "smash_brute_brawl",
            ("sample.png", b"IDAT", 4, 100, "from-old-crc"),
            {
                "EditMode": "Insert",
                "BfMode": "Brutus",
                "BruteCrc": "crc",
                "BruteLength": "length",
                "OldCrc": "old-crc",
            },
        ),
    ]


def test_checkpoint_runtime_runs_smash_brute_brawl_prompts():
    calls = []
    runtime = callback_runtime(calls)
    toolkit = ("sample.png", b"IDAT", 4, 100, "Insert", "TwoBytes", "crc", "length")

    assert checkpoint_runtime.ask_smash_brute_brawl_twobytes_retry(
        runtime,
        toolkit,
        brute_level=1,
        eta=2,
        ihdr_interlace="1",
    ) == "question"
    assert checkpoint_runtime.ask_smash_brute_brawl_dummy_idat_fallback(runtime) == "question"
    assert checkpoint_runtime.ask_smash_brute_brawl_custom_brutus(runtime) == "question"

    call_names = [call[0] for call in calls]
    assert call_names.count("question") == 3
    assert ("emit", ("-BruteForce Estimated Time : 0:00:24\n",), {}) in calls


def test_checkpoint_runtime_runs_smash_brute_brawl_end_actions():
    calls = []
    runtime = callback_runtime(calls)

    assert checkpoint_runtime.run_smash_brute_brawl_retry_ihdr(
        runtime,
        ("sample.png", b"IHDR", 13, 8, "Insert", "Bytes", "crc", "length"),
        "from-error",
        2,
    ) == (False, None)
    assert checkpoint_runtime.run_smash_brute_brawl_end_failed_noncustom(runtime) == (
        False,
        None,
    )
    assert checkpoint_runtime.run_smash_brute_brawl_end_unhandled(runtime) == (False, None)

    assert [call[0] for call in calls] == [
        "candy",
        "smash_brute_brawl",
        "candy",
        "end",
        "end",
    ]


def test_chunklate_checkpoint_runtime_uses_current_legacy_functions():
    calls = []

    def callback(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return name

        return inner

    with patched_attrs(
        Chunklate,
        WriteClone=callback("write_clone"),
        DummyChunk=callback("dummy_chunk"),
        Summarise=callback("summarise"),
        FindFuckingMagic=callback("find_fucking_magic"),
        CheckChunkName=callback("check_chunk_name"),
        SaveClone=callback("save_clone"),
        FixItFelix=callback("fix_it_felix"),
        Relics=callback("relics"),
        SmashBruteBrawl=callback("smash_brute_brawl"),
        Candy=callback("candy"),
        PRINT=callback("emit"),
        TheEnd=callback("end"),
        Question=callback("question"),
        CheckPoint_Print_Libpng_Critical=callback("print_libpng_critical"),
        CheckPoint_Discard_Libpng_Warning=callback("discard_libpng_warning"),
        CheckPoint_Libpng_End_Success=callback("libpng_end_success"),
    ):
        runtime = Chunklate.CheckPoint_Runtime()
        assert runtime.write_clone("data", "why") == "write_clone"
        assert runtime.relics("info") == "relics"
        assert runtime.end() == "end"
        assert runtime.question(skipauto=True) == "question"
        assert runtime.print_libpng_critical("warning") == "print_libpng_critical"
        assert runtime.discard_libpng_warning() == "discard_libpng_warning"
        assert runtime.libpng_end_success("done") == "libpng_end_success"

    assert [call[0] for call in calls] == [
        "write_clone",
        "relics",
        "end",
        "question",
        "print_libpng_critical",
        "discard_libpng_warning",
        "libpng_end_success",
    ]


def main():
    checks = [
        ("CheckPoint loop records and applies", test_checkpoint_loop_runtime_records_finding_pauses_and_applies_action),
        ("CheckPoint loop returns action result", test_checkpoint_loop_runtime_returns_first_action_result),
        ("CheckPoint entry routes loop", test_checkpoint_entry_runtime_emits_header_and_routes_loop),
        ("CheckPoint entry debug", test_checkpoint_entry_runtime_preserves_debug_and_pause),
        ("CheckPoint entry builders", test_checkpoint_entry_builders_preserve_legacy_namespace_mapping),
        ("CheckPoint namespace entry bridge", test_checkpoint_namespace_entry_bridge_builds_runtime_and_context),
        ("CheckPoint FogOfWar IDAT count", test_checkpoint_fog_of_war_counts_current_and_previous_idat_crc_errors),
        ("CheckPoint debug lines", test_checkpoint_debug_lines_preserve_legacy_print_shape),
        ("CheckPoint debug emit callback", test_emit_checkpoint_debug_uses_injected_emit_callback),
        ("CheckPointRuntime keeps callbacks", test_checkpoint_runtime_keeps_legacy_callbacks),
        ("CheckPointRuntime runs simple actions", test_checkpoint_runtime_runs_simple_actions),
        ("CheckPointRuntime runs libpng actions", test_checkpoint_runtime_runs_libpng_actions),
        (
            "CheckPointRuntime runs SmashBruteBrawl relaunches",
            test_checkpoint_runtime_runs_smash_brute_brawl_relaunches,
        ),
        (
            "CheckPointRuntime runs SmashBruteBrawl prompts",
            test_checkpoint_runtime_runs_smash_brute_brawl_prompts,
        ),
        (
            "CheckPointRuntime runs SmashBruteBrawl end actions",
            test_checkpoint_runtime_runs_smash_brute_brawl_end_actions,
        ),
        (
            "Chunklate builds CheckPointRuntime from legacy functions",
            test_chunklate_checkpoint_runtime_uses_current_legacy_functions,
        ),
    ]

    print("Running CheckPoint runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"checkpoint runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
