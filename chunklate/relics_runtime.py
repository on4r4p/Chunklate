from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


AskChoice = Callable[[str, Sequence[str], str], Any]
LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class RelicsRuntime:
    save_clone: LegacyCall
    smash_brute_brawl: LegacyCall
    full_chunk_forcer_no_crc: LegacyCall
    tk_manual_plte: LegacyCall
    remove_chunk: LegacyCall
    ask_choice: AskChoice
