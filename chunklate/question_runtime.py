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
    clear: bool = False
    prompt_candy: LegacyCall | None = None
    status_sink: LegacyCall | None = None


def _record_status(runtime: QuestionRuntime, status: str) -> None:
    if runtime.status_sink is not None:
        runtime.status_sink(status)


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


def _question_prompt(runtime: QuestionRuntime, skipauto: bool) -> str:
    return decisions.question_prompt(runtime.nodialogue, skipauto)


def _question_context_label(question_id: Any, offset: Any) -> str:
    label = _question_display_name(question_id)
    offset_label = _offset_label(offset)
    return "%s @ %s" % (label, offset_label)


def _question_prompt_text(question_id: Any, skipauto: bool) -> str:
    label = _question_display_name(question_id)
    if skipauto:
        return "Question: Should i stop this brute force branch and save the current candidate?"
    if "Wrong Crc" in label:
        return "Question: Should i try the cheap CRC-only patch here?"
    if "Wrong Chunk name" in label or "Wrong Chunk name" in str(question_id):
        return "Question: Should i try to recover this chunk name?"
    if "No NextChunk" in label:
        return "Question: Should i search nearby for the next chunk?"
    if "Missplaced" in label:
        return "Question: Should i try to move this chunk back where PNG expects it?"
    return "Question: Should i try this repair branch?"


def _question_display_name(question_id: Any) -> str:
    label = str(question_id)
    if ":-" in label:
        label = label.split(":-", 1)[1]
    if len(label) > 54:
        label = label[:51] + "..."
    return label


def _offset_label(offset: Any) -> str:
    try:
        offset_int = int(offset)
    except (TypeError, ValueError):
        return str(offset)
    return "index %s / byte 0x%x" % (offset_int, int(offset_int / 2))


def _history_question_id(entry: Any) -> str | None:
    text = str(entry)
    if not text.startswith("Infos:"):
        return None
    if " Answer:" not in text:
        return None
    return text.split(" Answer:", 1)[0].replace("Infos:", "", 1)


def _history_question_offset(entry: Any) -> str | None:
    text = str(entry)
    if " Offset:" not in text or " Hash:" not in text:
        return None
    return text.split(" Offset:", 1)[1].split(" Hash:", 1)[0]


def _question_occurrence_count(runtime: QuestionRuntime, question_id: Any) -> int:
    if question_id is None:
        return 1

    question_id_text = str(question_id)
    offsets = set()
    for entry in runtime.history:
        if _history_question_id(entry) != question_id_text:
            continue
        offset = _history_question_offset(entry)
        if offset is not None:
            offsets.add(offset)

    offsets.add(str(runtime.offset))
    return len(offsets)


def _emit_repeated_question_context(runtime: QuestionRuntime, question_id: Any) -> None:
    count = _question_occurrence_count(runtime, question_id)
    if count < 2:
        return

    label = _question_display_name(question_id)
    offset = _offset_label(runtime.offset)
    if count == 2:
        runtime.candy(
            "Cowsay",
            "Wait... another %s? Same mess, different spot: %s."
            % (label, offset),
            "com",
        )
        return

    runtime.candy(
        "Cowsay",
        "Ok, that is %s times now: %s. Current crime scene: %s."
        % (count, label, offset),
        "com",
    )


def _emit_deja_vu(runtime: QuestionRuntime, question_id: Any, answer: Any) -> None:
    runtime.candy("Cowsay", "Huh ..? Déja-vu. I already tried that repair route .", "com")
    runtime.candy(
        "Cowsay",
        "So i'm changing the answer before we headbutt the same door twice.",
        "com",
    )
    _emit_history_debug(runtime, question_id, answer)
    if runtime.pause_debug:
        runtime.pause("Question")


def _known_attempted_route(runtime: QuestionRuntime, question_id: Any, question_hash: Any) -> bool | None:
    if question_id is None:
        return None

    tried_yes = decisions.question_entry(
        question_id,
        True,
        runtime.offset,
        question_hash,
    )
    if tried_yes not in runtime.history:
        return None

    tried_no = decisions.question_entry(
        question_id,
        False,
        runtime.offset,
        question_hash,
    )
    if tried_no not in runtime.history:
        runtime.history.append(tried_no)
    _record_status(runtime, "duplicate_flipped")
    _emit_deja_vu(runtime, question_id, False)
    return False


def _emit_prompt_question_context(runtime: QuestionRuntime, question_id: Any, skipauto: bool) -> None:
    if question_id is None:
        return
    candy = runtime.prompt_candy or runtime.candy
    if runtime.clear is True and runtime.nodialogue is True:
        candy(
            "Cowsay",
            "Screen wiped. I brought notes don't worry.",
            "com",
        )
    runtime.emit("Context: (%s)\n" % _question_context_label(question_id, runtime.offset))
    candy("Cowsay", _question_prompt_text(question_id, skipauto), "com")


def _ask_yes_no_with_context(runtime: QuestionRuntime, question_id: Any, skipauto: bool) -> bool:
    prompt = _question_prompt(runtime, skipauto)
    _emit_prompt_question_context(runtime, question_id, skipauto)
    while True:
        response = decisions.normalize_choice(runtime.asker(prompt))
        if response == "yes":
            return True
        if response == "no":
            return False
        candy = runtime.prompt_candy or runtime.candy
        runtime.emit("")
        candy("Cowsay", "I need yes or no. Tiny paperwork, huge consequences.", "com")


def _ask_or_auto_answer(runtime: QuestionRuntime, question_id: Any, skipauto: bool) -> bool:
    answer = decisions.question_auto_answer(runtime.nodialogue, runtime.auto, skipauto)
    if answer is None:
        answer = _ask_yes_no_with_context(runtime, question_id, skipauto)
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
    _emit_repeated_question_context(runtime, question_id)

    known_answer = _known_attempted_route(runtime, question_id, question_hash)
    if known_answer is not None:
        return known_answer

    answer = _ask_or_auto_answer(runtime, question_id, skipauto)
    if question_id is None:
        _record_status(runtime, "untracked")
        return answer

    memory = decisions.remember_question_answer(
        runtime.history,
        question_id,
        answer,
        runtime.offset,
        question_hash,
    )
    _record_status(runtime, memory.status)
    if memory.status == "recorded":
        return memory.answer

    if memory.status == "duplicate_flipped":
        _emit_deja_vu(runtime, question_id, answer)
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
