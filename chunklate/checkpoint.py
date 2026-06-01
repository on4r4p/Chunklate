from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Literal

from . import relics


CheckpointStore = Literal["pandora_box", "cornucopia"]


@dataclass(frozen=True)
class CheckPointRegistration:
    should_record: bool
    store: CheckpointStore | None
    function: Any
    info: Any
    tools: Mapping[str, Any]
    store_key: Any = None
    side_note: str | None = None


@dataclass(frozen=True)
class CheckPointActionDecision:
    action: str | None = None
    side_note: str | None = None
    flags: Mapping[str, Any] | None = None
    summary: str | None = None
    return_value: Any = None


def finding_registration(
    *,
    error: bool,
    fixed: bool,
    function: Any,
    chunk: Any,
    info: Any,
    toolkit: tuple[Any, ...],
) -> CheckPointRegistration:
    if error is not True:
        return CheckPointRegistration(False, None, function, info, {})

    tools = relics.build_tools(relics.chunk_label(chunk), toolkit)
    if fixed is False:
        return CheckPointRegistration(
            should_record=True,
            store="pandora_box",
            function=function,
            info=info,
            tools=tools,
            side_note="Error:" + str(info),
        )

    return CheckPointRegistration(
        should_record=True,
        store="cornucopia",
        function=function,
        info=info,
        tools=tools,
        store_key=toolkit[-1],
        side_note="Error Fixed:" + str(info),
    )


def action_decision(
    *,
    error: bool,
    function: Any,
    chunk: Any,
    info: Any,
    toolkit: tuple[Any, ...],
    brute_level: int = 0,
    libpng_errors: Iterable[str] = (),
    libpng_finished_at_iend: bool = False,
) -> CheckPointActionDecision:
    if function == "TheGoodPlace":
        if "Found Missing Data" in info:
            return CheckPointActionDecision(action="write_clone")
        if "Missing Data Has Not Been Found" in info:
            return CheckPointActionDecision(action="dummy_chunk_from_the_good_place")

    if function == "DummyChunk":
        flags = {"Bad_Critical": False} if chunk == b"IEND" else None
        if "Filling with a dummy chunk" in info:
            return CheckPointActionDecision(action="write_clone", flags=flags)
        if flags is not None:
            return CheckPointActionDecision(flags=flags)

    if function == "Tk_Save_Plte":
        if "-PLTE Data has been replaced manually." in info:
            return CheckPointActionDecision(
                action="write_clone",
                side_note="-CheckPoint: %s" % info,
            )
        if "-Manually modify PLTE datas has been canceled by user." in info:
            return CheckPointActionDecision(side_note="-CheckPoint: %s" % info)

    if function == "FindMagic":
        if info == "-Found Magic":
            return CheckPointActionDecision(
                action="return_value",
                side_note="-CheckPoint: Returning next position based on Magic Offset %s" % toolkit[0],
                return_value=toolkit[0],
            )
        if info in ("-Cutting at Magic", "Cutting at Magic"):
            return CheckPointActionDecision(
                action="summarise_and_write_clone",
                summary=(
                    "-File does not start with a png signature.\n"
                    "-Found a png signature at offset: %s\n"
                    "-Creating starting with the right signature."
                    % toolkit[1]
                ),
            )
        if info == "-dig a little bit deeper":
            return CheckPointActionDecision(
                action="find_fucking_magic",
                side_note="-CheckPoint: Finding Harder Magic Header",
            )

    if function == "FindFuckingMagic":
        if info == "-Cutting at Magic":
            return CheckPointActionDecision(
                action="summarise_and_write_clone",
                summary=(
                    "-File does not start with a png signature.\n"
                    "-Found a png signature at offset: %s\n"
                    "-Creating starting with the right signature."
                    % toolkit[1]
                ),
            )
        if info == "-Prepending Magic":
            return CheckPointActionDecision(
                action="summarise_and_write_clone",
                summary=(
                    "-File does not start with a png signature.\n"
                    "-Did prepending a png signature at offset: %s\n"
                    "-Creating starting with the right signature."
                    % toolkit[1]
                ),
            )

    if function == "CheckLength":
        if info == "-Found NextChunk":
            return CheckPointActionDecision(
                action="check_chunk_name",
                side_note=(
                    "-CheckPoint:From Chunk [%s] Found NextChunk at length previously indicated for checking [%s]."
                    % (chunk, toolkit[0])
                ),
            )
        return CheckPointActionDecision(flags={"Bad_No_Next_Chunk": error})

    if function == "NearbyChunk":
        return CheckPointActionDecision(action="save_clone")

    if function == "CheckChunkOrder":
        flags = {}
        if chunk == "Critical":
            flags["Bad_Critical"] = error
        if "missplaced" in str(info).lower():
            flags["Bad_Missplaced"] = error
        if flags:
            return CheckPointActionDecision(flags=flags)

    if function == "Checksum" and "Wrong Crc" in info:
        return CheckPointActionDecision(flags={"Bad_Crc": error})

    if function == "LibpngCheck":
        return libpng_check_decision(
            error=error,
            info=info,
            known_errors=libpng_errors,
            finished_at_iend=libpng_finished_at_iend,
        )

    if function == "CheckChunkName":
        return check_chunk_name_decision(
            error=error,
            function=function,
            info=info,
            toolkit=toolkit,
        )

    if function == "SmashBruteBrawl":
        bf_mode = None
        if "-Bruteforcer has Failed" in info and len(toolkit) > 5:
            bf_mode = toolkit[5]
        return smash_brute_brawl_decision(
            info=info,
            chunk=chunk,
            brute_level=brute_level,
            bf_mode=bf_mode,
        )

    return CheckPointActionDecision()


def libpng_check_decision(
    *,
    error: bool,
    info: Any,
    known_errors: Iterable[str] = (),
    finished_at_iend: bool = False,
) -> CheckPointActionDecision:
    if "libpng error:" in info:
        return CheckPointActionDecision(
            action="fix_it_felix_continue",
            flags={"Bad_Libpng": error},
            return_value="LibpngCheck",
        )

    if "libpng warning:" in info:
        actionable_warnings = (
            "known incorrect sRGB profile",
            "hIST: out of place",
            "pCAL: out of place",
        )
        if any(warning in info for warning in actionable_warnings):
            return CheckPointActionDecision(
                action="fix_it_felix_return",
                flags={"Bad_Libpng": error},
                return_value="LibpngCheck",
            )

        if any(known_error in info for known_error in known_errors):
            return CheckPointActionDecision(action="libpng_warning_relics")

        if finished_at_iend:
            return CheckPointActionDecision(action="discard_libpng_warning_and_end")

        return CheckPointActionDecision(action="discard_libpng_warning")

    if error:
        return CheckPointActionDecision(flags={"Bad_Libpng": error})

    return CheckPointActionDecision(action="libpng_end_success")


def check_chunk_name_decision(
    *,
    error: bool,
    function: Any,
    info: Any,
    toolkit: tuple[Any, ...],
) -> CheckPointActionDecision:
    if "turning it into a valid Chunk name" in info:
        return CheckPointActionDecision(
            action="fix_it_felix_continue",
            side_note="-%s: %s" % (function, info),
            return_value=toolkit[3],
        )

    if "Wrong Ancillary in known Chunk name at offset" in info:
        if toolkit[5] is not None:
            return CheckPointActionDecision(flags={"Bad_Next_Ancillary": error})
        return CheckPointActionDecision(flags={"Bad_Ancillary": error})

    if "has Wrong Chunk name at offset:" in info:
        return CheckPointActionDecision(flags={"Bad_Current_Name": error})

    if "has Wrong Chunk name after Chunk[" in info:
        return CheckPointActionDecision(flags={"Bad_Next_Name": error})

    if "corrupted due to some missing bytes." in info:
        return CheckPointActionDecision(action="save_clone_missing_bytes")

    return CheckPointActionDecision()


def smash_brute_brawl_decision(
    *,
    info: Any,
    chunk: Any = None,
    brute_level: int = 0,
    bf_mode: Any = None,
) -> CheckPointActionDecision:
    if "Corrupted Data has been replaced" in info:
        return CheckPointActionDecision(
            action="write_clone",
            side_note="-CheckPoint: %s" % info,
        )

    if "Previous Crc checksum" in info:
        return CheckPointActionDecision(
            action="save_clone",
            side_note="-CheckPoint: %s" % info,
        )

    return smash_brute_brawl_failure_decision(
        info=info,
        chunk=chunk,
        brute_level=brute_level,
        bf_mode=bf_mode,
    )


def smash_brute_brawl_failure_decision(
    *,
    info: Any,
    chunk: Any,
    brute_level: int,
    bf_mode: Any,
) -> CheckPointActionDecision:
    if "-Bruteforcer has Failed" not in info:
        return CheckPointActionDecision("smash_brute_brawl_end_unhandled")

    if brute_level < 3 and chunk == "IHDR":
        return CheckPointActionDecision("smash_brute_brawl_retry_ihdr_harder")

    if brute_level < 1 and bf_mode == "TwoBytes":
        return CheckPointActionDecision("smash_brute_brawl_ask_twobytes_retry")

    if bf_mode != "Custom":
        return CheckPointActionDecision("smash_brute_brawl_end_failed_noncustom")

    return CheckPointActionDecision("smash_brute_brawl_ask_custom_brutus")
