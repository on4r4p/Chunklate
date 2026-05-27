#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import relics, relics_ui


def fake_candy_factory(calls):
    def fake_candy(*args):
        calls.append(args)
        if args[0] == "Color":
            return "<%s:%s>" % (args[1], args[2])
        if args[0] == "Chunky":
            return "<chunky:%s>" % args[1]
        return None

    return fake_candy


def test_relics_ui_shortens_long_tool_values():
    assert relics_ui.short_value("x" * 101) == "x" * 40 + "...To big to be displayed ..."
    assert relics_ui.short_value(b"x" * 101) == b"x" * 40 + b"...To big to be displayed ..."
    assert relics_ui.short_value(12) == 12


def test_relics_ui_emits_debug_state():
    emitted = []
    pauses = []

    relics_ui.emit_debug_state(
        debug=True,
        pandemonium={"sample": {}},
        pandora_box={"error": {"tool": "value"}},
        chunks_history=[b"IHDR"],
        chunks_history_index=["0:8:21"],
        pause_debug=True,
        emit=emitted.append,
        pause=pauses.append,
    )

    assert emitted == [
        "len pandemonium :1",
        "Pandorbox Key:error",
        "PandoraBox toolkey:tool",
        "PandoraBox keyvalue:value",
        "\nCame accross that chunk: b'IHDR'",
        "With those index: 0:8:21",
    ]
    assert pauses == ["-Debug Pause Press Return to continue:"]


def test_relics_ui_emits_pandemonium_summary():
    emitted = []
    candy_calls = []
    summary = (
        relics.RelicSampleSummary(
            sample="sample.0_Fixed.png",
            errors=(
                relics.RelicErrorSummary(
                    error="Checksum_Error_0",
                    tools=(("IDAT_Tool_0", "x" * 101),),
                ),
            ),
        ),
    )

    relics_ui.emit_pandemonium_summary(
        summary,
        emit=emitted.append,
        candy=fake_candy_factory(candy_calls),
    )

    assert candy_calls[0] == ("Cowsay", "This is a short summary of what we have done :", "good")
    assert emitted == [
        "<white:[File:0]>:-Errors fixed in File sample.0_Fixed.png :",
        "<red:    [-0]>:Checksum_Error_0",
        "<yellow:        [Tool used :0]>:IDAT_Tool_0:%s" % ("x" * 40 + "...To big to be displayed ..."),
    ]


def test_relics_ui_emits_core_relic_messages():
    candy_calls = []
    candy = fake_candy_factory(candy_calls)

    relics_ui.say_current_wrong_crc_idat(candy=candy)
    relics_ui.say_wrong_crc_data_brawl("IDAT", candy=candy)
    relics_ui.say_plte_intro(candy=candy)
    relics_ui.say_plte_valid_crc(candy=candy)
    relics_ui.say_plte_bad_crc(candy=candy)
    relics_ui.say_plte_fallback(candy=candy)
    relics_ui.say_single_pandemonium_intro(candy=candy)
    relics_ui.say_single_pandemonium_unsupported(candy=candy)
    relics_ui.say_dummy_chunk_critical_prompt("IHDR", candy=candy)
    relics_ui.say_dummy_chunk_ancillary_prompt("tEXt", candy=candy)

    assert ("Cowsay", "Crc checksum is not valid !!!", "bad") in candy_calls
    assert ("Cowsay", "Maybe the culprit was in fact the IDAT Data itself!", "bad") in candy_calls
    assert ("Cowsay", "Alright this is a tough one as PLTE is a critical chunk..", "bad") in candy_calls
    assert ("Cowsay", "Only one Error,That is short indeed ..", "com") in candy_calls
    assert ("Cowsay", "Erf this case is not implemented yet ...", "bad") in candy_calls
    assert (
        "Cowsay",
        "Ok it's time to brute force that dummy IHDR chunk ..",
        "good",
    ) in candy_calls
    assert (
        "Cowsay",
        "We better remove that tEXt chunk than trying to bruteforce it",
        "com",
    ) in candy_calls


def test_relics_ui_emits_no_pandemonium_messages():
    emitted = []
    candy_calls = []
    candy = fake_candy_factory(candy_calls)
    context = relics.NoPandemoniumPromptContext("getinfo_brawl", ("hit-0", "hit-1"))

    relics_ui.say_no_pandemonium_intro(emit=emitted.append, candy=candy)
    relics_ui.emit_prompt_context_hits(context, emit=emitted.append)
    relics_ui.say_no_pandemonium_getinfo(skip_bad_crc=False, candy=candy)
    relics_ui.say_no_pandemonium_forcer(candy=candy)
    relics_ui.say_no_pandemonium_failure(candy=candy)
    relics_ui.emit_todo(emit=emitted.append, candy=candy)

    assert emitted == [
        "-<red:No Error> has been Fixed yet. <chunky:bad>",
        "\n-\033[1;31;49mCriticalHit\033[m: hit-0",
        "\n-\033[1;31;49mCriticalHit\033[m: hit-1",
        "<yellow:\n-ToDo>",
    ]
    assert ("Cowsay", "Erf...Kay let me check if iv forgot any error somewhere ..", "com") in candy_calls
    assert ("Cowsay", "And of course Crc is valid ...This must be a joke..", "bad") in candy_calls
    assert (
        "Cowsay",
        "This is bad ..i don't have enough info to handle this error quickly..",
        "com",
    ) in candy_calls
    assert ("Cowsay", "We r out of luck for now sorry..", "bad") in candy_calls


def main():
    checks = [
        ("Relics UI shortens long tool values", test_relics_ui_shortens_long_tool_values),
        ("Relics UI emits debug state", test_relics_ui_emits_debug_state),
        ("Relics UI emits Pandemonium summary", test_relics_ui_emits_pandemonium_summary),
        ("Relics UI emits core relic messages", test_relics_ui_emits_core_relic_messages),
        ("Relics UI emits no-Pandemonium messages", test_relics_ui_emits_no_pandemonium_messages),
    ]

    print("Running Relics UI tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"relics UI tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
