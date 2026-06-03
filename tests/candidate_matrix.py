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
        CANDIDATE_FOR_STRICT_REPAIR,
        (
            "Found Next Chunk[b'heRB'] has Wrong Chunk name",
            "moved IDAT-interrupting ancillary chunk(s) after final IDAT: heRB",
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
        ALREADY_STRICT_ELSEWHERE,
        ("PLTE Total palettes number must be divisible by 3",),
    ),
    CandidateCase(
        "plte_too_many_entries.png",
        f"{BROKEN_SUITE}/plte_too_many_entries.png",
        ALREADY_STRICT_ELSEWHERE,
        ("PLTE Wrong RED 1 palettes not in bitdepht range",),
    ),
    CandidateCase(
        "plte_too_many_entries_2.png",
        f"{BROKEN_SUITE}/plte_too_many_entries_2.png",
        CANDIDATE_FOR_STRICT_REPAIR,
        ("Error PLTER > 256",),
    ),
    CandidateCase(
        "gama_after_idat.png",
        f"{BROKEN_SUITE}/gama_after_idat.png",
        NEEDS_REPAIR_STRATEGY,
        (
            "Error:-Missplaced",
            "Error:-No NextChunk",
            "-Reached the end of file.",
        ),
    ),
    CandidateCase(
        "plte_after_idat.png",
        f"{BROKEN_SUITE}/plte_after_idat.png",
        NEEDS_REPAIR_STRATEGY,
        (
            "Error:-Missplaced",
            "Error:-No NextChunk",
            "-Reached the end of file.",
        ),
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
        "private_compression_method.png",
        f"{BROKEN_SUITE}/private_compression_method.png",
        CANDIDATE_FOR_STRICT_REPAIR,
        (
            "IHDR Compression Algorithms",
            "converted private bzip2 compression method to standard zlib IDAT",
        ),
    ),
    CandidateCase(
        "private_filter_type.png",
        f"{BROKEN_SUITE}/private_filter_type.png",
        CANDIDATE_FOR_STRICT_REPAIR,
        (
            "bad adaptive filter value",
            "idat-filter0-normalize replaced 1 invalid scanline filter bytes",
        ),
    ),
    CandidateCase(
        "sbit_sample_depth.png",
        f"{BROKEN_SUITE}/sbit_sample_depth.png",
        CANDIDATE_FOR_STRICT_REPAIR,
        (
            "sBit red value",
            "normalized sBIT sample depths from ff0505 to 080505",
        ),
    ),
    CandidateCase(
        "truncate_idat_0.png",
        f"{BROKEN_SUITE}/truncate_idat_0.png",
        UNSUPPORTED,
    ),
)
