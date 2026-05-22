#!/usr/bin/env python3
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import checkpoint, relics

CHUNKLATE = ROOT / "Chunklate.py"


def load_chunklate():
    spec = importlib.util.spec_from_file_location("chunklate_legacy_for_relic_tests", CHUNKLATE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


chunklate = load_chunklate()


def reset_relic_state():
    chunklate.PandoraBox = {}
    chunklate.Cornucopia = {}
    chunklate.Pandemonium = {}
    chunklate.ArkOfCovenant = {}
    chunklate.SideNotes = []
    chunklate.Sample = "sample.png"
    chunklate.DEBUG = False
    chunklate.PAUSEDEBUG = False
    chunklate.PAUSEERROR = False
    chunklate.NODIALOGUE = True


def test_relic_build_tools_uses_legacy_tool_names():
    tools = chunklate.Relic_Build_Tools(b"IDAT", ("crc", 12, 20))

    assert tools == {
        "IDAT_Tool_0": "crc",
        "IDAT_Tool_1": 12,
        "IDAT_Tool_2": 20,
    }


def test_relics_module_uses_explicit_state_objects():
    pandora_box = {}
    tools = relics.build_tools(b"IDAT", ("newcrc", 12, 20))

    key = relics.add_pandora_error(pandora_box, "Checksum", "Wrong Crc", tools)

    assert key == "Checksum_Error_0:Wrong Crc"
    assert pandora_box[key] is tools
    assert relics.tool_key("IDAT_Tool_", 1) == "IDAT_Tool_1"
    assert relics.tool_value(tools, "IDAT_Tool_", 1) == 12


def test_relics_module_finds_chunk_names_in_legacy_text_and_tool_keys():
    known_chunks = [b"IHDR", b"IDAT", b"IEND"]
    tools = relics.build_tools(b"IDAT", ("newcrc", 12, 20))

    from_text = relics.chunk_name_from_text("Checksum_Error_0:-Found Chunk[IDAT] has Wrong Crc", known_chunks)
    from_tools = relics.chunk_name_from_tool_keys(tools, known_chunks)

    assert from_text == "IDAT"
    assert from_tools == "IDAT"


def test_relics_module_exposes_wrong_crc_tools_by_name():
    tools = relics.build_tools(
        b"IDAT",
        ("newcrc", 12, 20, b"IDAT", "0x2a", "oldcrc", 433, 100),
    )

    crc_tools = relics.wrong_crc_tools(tools, "IDAT_Tool_")

    assert crc_tools.replacement_crc == "newcrc"
    assert crc_tools.start == 12
    assert crc_tools.end == 20
    assert crc_tools.chunk == b"IDAT"
    assert crc_tools.offset == "0x2a"
    assert crc_tools.old_crc == "oldcrc"
    assert crc_tools.chunk_length == 433
    assert crc_tools.data_offset == 100


def test_relics_module_exposes_wrong_chunk_name_tools_by_name():
    tools = relics.build_tools(
        b"bad!",
        (b"bad!", "00000004", 42, b"IDAT", None),
    )

    name_tools = relics.wrong_chunk_name_tools(tools, "bad!_Tool_")

    assert name_tools.chunk_type == b"bad!"
    assert name_tools.chunk_length == "00000004"
    assert name_tools.chunk_type_offset == 42
    assert name_tools.previous_chunk == b"IDAT"
    assert name_tools.next_marker is None


def test_relics_module_exposes_no_next_chunk_tools_by_name():
    tools = relics.build_tools(
        b"IDAT",
        (b"IDAT", "00000000", b"PLTE"),
    )

    no_next_tools = relics.no_next_chunk_tools(tools, "IDAT_Tool_")

    assert no_next_tools.chunk_type == b"IDAT"
    assert no_next_tools.chunk_length == "00000000"
    assert no_next_tools.previous_chunk == b"PLTE"


def test_relics_module_exposes_dummy_chunk_tools_by_name():
    tools = relics.build_tools(
        b"IEND",
        ("fixed-data", 0, 128, 128, 152, "No NextChunk"),
    )

    dummy_tools = relics.dummy_chunk_tools(tools, "IEND_Tool_")

    assert dummy_tools.fixed_data == "fixed-data"
    assert dummy_tools.dummy_data_length == 0
    assert dummy_tools.bad_position == 128
    assert dummy_tools.bad_start == 128
    assert dummy_tools.bad_end == 152
    assert dummy_tools.from_error == "No NextChunk"


def test_relics_module_routes_current_wrong_crc_errors():
    pandora_box = {
        "Checksum_Error_0:Wrong Crc b'IDAT'": relics.build_tools(
            b"IDAT",
            ("newcrc", 12, 20, b"IDAT", "0x2a", "oldcrc", 433, 100),
        ),
        "Checksum_Error_1:Wrong Crc b'PLTE'": relics.build_tools(
            b"PLTE",
            ("newcrc", 12, 20, b"PLTE", "0x2a", "oldcrc", 768, 100),
        ),
        "GetInfo_Error_0:Other": {},
    }
    cornucopia = {"Checksum_Error_1:Wrong Crc b'PLTE'": {}}

    routes = relics.current_wrong_crc_routes(pandora_box, cornucopia, [b"IDAT", b"PLTE"])

    assert routes == [
        relics.WrongCrcRoute(
            source=None,
            error="Checksum_Error_0:Wrong Crc b'IDAT'",
            chunk_name="IDAT",
            tool_prefix="IDAT_Tool_",
        )
    ]
    assert routes[0].is_current_file is True


def test_relics_module_routes_remembered_wrong_crc_errors():
    pandemonium = {
        "sample.0_Fixed.png": {
            "Checksum_Error_0:Wrong Crc": relics.build_tools(
                b"IDAT",
                ("newcrc", 12, 20, b"IDAT", "0x2a", "oldcrc", 433, 100),
            ),
            "GetInfo_Error_0:Other": {},
        }
    }

    routes = relics.remembered_wrong_crc_routes(pandemonium, [b"IDAT", b"PLTE"])

    assert routes == [
        relics.WrongCrcRoute(
            source="sample.0_Fixed.png",
            error="Checksum_Error_0:Wrong Crc",
            chunk_name="IDAT",
            tool_prefix="IDAT_Tool_",
        )
    ]
    assert routes[0].is_current_file is False


def test_relics_module_filters_idat_wrong_crc_routes():
    routes = (
        relics.WrongCrcRoute(None, "idat", "IDAT", "IDAT_Tool_"),
        relics.WrongCrcRoute(None, "plte", "PLTE", "PLTE_Tool_"),
    )

    assert relics.idat_wrong_crc_routes(routes) == (routes[0],)


def test_relics_module_summarises_pandemonium_without_formatting():
    pandemonium = {
        "sample.0_Fixed.png": {
            "Checksum_Error_0:Wrong Crc": {
                "IDAT_Tool_0": "newcrc",
                "IDAT_Tool_1": 12,
            }
        }
    }

    assert relics.pandemonium_summary(pandemonium) == (
        relics.RelicSampleSummary(
            sample="sample.0_Fixed.png",
            errors=(
                relics.RelicErrorSummary(
                    error="Checksum_Error_0:Wrong Crc",
                    tools=(("IDAT_Tool_0", "newcrc"), ("IDAT_Tool_1", 12)),
                ),
            ),
        ),
    )


def test_relics_module_exposes_plte_interactive_choices():
    assert relics.plte_repair_choices(False) == ("manually", "remove", "quit")
    assert relics.plte_repair_choices(True) == (
        "manually",
        "bruteforce",
        "remove",
        "quit",
    )


def test_relics_module_builds_idat_wrong_crc_brawl_plan():
    route = relics.WrongCrcRoute(
        source="sample.0_Fixed.png",
        error="Checksum_Error_0:Wrong Crc",
        chunk_name="IDAT",
        tool_prefix="IDAT_Tool_",
    )
    tools = relics.WrongCrcTools(
        replacement_crc="newcrc",
        start=12,
        end=20,
        chunk=b"IDAT",
        offset="0x2a",
        old_crc="oldcrc",
        chunk_length=433,
        data_offset=100,
    )

    plan = relics.wrong_crc_brawl_plan(
        route,
        tools,
        target_file="origin.png",
        from_error="libpng",
    )

    assert plan == relics.WrongCrcBrawlPlan(
        target_file="origin.png",
        chunk=b"IDAT",
        chunk_length=433,
        data_offset=100,
        from_error="libpng",
        old_crc="oldcrc",
        bf_mode="TwoBytes",
    )


def test_relics_module_builds_non_idat_wrong_crc_brawl_plan():
    route = relics.WrongCrcRoute(
        source="sample.0_Fixed.png",
        error="Checksum_Error_0:Wrong Crc",
        chunk_name="PLTE",
        tool_prefix="PLTE_Tool_",
    )
    tools = relics.WrongCrcTools(
        replacement_crc="newcrc",
        start=12,
        end=20,
        chunk=b"PLTE",
        offset="0x2a",
        old_crc="oldcrc",
        chunk_length=768,
        data_offset=100,
    )

    plan = relics.wrong_crc_brawl_plan(
        route,
        tools,
        target_file="origin.png",
        from_error="libpng",
    )

    assert plan == relics.WrongCrcBrawlPlan(
        target_file="origin.png",
        chunk=b"PLTE",
        chunk_length=768,
        data_offset=100,
        from_error="libpng",
        old_crc="oldcrc",
        brute_length=False,
    )


def test_relics_module_resolves_remembered_sample_target():
    assert (
        relics.remembered_sample_target(
            0,
            "sample.0_Fixed.png",
            file_origin="/tmp/origin.png",
            current_sample="/tmp/current.png",
        )
        == "/tmp/origin.png"
    )
    assert (
        relics.remembered_sample_target(
            1,
            "sample.1_Fixed.png",
            file_origin="/tmp/origin.png",
            current_sample="/tmp/current.png",
        )
        == "/tmp/sample.1_Fixed.png"
    )


def test_relics_module_builds_dummy_chunk_brawl_plan():
    route = relics.DummyChunkRoute(
        source="sample.0_Fixed.png",
        error="DummyChunk_Error_0:Filling with a dummy chunk",
        chunk_name="IHDR",
        tool_prefix="IHDR_Tool_",
        is_critical=True,
    )
    tools = relics.DummyChunkTools(
        fixed_data="fixed-data",
        dummy_data_length=13,
        bad_position=128,
        bad_start=128,
        bad_end=152,
        from_error="No NextChunk",
    )

    plan = relics.dummy_chunk_brawl_plan(route, tools, from_error="libpng")

    assert plan == relics.DummyChunkBrawlPlan(
        target_file="sample.0_Fixed.png",
        chunk="IHDR",
        chunk_length=13,
        data_offset=128,
        from_error="libpng",
    )


def test_relics_module_exposes_dummy_chunk_decline_action():
    critical_route = relics.DummyChunkRoute(
        source="sample.0_Fixed.png",
        error="DummyChunk_Error_0:Filling with a dummy chunk",
        chunk_name="IHDR",
        tool_prefix="IHDR_Tool_",
        is_critical=True,
    )
    ancillary_route = relics.DummyChunkRoute(
        source="sample.1_Fixed.png",
        error="DummyChunk_Error_1:Filling with a dummy chunk",
        chunk_name="tEXt",
        tool_prefix="tEXt_Tool_",
        is_critical=False,
    )

    assert relics.dummy_chunk_decline_action(critical_route) == "end"
    assert relics.dummy_chunk_decline_action(ancillary_route) == "todo_end"


def test_relics_module_routes_remembered_dummy_chunks():
    pandemonium = {
        "sample.0_Fixed.png": {
            "DummyChunk_Error_0:Filling with a dummy chunk": relics.build_tools(
                b"IHDR",
                ("fixed-data", 13, 128, 128, 152, "No NextChunk"),
            ),
            "Checksum_Error_0:Wrong Crc": relics.build_tools(
                b"IDAT",
                ("newcrc", 12, 20, b"IDAT", "0x2a", "oldcrc", 433, 100),
            ),
        },
        "sample.1_Fixed.png": {
            "DummyChunk_Error_1:Filling with a dummy chunk": relics.build_tools(
                b"tEXt",
                ("fixed-data", 4, 256, 256, 280, "No NextChunk"),
            ),
        },
    }

    routes = relics.remembered_dummy_chunk_routes(
        pandemonium,
        [b"IHDR", b"IDAT", b"IEND", b"tEXt"],
        [b"IHDR", b"PLTE", b"IDAT", b"IEND"],
    )

    assert routes == [
        relics.DummyChunkRoute(
            source="sample.0_Fixed.png",
            error="DummyChunk_Error_0:Filling with a dummy chunk",
            chunk_name="IHDR",
            tool_prefix="IHDR_Tool_",
            is_critical=True,
        ),
        relics.DummyChunkRoute(
            source="sample.1_Fixed.png",
            error="DummyChunk_Error_1:Filling with a dummy chunk",
            chunk_name="tEXt",
            tool_prefix="tEXt_Tool_",
            is_critical=False,
        ),
    ]


def test_pandorabox_add_keeps_legacy_error_numbering():
    reset_relic_state()

    first = chunklate.PandoraBox_Add("Checksum", "Wrong Crc", {"IDAT_Tool_0": "newcrc"})
    second = chunklate.PandoraBox_Add("Checksum", "Another Crc", {"IDAT_Tool_0": "other"})

    assert first == "Checksum_Error_0:Wrong Crc"
    assert second == "Checksum_Error_1:Another Crc"
    assert list(chunklate.PandoraBox) == [first, second]


def test_relics_records_checkpoint_registration_in_pandorabox():
    pandora_box = {}
    cornucopia = {}
    registration = checkpoint.finding_registration(
        error=True,
        fixed=False,
        function="Checksum",
        chunk=b"IDAT",
        info="Wrong Crc",
        toolkit=("newcrc", 12, 20),
    )

    key = relics.record_checkpoint_registration(pandora_box, cornucopia, registration)

    assert key == "Checksum_Error_0:Wrong Crc"
    assert pandora_box[key] == {
        "IDAT_Tool_0": "newcrc",
        "IDAT_Tool_1": 12,
        "IDAT_Tool_2": 20,
    }
    assert cornucopia == {}


def test_relics_records_checkpoint_registration_in_cornucopia():
    pandora_box = {}
    cornucopia = {}
    registration = checkpoint.finding_registration(
        error=True,
        fixed=True,
        function="UnitTest",
        chunk=b"PLTE",
        info="Fixed Data",
        toolkit=("fixed", "solution-key"),
    )

    key = relics.record_checkpoint_registration(pandora_box, cornucopia, registration)

    assert key == "solution-key"
    assert pandora_box == {}
    assert cornucopia == {
        "solution-key": {
            "PLTE_Tool_0": "fixed",
            "PLTE_Tool_1": "solution-key",
        }
    }


def test_relics_discards_pandora_error_by_key():
    pandora_box = {"error": {"IDAT_Tool_0": "newcrc"}}

    removed = relics.discard_pandora_error(pandora_box, "error")
    missing = relics.discard_pandora_error(pandora_box, "missing")

    assert removed == {"IDAT_Tool_0": "newcrc"}
    assert missing == "key_not_found"
    assert pandora_box == {}


def test_checkpoint_records_current_errors_in_pandorabox():
    reset_relic_state()

    chunklate.CheckPoint(
        True,
        False,
        "Checksum",
        b"IDAT",
        ["Wrong Crc"],
        "newcrc",
        12,
        20,
    )

    assert chunklate.Bad_Crc is True
    assert chunklate.SideNotes == ["Error:Wrong Crc"]
    assert chunklate.PandoraBox == {
        "Checksum_Error_0:Wrong Crc": {
            "IDAT_Tool_0": "newcrc",
            "IDAT_Tool_1": 12,
            "IDAT_Tool_2": 20,
        }
    }


def test_checkpoint_records_fixed_items_in_cornucopia():
    reset_relic_state()

    chunklate.CheckPoint(
        True,
        True,
        "UnitTest",
        b"PLTE",
        ["Fixed Data"],
        "fixed-bytes",
        4,
        8,
        "solution-key",
    )

    assert chunklate.PandoraBox == {}
    assert chunklate.SideNotes == ["Error Fixed:Fixed Data"]
    assert chunklate.Cornucopia == {
        "solution-key": {
            "PLTE_Tool_0": "fixed-bytes",
            "PLTE_Tool_1": 4,
            "PLTE_Tool_2": 8,
            "PLTE_Tool_3": "solution-key",
        }
    }


def test_pandemonium_snapshot_preserves_legacy_shared_reference():
    reset_relic_state()
    chunklate.PandoraBox_Add("Checksum", "Wrong Crc", {"IDAT_Tool_0": "newcrc"})
    chunklate.Cornucopia_Add("fixed-key", {"IDAT_Tool_0": "fixedcrc"})

    chunklate.Pandemonium_Remember_Current_Sample()

    assert chunklate.Pandemonium["sample.png"] is chunklate.PandoraBox
    assert chunklate.ArkOfCovenant["sample.png"] is chunklate.Cornucopia


def main():
    checks = [
        ("Relic tools keep legacy key names", test_relic_build_tools_uses_legacy_tool_names),
        ("Relics module uses explicit state objects", test_relics_module_uses_explicit_state_objects),
        (
            "Relics module finds chunk names in legacy text and tool keys",
            test_relics_module_finds_chunk_names_in_legacy_text_and_tool_keys,
        ),
        ("Relics module exposes wrong CRC tools by name", test_relics_module_exposes_wrong_crc_tools_by_name),
        (
            "Relics module exposes wrong chunk name tools by name",
            test_relics_module_exposes_wrong_chunk_name_tools_by_name,
        ),
        (
            "Relics module exposes no-next-chunk tools by name",
            test_relics_module_exposes_no_next_chunk_tools_by_name,
        ),
        ("Relics module exposes dummy chunk tools by name", test_relics_module_exposes_dummy_chunk_tools_by_name),
        ("Relics module routes current wrong CRC errors", test_relics_module_routes_current_wrong_crc_errors),
        ("Relics module routes remembered wrong CRC errors", test_relics_module_routes_remembered_wrong_crc_errors),
        ("Relics module filters IDAT wrong CRC routes", test_relics_module_filters_idat_wrong_crc_routes),
        ("Relics module summarises Pandemonium", test_relics_module_summarises_pandemonium_without_formatting),
        ("Relics module exposes PLTE choices", test_relics_module_exposes_plte_interactive_choices),
        ("Relics module builds IDAT wrong CRC brawl plan", test_relics_module_builds_idat_wrong_crc_brawl_plan),
        (
            "Relics module builds non-IDAT wrong CRC brawl plan",
            test_relics_module_builds_non_idat_wrong_crc_brawl_plan,
        ),
        ("Relics module resolves remembered sample target", test_relics_module_resolves_remembered_sample_target),
        ("Relics module builds dummy chunk brawl plan", test_relics_module_builds_dummy_chunk_brawl_plan),
        ("Relics module exposes dummy chunk decline action", test_relics_module_exposes_dummy_chunk_decline_action),
        ("Relics module routes remembered dummy chunks", test_relics_module_routes_remembered_dummy_chunks),
        ("PandoraBox keys keep legacy numbering", test_pandorabox_add_keeps_legacy_error_numbering),
        (
            "Relics records CheckPoint registration in PandoraBox",
            test_relics_records_checkpoint_registration_in_pandorabox,
        ),
        (
            "Relics records CheckPoint registration in Cornucopia",
            test_relics_records_checkpoint_registration_in_cornucopia,
        ),
        ("Relics discards PandoraBox errors by key", test_relics_discards_pandora_error_by_key),
        ("CheckPoint records current errors", test_checkpoint_records_current_errors_in_pandorabox),
        ("CheckPoint records fixed items", test_checkpoint_records_fixed_items_in_cornucopia),
        ("Pandemonium snapshot keeps legacy references", test_pandemonium_snapshot_preserves_legacy_shared_reference),
    ]

    print("Running Relics state tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"relics state tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
