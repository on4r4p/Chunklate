from __future__ import annotations

from collections.abc import Callable
from typing import Any


Emit = Callable[[str], Any]
LegacyCall = Callable[..., Any]


def short_value(tools_value: Any) -> Any:
    if type(tools_value) == bytes:
        return tools_value[0:40] + b"...To big to be displayed ..."
    if type(tools_value) == str:
        return tools_value[0:40] + "...To big to be displayed ..."
    return tools_value


def emit_debug_state(
    *,
    debug: bool,
    pandemonium: Any,
    pandora_box: Any,
    chunks_history: Any,
    chunks_history_index: Any,
    pause_debug: bool,
    emit: Emit,
    pause: LegacyCall,
) -> None:
    if debug is not True:
        return

    emit("len pandemonium :%s" % len(pandemonium))
    for nb, key in enumerate(pandora_box):
        emit("Pandorbox Key:%s" % str(key))
        for toolkey, keyvalue in pandora_box[key].items():
            emit("PandoraBox toolkey:%s" % toolkey)
            emit("PandoraBox keyvalue:%s" % keyvalue)

    for chunk, index in zip(chunks_history, chunks_history_index):
        emit("\nCame accross that chunk: %s" % chunk)
        emit("With those index: %s" % index)
    if pause_debug is True:
        pause("-Debug Pause Press Return to continue:")


def emit_tool(nb3: int, tools: Any, tools_values: Any, *, emit: Emit, candy: LegacyCall) -> None:
    if type(tools_values) == str or type(tools_values) == bytes:
        if len(tools_values) > 100:
            tools_values = short_value(tools_values)

    emit(
        "%s:%s:%s"
        % (
            candy("Color", "yellow", "        [Tool used :%s]" % nb3),
            tools,
            tools_values,
        )
    )


def emit_pandemonium_summary(summary: Any, *, emit: Emit, candy: LegacyCall) -> None:
    candy("Cowsay", "This is a short summary of what we have done :", "good")

    for nb1, sample_summary in enumerate(summary):
        emit(
            "%s:-Errors fixed in File %s :"
            % (candy("Color", "white", "[File:%s]" % nb1), sample_summary.sample)
        )

        for nb2, error_summary in enumerate(sample_summary.errors):
            emit("%s:%s" % (candy("Color", "red", "    [-%s]" % nb2), error_summary.error))
            for nb3, (tools, tools_values) in enumerate(error_summary.tools):
                emit_tool(nb3, tools, tools_values, emit=emit, candy=candy)


def emit_critical_hit(value: Any, *, emit: Emit) -> None:
    emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % value)


def emit_todo(*, emit: Emit, candy: LegacyCall) -> None:
    emit(candy("Color", "yellow", "\n-ToDo"))


def say_current_wrong_crc_idat(*, candy: LegacyCall) -> None:
    candy("Cowsay", "Crc checksum is not valid !!!", "bad")
    candy(
        "Cowsay",
        "Well this one have to be fixed first let's see if replacing that Crc is enough..",
        "com",
    )


def say_wrong_crc_data_brawl(chunk_name: Any, *, candy: LegacyCall) -> None:
    candy(
        "Cowsay",
        "Perhaps that wasn't a Crc problem after all..",
        "com",
    )
    candy(
        "Cowsay",
        "Maybe the culprit was in fact the %s Data itself!" % chunk_name,
        "bad",
    )
    candy(
        "Cowsay",
        "How about taking a coffee break while im taking care of something?",
        "good",
    )


def say_plte_intro(*, candy: LegacyCall) -> None:
    candy("Cowsay", "Alright this is a tough one as PLTE is a critical chunk..", "bad")


def say_plte_valid_crc(*, candy: LegacyCall) -> None:
    candy("Cowsay", "Crc is valid ...So this has been made on purpose..", "bad")
    candy("Cowsay", "Anyway im just gona fill the gap then.", "com")
    candy("Cowsay", "Since i have no information about what to put in there ...", "bad")
    candy("Cowsay", "I will need you to manually click a few buttons for me.", "com")
    candy(
        "Cowsay",
        "Or perhaps i could just remove that PLTE chunk but trust me this is useless as it wont work..",
        "com",
    )


def say_plte_bad_crc(*, candy: LegacyCall) -> None:
    candy("Cowsay", "Since i have no information about what to put in there ...", "bad")
    candy("Cowsay", "I ll have to bruteforce my way through until i end up with the old Crc.", "bad")
    candy("Cowsay", "Or maybe you do want to try to play with the PLTE manually ?", "com")
    candy("Cowsay", "In many ways , its is the best solution in my opinion .", "com")
    candy(
        "Cowsay",
        "To give you an hint:Take the nbr of atoms in the univers multiply it by itself a couple of times.",
        "good",
    )
    candy("Cowsay", "And even there we would not be near to get every combination for a PLTE Chunk.", "bad")
    candy("Cowsay", "Perhaps i could just remove that PLTE chunk but no it just wont work ..", "com")


def say_plte_fallback(*, candy: LegacyCall) -> None:
    candy(
        "Cowsay",
        "Shall i give it a try ? Otherwise Chunklate is going to exit.",
        "com",
    )


def say_single_pandemonium_intro(*, candy: LegacyCall) -> None:
    candy("Cowsay", "Only one Error,That is short indeed ..", "com")


def say_single_pandemonium_unsupported(*, candy: LegacyCall) -> None:
    candy("Cowsay", "Erf this case is not implemented yet ...", "bad")


def say_dummy_chunk_critical_prompt(chunk_name: Any, *, candy: LegacyCall) -> None:
    candy(
        "Cowsay",
        "Ok it's time to brute force that dummy %s chunk .." % (chunk_name),
        "good",
    )
    candy(
        "Cowsay",
        "I mean we have to since it is a critical chunk..",
        "com",
    )
    candy(
        "Cowsay",
        "I hope you brought a book...A big one ..Cause it may takes forever.",
        "bad",
    )
    candy(
        "Cowsay",
        "Shall i begin ? Otherwise Chunklate is going to close.",
        "bad",
    )


def say_dummy_chunk_ancillary_prompt(chunk_name: Any, *, candy: LegacyCall) -> None:
    candy(
        "Cowsay",
        "We better remove that %s chunk than trying to bruteforce it" % (chunk_name),
        "com",
    )
    candy(
        "Cowsay",
        "I mean it would be less time consuming since it is not a critical chunk",
        "com",
    )
    candy(
        "Cowsay",
        "Do you still want to bruteforce this chunk ?",
        "com",
    )


def say_no_pandemonium_intro(*, emit: Emit, candy: LegacyCall) -> None:
    emit(
        "-%s has been Fixed yet. %s"
        % (candy("Color", "red", "No Error"), candy("Emoj", "bad"))
    )
    candy(
        "Cowsay",
        "Erf...Kay let me check if iv forgot any error somewhere ..",
        "com",
    )


def emit_prompt_context_hits(prompt_context: Any, *, emit: Emit) -> None:
    for key in prompt_context.print_hits:
        emit_critical_hit(key, emit=emit)


def say_no_pandemonium_getinfo(*, skip_bad_crc: bool, candy: LegacyCall) -> None:
    candy(
        "Cowsay",
        "Hm yeah that could be problematic indeed..",
        "com",
    )

    if not skip_bad_crc:
        candy(
            "Cowsay",
            "And of course Crc is valid ...This must be a joke..",
            "bad",
        )
    candy(
        "Cowsay",
        "We can't just let this thing like that The allmighty libpng will yell at us again!",
        "com",
    )
    candy(
        "Cowsay",
        "So what do you say ? Shall we try to fix it ?",
        "com",
    )
    candy(
        "Cowsay",
        "(Beware this could take some time !!)",
        "bad",
    )


def say_no_pandemonium_forcer(*, candy: LegacyCall) -> None:
    candy(
        "Cowsay",
        "This is bad ..i don't have enough info to handle this error quickly..",
        "com",
    )

    candy(
        "Cowsay",
        "(I need to bruteforce every chunks until libpng is happy ...)",
        "com",
    )
    candy(
        "Cowsay",
        "(And this will definitively take some ..time ...like years maybe..Are you ok ?)",
        "bad",
    )


def say_no_pandemonium_failure(*, candy: LegacyCall) -> None:
    candy(
        "Cowsay",
        "Couldn't find anything in all those lines of codes which could handle this..",
        "bad",
    )
    candy("Cowsay", "We r out of luck for now sorry..", "bad")
