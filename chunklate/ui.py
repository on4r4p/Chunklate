from __future__ import annotations

from collections.abc import Callable
import random

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
EMOJIS = {
    "good": (
        "¯\\(◉‿◉)/¯",
        "ᕦ(ò_óˇ)ᕤ",
        "(ง ͡ʘ ͜ʖ ͡ʘ)ง",
        "^• ̮•^",
        "(◍•ᴗ•◍)❤",
        "(ツ)",
        "❣◕ ‿ ◕❣",
        "(⁎⚈᷀᷁ᴗ⚈᷀᷁⁎)",
        "(☞ﾟヮﾟ)☞",
        "【ツ】",
        "☜(⌒▽⌒)☞",
        "(◡‿◡✿)",
        "(☆ω☆)",
        "∠(ᐛ)੭",
        "ଘ(੭ˊᵕˋ)੭* ੈ✩‧₊",
        "[̲̅$̲̅(̲̅ ͡° ͜ʖ ͡°̲̅)̲̅$̲̅]",
        "(ʘ ͜ʖ ʘ)",
        "( ͡ᵔ ͜ʖ ͡ᵔ)",
        "乁( • ω •乁)",
        "(〜￣▽￣)〜",
        "( o˘◡˘o) ┌iii┐",
        "(っ˘ڡ˘ς)",
        "(*°▽°*)",
        "⊂( ´ ▽ ` )⊃",
        "☆⌒(ゝ。∂)",
        "ヽ(✧◡✧)ノ",
        "(ᕦ｡◕‿‿◕)づ",
        "ᕙ(⇀‸↼)ᕗ",
        "ヽ('ノ)ノ",
        "ԅ(≖‿≖ԅ)",
        "(⩾‿⩽)",
        ">^.^<",
        "^^)",
        "(-^^-)",
        "( ˘ ³˘)♥",
        "♥‿♥",
        "(ಥ⌣ಥ)",
        "ʘ‿ʘ",
        "´ ▽ ` )ﾉ",
        "Σ ◕ ◡ ◕",
        "٩(｡͡•‿•｡)۶",
        "ᕕ( ᐛ )ᕗ",
        "☜(⌒▽⌒)☞",
        "(｡◕‿‿◕｡)",
        "(ღ˘⌣˘ღ)",
        "(∪ ◡ ∪)",
        "(▰˘◡˘▰)",
        "(✿ ♥‿♥)",
        "(｡◕ ‿ ◕｡)",
        "( ͡° ͜ʖ ͡°)",
        "(/◔ ◡ ◔)/",
        "(ᵔᴥᵔ)",
        "ʕつ ͡◔ ᴥ ͡◔ʔつ",
        "彡໒(⊙ ᴗ⊙)७彡",
        "(´◡`)",
        "(✯◡✯)",
        "(๑˘︶˘๑)",
        "｡^‿^｡",
        "ヽ(ヅ)ノ",
        "(^人^)",
        "(°◡°♡)",
        "(♥ ω♥ *)",
        "❀ ◕ ‿ ◕ ❀",
        "(⁀ᗢ⁀)",
        "ミ=͟͟͞͞(✿ʘ ᴗʘ)っ",
        "ଘ(੭*ˊᵕˋ)੭* ̀ˋ",
        "─=≡Σ(((つ^̀ω^́)つ ",
        "~( ˘▾˘~)",
        "(=^･ω･^=)",
        " ＼ʕ •ᴥ•ʔ／",
        "ヽ(•‿•)ノ",
        "ヾ(☆▽☆)",
        "(ツ)",
        "◝(^⌣^)◜",
        "ʕ ◉ ᴥ ◉ ʔ",
        "( =① ω① =)",
        ">(^.^)<",
    ),
    "bad": (
        "(⋟~⋞)",
        "(ノಠ ∩ಠ)ノ彡(o°o)",
        "(╯°□°)╯︵ ʞɔnℲ",
        "(ง ͠° ͟ʖ",
        "(#ಠQಠ#)",
        "(⋋▂⋌)",
        "(☞ﾟヮﾟ)☞ ┻━┻",
        "✂╰⋃╯",
        "‿︵‿ヽ(°□° )ノ︵‿︵",
        "、ヽ｀☂ヽ｀、",
        "(oT-T)尸",
        "(－‸ლ)",
        "(╯°益°)╯彡┻━┻",
        "(;´༎ຶٹ༎ຶ`)",
        "( ͡ಠ ʖ̯ ͡ಠ)",
        "(ఠ益ఠ)୨",
        "(∩` ﾛ ´)",
        "Q(`⌒´Q)",
        "٩(`皿´҂)ง",
        "(っ≧ω≦)っ",
        "─=≡Σ((( つ＞□＜)つ",
        "(凸✧∀✧)つ",
        "(￣_￣)・・・",
        "(ﾉಥ益ಥ)ﾉ",
        "↑_(ΦwΦ)Ψ",
        "୧((#Φ益Φ#))୨",
        "٩(╬ʘ益ʘ╬)۶",
        "[¬º-°]¬",
        "(°︹°)╭∩╮",
        "▀皿▀￣",
        "(っ˘ڡ˘ς)",
        "ლ(๏□ ๏ლ)",
        "(♨_♨)",
        "( ͡ಠ ʖ̯ ͡ಠ )",
        "(⩾ヘ⩽)",
        "(҂◡_◡)",
        "(~~,)",
        "(ಥ_ಥ)",
        "(ಥ﹏ಥ)",
        "(►_◄)",
        "(◉ ︵◉)",
        "ヽ(ｏ`皿′ｏ)ﾉ",
        "凸ಠ益ಠ)凸",
        "╯‵Д′)╯彡┻━┻",
        "¯\\_(⊙︿⊙)_/¯",
        "ಠ︵ಠ 凸",
        "ヽ(`Д´)ﾉ",
        "(╯°□°）╯︵ ┻━┻",
        "(✖╭╮✖)",
        "(︶︹︺)",
        "(╯︵╰,)",
        "ヽ(˚௰˚)づ",
        "(⊙ ▂⊙ ✖ )",
        "ᕕ༼ ͠ຈ Ĺ̯ ͠ຈ ༽┌∩┐",
        "凸(>皿<)凸",
        "ʕ థ ౪ థ ʔ",
        "༼ ༎ຶ ᆺ ༎ຶ༽",
        "( ◥◣ _◢◤ )",
        "(━┳━ _ ━┳━)",
        "┐(￣ヘ￣)┌",
        "༼☯﹏☯༽",
        "(° -°） ︵ ┻━┻ ",
        "┻━┻︵ \\(°□°)/ ︵ ┻━┻ ",
        "◕ ︵◕ ",
        "( ◡ ︵◡ )",
        "(；⌣̀_⌣́)",
        "( ´〒^〒`)",
        "(；￣Д￣)",
        "ʕ TᴥT ʔ ",
        "ヽ(๏ ∀ ๏ )ﾉ",
        "┗(･ω･;)┛",
        "(*￣o￣)",
        "ヽ(O_O )ﾉ",
        "ƪ( ` ▿▿▿▿ ´ ƪ) ",
        "(>ΦωΦ<)",
        "(x_x)⌒☆",
        "ヾ(⌣́︹⌣́ )ゞ ",
    ),
    "com": (
        "(◉_●`)",
        "(ب_ب)",
        "ಠ_ರೃ",
        "(^..^)ﾉ",
        "(´･o･｀*)",
        "(^◕~◕^)",
        "(⌐■_■)",
        "(ʘ ʖ̯ ʘ)",
        "(ʘ ͟ʖ ʘ)",
        "(.•́ _ʖ •̀.)",
        "( ͠° ͟ʖ ͡°)",
        "( ͡° ʖ̯ ͡°)",
        "＼(￣(oo)￣)／",
        "(∪｡∪)",
        "ε=ε=ε=ε=┌(;￣o￣)┘",
        "┬┴┬┴┤･ω･)ﾉ",
        "ﾍ(･_|",
        "|ω･)ﾉ",
        "(•́ _ʖ •̀)",
        "(￢ ￢)",
        "╮(￣ω￣;)╭",
        "(~ω~)",
        "(っ•́｡•́)",
        "(▀.▀￣)",
        "｡•́_•̀｡",
        "(ㆆ㉨ㆆ)",
        "¿Ⓧ_Ⓧﮌ",
        "ᕦ(ò_óˇ)ᕤ",
        "(Ծ‸ Ծ)",
        "(눈_눈)",
        "( ఠ ͟ʖ ఠ )",
        "(⥀.⥀)",
        "(~.~)",
        "(◔_◔)",
        "(๑•́ ₃ •̀๑)",
        "(ఠ_ఠ)",
        "(◎_◎)",
        "(⊙﹏⊙)",
        "(´･_･`)",
        "(ಠ_ಠ)",
        "（　ﾟДﾟ）",
        "~' ▽ '~ )ﾉ",
        "⁀⊙ ෴ ☉⁀",
        "(๏ᆺ   ๏ υ)",
        "─=≡Σ((( つ•̀ω•́)つ ",
        "⌗(́◉◞౪◟◉‵⌗)",
        "(∩｀-´)⊃━☆ﾟ.*･｡ﾟ ",
        "(〓￣(∵エ∵)￣〓)",
        "┬┴┬┴┤ᵒᵏ (･_├┬┴┬┴ ",
        "((유∀유|||))",
        "ε=ε=(っ* ´□` )っ",
        "（・⊝・∞）",
        "( ● ´⌓ `● )",
        "(╯•﹏•╰)",
        "˛˛ƪ(⌾⃝ ౪ ⌾⃝ ๑)و ̉ ̉ ",
        "( ؕؔʘ̥̥̥̥ ه ؔؕʘ̥̥̥̥ )? ",
        "(´⊙ ω ⊙`)！",
        "ლ(́◉◞౪◟◉‵ლ)",
        "(*′☉.̫☉)",
        "=͟͟͞͞ =͟͟͞͞ ﾍ ( ´ Д `)ﾉ ",
        "  (⁄ ⁄•⁄ω⁄•⁄ ⁄)",
        "(〃＞＿＜;〃)",
        "<(￣ ﹌ ￣)>",
        "(￣ ￣|||)",
        "(￢_￢;)",
        "＼(〇_ｏ)／",
        "(／。＼)",
        "〜(＞＜)〜",
        "(/ω＼)",
        "┐(￣～￣)┌",
        "┐(︶▽︶)┌",
        "ヽ(ˇヘˇ)ノ",
    ),
}


def colorize(color: str, data: object, *, use_color: bool = True) -> object:
    if not use_color:
        return data
    return "%s%s%s" % (COLOR_CODES[color], data, RESET)


def pick_emoji(kind: str, randint: Callable[[int, int], int] | None = None) -> str | None:
    candidates = EMOJIS.get(kind)
    if candidates is None:
        return None
    if randint is None:
        randint = random.randint
    return candidates[randint(0, len(candidates) - 1)]


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


def printable_message(msg: object, *, max_columns: int, no_dialogue: bool = False) -> object | None:
    if no_dialogue:
        return None
    if len(str(msg)) > max_columns * 2:
        return "%s ...Too Big To be displayed..." % str(msg[: int(max_columns) - 30])  # type: ignore[index]
    return msg
