#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import question_runtime


def input_from(values):
    answers = iter(values)
    return lambda prompt: next(answers)


def runtime_from(*, history=None, answers=None, **overrides):
    calls = []

    def callback(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            if name == "candy" and args and args[0] == "Color":
                return args[2]
            return name

        return inner

    runtime = question_runtime.QuestionRuntime(
        history=[] if history is None else history,
        nodialogue=False,
        auto=False,
        debug=False,
        pause_debug=False,
        offset=12,
        asker=input_from(["yes"] if answers is None else answers),
        candy=callback("candy"),
        emit=callback("emit"),
        pause=callback("pause"),
        end=callback("end"),
    )
    if overrides:
        runtime = question_runtime.QuestionRuntime(
            history=overrides.get("history", runtime.history),
            nodialogue=overrides.get("nodialogue", runtime.nodialogue),
            auto=overrides.get("auto", runtime.auto),
            debug=overrides.get("debug", runtime.debug),
            pause_debug=overrides.get("pause_debug", runtime.pause_debug),
            offset=overrides.get("offset", runtime.offset),
            asker=overrides.get("asker", runtime.asker),
            candy=overrides.get("candy", runtime.candy),
            emit=overrides.get("emit", runtime.emit),
            pause=overrides.get("pause", runtime.pause),
            end=overrides.get("end", runtime.end),
            clear=overrides.get("clear", runtime.clear),
            prompt_candy=overrides.get("prompt_candy", runtime.prompt_candy),
            status_sink=overrides.get("status_sink", runtime.status_sink),
        )
    return runtime, calls


def test_question_runtime_records_auto_answer_without_input():
    history = []
    runtime, calls = runtime_from(history=history, nodialogue=True, answers=[])

    answer = question_runtime.ask_question(runtime, "crc", 99)

    assert answer is True
    assert history == ["Infos:crc Answer:True Offset:12 Hash:99"]
    assert calls == [("candy", ("Title", "QUESTION!"), {})]


def test_question_runtime_reports_auto_mode_when_legacy_auto_is_enabled():
    runtime, calls = runtime_from(auto=True)

    assert question_runtime.ask_question(runtime, skipauto=False) is True

    assert calls == [
        ("candy", ("Title", "QUESTION!"), {}),
        ("candy", ("Color", "green", "Auto Answer Mode"), {}),
        ("emit", ("-Auto Answer Mode\n",), {}),
    ]


def test_question_runtime_manual_answer_uses_legacy_feedback():
    runtime, calls = runtime_from(answers=["no"])

    assert question_runtime.ask_question(runtime) is False

    assert calls == [
        ("candy", ("Title", "QUESTION!"), {}),
        ("candy", ("Cowsay", "Ok ,just do not make eye contact !", "com"), {}),
    ]


def test_question_runtime_eof_answer_is_decline():
    def eof_asker(_prompt):
        raise EOFError

    runtime, calls = runtime_from(asker=eof_asker)

    assert question_runtime.ask_question(runtime, "No NextChunk", 7) is False

    assert (
        "candy",
        (
            "Cowsay",
            "No answer came back. I will take that as no and keep my hands visible.",
            "com",
        ),
        {},
    ) in calls
    assert not [call for call in calls if call[0] == "end"]


def test_question_runtime_names_idat_heavy_probe_prompt():
    runtime, calls = runtime_from(answers=["yes"])

    assert question_runtime.ask_question(
        runtime,
        "IDAT Heavy Probe:-Deflate stream still broken",
        ("probe", 1),
    ) is True

    assert (
        "candy",
        ("Cowsay", "Question: Should i launch the heavier IDAT probe?", "com"),
        {},
    ) in calls


def test_question_runtime_names_ihdr_crc_bruteforce_prompt():
    runtime, calls = runtime_from(answers=["yes"])

    assert question_runtime.ask_question(
        runtime,
        "IHDR CRC Brute Force:-Wrong Crc b'IHDR'",
        ("probe", 1),
    ) is True

    assert (
        "candy",
        (
            "Cowsay",
            "Question: Should i brute force IHDR against the stored CRC before rebuilding it?",
            "com",
        ),
        {},
    ) in calls


def test_question_runtime_names_chrm_inference_prompt():
    runtime, calls = runtime_from(answers=["yes"], auto=True)

    assert question_runtime.ask_question(
        runtime,
        "cHRM Missing Bytes Inference:-cHRM length is not Valid",
        ("cHRM", 49, 31),
        skipauto=True,
    ) is True

    assert (
        "candy",
        (
            "Cowsay",
            "Question: Should i write the inferred cHRM bytes instead of removing the optional cHRM chunk?",
            "com",
        ),
        {},
    ) in calls
    assert not [call for call in calls if call[0] == "emit" and "Auto Answer Mode" in str(call[1])]


def test_question_runtime_names_unknown_private_removal_prompt_and_skips_auto():
    runtime, calls = runtime_from(answers=["yes"], auto=True)

    assert question_runtime.ask_question(
        runtime,
        "Unknown Private Chunk Removal: msOG",
        ("msOG", 24),
        skipauto=True,
    ) is True

    assert (
        "candy",
        (
            "Cowsay",
            "Question: Should i remove this unknown private chunk from the clone?",
            "com",
        ),
        {},
    ) in calls
    assert not [call for call in calls if call[0] == "emit" and "Auto Answer Mode" in str(call[1])]


def test_question_runtime_names_idat_interruption_prompts_and_skips_auto():
    runtime, calls = runtime_from(answers=["yes"], auto=True)

    assert question_runtime.ask_question(
        runtime,
        "IDAT Interruption Move:-Move ancillary chunk(s) out of the IDAT chain?",
        ("heRB", "move"),
        skipauto=True,
    ) is True

    assert (
        "candy",
        (
            "Cowsay",
            "Question: Should i move this ancillary chunk out of the IDAT chain?",
            "com",
        ),
        {},
    ) in calls
    assert not [call for call in calls if call[0] == "emit" and "Auto Answer Mode" in str(call[1])]


def test_question_runtime_names_hist_optional_removal_prompt():
    runtime, calls = runtime_from(answers=["no"])

    assert question_runtime.ask_question(
        runtime,
        "hIST Optional Metadata Removal:-Remove hIST chunk(s) to silence libpng?",
        ("hIST", 121),
    ) is False

    assert (
        "candy",
        (
            "Cowsay",
            "Question: Should i remove the optional hIST chunk(s), or keep them as-is?",
            "com",
        ),
        {},
    ) in calls


def test_question_runtime_names_super_mega_linefeed_force_prompt():
    runtime, calls = runtime_from(answers=["yes"])

    assert question_runtime.ask_question(
        runtime,
        "SuperMegaLineFeedForceOfDeath",
        ("probe", 1),
    ) is True

    assert (
        "candy",
        (
            "Cowsay",
            "Question: Should i launch SuperMegaLineFeedForceOfDeath, the full IDAT line-feed brute force?",
            "com",
        ),
        {},
    ) in calls


def test_question_runtime_names_ultimate_linefeed_force_prompt_and_skips_auto():
    runtime, calls = runtime_from(answers=["yes"], auto=True)

    assert question_runtime.ask_question(
        runtime,
        "UltimateMegaSuperLineFeedBruteForce",
        ("probe", 1),
        skipauto=True,
    ) is True

    assert (
        "candy",
        (
            "Cowsay",
            "Question: Should I open the forbidden line-feed combinatorics vault?",
            "com",
        ),
        {},
    ) in calls
    assert not [call for call in calls if call[0] == "emit" and "Auto Answer Mode" in str(call[1])]


def test_question_runtime_flips_duplicate_question_answer():
    history = ["Infos:same Answer:True Offset:12 Hash:99"]
    def fail_asker(_prompt):
        raise AssertionError("known route should not ask again")

    runtime, calls = runtime_from(history=history, asker=fail_asker)

    answer = question_runtime.ask_question(runtime, "same", 99)

    assert answer is False
    assert history == [
        "Infos:same Answer:True Offset:12 Hash:99",
        "Infos:same Answer:False Offset:12 Hash:99",
    ]
    assert (
        "candy",
        ("Cowsay", "Huh ..? Déja-vu. I already tried that repair route .", "com"),
        {},
    ) in calls
    assert (
        "candy",
        (
            "Cowsay",
            "So i'm changing the answer before we headbutt the same door twice.",
            "com",
        ),
        {},
    ) in calls


def test_question_runtime_known_yes_no_route_does_not_loop():
    history = [
        "Infos:same Answer:True Offset:12 Hash:99",
        "Infos:same Answer:False Offset:12 Hash:99",
    ]
    def fail_asker(_prompt):
        raise AssertionError("known route should not ask again")

    runtime, calls = runtime_from(
        history=history,
        asker=fail_asker,
        pause_debug=True,
    )

    answer = question_runtime.ask_question(runtime, "same", 99)

    assert answer is False
    assert history == [
        "Infos:same Answer:True Offset:12 Hash:99",
        "Infos:same Answer:False Offset:12 Hash:99",
        "Exhausted:same Offset:12 Hash:99",
    ]
    assert ("pause", ("Question",), {}) in calls
    assert not [call for call in calls if call[0] == "end"]
    assert not [
        call
        for call in calls
        if call[0] == "emit" and "Loop Detected" in str(call[1])
    ]


def test_question_runtime_known_no_route_is_exhausted_without_input():
    history = ["Infos:same Answer:False Offset:12 Hash:99"]
    statuses = []

    def fail_asker(_prompt):
        raise AssertionError("known declined route should not ask again")

    runtime, calls = runtime_from(
        history=history,
        asker=fail_asker,
        status_sink=statuses.append,
    )

    answer = question_runtime.ask_question(runtime, "same", 99)

    assert answer is False
    assert statuses == ["route_exhausted"]
    assert history == [
        "Infos:same Answer:False Offset:12 Hash:99",
        "Exhausted:same Offset:12 Hash:99",
    ]
    assert not [call for call in calls if call[0] == "end"]


def main():
    checks = [
        ("Record auto answer", test_question_runtime_records_auto_answer_without_input),
        ("Report auto mode", test_question_runtime_reports_auto_mode_when_legacy_auto_is_enabled),
        ("Manual feedback", test_question_runtime_manual_answer_uses_legacy_feedback),
        ("EOF answer declines", test_question_runtime_eof_answer_is_decline),
        ("IDAT heavy probe prompt", test_question_runtime_names_idat_heavy_probe_prompt),
        ("IHDR CRC brute force prompt", test_question_runtime_names_ihdr_crc_bruteforce_prompt),
        ("cHRM inference prompt", test_question_runtime_names_chrm_inference_prompt),
        (
            "Unknown private removal prompt",
            test_question_runtime_names_unknown_private_removal_prompt_and_skips_auto,
        ),
        (
            "IDAT interruption move prompt",
            test_question_runtime_names_idat_interruption_prompts_and_skips_auto,
        ),
        ("hIST optional removal prompt", test_question_runtime_names_hist_optional_removal_prompt),
        ("SuperMegaLineFeedForceOfDeath prompt", test_question_runtime_names_super_mega_linefeed_force_prompt),
        (
            "UltimateMegaSuperLineFeedBruteForce prompt",
            test_question_runtime_names_ultimate_linefeed_force_prompt_and_skips_auto,
        ),
        ("Flip duplicate answer", test_question_runtime_flips_duplicate_question_answer),
        ("Known yes/no route does not loop", test_question_runtime_known_yes_no_route_does_not_loop),
        ("Known no route is exhausted", test_question_runtime_known_no_route_is_exhausted_without_input),
    ]

    print("Running question runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"question runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
