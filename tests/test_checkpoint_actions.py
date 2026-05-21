#!/usr/bin/env python3
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Chunklate
from chunklate import checkpoint


@contextmanager
def patched_attrs(module, **attrs):
    old_values = {name: getattr(module, name) for name in attrs}
    try:
        for name, value in attrs.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in old_values.items():
            setattr(module, name, value)


def reset_checkpoint_globals():
    Chunklate.SideNotes = []
    Chunklate.PandoraBox = {}
    Chunklate.Brute_LvL = 0
    Chunklate.ETA = 1
    Chunklate.IHDR_Interlace = "0"
    Chunklate.Bad_Libpng = False
    Chunklate.Bad_Current_Name = False
    Chunklate.Bad_Next_Name = False
    Chunklate.Bad_Ancillary = False
    Chunklate.Bad_Next_Ancillary = False


def test_apply_action_routes_known_srgb_warning_to_fixitfelix():
    reset_checkpoint_globals()
    calls = []

    def fake_fixit_felix(source):
        calls.append(source)
        return "fixed-by-felix"

    decision = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: iCCP: known incorrect sRGB profile",
        toolkit=(),
    )

    with patched_attrs(Chunklate, FixItFelix=fake_fixit_felix):
        should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
            decision,
            "LibpngCheck",
            "libpng warning: iCCP: known incorrect sRGB profile",
            (),
        )

    assert should_return is True
    assert result == "fixed-by-felix"
    assert calls == ["LibpngCheck"]
    assert Chunklate.Bad_Libpng is True


def test_apply_action_discards_libpng_false_positive_warning():
    reset_checkpoint_globals()
    warning_key = "LibpngCheck_Error_0:libpng warning: iCCP: profile is noisy"
    Chunklate.PandoraBox = {warning_key: {"LibpngCheck_Tool_0": "sample.png"}}

    decision = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: iCCP: profile is noisy",
        toolkit=(),
    )

    with patched_attrs(
        Chunklate,
        Candy=lambda *args, **kwargs: "",
        PRINT=lambda *args, **kwargs: None,
    ):
        should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
            decision,
            "LibpngCheck",
            "libpng warning: iCCP: profile is noisy",
            (),
        )

    assert should_return is False
    assert result is None
    assert Chunklate.PandoraBox == {}
    assert Chunklate.SideNotes == [
        "-Found False-Positive :[Error:-%s]." % warning_key
    ]


def test_apply_action_routes_chunk_name_missing_bytes_to_saveclone():
    reset_checkpoint_globals()
    calls = []

    def fake_save_clone(data, suffix, combined, reason):
        calls.append((data, suffix, combined, reason))
        return "saved-missing-bytes"

    decision = checkpoint.action_decision(
        error=True,
        function="CheckChunkName",
        chunk=b"IDAT",
        info="Chunk name corrupted due to some missing bytes.",
        toolkit=(b"prefix", b"missing", b"suffix", None),
    )

    with patched_attrs(Chunklate, SaveClone=fake_save_clone):
        should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
            decision,
            b"IDAT",
            "Chunk name corrupted due to some missing bytes.",
            (b"prefix", b"missing", b"suffix", None),
        )

    assert should_return is True
    assert result == "saved-missing-bytes"
    assert calls == [
        (
            b"prefix",
            b"suffix",
            b"missingsuffix",
            "Fixing Missing bytes corruption",
        )
    ]


def test_apply_action_sets_chunk_name_flags():
    reset_checkpoint_globals()
    decision = checkpoint.action_decision(
        error=True,
        function="CheckChunkName",
        chunk=b"bADR",
        info="Chunk has Wrong Chunk name after Chunk[b'IHDR']",
        toolkit=(),
    )

    should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
        decision,
        b"bADR",
        "Chunk has Wrong Chunk name after Chunk[b'IHDR']",
        (),
    )

    assert should_return is False
    assert result is None
    assert Chunklate.Bad_Next_Name is True


def test_apply_action_routes_simple_smash_brute_brawl_write_clone():
    reset_checkpoint_globals()
    calls = []

    def fake_write_clone(data, reason):
        calls.append((data, reason))
        return "written-bruteforce-result"

    decision = checkpoint.action_decision(
        error=True,
        function="SmashBruteBrawl",
        chunk=b"IDAT",
        info="Corrupted Data has been replaced",
        toolkit=(b"fixed-data",),
    )

    with patched_attrs(Chunklate, WriteClone=fake_write_clone):
        should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
            decision,
            b"IDAT",
            "Corrupted Data has been replaced",
            (b"fixed-data",),
        )

    assert should_return is True
    assert result == "written-bruteforce-result"
    assert calls == [(b"fixed-data", "-About to save.")]
    assert Chunklate.SideNotes == ["-CheckPoint: Corrupted Data has been replaced"]


def test_apply_action_routes_simple_smash_brute_brawl_save_clone():
    reset_checkpoint_globals()
    calls = []

    def fake_save_clone(data, chunk, start, end):
        calls.append((data, chunk, start, end))
        return "saved-old-crc"

    decision = checkpoint.action_decision(
        error=True,
        function="SmashBruteBrawl",
        chunk=b"IDAT",
        info="Previous Crc checksum has been restored",
        toolkit=(b"fixed-data", b"IDAT", 12, 20),
    )

    with patched_attrs(Chunklate, SaveClone=fake_save_clone):
        should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
            decision,
            b"IDAT",
            "Previous Crc checksum has been restored",
            (b"fixed-data", b"IDAT", 12, 20),
        )

    assert should_return is True
    assert result == "saved-old-crc"
    assert calls == [(b"fixed-data", b"IDAT", 12, 20)]
    assert Chunklate.SideNotes == [
        "-CheckPoint: Previous Crc checksum has been restored"
    ]


def test_apply_smash_brute_brawl_retry_ihdr_relaunches_with_higher_level():
    reset_checkpoint_globals()
    calls = []
    toolkit = ("sample.png", b"IHDR", 13, 8, "edit", "Bytes", "crc", "length", "from-error")
    decision = checkpoint.CheckPointActionDecision("smash_brute_brawl_retry_ihdr_harder")

    def fake_smash_brute_brawl(*args, **kwargs):
        calls.append((args, kwargs))

    with patched_attrs(
        Chunklate,
        Candy=lambda *args, **kwargs: "",
        SmashBruteBrawl=fake_smash_brute_brawl,
    ):
        should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
            decision,
            "IHDR",
            "-Bruteforcer has Failed",
            toolkit,
        )

    assert should_return is False
    assert result is None
    assert Chunklate.Brute_LvL == 1
    assert Chunklate.SideNotes == ["-CheckPoint: -Bruteforcer has Failed"]
    assert calls == [
        (
            ("sample.png", b"IHDR", 13, 8, "from-error"),
            {
                "EditMode": "edit",
                "BfMode": "Bytes",
                "BruteCrc": "crc",
                "BruteLength": "length",
            },
        )
    ]


def test_apply_smash_brute_brawl_twobytes_retry_preserves_old_crc_route():
    reset_checkpoint_globals()
    calls = []
    questions = []
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "edit",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "from-error",
    )
    decision = checkpoint.CheckPointActionDecision("smash_brute_brawl_ask_twobytes_retry")

    def fake_question(*args, **kwargs):
        questions.append((args, kwargs))
        return True

    def fake_smash_brute_brawl(*args, **kwargs):
        calls.append((args, kwargs))

    with patched_attrs(
        Chunklate,
        Candy=lambda *args, **kwargs: "",
        PRINT=lambda *args, **kwargs: None,
        Question=fake_question,
        SmashBruteBrawl=fake_smash_brute_brawl,
    ):
        should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
            decision,
            "IDAT",
            "-Bruteforcer has Failed OldCrc",
            toolkit,
        )

    assert should_return is False
    assert result is None
    assert Chunklate.Brute_LvL == 1
    assert questions == [((), {"skipauto": True})]
    assert Chunklate.SideNotes == [
        "-CheckPoint: Increasing BfLvl: -Bruteforcer has Failed OldCrc"
    ]
    assert calls == [
        (
            ("sample.png", b"IDAT", 4, 100, "from-error"),
            {
                "EditMode": "edit",
                "BfMode": "TwoBytes",
                "BruteCrc": "crc",
                "BruteLength": "length",
                "OldCrc": "old-crc",
            },
        )
    ]


def test_apply_smash_brute_brawl_twobytes_decline_can_dummy_interlaced_idat():
    reset_checkpoint_globals()
    dummy_calls = []
    answers = iter([False, True])
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "edit",
        "TwoBytes",
        "crc",
        "length",
        "from-error",
    )
    decision = checkpoint.CheckPointActionDecision("smash_brute_brawl_ask_twobytes_retry")

    def fake_question(*args, **kwargs):
        return next(answers)

    def fake_dummy_chunk(*args):
        dummy_calls.append(args)

    with patched_attrs(
        Chunklate,
        Candy=lambda *args, **kwargs: "",
        PRINT=lambda *args, **kwargs: None,
        Question=fake_question,
        DummyChunk=fake_dummy_chunk,
        IHDR_Interlace="1",
    ):
        should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
            decision,
            "IDAT",
            "-Bruteforcer has Failed",
            toolkit,
        )

    assert should_return is False
    assert result is None
    assert Chunklate.Brute_LvL == 1
    assert Chunklate.SideNotes == [
        "-CheckPoint:User choose to replace IDAT: -Bruteforcer has Failed"
    ]
    assert dummy_calls == [(b"IDAT", 100, 100, 4, "from-error")]


def test_apply_smash_brute_brawl_custom_can_switch_to_brutus():
    reset_checkpoint_globals()
    Chunklate.Brute_LvL = 5
    calls = []
    toolkit = ("sample.png", b"IDAT", 4, 100, "edit", "Custom", "crc", "length", "from-error")
    decision = checkpoint.CheckPointActionDecision("smash_brute_brawl_ask_custom_brutus")

    def fake_smash_brute_brawl(*args, **kwargs):
        calls.append((args, kwargs))

    with patched_attrs(
        Chunklate,
        Candy=lambda *args, **kwargs: "",
        Question=lambda *args, **kwargs: True,
        SmashBruteBrawl=fake_smash_brute_brawl,
    ):
        should_return, result = Chunklate.CheckPoint_Apply_Action_Decision(
            decision,
            "IDAT",
            "-Bruteforcer has Failed",
            toolkit,
        )

    assert should_return is False
    assert result is None
    assert Chunklate.Brute_LvL == 0
    assert Chunklate.SideNotes == [
        "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!(CUSTOM END)"
    ]
    assert calls == [
        (
            ("sample.png", b"IDAT", 4, 100, "from-error"),
            {
                "EditMode": "edit",
                "BfMode": "Brutus",
                "BruteCrc": "crc",
                "BruteLength": "length",
            },
        )
    ]


def main():
    checks = [
        ("Apply known sRGB warning with FixItFelix", test_apply_action_routes_known_srgb_warning_to_fixitfelix),
        ("Apply libpng false-positive warning removal", test_apply_action_discards_libpng_false_positive_warning),
        ("Apply chunk-name missing-bytes SaveClone", test_apply_action_routes_chunk_name_missing_bytes_to_saveclone),
        ("Apply chunk-name flags", test_apply_action_sets_chunk_name_flags),
        ("Apply simple SmashBruteBrawl WriteClone", test_apply_action_routes_simple_smash_brute_brawl_write_clone),
        ("Apply simple SmashBruteBrawl SaveClone", test_apply_action_routes_simple_smash_brute_brawl_save_clone),
        ("Apply SmashBruteBrawl IHDR retry", test_apply_smash_brute_brawl_retry_ihdr_relaunches_with_higher_level),
        ("Apply SmashBruteBrawl TwoBytes retry", test_apply_smash_brute_brawl_twobytes_retry_preserves_old_crc_route),
        ("Apply SmashBruteBrawl interlaced IDAT dummy fallback", test_apply_smash_brute_brawl_twobytes_decline_can_dummy_interlaced_idat),
        ("Apply SmashBruteBrawl Custom Brutus fallback", test_apply_smash_brute_brawl_custom_can_switch_to_brutus),
    ]

    print("Running CheckPoint action application tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"checkpoint action application tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
