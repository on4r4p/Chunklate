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
