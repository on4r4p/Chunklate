from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
from typing import Any

from . import decisions


LegacyCall = Callable[..., Any]
InputFunc = Callable[[str], str]


@dataclass(frozen=True)
class QuestionRuntime:
    history: MutableSequence[str]
    nodialogue: bool
    auto: bool
    debug: bool
    pause_debug: bool
    offset: Any
    asker: InputFunc
    candy: LegacyCall
    emit: LegacyCall
    pause: LegacyCall
    end: LegacyCall


def _debug_intro(runtime: QuestionRuntime, question_id: Any) -> None:
    if not runtime.debug:
        return

    runtime.emit("IFOP:\n%s" % runtime.history)
    runtime.emit("\nId:%s" % question_id)
    if runtime.pause_debug:
        runtime.pause("Pause Debug")


def _emit_history_debug(
    runtime: QuestionRuntime,
    question_id: Any,
    answer: Any,
) -> None:
    if not runtime.debug:
        return

    runtime.emit("IFOP:\n")
    for entry in runtime.history:
        runtime.emit(entry)
    runtime.emit("\nId:%s" % question_id)
    runtime.emit("\nAnswer:%s" % answer)


def _ask_or_auto_answer(runtime: QuestionRuntime, skipauto: bool) -> bool:
    answer = decisions.question_auto_answer(runtime.nodialogue, runtime.auto, skipauto)
    if answer is None:
        answer = decisions.ask_yes_no(
            runtime.asker,
            decisions.question_prompt(runtime.nodialogue, skipauto),
        )
        if not (runtime.nodialogue and skipauto):
            if answer is True:
                runtime.candy("Cowsay", "Fine , let me see what i can do .", "good")
            else:
                runtime.candy("Cowsay", "Ok ,just do not make eye contact !", "com")
    elif runtime.nodialogue is False and runtime.auto is True and skipauto is False:
        runtime.emit("-%s\n" % runtime.candy("Color", "green", "Auto Answer Mode"))

    return answer


def ask_question(
    runtime: QuestionRuntime,
    question_id: Any = None,
    question_hash: Any = None,
    *,
    skipauto: bool = False,
) -> bool:
    runtime.candy("Title", "QUESTION!")
    _debug_intro(runtime, question_id)

    answer = _ask_or_auto_answer(runtime, skipauto)
    if question_id is None:
        return answer

    memory = decisions.remember_question_answer(
        runtime.history,
        question_id,
        answer,
        runtime.offset,
        question_hash,
    )
    if memory.status == "recorded":
        return memory.answer

    if memory.status == "duplicate_flipped":
        runtime.emit("-%s\n" % runtime.candy("Color", "red", "Error Already fixed"))
        runtime.emit("-%s\n" % runtime.candy("Color", "red", "Answer Changed"))
        runtime.candy("Cowsay", "Huh ..? Déja-vu ?", "com")
        _emit_history_debug(runtime, question_id, answer)
        if runtime.pause_debug:
            runtime.pause("Question")
        return memory.answer

    if memory.status == "loop_detected":
        runtime.emit(
            "-%s\n"
            % runtime.candy(
                "Color",
                "red",
                "Loop Detected please contact github.com/on4r4p/Chunklate",
            )
        )
        _emit_history_debug(runtime, question_id, memory.answer)
        if runtime.pause_debug:
            runtime.pause("Pause Question")
            runtime.end()
        return memory.answer

    return answer
