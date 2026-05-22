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


def main():
    checks = [
        ("Select candidate", test_ask_pokemon_choice_returns_selected_candidate),
        ("Retry invalid choice", test_ask_pokemon_choice_retries_invalid_choice_and_reports_it),
        ("Quit action", test_ask_pokemon_choice_preserves_quit_action),
        ("Pause returns input", test_pause_returns_answer_from_injected_input),
        ("Pause handles EOF", test_pause_reports_eof_and_returns_none),
    ]

    print("Running prompt tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"prompt tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
