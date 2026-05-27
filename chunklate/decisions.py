from __future__ import annotations

from collections.abc import Callable, MutableSequence, Sequence
from dataclasses import dataclass
from typing import Literal


InputFunc = Callable[[str], str]
QuestionStatus = Literal["untracked", "recorded", "duplicate_flipped", "route_exhausted"]
PokemonAction = Literal["select", "length", "quit", "invalid"]


@dataclass(frozen=True)
class RememberedQuestion:
    answer: bool
    status: QuestionStatus
    entry: str | None = None


@dataclass(frozen=True)
class PokemonChoice:
    action: PokemonAction
    index: int | None = None


def normalize_choice(choice: object) -> str:
    return str(choice).strip().lower()


def ask_choice(
    input_func: InputFunc,
    prompt: str,
    choices: Sequence[str],
    retry_prompt: str | None = None,
) -> str:
    normalized_choices = tuple(normalize_choice(choice) for choice in choices)
    response = normalize_choice(input_func(prompt))
    while response not in normalized_choices:
        response = normalize_choice(input_func(retry_prompt or prompt))
    return response


def ask_yes_no(
    input_func: InputFunc,
    prompt: str = "Answer(yes/no):",
    retry_prompt: str = "Answer(yes/no):",
) -> bool:
    return ask_choice(input_func, prompt, ("yes", "no"), retry_prompt) == "yes"


def question_auto_answer(nodialogue: bool, auto: bool, skipauto: bool) -> bool | None:
    if nodialogue and not skipauto:
        return True
    if not nodialogue and auto and not skipauto:
        return True
    return None


def question_prompt(nodialogue: bool, skipauto: bool) -> str:
    if nodialogue and skipauto:
        return "-Stop bruteforce and save this png?(yes/no):"
    return "Answer(yes/no):"


def question_entry(question_id: object, answer: bool, offset: object, question_hash: object) -> str:
    return (
        "Infos:"
        + str(question_id)
        + " Answer:"
        + str(answer)
        + " Offset:"
        + str(offset)
        + " Hash:"
        + str(question_hash)
    )


def remember_question_answer(
    history: MutableSequence[str],
    question_id: object,
    answer: bool,
    offset: object,
    question_hash: object,
) -> RememberedQuestion:
    if question_id is None:
        return RememberedQuestion(answer, "untracked")

    entry = question_entry(question_id, answer, offset, question_hash)
    if entry not in history:
        history.append(entry)
        return RememberedQuestion(answer, "recorded", entry)

    flipped_answer = not answer
    flipped_entry = question_entry(question_id, flipped_answer, offset, question_hash)
    if flipped_entry not in history:
        history.append(flipped_entry)
        return RememberedQuestion(flipped_answer, "duplicate_flipped", flipped_entry)

    return RememberedQuestion(flipped_answer, "route_exhausted", flipped_entry)


def parse_pokemon_choice(choice: object, candidate_count: int) -> PokemonChoice:
    response = normalize_choice(choice)
    if response == "quit":
        return PokemonChoice("quit")
    if response == "wtf":
        return PokemonChoice("length")

    try:
        index = int(response)
    except ValueError:
        return PokemonChoice("invalid")

    if index in range(0, candidate_count):
        return PokemonChoice("select", index)
    return PokemonChoice("invalid")
