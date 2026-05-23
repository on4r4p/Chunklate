#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import decisions, prompts


def input_from(values):
    answers = iter(values)
    return lambda prompt: next(answers)


def test_ask_pokemon_choice_returns_selected_candidate():
    choice = prompts.ask_pokemon_choice(input_from(["1"]), 3)

    assert choice == decisions.PokemonChoice("select", 1)


def test_ask_pokemon_choice_retries_invalid_choice_and_reports_it():
    invalid = []

    choice = prompts.ask_pokemon_choice(
        input_from(["nope", "wtf"]),
        3,
        on_invalid=invalid.append,
    )

    assert choice == decisions.PokemonChoice("length")
    assert invalid == ["nope"]


def test_ask_pokemon_choice_preserves_quit_action():
    choice = prompts.ask_pokemon_choice(input_from(["quit"]), 3)

    assert choice == decisions.PokemonChoice("quit")


def test_pause_returns_answer_from_injected_input():
    assert prompts.pause(input_from([""]), "Pause:") == ""
    assert prompts.pause(input_from(["ok"]), "Pause:") == "ok"


def test_pause_reports_eof_and_returns_none():
    errors = []

    def asker(prompt):
        raise EOFError("closed")

    assert prompts.pause(asker, "Pause:", on_eof=errors.append) is None
    assert len(errors) == 1
    assert str(errors[0]) == "closed"


def test_pause_with_legacy_eof_report_uses_injected_callbacks():
    emitted = []
    redirected = []

    class FakeRedirector:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            redirected.append(("enter", self.stream))

        def __exit__(self, exc_type, exc, tb):
            redirected.append(("exit", self.stream))

    def asker(prompt):
        raise EOFError("closed")

    stream = object()
    result = prompts.pause_with_legacy_eof_report(
        asker,
        "Pause:",
        error_emit=lambda *args: emitted.append(args),
        stderr_redirector=FakeRedirector,
        stream_factory=lambda: stream,
    )

    assert result is None
    assert len(emitted) == 1
    assert emitted[0][0] == "Error:"
    assert str(emitted[0][1]) == "closed"
    assert redirected == [("enter", stream), ("exit", stream)]


def test_pause_dialogue_skips_input_when_disabled():
    calls = []

    assert prompts.pause_dialogue(lambda prompt: calls.append(prompt), False) is None
    assert calls == []


def test_pause_dialogue_uses_legacy_prompt_when_enabled():
    prompts_seen = []

    def asker(prompt):
        prompts_seen.append(prompt)
        return "ok"

    assert prompts.pause_dialogue(asker, True) == "ok"
    assert prompts_seen == [prompts.DIALOGUE_PAUSE_PROMPT]


def test_pause_dialogue_preserves_input_errors():
    def asker(prompt):
        raise EOFError("closed")

    try:
        prompts.pause_dialogue(asker, True)
    except EOFError as exc:
        assert str(exc) == "closed"
    else:
        raise AssertionError("pause_dialogue should preserve EOFError")


def main():
    checks = [
        ("Select candidate", test_ask_pokemon_choice_returns_selected_candidate),
        ("Retry invalid choice", test_ask_pokemon_choice_retries_invalid_choice_and_reports_it),
        ("Quit action", test_ask_pokemon_choice_preserves_quit_action),
        ("Pause returns input", test_pause_returns_answer_from_injected_input),
        ("Pause handles EOF", test_pause_reports_eof_and_returns_none),
        ("Pause legacy EOF report", test_pause_with_legacy_eof_report_uses_injected_callbacks),
        ("Dialogue pause disabled", test_pause_dialogue_skips_input_when_disabled),
        ("Dialogue pause enabled", test_pause_dialogue_uses_legacy_prompt_when_enabled),
        ("Dialogue pause preserves input errors", test_pause_dialogue_preserves_input_errors),
    ]

    print("Running prompt tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"prompt tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
