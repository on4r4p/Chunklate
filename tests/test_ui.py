#!/usr/bin/env python3
import contextlib
import io
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import ui
import Chunklate


@contextmanager
def patched_attrs(module, **attrs):
    old_values = {name: getattr(module, name, None) for name in attrs}
    missing = {name for name in attrs if not hasattr(module, name)}
    try:
        for name, value in attrs.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in old_values.items():
            if name in missing:
                delattr(module, name)
            else:
                setattr(module, name, value)


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
    assert ui.colorize("green", marker, use_color=False) == str(marker)


def test_pick_chunky_uses_legacy_groups_deterministically():
    assert ui.pick_chunky("good", lambda start, end: start) == ui.Chunky_State["good"][0]
    assert ui.pick_chunky("bad", lambda start, end: end) == ui.Chunky_State["bad"][-1]
    assert ui.pick_chunky("com", lambda start, end: 1) == ui.Chunky_State["com"][1]
    assert ui.pick_chunky("unknown", lambda start, end: 0) is None


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
        chunky_provider=lambda name: ":" + name + ":",
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
        chunky_provider=lambda name: ":" + name + ":",
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
+-------------------------------------------------+
  <[0x00000016]>[C|H|U|N|K|L|A|T|E]<[0x98bd5cb8]>
+-------------------------------------------------+
""",
    )


def test_render_chunklate_banner_can_disable_color_on_posix():
    calls = []

    assert ui.render_chunklate_banner("posix", lambda start, end: calls.append((start, end)), use_color=False) == (
        """
╭─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╮
  <[0x00000016]>[C|H|U|N|K|L|A|T|E]<[0x98bd5cb8]>
╰─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╯
""",
    )
    assert calls == []


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


def test_loadingbar_progress_keeps_frame_between_100_steps():
    progress = ui.loadingbar_progress(
        500,
        3,
        42,
        ["frame0", "frame1"],
        fish_pos=0,
        len_fish_list=1,
    )

    assert progress == ui.LoadingbarProgress(text="042/500frame0", fish_pos=0)


def test_loadingbar_progress_maps_position_to_budget_ratio():
    progress = ui.loadingbar_progress(
        500,
        3,
        250,
        ["frame0>", "frame1>", "frame2>", "frame3>", "frame4>"],
        fish_pos=0,
        len_fish_list=4,
    )

    assert progress == ui.LoadingbarProgress(text="250/500frame2>", fish_pos=2)


def test_loadingbar_fish_speed_scales_with_budget_digits():
    assert ui.loadingbar_fish_speed(500) == 1
    assert ui.loadingbar_fish_speed(100000) == 4


def test_loadingbar_progress_moves_faster_for_large_budgets():
    progress = ui.loadingbar_progress(
        100000,
        6,
        6000,
        [
            "frame0>",
            "frame1>",
            "frame2>",
            "frame3>",
            "frame4>",
            "frame5>",
            "frame6>",
            "frame7>",
            "frame8>",
            "frame9>",
            "frame10>",
        ],
        fish_pos=0,
        len_fish_list=10,
    )

    assert progress == ui.LoadingbarProgress(text="006000/100000frame2>", fish_pos=2)


def test_loadingbar_progress_animates_huge_budget_each_callback():
    frames = [
        "frame0>",
        "frame1>",
        "frame2>",
        "frame3>",
        "frame4>",
    ]
    first = ui.loadingbar_progress(
        3_506_270_321,
        10,
        100,
        frames,
        fish_pos=0,
        len_fish_list=4,
    )
    second = ui.loadingbar_progress(
        3_506_270_321,
        10,
        200,
        frames,
        fish_pos=first.fish_pos,
        len_fish_list=4,
    )

    assert first == ui.LoadingbarProgress(
        text="0000000100/3506270321frame1>",
        fish_pos=1,
    )
    assert second == ui.LoadingbarProgress(
        text="0000000200/3506270321frame2>",
        fish_pos=2,
    )


def test_loadingbar_progress_stops_at_last_visible_fish_frame():
    progress = ui.loadingbar_progress(
        500,
        3,
        500,
        ["frame0>", "frame1>", "trail"],
        fish_pos=0,
        len_fish_list=2,
    )

    assert progress == ui.LoadingbarProgress(text="500/500frame1>", fish_pos=1)


def test_run_loadingbar_from_namespace_builds_and_prints_progress():
    calls = []
    namespace = {
        "os": type("FakeOs", (), {"get_terminal_size": staticmethod(lambda fd: (24, 80))})(),
        "print": lambda *args, **kwargs: calls.append(("print", args, kwargs)),
    }

    ui.run_loadingbar_from_namespace(namespace, 500, 3, 0, True)

    assert namespace["LenFishList"] == len(namespace["ThksForTheFish"]) - 1
    assert namespace["FishPos"] == 0

    ui.run_loadingbar_from_namespace(namespace, 500, 3, 250, False)

    visible_fish_end = ui.loadingbar_last_visible_fish_frame(
        namespace["ThksForTheFish"],
        namespace["LenFishList"],
    )
    expected_position = round((250 / 500) * visible_fish_end)
    assert namespace["FishPos"] == expected_position
    assert calls == [
        (
            "print",
            ("250/500" + namespace["ThksForTheFish"][expected_position] + "\033[K",),
            {"end": "\r", "flush": True},
        )
    ]


def test_run_loadingbar_from_namespace_clears_dialogue_pause_before_loader_output():
    calls = []
    namespace = {
        "os": type("FakeOs", (), {"get_terminal_size": staticmethod(lambda fd: (24, 80))})(),
        "print": lambda *args, **kwargs: calls.append(("print", args, kwargs)),
        "Clear_Terminal_Dialogue_Pause": lambda: calls.append(("clear_dialogue_pause",)),
    }

    ui.run_loadingbar_from_namespace(namespace, 500, 3, 0, True)
    ui.run_loadingbar_from_namespace(namespace, 500, 3, 100, False)

    assert calls[0] == ("clear_dialogue_pause",)
    assert calls[1] == ("clear_dialogue_pause",)
    assert calls[2][0] == "print"


def test_run_loadingbar_from_namespace_uses_print_fallback():
    namespace = {
        "os": type("FakeOs", (), {"get_terminal_size": staticmethod(lambda fd: (24, 80))})(),
    }
    output = io.StringIO()

    with contextlib.redirect_stdout(output):
        ui.run_loadingbar_from_namespace(namespace, 500, 3, 0, True)
        ui.run_loadingbar_from_namespace(namespace, 500, 3, 100, False)

    visible_fish_end = ui.loadingbar_last_visible_fish_frame(
        namespace["ThksForTheFish"],
        namespace["LenFishList"],
    )
    expected_position = round((100 / 500) * visible_fish_end)
    assert namespace["FishPos"] == expected_position
    assert output.getvalue() == "100/500" + namespace["ThksForTheFish"][expected_position] + "\033[K\r"


def test_run_loadingbar_from_namespace_uses_terminal_fallback_on_non_tty():
    class FakeOs:
        @staticmethod
        def get_terminal_size(fd):
            raise OSError("not a tty")

    namespace = {
        "os": FakeOs(),
        "print": lambda *args, **kwargs: None,
    }

    ui.run_loadingbar_from_namespace(namespace, 500, 3, 0, True)

    assert namespace["LenFishList"] == len(namespace["ThksForTheFish"]) - 1
    assert len(namespace["ThksForTheFish"]) > 0


def test_chunklate_minibar_resets_by_indication_and_clears_line():
    calls = []

    def fake_print(*args, **kwargs):
        calls.append((args, kwargs))

    with patched_attrs(
        Chunklate,
        print=fake_print,
        MAXCHAR=20,
        Loading_txt="old........ ",
        Loading_sep="old",
        CharPos=9,
        GoBack=True,
        PROGRESS_LINE_ACTIVE=False,
    ):
        Chunklate.Minibar("new")

        assert Chunklate.Loading_txt == "new. "
        assert Chunklate.Loading_sep == "new"
        assert Chunklate.CharPos == 2
        assert Chunklate.GoBack is False
        assert Chunklate.PROGRESS_LINE_ACTIVE is True

    assert calls == [(("new. \033[K",), {"end": "\r"})]


def test_chunklate_minibar_keeps_animation_when_counter_changes():
    calls = []

    def fake_print(*args, **kwargs):
        calls.append((args, kwargs))

    with patched_attrs(
        Chunklate,
        print=fake_print,
        MAXCHAR=30,
        Loading_txt="1/10.. ",
        Loading_sep="#/##",
        CharPos=3,
        GoBack=False,
        PROGRESS_LINE_ACTIVE=False,
    ):
        Chunklate.Minibar("2/10")

        assert Chunklate.Loading_txt == "2/10... "
        assert Chunklate.Loading_sep == "#/##"
        assert Chunklate.CharPos == 4
        assert Chunklate.PROGRESS_LINE_ACTIVE is True

    assert calls == [(("2/10... \033[K",), {"end": "\r"})]


def test_chunklate_print_finishes_active_progress_line_before_output():
    calls = []

    def fake_print(*args, **kwargs):
        calls.append((args, kwargs))

    with patched_attrs(
        Chunklate,
        print=fake_print,
        MAXCHAR=80,
        NODIALOGUE=False,
        PROGRESS_LINE_ACTIVE=True,
    ):
        Chunklate.PRINT("after")

        assert Chunklate.PROGRESS_LINE_ACTIVE is False

    assert calls == [
        (("",), {}),
        (("after",), {}),
    ]


def test_chunklate_loader_message_redraws_active_progress_line():
    calls = []

    def fake_print(*args, **kwargs):
        calls.append((args, kwargs))

    with patched_attrs(
        Chunklate,
        print=fake_print,
        MAXCHAR=80,
        NODIALOGUE=False,
        DEBUGFILE=False,
        PROGRESS_LINE_ACTIVE=True,
        LAST_PROGRESS_LINE="000200/001000><(((º>",
    ):
        Chunklate.PRINT_With_Loader_Redraw("-Preview image : out.png")

        assert Chunklate.PROGRESS_LINE_ACTIVE is True

    assert calls == [
        (("\r\033[K",), {"end": ""}),
        (("-Preview image : out.png",), {}),
        (("000200/001000><(((º>\033[K",), {"end": "\r"}),
    ]


def main():
    checks = [
        ("Colorize ANSI colors", test_colorize_preserves_legacy_ansi_colors),
        ("Colorize Windows mode", test_colorize_returns_data_on_windows_mode),
        ("Chunky selection", test_pick_chunky_uses_legacy_groups_deterministically),
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
        ("Loadingbar progress static", test_loadingbar_progress_keeps_frame_between_100_steps),
        ("Loadingbar progress ratio", test_loadingbar_progress_maps_position_to_budget_ratio),
        ("Loadingbar fish speed scales", test_loadingbar_fish_speed_scales_with_budget_digits),
        ("Loadingbar progress large budget speed", test_loadingbar_progress_moves_faster_for_large_budgets),
        ("Loadingbar huge budget callback animation", test_loadingbar_progress_animates_huge_budget_each_callback),
        ("Loadingbar progress visible end", test_loadingbar_progress_stops_at_last_visible_fish_frame),
        ("Loadingbar namespace bridge", test_run_loadingbar_from_namespace_builds_and_prints_progress),
        ("Loadingbar clears dialogue pause", test_run_loadingbar_from_namespace_clears_dialogue_pause_before_loader_output),
        ("Loadingbar print fallback", test_run_loadingbar_from_namespace_uses_print_fallback),
        ("Loadingbar terminal fallback", test_run_loadingbar_from_namespace_uses_terminal_fallback_on_non_tty),
        ("Chunklate Minibar clears line", test_chunklate_minibar_resets_by_indication_and_clears_line),
        ("Chunklate Minibar keeps counter animation", test_chunklate_minibar_keeps_animation_when_counter_changes),
        ("Chunklate PRINT finishes progress", test_chunklate_print_finishes_active_progress_line_before_output),
        ("Chunklate loader message redraw", test_chunklate_loader_message_redraws_active_progress_line),
    ]

    print("Running UI tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"UI tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
