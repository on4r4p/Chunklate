#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import ui


def test_colorize_preserves_legacy_ansi_colors():
    assert ui.colorize("red", "ERR") == "\033[1;31;49mERR\033[m"
    assert ui.colorize("green", 42) == "\033[1;32;49m42\033[m"
    assert ui.colorize("blue", "B") == "\033[1;34;49mB\033[m"
    assert ui.colorize("purple", "P") == "\033[1;35;49mP\033[m"
    assert ui.colorize("yellow", "Y") == "\033[1;33;49mY\033[m"
    assert ui.colorize("white", "W") == "\033[1;37;49mW\033[m"


def test_colorize_returns_data_on_windows_mode():
    marker = object()

    assert ui.colorize("red", "ERR", use_color=False) == "ERR"
    assert ui.colorize("green", marker, use_color=False) is marker


def test_pick_emoji_uses_legacy_groups_deterministically():
    assert ui.pick_emoji("good", lambda start, end: start) == ui.EMOJIS["good"][0]
    assert ui.pick_emoji("bad", lambda start, end: end) == ui.EMOJIS["bad"][-1]
    assert ui.pick_emoji("com", lambda start, end: 1) == ui.EMOJIS["com"][1]
    assert ui.pick_emoji("unknown", lambda start, end: 0) is None


def test_title_separator_length_matches_legacy_color_adjustment():
    colored = "\033[1;37;49mDATA\033[m"

    assert ui.title_separator_length("Title") == 5
    assert ui.title_separator_length("Title", "Data") == 12
    assert ui.title_separator_length("Title", colored) == 10


def test_render_title_preserves_legacy_non_windows_layout():
    assert ui.render_title("A", use_color=True) == """
\033[1;37;49m╭─━─╮\033[m
  A
\033[1;37;49m╰─━─╯\033[m
"""


def test_render_title_preserves_legacy_windows_layout():
    assert ui.render_title("A", "B", use_color=False) == """
╭─━━━━━─╮
  A B
╰─━━━━━─╯
"""


def test_legacy_visible_length_ignores_ansi_and_linefeed_bytes():
    red = "\033[1;31;49mERR\033[m"

    assert ui.legacy_visible_length("Hello") == 5
    assert ui.legacy_visible_length("A\nB") == 2
    assert ui.legacy_visible_length(red) == 3


def test_render_dialogue_preserves_legacy_colored_layout():
    rendered = ui.render_dialogue(
        "Hello",
        "good",
        max_columns=80,
        emoji_provider=lambda name: ":" + name + ":",
        use_color=True,
    )

    assert rendered == """
 Hello
\033[1;32;49m╰─━━━━━─╯
      /
:good:
\033[m"""


def test_render_dialogue_preserves_legacy_plain_layout():
    rendered = ui.render_dialogue(
        "Hello",
        "good",
        max_columns=80,
        emoji_provider=lambda name: ":" + name + ":",
        use_color=False,
    )

    assert rendered == """
 Hello
╰─━━━━━─╯
      /
:good:
"""


def test_printable_message_preserves_legacy_print_rules():
    marker = object()

    assert ui.printable_message("hello", max_columns=40) == "hello"
    assert ui.printable_message(marker, max_columns=40) is marker
    assert ui.printable_message("hidden", max_columns=40, no_dialogue=True) is None
    assert ui.printable_message("x" * 100, max_columns=40) == (
        "xxxxxxxxxx ...Too Big To be displayed..."
    )


def test_emit_printable_message_uses_injected_emit_callback():
    emitted = []

    assert ui.emit_printable_message(emitted.append, "hello", max_columns=40) == "hello"
    assert emitted == ["hello"]
    assert ui.emit_printable_message(
        emitted.append,
        "hidden",
        max_columns=40,
        no_dialogue=True,
    ) is None
    assert emitted == ["hello"]


def test_render_chunklate_banner_preserves_windows_layout():
    assert ui.render_chunklate_banner("nt", lambda start, end: start) == (
        """
╭─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╮
  <[0x00000016]>[C|H|U|N|K|L|A|T|E]<[0x98bd5cb8]>
╰─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╯
""",
    )


def test_render_chunklate_banner_preserves_legacy_color_calls():
    calls = []

    def random_int(start, end):
        calls.append((start, end))
        return start

    top, middle, bottom = ui.render_chunklate_banner("posix", random_int)

    assert len(calls) == 132
    assert top.startswith("\033[1;31;49m\n\033[m")
    assert middle.startswith("  \033[1;31;49m<\033[m")
    assert "\033[1;37;49m[\033[mC" in middle
    assert middle.endswith("\033[1;31;49m>\033[m")
    assert bottom.startswith("\033[1;31;49m╰\033[m")


def test_minibar_step_preserves_forward_animation():
    assert ui.minibar_step("3/9", "", 1, False, 20) == ui.MinibarStep(
        loading_text="3/9. ",
        char_pos=2,
        go_back=False,
        should_print=True,
    )


def test_minibar_step_preserves_backward_animation():
    assert ui.minibar_step("3/9", "3/9...... ", 4, False, 5) == ui.MinibarStep(
        loading_text="3/9.... ",
        char_pos=3,
        go_back=True,
        should_print=True,
    )


def test_minibar_step_preserves_turnaround_without_print():
    assert ui.minibar_step("3/9", "3/9..", 1, True, 20) == ui.MinibarStep(
        loading_text="3/9..",
        char_pos=1,
        go_back=False,
        should_print=False,
    )


def test_build_loadingbar_frames_preserves_legacy_animation_shape():
    built = ui.build_loadingbar_frames(500, 3, terminal_width=24)

    assert built.len_fish_list == len(built.frames) - 1
    assert built.fish_pos == 0
    assert len(built.frames) == 43
    assert built.frames[:6] == [
        "¸><(((º>",
        "¸.⸌<(((º>",
        "¸.·><(((º>",
        "¸.·´⸝<(((º>",
        "¸.·´¯><(((º>",
        "¸.·´¯`⸌<(((º>",
    ]
    assert built.frames[-3:] == [
        "          .·´¯`",
        "           ·´¯`",
        "            ´¯`",
    ]


def main():
    checks = [
        ("Colorize ANSI colors", test_colorize_preserves_legacy_ansi_colors),
        ("Colorize Windows mode", test_colorize_returns_data_on_windows_mode),
        ("Emoji selection", test_pick_emoji_uses_legacy_groups_deterministically),
        ("Title separator length", test_title_separator_length_matches_legacy_color_adjustment),
        ("Title non-Windows layout", test_render_title_preserves_legacy_non_windows_layout),
        ("Title Windows layout", test_render_title_preserves_legacy_windows_layout),
        ("Visible length ignores ANSI and linefeed bytes", test_legacy_visible_length_ignores_ansi_and_linefeed_bytes),
        ("Dialogue colored layout", test_render_dialogue_preserves_legacy_colored_layout),
        ("Dialogue plain layout", test_render_dialogue_preserves_legacy_plain_layout),
        ("Printable message rules", test_printable_message_preserves_legacy_print_rules),
        ("Emit printable message", test_emit_printable_message_uses_injected_emit_callback),
        ("Chunklate banner Windows", test_render_chunklate_banner_preserves_windows_layout),
        ("Chunklate banner color calls", test_render_chunklate_banner_preserves_legacy_color_calls),
        ("Minibar forward", test_minibar_step_preserves_forward_animation),
        ("Minibar backward", test_minibar_step_preserves_backward_animation),
        ("Minibar turnaround", test_minibar_step_preserves_turnaround_without_print),
        ("Loadingbar frames", test_build_loadingbar_frames_preserves_legacy_animation_shape),
    ]

    print("Running UI tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"UI tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
