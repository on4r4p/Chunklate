from __future__ import annotations

from collections.abc import Callable

from . import decisions


POKEMON_PROMPT = "WHO'S THAT POKEMON !? :"

InputFunc = Callable[[str], str]
InvalidChoiceCallback = Callable[[str], None]


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
