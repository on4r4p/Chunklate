from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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


@dataclass(frozen=True)
class MinibarStep:
    loading_text: str
    char_pos: int
    go_back: bool
    should_print: bool


@dataclass(frozen=True)
class LoadingbarFrames:
    frames: list[str]
    len_fish_list: int
    fish_pos: int


@dataclass(frozen=True)
class LoadingbarProgress:
    text: str
    fish_pos: int


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


def emit_printable_message(
    emit,
    msg: object,
    *,
    max_columns: int,
    no_dialogue: bool = False,
) -> object | None:
    printable = printable_message(msg, max_columns=max_columns, no_dialogue=no_dialogue)
    if printable is not None:
        emit(printable)
    return printable


def render_chunklate_banner(os_name: str, random_int) -> tuple[str, ...]:
    if os_name == "nt":
        return (
            """
╭─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╮
  <[0x00000016]>[C|H|U|N|K|L|A|T|E]<[0x98bd5cb8]>
╰─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╯
""",
        )

    color = [
        "\033[1;31;49m",
        "\033[1;32;49m",
        "\033[1;34;49m",
        "\033[1;35;49m",
        "\033[1;33;49m",
        "\033[1;37;49m",
    ]

    length = "<[0x00000016]>"
    crc = "<[0x98bd5cb8]>"

    title = "\033[1;37;49m[\033[mC\033[1;37;49m|\033[mH\033[1;37;49m|\033[mU\033[1;37;49m|\033[mN\033[1;37;49m|\033[mK\033[1;37;49m|\033[mL\033[1;37;49m|\033[mA\033[1;37;49m|\033[mT\033[1;37;49m|\033[mE\033[1;37;49m]\033[m"

    top = "\n╭─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╮"
    bot = "╰─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╯\n"

    colored_len = ""
    colored_crc = ""
    toped = ""
    boted = ""

    for i, j in zip([i for i in length], [i for i in crc]):
        rnd = random_int(0, len(color) - 1)
        colored_len += str(color[rnd]) + str(i) + str("\033[m")

        random_int(0, len(color) - 1)
        colored_crc += str(color[rnd]) + str(j) + str("\033[m")

    for i, j in zip([i for i in top], [i for i in bot]):
        rnd2 = random_int(0, len(color) - 1)
        rnd3 = random_int(0, len(color) - 1)

        toped += str(color[rnd2]) + str(i) + str("\033[m")
        boted += str(color[rnd3]) + str(j) + str("\033[m")

    return (
        toped,
        "  " + colored_len + title + colored_crc,
        boted,
    )


def minibar_step(
    indication: str,
    loading_text: str,
    char_pos: int,
    go_back: bool,
    max_columns: int,
) -> MinibarStep:
    point = "."
    space = " "

    text_length = len(loading_text)
    if text_length < max_columns - len(indication) + 1 and go_back is False:
        return MinibarStep(
            loading_text=str(indication) + (point * char_pos) + space,
            char_pos=char_pos + 1,
            go_back=go_back,
            should_print=True,
        )

    if text_length > len(indication) + 2:
        return MinibarStep(
            loading_text=str(indication) + (point * char_pos) + space,
            char_pos=char_pos - 1,
            go_back=True,
            should_print=True,
        )

    return MinibarStep(
        loading_text=loading_text,
        char_pos=char_pos,
        go_back=False,
        should_print=False,
    )


def build_loadingbar_frames(fishs: int, fishsize: int, terminal_width: int) -> LoadingbarFrames:
    frames = []
    fishbowl = "[" + "0".zfill(fishsize) + "/" + str(fishs) + "]"
    loading_text = ""
    char_pos = 0
    pos_line = 0
    tail = 0
    maxchar = (int(terminal_width) - 1) - len(fishbowl)
    line = "¸.·´¯`·.¸"
    linelst = []
    fish_right = ["><(((º>", "⸌<(((º>", "><(((º>", "⸝<(((º>"]
    trail = 3 * len(line)
    trail_end = 0

    for _ in range(0, maxchar + 7):
        if pos_line <= len(line) - 1:
            linelst.append(line[pos_line])
        else:
            pos_line = 0
            linelst.append(line[pos_line])
        pos_line += 1

    for _ in range(maxchar + trail + 2):
        text_length = len(loading_text)
        if text_length < maxchar - 7:
            if char_pos >= trail:
                loading_text = (" " * trail_end) + loading_text[trail_end:]
                loading_text += linelst[char_pos]
                trail_end += 1
            else:
                loading_text += linelst[char_pos]

            if tail > 3:
                tail = 0
            frames.append(loading_text + fish_right[tail])
            char_pos += 1
            tail += 1
        else:
            fishapear = (maxchar - 7) - char_pos
            loading_text = (" " * trail_end) + loading_text[trail_end:]
            if fishapear >= -7:
                loading_text += linelst[char_pos]
            trail_end += 1

            if tail > 3:
                tail = 0
            frames.append(loading_text + fish_right[tail][:fishapear])
            char_pos += 1
            tail += 1
            if trail_end >= maxchar + 2:
                loading_text = ""
                pos_line = 0
                trail = 3 * len(line)
                tail = 0
                trail_end = 0
                char_pos = 0

    return LoadingbarFrames(
        frames=frames,
        len_fish_list=len(frames) - 1,
        fish_pos=0,
    )


def loadingbar_progress(
    fishs: int,
    fishsize: int,
    loop: int,
    frames: list[str],
    fish_pos: int,
    len_fish_list: int,
) -> LoadingbarProgress:
    if loop % 100 == 0:
        if fish_pos != len_fish_list:
            fish_pos += 1
        else:
            fish_pos = 0

    return LoadingbarProgress(
        text="%s/%s%s" % (str(loop).zfill(fishsize), fishs, frames[fish_pos]),
        fish_pos=fish_pos,
    )


def run_loadingbar_from_namespace(
    namespace: dict,
    fishs: int,
    fishsize: int,
    loop: int,
    build: bool,
) -> None:
    if build:
        built = build_loadingbar_frames(
            fishs,
            fishsize,
            int(namespace["os"].get_terminal_size(0)[0]),
        )
        namespace["ThksForTheFish"] = built.frames
        namespace["LenFishList"] = built.len_fish_list
        namespace["FishPos"] = built.fish_pos
        return

    progress = loadingbar_progress(
        fishs,
        fishsize,
        loop,
        namespace["ThksForTheFish"],
        namespace["FishPos"],
        namespace["LenFishList"],
    )
    namespace["FishPos"] = progress.fish_pos
    namespace["print"](progress.text, end="\r")
