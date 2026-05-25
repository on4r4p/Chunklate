from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateCase:
    fixture: str
    source_path: str
    max_saves: int = 1
    known_python_traceback: bool = False


BROKEN_SUITE = "schaik-javapng-samples/brokenjavapngsuite"


CANDIDATE_CASES: tuple[CandidateCase, ...] = (
    CandidateCase("nonconsecutive_idat.png", f"{BROKEN_SUITE}/nonconsecutive_idat.png"),
    CandidateCase("missing_idat.png", f"{BROKEN_SUITE}/missing_idat.png"),
    CandidateCase("missing_plte.png", f"{BROKEN_SUITE}/missing_plte.png"),
    CandidateCase("plte_length_mod_three.png", f"{BROKEN_SUITE}/plte_length_mod_three.png"),
    CandidateCase("plte_too_many_entries.png", f"{BROKEN_SUITE}/plte_too_many_entries.png"),
    CandidateCase(
        "gama_after_idat.png",
        f"{BROKEN_SUITE}/gama_after_idat.png",
        known_python_traceback=True,
    ),
    CandidateCase(
        "plte_after_idat.png",
        f"{BROKEN_SUITE}/plte_after_idat.png",
        known_python_traceback=True,
    ),
    CandidateCase("multiple_ihdr.png", f"{BROKEN_SUITE}/multiple_ihdr.png"),
    CandidateCase("length_ihdr.png", f"{BROKEN_SUITE}/length_ihdr.png"),
    CandidateCase("truncate_idat_0.png", f"{BROKEN_SUITE}/truncate_idat_0.png"),
)
