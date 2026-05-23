#!/usr/bin/env python3
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Chunklate
from chunklate import relics_runtime


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


def test_relics_runtime_keeps_legacy_callbacks():
    calls = []

    def callback(*args, **kwargs):
        calls.append((args, kwargs))
        return "called"

    runtime = relics_runtime.RelicsRuntime(
        save_clone=callback,
        smash_brute_brawl=callback,
        full_chunk_forcer_no_crc=callback,
        tk_manual_plte=callback,
        remove_chunk=callback,
        ask_choice=callback,
    )

    assert runtime.save_clone("data", 1, 2, "info") == "called"
    assert runtime.smash_brute_brawl("sample.png", b"IDAT", 4, 100, "error") == "called"
    assert runtime.full_chunk_forcer_no_crc("sample.png", b"IEND", 1, 2, "error") == "called"
    assert runtime.tk_manual_plte("sample.png", b"PLTE", 3, 4, "error") == "called"
    assert runtime.remove_chunk(1, 2, "remove") == "called"
    assert runtime.ask_choice("prompt", ("yes", "no"), "retry") == "called"
    assert len(calls) == 6


def test_chunklate_relics_runtime_uses_current_legacy_functions():
    calls = []

    def fake_save_clone(*args, **kwargs):
        calls.append(("save_clone", args, kwargs))
        return "save"

    def fake_smash_brute_brawl(*args, **kwargs):
        calls.append(("smash_brute_brawl", args, kwargs))
        return "brawl"

    def fake_full_chunk_forcer(*args, **kwargs):
        calls.append(("full_chunk_forcer_no_crc", args, kwargs))
        return "forcer"

    def fake_tk_manual_plte(*args, **kwargs):
        calls.append(("tk_manual_plte", args, kwargs))
        return "manual"

    def fake_remove_chunk(*args, **kwargs):
        calls.append(("remove_chunk", args, kwargs))
        return "remove"

    def fake_ask_choice(asker, prompt, choices, retry_prompt):
        calls.append(("ask_choice", (prompt, choices, retry_prompt), {"asker": asker}))
        return "choice"

    with patched_attrs(
        Chunklate,
        SaveClone=fake_save_clone,
        SmashBruteBrawl=fake_smash_brute_brawl,
        FullChunkForcerNoCrc=fake_full_chunk_forcer,
        Tk_Manual_Plte=fake_tk_manual_plte,
        RemoveChunk=fake_remove_chunk,
    ), patched_attrs(Chunklate.decisions, ask_choice=fake_ask_choice):
        runtime = Chunklate.Relics_Runtime()

        assert runtime.save_clone("data", 1, 2, "info") == "save"
        assert runtime.smash_brute_brawl("sample.png", b"IDAT", 4, 100, "error") == "brawl"
        assert runtime.full_chunk_forcer_no_crc("sample.png", b"IEND", 1, 2, "error") == "forcer"
        assert runtime.tk_manual_plte("sample.png", b"PLTE", 3, 4, "error") == "manual"
        assert runtime.remove_chunk(1, 2, "remove") == "remove"
        assert runtime.ask_choice("prompt", ("yes", "no"), "retry") == "choice"

    assert [call[0] for call in calls] == [
        "save_clone",
        "smash_brute_brawl",
        "full_chunk_forcer_no_crc",
        "tk_manual_plte",
        "remove_chunk",
        "ask_choice",
    ]


def main():
    checks = [
        ("RelicsRuntime keeps callbacks", test_relics_runtime_keeps_legacy_callbacks),
        ("Chunklate builds RelicsRuntime from legacy functions", test_chunklate_relics_runtime_uses_current_legacy_functions),
    ]

    print("Running Relics runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"relics runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
