from __future__ import annotations

COLOR_CODES = {
    "red": "\033[1;31;49m",
    "green": "\033[1;32;49m",
    "blue": "\033[1;34;49m",
    "purple": "\033[1;35;49m",
    "yellow": "\033[1;33;49m",
    "white": "\033[1;37;49m",
}
RESET = "\033[m"


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
