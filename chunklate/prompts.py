from __future__ import annotations

from collections.abc import Callable

from . import decisions


POKEMON_PROMPT = "WHO'S THAT POKEMON !? :"

InputFunc = Callable[[str], str]
InvalidChoiceCallback = Callable[[str], None]
PauseEofCallback = Callable[[EOFError], None]


def ask_pokemon_choice(
    asker: InputFunc,
    candidate_count: int,
    *,
    prompt: str = POKEMON_PROMPT,
    on_invalid: InvalidChoiceCallback | None = None,
) -> decisions.PokemonChoice:
    while True:
        raw_choice = asker(prompt)
        choice = decisions.parse_pokemon_choice(raw_choice, candidate_count)
        if choice.action != "invalid":
            return choice
        if on_invalid is not None:
            on_invalid(str(raw_choice))


def pause(asker: InputFunc, msg: str, *, on_eof: PauseEofCallback | None = None) -> str | None:
    try:
        return asker(msg)
    except EOFError as exc:
        if on_eof is not None:
            on_eof(exc)
        return None
