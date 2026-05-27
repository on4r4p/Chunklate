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
    ]
    assert ("pause", ("Question",), {}) in calls
    assert not [call for call in calls if call[0] == "end"]
    assert not [
        call
        for call in calls
        if call[0] == "emit" and "Loop Detected" in str(call[1])
    ]


def main():
    checks = [
        ("Record auto answer", test_question_runtime_records_auto_answer_without_input),
        ("Report auto mode", test_question_runtime_reports_auto_mode_when_legacy_auto_is_enabled),
        ("Manual feedback", test_question_runtime_manual_answer_uses_legacy_feedback),
        ("Flip duplicate answer", test_question_runtime_flips_duplicate_question_answer),
        ("Known yes/no route does not loop", test_question_runtime_known_yes_no_route_does_not_loop),
    ]

    print("Running question runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"question runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
