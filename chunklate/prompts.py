from __future__ import annotations

from collections.abc import Callable

from . import decisions


POKEMON_PROMPT = "WHO'S THAT POKEMON !? :"
DIALOGUE_PAUSE_PROMPT = "-Pause Dialogue-"

InputFunc = Callable[[str], str]
InvalidChoiceCallback = Callable[[str], None]
PauseEofCallback = Callable[[EOFError], None]
ErrorEmitCallback = Callable[..., None]


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


def pause_with_legacy_eof_report(
    asker: InputFunc,
    msg: str,
    *,
    error_emit: ErrorEmitCallback,
    stderr_redirector,
    stream_factory,
) -> str | None:
    def on_eof(exc: EOFError) -> None:
        error_emit("Error:", exc)
        stream = stream_factory()
        with stderr_redirector(stream):
            pass

    return pause(asker, msg, on_eof=on_eof)


def pause_dialogue(
    asker: InputFunc,
    enabled: bool,
    *,
    prompt: str = DIALOGUE_PAUSE_PROMPT,
) -> str | None:
    if not enabled:
        return None
    return asker(prompt)
