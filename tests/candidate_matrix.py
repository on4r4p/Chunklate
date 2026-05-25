from __future__ import annotations

from dataclasses import dataclass


UNSUPPORTED = "unsupported"
NEEDS_REPAIR_STRATEGY = "needs repair strategy"
CANDIDATE_FOR_STRICT_REPAIR = "candidate for strict repair"
ALREADY_STRICT_ELSEWHERE = "already strict elsewhere"

ALLOWED_CANDIDATE_STATUSES = {
    UNSUPPORTED,
    NEEDS_REPAIR_STRATEGY,
    CANDIDATE_FOR_STRICT_REPAIR,
    ALREADY_STRICT_ELSEWHERE,
}


@dataclass(frozen=True)
class CandidateCase:
    fixture: str
    source_path: str
    status: str
    diagnostic_markers: tuple[str, ...] = ()
    max_saves: int = 1
    known_python_traceback: bool = False


BROKEN_SUITE = "schaik-javapng-samples/brokenjavapngsuite"


CANDIDATE_CASES: tuple[CandidateCase, ...] = (
    CandidateCase(
        "nonconsecutive_idat.png",
        f"{BROKEN_SUITE}/nonconsecutive_idat.png",
        NEEDS_REPAIR_STRATEGY,
        (
            "Found Next Chunk[b'heRB'] has Wrong Chunk name",
            "Critical Chunk b'IEND' is Missing",
        ),
    ),
    CandidateCase(
        "missing_idat.png",
        f"{BROKEN_SUITE}/missing_idat.png",
        UNSUPPORTED,
        ("Critical Chunk b'IDAT' is Missing",),
    ),
    CandidateCase(
        "missing_plte.png",
        f"{BROKEN_SUITE}/missing_plte.png",
        CANDIDATE_FOR_STRICT_REPAIR,
    ),
    CandidateCase(
        "plte_length_mod_three.png",
        f"{BROKEN_SUITE}/plte_length_mod_three.png",
        CANDIDATE_FOR_STRICT_REPAIR,
        ("PLTE Total palettes number must be divisible by 3",),
    ),
    CandidateCase(
        "plte_too_many_entries.png",
        f"{BROKEN_SUITE}/plte_too_many_entries.png",
        CANDIDATE_FOR_STRICT_REPAIR,
        ("PLTE Wrong RED 1 palettes not in bitdepht range",),
    ),
    CandidateCase(
        "gama_after_idat.png",
        f"{BROKEN_SUITE}/gama_after_idat.png",
        NEEDS_REPAIR_STRATEGY,
        ("IndexError: list index out of range",),
        known_python_traceback=True,
    ),
    CandidateCase(
        "plte_after_idat.png",
        f"{BROKEN_SUITE}/plte_after_idat.png",
        NEEDS_REPAIR_STRATEGY,
        ("IndexError: list index out of range",),
        known_python_traceback=True,
    ),
    CandidateCase(
        "multiple_ihdr.png",
        f"{BROKEN_SUITE}/multiple_ihdr.png",
        NEEDS_REPAIR_STRATEGY,
        ("Error:-Multiple",),
    ),
    CandidateCase(
        "length_ihdr.png",
        f"{BROKEN_SUITE}/length_ihdr.png",
        CANDIDATE_FOR_STRICT_REPAIR,
        ("IHDR size have to always be 13 bytes",),
    ),
    CandidateCase(
        "truncate_idat_0.png",
        f"{BROKEN_SUITE}/truncate_idat_0.png",
        UNSUPPORTED,
    ),
)
