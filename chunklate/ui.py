from __future__ import annotations

from collections.abc import Callable

COLOR_CODES = {
    "red": "\033[1;31;49m",
    "green": "\033[1;32;49m",
    "blue": "\033[1;34;49m",
    "purple": "\033[1;35;49m",
    "yellow": "\033[1;33;49m",
    "white": "\033[1;37;49m",
}
RESET = "\033[m"
ANSI_SEQUENCES = tuple(code.encode() for code in COLOR_CODES.values()) + (RESET.encode(), b"\x0A")


def colorize(color: str, data: object, *, use_color: bool = True) -> object:
    if not use_color:
        return data
    return "%s%s%s" % (COLOR_CODES[color], data, RESET)


def title_separator_length(arg: object, data: object | None = None) -> int:
    if data is None:
        return len(str(arg))
    if "\x1b[m" not in data:
        return len(str(arg) + str(data)) + 3
    return len(str(arg) + str(data)) - 12


def render_title(arg: object, data: object | None = None, *, use_color: bool = True) -> str:
    bot_l = "╰─"
    bot_r = "─╯"
    top_l = "╭─"
    top_r = "─╮"
    separator = "━" * title_separator_length(arg, data)
    top = top_l + separator + top_r
    bottom = bot_l + separator + bot_r
    body = "  " + str(arg) if data is None else "  " + str(arg) + " " + str(data)

    if not use_color:
        return """
%s
%s
%s
""" % (
            top,
            body,
            bottom,
        )

    return """
\033[1;37;49m%s\033[m
%s
\033[1;37;49m%s\033[m
""" % (
        top,
        body,
        bottom,
    )


def legacy_visible_length(text: object) -> int:
    value = str(text)
    visible_length = 0
    for _character in value:
        visible_length += 1

    encoded = value.encode(errors="ignore")
    for sequence in ANSI_SEQUENCES:
        if sequence in encoded:
            visible_length -= len(sequence) * encoded.count(sequence)
    return visible_length


def render_dialogue(
    arg: object,
    data: object,
    *,
    max_columns: int,
    emoji_provider: Callable[[str], str],
    use_color: bool = True,
) -> str:
    text = str(arg)
    line_length = legacy_visible_length(text)
    separator = "━" * line_length

    if data == "com":
        marker = str(emoji_provider("com"))
    elif data == "good":
        marker = str(emoji_provider("good"))
    else:
        marker = str(emoji_provider("bad"))

    marker_block = " " * len(marker)
    marker_block += "/\n"
    marker_block += marker

    bottom = "╰─" + separator + "─╯"
    printed = " " + text
    if len(printed) >= max_columns:
        full_printed = printed
        printed = " "
        line_length = int(line_length / 2) + 5
        separator = "━" * line_length
        bottom = "╰─" + separator + "─╯"
        for index in range(0, len(full_printed), line_length):
            if len(text[index:]) > line_length:
                printed += "  " + str(text[index : index + line_length]) + "\n"
            else:
                printed += "  " + str(text[index:])

    if not use_color:
        return """
%s
%s
%s
""" % (
            printed,
            bottom,
            marker_block,
        )

    if data == "com":
        color = COLOR_CODES["yellow"]
    elif data == "good":
        color = COLOR_CODES["green"]
    elif data == "bad":
        color = COLOR_CODES["red"]
    else:
        color = ""

    if color:
        return """
%s
%s%s
%s
%s""" % (
            printed,
            color,
            bottom,
            marker_block,
            RESET,
        )

    return """
%s
%s
%s
""" % (
        printed,
        bottom,
        marker_block,
    )
