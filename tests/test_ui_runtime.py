#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import ui_runtime


def runtime(**kwargs):
    emitted = []
    pauses = []
    params = {
        "emit": emitted.append,
        "random_int": lambda start, end: start,
        "max_columns": 80,
        "no_dialogue": False,
        "use_color": True,
        "pause_dialogue_enabled": False,
        "pause_dialogue": lambda: pauses.append("pause"),
    }
    params.update(kwargs)
    obj = ui_runtime.LegacyUiRuntime(**params)
    return obj, emitted, pauses


def test_legacy_ui_runtime_color_and_emoji_modes():
    ui, emitted, pauses = runtime()

    assert ui.candy("Color", "red", "ERR") == "\033[1;31;49mERR\033[m"
    assert ui.candy("Emoj", "good") == "¯\\(◉‿◉)/¯"
    assert emitted == []
    assert pauses == []


def test_legacy_ui_runtime_plain_color_mode():
    ui, _, _ = runtime(use_color=False)

    assert ui.candy("Color", "red", "ERR") == "ERR"


def test_legacy_ui_runtime_emits_cowsay_and_optional_pause():
    ui, emitted, pauses = runtime(pause_dialogue_enabled=True)

    assert ui.candy("Cowsay", "Hello", "good") is None

    assert len(emitted) == 1
    assert "Hello" in emitted[0]
    assert "¯\\(◉‿◉)/¯" in emitted[0]
    assert pauses == ["pause"]


def test_legacy_ui_runtime_pauses_once_per_dialogue_group_with_shared_state():
    state = ui_runtime.LegacyDialoguePauseState()
    ui, emitted, pauses = runtime(
        pause_dialogue_enabled=True,
        pause_state=state,
    )

    assert ui.candy("Cowsay", "Fine, let me see what i can do.", "good") is None
    assert pauses == []

    assert ui.candy("Title", "Chunk N Destroy:") is None
    assert pauses == ["pause"]

    assert ui.candy("Cowsay", "Now where shall i start..?", "com") is None
    assert ui.candy("Title", "Checking Already Used Chunks :") is None
    assert pauses == ["pause", "pause"]

    assert ui.candy("Title", "QUESTION!") is None
    assert ui.candy("Cowsay", "Fresh question, fresh paperwork.", "com") is None
    assert ui.candy("Title", "Chunk N Destroy:") is None
    assert pauses == ["pause", "pause", "pause"]
    assert len(emitted) == 7


def test_legacy_ui_runtime_pauses_once_for_consecutive_dialogue_group():
    state = ui_runtime.LegacyDialoguePauseState()
    ui, _, pauses = runtime(
        pause_dialogue_enabled=True,
        pause_state=state,
    )

    ui.candy("Cowsay", "First note.", "com")
    ui.candy("Cowsay", "Second note.", "com")
    ui.candy("Title", "Next Section")

    assert pauses == ["pause"]


def test_legacy_ui_runtime_flushes_dialogue_pause_before_non_title_output():
    state = ui_runtime.LegacyDialoguePauseState()
    ui, _, pauses = runtime(
        pause_dialogue_enabled=True,
        pause_state=state,
    )

    ui.candy("Cowsay", "Careful, something happened.", "bad")
    colored = ui.candy("Color", "red", "FAILED")

    assert colored == "\033[1;31;49mFAILED\033[m"
    assert pauses == ["pause"]


def test_legacy_ui_runtime_emits_title_unless_dialogue_disabled():
    ui, emitted, _ = runtime()

    assert ui.candy("Title", "A", "B") is None
    assert len(emitted) == 1
    assert "A B" in emitted[0]

    quiet, quiet_emitted, _ = runtime(no_dialogue=True)
    assert quiet.candy("Title", "A", "B") == ()
    assert quiet_emitted == []


def main():
    checks = [
        ("color and emoji modes", test_legacy_ui_runtime_color_and_emoji_modes),
        ("plain color mode", test_legacy_ui_runtime_plain_color_mode),
        ("cowsay and pause", test_legacy_ui_runtime_emits_cowsay_and_optional_pause),
        ("shared pause state", test_legacy_ui_runtime_pauses_once_per_dialogue_group_with_shared_state),
        ("consecutive dialogue group", test_legacy_ui_runtime_pauses_once_for_consecutive_dialogue_group),
        ("non-title output flush", test_legacy_ui_runtime_flushes_dialogue_pause_before_non_title_output),
        ("title output", test_legacy_ui_runtime_emits_title_unless_dialogue_disabled),
    ]

    print("Running UI runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"UI runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
