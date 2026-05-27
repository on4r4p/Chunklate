#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import decisions


def input_from(values):
    answers = iter(values)
    return lambda prompt: next(answers)


def test_ask_yes_no_retries_until_valid_answer():
    answer = decisions.ask_yes_no(input_from(["wat", "YES"]))

    assert answer is True


def test_question_auto_answer_preserves_legacy_modes():
    assert decisions.question_auto_answer(nodialogue=True, auto=True, skipauto=False) is True
    assert decisions.question_auto_answer(nodialogue=False, auto=True, skipauto=False) is True
    assert decisions.question_auto_answer(nodialogue=True, auto=True, skipauto=True) is None
    assert decisions.question_auto_answer(nodialogue=False, auto=False, skipauto=False) is None


def test_question_prompt_uses_stop_bruteforce_prompt_only_for_stfu_skipauto():
    assert decisions.question_prompt(nodialogue=True, skipauto=True).startswith("-Stop bruteforce")
    assert decisions.question_prompt(nodialogue=False, skipauto=True) == "Answer(yes/no):"


def test_question_memory_records_then_flips_duplicate_answer():
    history = []

    first = decisions.remember_question_answer(history, "same", True, 12, 99)
    second = decisions.remember_question_answer(history, "same", True, 12, 99)
    third = decisions.remember_question_answer(history, "same", True, 12, 99)

    assert first.answer is True
    assert first.status == "recorded"
    assert second.answer is False
    assert second.status == "duplicate_flipped"
    assert third.answer is False
    assert third.status == "route_exhausted"
    assert len(history) == 2


def test_parse_pokemon_choice():
    assert decisions.parse_pokemon_choice("1", 3) == decisions.PokemonChoice("select", 1)
    assert decisions.parse_pokemon_choice("wtf", 3) == decisions.PokemonChoice("length")
    assert decisions.parse_pokemon_choice("quit", 3) == decisions.PokemonChoice("quit")
    assert decisions.parse_pokemon_choice("3", 3) == decisions.PokemonChoice("invalid")
    assert decisions.parse_pokemon_choice("nope", 3) == decisions.PokemonChoice("invalid")


def main():
    checks = [
        ("ask yes/no retries until valid answer", test_ask_yes_no_retries_until_valid_answer),
        ("question auto answer preserves legacy modes", test_question_auto_answer_preserves_legacy_modes),
        (
            "question prompt uses stop-bruteforce prompt only for stfu skipauto",
            test_question_prompt_uses_stop_bruteforce_prompt_only_for_stfu_skipauto,
        ),
        ("question memory records then flips duplicate answer", test_question_memory_records_then_flips_duplicate_answer),
        ("pokemon prompt parser classifies choices", test_parse_pokemon_choice),
    ]

    print("Running decision tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"decision tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
