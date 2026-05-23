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
    tools = relics.build_tools(b"IDAT", ("crc", 12, 20))

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


def test_relics_module_question_hash_preserves_tool_triplet_and_key_fallback():
    store = {
        "Checksum_Error_0:Wrong Crc": {
            "IDAT_Tool_0": "crc",
            "IDAT_Tool_1": 12,
            "IDAT_Tool_2": 20,
        }
    }

    assert relics.question_hash(store, "Checksum_Error_0:Wrong Crc", "IDAT_Tool_") == hash("crc1220")
    assert relics.question_hash(store, "missing", "IDAT_Tool_") == hash("missing")


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


def test_relics_module_preserves_pandemonium_policy_order():
    assert relics.pandemonium_policy_steps(0) == ()
    assert relics.pandemonium_policy_steps(1) == (
        relics.PandemoniumPolicyStep("current_wrong_crc"),
        relics.PandemoniumPolicyStep("remembered_idat_wrong_crc"),
        relics.PandemoniumPolicyStep("plte"),
        relics.PandemoniumPolicyStep("single_pandemonium"),
    )
    assert relics.pandemonium_policy_steps(2) == (
        relics.PandemoniumPolicyStep("current_wrong_crc"),
        relics.PandemoniumPolicyStep("remembered_idat_wrong_crc"),
        relics.PandemoniumPolicyStep("plte"),
        relics.PandemoniumPolicyStep("remembered_dummy_chunks"),
    )


def test_relics_module_builds_wrong_crc_save_clone_plan():
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

    assert relics.wrong_crc_save_clone_plan(tools) == relics.WrongCrcSaveClonePlan(
        fixed_data="newcrc",
        start=12,
        end=20,
        info=(
            "-Found Chunk[b'IDAT'] has Wrong Crc at offset: 0x2a\n"
            "-Replaced with: newcrc old value was: oldcrc"
        ),
    )


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


def test_relics_module_exposes_plte_interactive_prompts():
    assert relics.plte_repair_prompt(False) == "Answer(Manually/Remove/Quit):"
    assert relics.plte_repair_retry_prompt(False) is None
    assert relics.plte_repair_prompt(True) == "Answer(Manually/Bruteforce/Remove/Quit):"
    assert relics.plte_repair_retry_prompt(True) == "Answer(Manually/bruteforce/Remove/Quit):"


def test_relics_module_finds_plte_chunk_window():
    window = relics.plte_chunk_window(
        [b"IHDR", b"PLTE", b"IDAT"],
        ["0:8:21", "1:33:801", "2:801:900"],
    )

    assert window == relics.PlteChunkWindow(
        chunk=b"PLTE",
        data_offset=33,
        end_offset=801,
    )
    assert relics.plte_chunk_window([b"IHDR", b"IDAT"], ["0:8:21", "1:21:900"]) is None


def test_relics_module_builds_plte_manual_plan():
    window = relics.PlteChunkWindow(b"PLTE", 33, 801)

    assert relics.plte_manual_plan(window, target_file="sample.png") == (
        relics.PlteManualPlan(
            target_file="sample.png",
            chunk=b"PLTE",
            chunk_length=801,
            data_offset=33,
            from_error="-PLTE Wrong Data",
        )
    )


def test_relics_module_builds_plte_remove_plan():
    window = relics.PlteChunkWindow(b"PLTE", 33, 801)

    assert relics.plte_remove_plan(window) == relics.PlteRemovePlan(
        start=33,
        end=801,
        info="-PLTE Chunk Removed.",
    )


def test_relics_module_builds_plte_brawl_plan():
    window = relics.PlteChunkWindow(b"PLTE", 33, 801)

    assert relics.plte_brawl_plan(window, target_file="sample.png", old_crc="oldcrc") == (
        relics.PlteBrawlPlan(
            target_file="sample.png",
            chunk=b"PLTE",
            chunk_length=801,
            data_offset=33,
            from_error="-PLTE Wrong Data",
            edit_mode="Insert",
            old_crc="oldcrc",
        )
    )
    assert relics.plte_brawl_plan(window, target_file="sample.png").old_crc is None


def test_relics_module_selects_plte_repair_decisions():
    window = relics.PlteChunkWindow(b"PLTE", 33, 801)

    assert relics.plte_repair_decision(
        "manually",
        window,
        target_file="sample.png",
    ) == relics.PlteRepairDecision(
        "manual",
        relics.PlteManualPlan("sample.png", b"PLTE", 801, 33, "-PLTE Wrong Data"),
    )
    assert relics.plte_repair_decision(
        "remove",
        window,
        target_file="sample.png",
    ) == relics.PlteRepairDecision(
        "remove",
        relics.PlteRemovePlan(33, 801, "-PLTE Chunk Removed."),
    )
    assert relics.plte_repair_decision(
        "bruteforce",
        window,
        target_file="sample.png",
        old_crc="oldcrc",
    ) == relics.PlteRepairDecision(
        "brawl",
        relics.PlteBrawlPlan(
            "sample.png",
            b"PLTE",
            801,
            33,
            "-PLTE Wrong Data",
            "Insert",
            "oldcrc",
        ),
    )
    assert relics.plte_repair_decision(
        "quit",
        window,
        target_file="sample.png",
        quit_note="-User chose to quit.",
    ) == relics.PlteRepairDecision("quit", side_note="-User chose to quit.")
    assert relics.plte_repair_decision(
        "manually",
        None,
        target_file="sample.png",
    ) == relics.PlteRepairDecision("none")


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


def test_relics_module_selects_single_pandemonium_wrong_crc_decision():
    tools = relics.build_tools(
        b"IDAT",
        ("newcrc", 12, 20, b"IDAT", "0x2a", "oldcrc", 433, 100),
    )

    decision = relics.single_pandemonium_decision(
        0,
        "sample.0_Fixed.png",
        "Checksum_Error_0:Wrong Crc",
        tools,
        known_chunks=(b"IDAT", b"PLTE"),
        file_origin="/tmp/origin.png",
        current_sample="/tmp/current.png",
        from_error="libpng",
    )

    assert decision == relics.SinglePandemoniumDecision(
        "wrong_crc_brawl",
        route=relics.WrongCrcRoute(
            source="sample.0_Fixed.png",
            error="Checksum_Error_0:Wrong Crc",
            chunk_name="IDAT",
            tool_prefix="IDAT_Tool_",
        ),
        tools=relics.WrongCrcTools(
            replacement_crc="newcrc",
            start=12,
            end=20,
            chunk=b"IDAT",
            offset="0x2a",
            old_crc="oldcrc",
            chunk_length=433,
            data_offset=100,
        ),
        plan=relics.WrongCrcBrawlPlan(
            target_file="/tmp/origin.png",
            chunk=b"IDAT",
            chunk_length=433,
            data_offset=100,
            from_error="libpng",
            old_crc="oldcrc",
            bf_mode="TwoBytes",
        ),
    )


def test_relics_module_selects_single_pandemonium_remembered_target():
    tools = relics.build_tools(
        b"PLTE",
        ("newcrc", 12, 20, b"PLTE", "0x2a", "oldcrc", 768, 100),
    )

    decision = relics.single_pandemonium_decision(
        1,
        "sample.1_Fixed.png",
        "Checksum_Error_1:Wrong Crc",
        tools,
        known_chunks=(b"IDAT", b"PLTE"),
        file_origin="/tmp/origin.png",
        current_sample="/tmp/current.png",
        from_error="libpng",
    )

    assert decision.plan == relics.WrongCrcBrawlPlan(
        target_file="/tmp/sample.1_Fixed.png",
        chunk=b"PLTE",
        chunk_length=768,
        data_offset=100,
        from_error="libpng",
        old_crc="oldcrc",
        brute_length=False,
    )


def test_relics_module_selects_single_pandemonium_unsupported_decision():
    decision = relics.single_pandemonium_decision(
        0,
        "sample.0_Fixed.png",
        "Unsupported_Error",
        {},
        known_chunks=(b"IDAT", b"PLTE"),
        file_origin="/tmp/origin.png",
        current_sample="/tmp/current.png",
        from_error="libpng",
    )

    assert decision == relics.SinglePandemoniumDecision("unsupported")


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


def test_relics_module_selects_dummy_chunk_repair_decisions():
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
    tools = relics.DummyChunkTools(
        fixed_data="fixed-data",
        dummy_data_length=13,
        bad_position=128,
        bad_start=128,
        bad_end=152,
        from_error="No NextChunk",
    )

    assert relics.dummy_chunk_repair_decision(
        critical_route,
        tools,
        from_error="libpng",
        answer=True,
    ) == relics.DummyChunkRepairDecision(
        "brawl",
        relics.DummyChunkBrawlPlan("sample.0_Fixed.png", "IHDR", 13, 128, "libpng"),
    )
    assert relics.dummy_chunk_repair_decision(
        critical_route,
        tools,
        from_error="libpng",
        answer=False,
    ) == relics.DummyChunkRepairDecision("end")
    assert relics.dummy_chunk_repair_decision(
        ancillary_route,
        tools,
        from_error="libpng",
        answer=False,
    ) == relics.DummyChunkRepairDecision("todo_end")


def test_relics_module_finds_first_getinfo_critical_chunk():
    pandora_box = {
        "Checksum_Error_0:Wrong Crc b'IDAT'": {},
        "GetInfo_Error_0:IHDR StructIndex:0": {},
        "GetInfo_Error_1:IDAT StructIndex:1": {},
    }

    assert relics.first_getinfo_critical_chunk(pandora_box, [b"IHDR", b"IDAT"]) == "IHDR"
    assert relics.first_getinfo_critical_chunk({"Other_Error": {}}, [b"IHDR"]) is None


def test_relics_module_collects_getinfo_struct_index_errors():
    pandora_box = {
        "GetInfo_Error_0:IHDR StructIndex:0": {},
        "GetInfo_Error_1:IHDR StructIndex:1": {},
        "GetInfo_Error_2:IHDR Other": {},
        "GetInfo_Error_3:IDAT StructIndex:0": {},
    }

    assert relics.getinfo_struct_index_errors(pandora_box, "IHDR") == (
        "GetInfo_Error_0:IHDR StructIndex:0",
        "GetInfo_Error_1:IHDR StructIndex:1",
    )


def test_relics_module_selects_getinfo_brawl_mode():
    assert (
        relics.getinfo_brawl_mode(
            "IHDR",
            struct_index_error_count=1,
            chunks_len_not_fixed=[b"IHDR"],
        )
        == "Brutus"
    )
    assert (
        relics.getinfo_brawl_mode(
            "IDAT",
            struct_index_error_count=3,
            chunks_len_not_fixed=[b"IHDR"],
        )
        == "Brutus"
    )
    assert (
        relics.getinfo_brawl_mode(
            "IDAT",
            struct_index_error_count=1,
            chunks_len_not_fixed=[b"IHDR"],
        )
        == "Custom"
    )


def test_relics_module_builds_getinfo_brawl_plan():
    plan = relics.getinfo_brawl_plan(
        "IDAT",
        [b"IHDR", b"IDAT"],
        ["0:8:21", "1:33:277"],
        target_file="sample.png",
        from_error="GetInfo",
        chunks_len_not_fixed=[b"IHDR"],
        struct_index_error_count=1,
    )

    assert plan == relics.GetInfoBrawlPlan(
        target_file="sample.png",
        chunk="IDAT",
        chunk_length=277,
        data_offset=33,
        from_error="GetInfo",
        bf_mode="Custom",
    )
    assert (
        relics.getinfo_brawl_plan(
            "PLTE",
            [b"IHDR", b"IDAT"],
            ["0:8:21", "1:33:277"],
            target_file="sample.png",
            from_error="GetInfo",
            chunks_len_not_fixed=[b"IHDR"],
            struct_index_error_count=1,
        )
        is None
    )


def test_relics_module_finds_first_getinfo_known_chunk():
    pandora_box = {
        "Other_Error": {},
        "GetInfo_Error_0:tEXt missing info": {},
        "GetInfo_Error_1:IDAT missing info": {},
    }

    assert relics.first_getinfo_known_chunk(pandora_box, [b"IDAT", b"tEXt"]) == (
        relics.GetInfoChunkRoute(
            finding="GetInfo_Error_0:tEXt missing info",
            chunk_name="tEXt",
        )
    )
    assert relics.first_getinfo_known_chunk({"Other_Error": {}}, [b"IDAT"]) is None


def test_relics_module_selects_no_pandemonium_policy_for_getinfo_brawl():
    pandora_box = {
        "Checksum_Error_0:Wrong Crc b'IDAT'": {},
        "GetInfo_Error_0:IHDR StructIndex:0": {},
        "GetInfo_Error_1:IHDR StructIndex:1": {},
    }

    assert relics.no_pandemonium_policy(pandora_box, [b"IHDR", b"IDAT"], [b"IHDR", b"IDAT"]) == (
        relics.NoPandemoniumPolicy(
            action="getinfo_brawl",
            chunk_name="IHDR",
            struct_index_errors=(
                "GetInfo_Error_0:IHDR StructIndex:0",
                "GetInfo_Error_1:IHDR StructIndex:1",
            ),
        )
    )


def test_relics_module_selects_no_pandemonium_policy_for_full_chunk_forcer():
    pandora_box = {
        "Other_Error": {},
        "GetInfo_Error_0:tEXt missing info": {},
    }

    assert relics.no_pandemonium_policy(pandora_box, [b"IHDR", b"IDAT"], [b"IDAT", b"tEXt"]) == (
        relics.NoPandemoniumPolicy(
            action="full_chunk_forcer",
            known_chunk_route=relics.GetInfoChunkRoute(
                finding="GetInfo_Error_0:tEXt missing info",
                chunk_name="tEXt",
            ),
        )
    )
    assert relics.no_pandemonium_policy({"Other_Error": {}}, [b"IHDR"], [b"IDAT"]) == (
        relics.NoPandemoniumPolicy(action="unsupported")
    )


def test_relics_module_preserves_legacy_getinfo_print_hits():
    pandora_box = {
        "GetInfo_Error_0:IDAT missing info": {},
        "GetInfo_Error_1:IDAT other": {},
        "GetInfo_Error_2:IHDR other": {},
    }

    assert relics.getinfo_related_print_hits(
        pandora_box,
        "IDAT",
        "GetInfo_Error_0:IDAT missing info",
    ) == (
        "GetInfo_Error_0:IDAT missing info",
        "GetInfo_Error_0:IDAT missing info",
    )


def test_relics_module_builds_full_chunk_forcer_plan():
    plan = relics.full_chunk_forcer_plan(
        "IDAT",
        ["IHDR", "IDAT"],
        ["0:8:21", "1:33:277"],
        target_file="sample.png",
        from_error="GetInfo",
    )

    assert plan == relics.FullChunkForcerPlan(
        target_file="sample.png",
        chunk="IDAT",
        start=33,
        end=277,
        from_error="GetInfo",
    )
    assert (
        relics.full_chunk_forcer_plan(
            "PLTE",
            ["IHDR", "IDAT"],
            ["0:8:21", "1:33:277"],
            target_file="sample.png",
            from_error="GetInfo",
        )
        is None
    )


def test_relics_module_selects_no_pandemonium_repair_decisions():
    getinfo_policy = relics.NoPandemoniumPolicy(
        action="getinfo_brawl",
        chunk_name="IDAT",
        struct_index_errors=("StructIndex:0", "StructIndex:1", "StructIndex:2"),
    )
    forcer_policy = relics.NoPandemoniumPolicy(
        action="full_chunk_forcer",
        known_chunk_route=relics.GetInfoChunkRoute("GetInfo_Error_0:tEXt", "tEXt"),
    )

    assert relics.no_pandemonium_repair_decision(
        getinfo_policy,
        [b"IHDR", b"IDAT"],
        ["0:8:21", "1:33:277"],
        target_file="sample.png",
        from_error="GetInfo",
        chunks_len_not_fixed=[],
        answer=True,
    ) == relics.NoPandemoniumRepairDecision(
        "getinfo_brawl",
        relics.GetInfoBrawlPlan("sample.png", "IDAT", 277, 33, "GetInfo", "Brutus"),
    )
    assert relics.no_pandemonium_repair_decision(
        forcer_policy,
        ["IHDR", "tEXt"],
        ["0:8:21", "1:33:277"],
        target_file="sample.png",
        from_error="GetInfo",
        chunks_len_not_fixed=[],
        answer=True,
    ) == relics.NoPandemoniumRepairDecision(
        "full_chunk_forcer",
        relics.FullChunkForcerPlan("sample.png", "tEXt", 33, 277, "GetInfo"),
    )
    assert relics.no_pandemonium_repair_decision(
        getinfo_policy,
        [b"IHDR", b"IDAT"],
        ["0:8:21", "1:33:277"],
        target_file="sample.png",
        from_error="GetInfo",
        chunks_len_not_fixed=[],
        answer=False,
    ) == relics.NoPandemoniumRepairDecision("none")
    assert relics.no_pandemonium_repair_decision(
        relics.NoPandemoniumPolicy(action="unsupported"),
        [],
        [],
        target_file="sample.png",
        from_error="GetInfo",
        chunks_len_not_fixed=[],
        answer=True,
    ) == relics.NoPandemoniumRepairDecision("unsupported")


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
    pandora_box = {}

    first = relics.add_pandora_error(pandora_box, "Checksum", "Wrong Crc", {"IDAT_Tool_0": "newcrc"})
    second = relics.add_pandora_error(pandora_box, "Checksum", "Another Crc", {"IDAT_Tool_0": "other"})

    assert first == "Checksum_Error_0:Wrong Crc"
    assert second == "Checksum_Error_1:Another Crc"
    assert list(pandora_box) == [first, second]


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
    relics.add_pandora_error(chunklate.PandoraBox, "Checksum", "Wrong Crc", {"IDAT_Tool_0": "newcrc"})
    relics.add_cornucopia_fix(chunklate.Cornucopia, "fixed-key", {"IDAT_Tool_0": "fixedcrc"})

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
        (
            "Relics module question hash preserves triplet and fallback",
            test_relics_module_question_hash_preserves_tool_triplet_and_key_fallback,
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
        ("Relics module preserves Pandemonium policy order", test_relics_module_preserves_pandemonium_policy_order),
        ("Relics module builds wrong CRC SaveClone plan", test_relics_module_builds_wrong_crc_save_clone_plan),
        ("Relics module summarises Pandemonium", test_relics_module_summarises_pandemonium_without_formatting),
        ("Relics module exposes PLTE choices", test_relics_module_exposes_plte_interactive_choices),
        ("Relics module exposes PLTE prompts", test_relics_module_exposes_plte_interactive_prompts),
        ("Relics module finds PLTE chunk window", test_relics_module_finds_plte_chunk_window),
        ("Relics module builds PLTE manual plan", test_relics_module_builds_plte_manual_plan),
        ("Relics module builds PLTE remove plan", test_relics_module_builds_plte_remove_plan),
        ("Relics module builds PLTE brawl plan", test_relics_module_builds_plte_brawl_plan),
        ("Relics module selects PLTE repair decisions", test_relics_module_selects_plte_repair_decisions),
        ("Relics module builds IDAT wrong CRC brawl plan", test_relics_module_builds_idat_wrong_crc_brawl_plan),
        (
            "Relics module builds non-IDAT wrong CRC brawl plan",
            test_relics_module_builds_non_idat_wrong_crc_brawl_plan,
        ),
        (
            "Relics module selects single-Pandemonium wrong CRC decision",
            test_relics_module_selects_single_pandemonium_wrong_crc_decision,
        ),
        (
            "Relics module selects single-Pandemonium remembered target",
            test_relics_module_selects_single_pandemonium_remembered_target,
        ),
        (
            "Relics module selects single-Pandemonium unsupported decision",
            test_relics_module_selects_single_pandemonium_unsupported_decision,
        ),
        ("Relics module resolves remembered sample target", test_relics_module_resolves_remembered_sample_target),
        ("Relics module builds dummy chunk brawl plan", test_relics_module_builds_dummy_chunk_brawl_plan),
        ("Relics module exposes dummy chunk decline action", test_relics_module_exposes_dummy_chunk_decline_action),
        (
            "Relics module selects dummy chunk repair decisions",
            test_relics_module_selects_dummy_chunk_repair_decisions,
        ),
        ("Relics module finds first GetInfo critical chunk", test_relics_module_finds_first_getinfo_critical_chunk),
        ("Relics module collects GetInfo StructIndex errors", test_relics_module_collects_getinfo_struct_index_errors),
        ("Relics module selects GetInfo brawl mode", test_relics_module_selects_getinfo_brawl_mode),
        ("Relics module builds GetInfo brawl plan", test_relics_module_builds_getinfo_brawl_plan),
        ("Relics module finds first GetInfo known chunk", test_relics_module_finds_first_getinfo_known_chunk),
        ("Relics module selects no-Pandemonium GetInfo policy", test_relics_module_selects_no_pandemonium_policy_for_getinfo_brawl),
        ("Relics module selects no-Pandemonium full forcer policy", test_relics_module_selects_no_pandemonium_policy_for_full_chunk_forcer),
        (
            "Relics module preserves legacy GetInfo print hits",
            test_relics_module_preserves_legacy_getinfo_print_hits,
        ),
        ("Relics module builds FullChunkForcer plan", test_relics_module_builds_full_chunk_forcer_plan),
        (
            "Relics module selects no-Pandemonium repair decisions",
            test_relics_module_selects_no_pandemonium_repair_decisions,
        ),
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
