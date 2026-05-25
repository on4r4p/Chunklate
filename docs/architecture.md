# Chunklate Architecture

This document gives a practical map of the project. `Chunklate.py` remains the
command entry point, while the `chunklate/` package contains the parsing,
validation, repair, output, and UI helpers used by that command.

## Main Workflow

Chunklate follows this high-level flow:

1. Parse CLI options and initialize the run.
2. Read the target file and locate or rebuild the PNG signature when possible.
3. Walk through PNG chunks and collect structure, CRC, length, and payload data.
4. Report chunk information and validate chunk-specific expectations.
5. Record findings through the checkpoint system.
6. Pick a repair route when one is available.
7. Write repaired clones to `Folder_*` output directories.
8. Print a summary of the actions taken.

## Entry Point

`Chunklate.py`
: CLI entry point and orchestration layer. It keeps the public function names
  used by the tool, wires runtime callbacks together, and coordinates the full
  scan/repair flow.

`chunklate/main_runtime.py`
: Helpers for CLI option handling, per-file setup, state reset, and chunk
  walking.

`chunklate/cli.py`
: CLI parser defaults and option helpers.

## PNG Model And Parsing

`chunklate/png.py`
: Low-level PNG helpers: signature handling, chunk reading, CRC checks, byte
  ranges, and chunk rebuild helpers.

`chunklate/chunk_info.py`
: Payload parsers for chunks such as `IHDR`, `gAMA`, `pHYs`, `tIME`, `PLTE`,
  text chunks, and related metadata.

`chunklate/chunk_state.py`
: Runtime state for information discovered while walking chunks, including
  image dimensions, color mode, IDAT counters, palette data, and text chunks.

`chunklate/chunk_state_runtime.py`
: Synchronization helpers between the run state and the public variables used
  by the command layer.

`chunklate/chunk_report.py`
: Formatting for chunk reports. It receives an output callback, so tests can
  verify reports without printing to the terminal.

`chunklate/specs.py`
: Chunk specification data used by validation and bruteforce generation:
  allowed values, ranges, color type combinations, and candidate inputs.

`chunklate/spec_length_runtime.py`
: Runtime wrapper for expected chunk length checks.

## Validation And Decisions

`chunklate/youshallpass_runtime.py`
: Dispatch for chunk payload validation.

`chunklate/chunk_validation_runtime.py`
: Runtime helpers for length and checksum validation.

`chunklate/chunk_order.py`
: Pure helpers for PNG chunk ordering constraints.

`chunklate/chunk_order_runtime.py`
: Runtime orchestration for chunk order checks and chunk repositioning.

`chunklate/checkpoint.py`
: Finding registration and checkpoint action decisions.

`chunklate/checkpoint_runtime.py`
: Checkpoint entry flow, debug output, and action routing.

`chunklate/checkpoint_actions_runtime.py`
: Action handlers triggered by checkpoint decisions.

`chunklate/decisions.py`
: Small decision objects and helpers shared by repair runtimes.

`chunklate/chunk_story.py`
: Human-readable explanations attached to chunk findings.

## Repair Paths

`chunklate/fixit_felix.py`
: Automatic repair planning helpers.

`chunklate/fixit_felix_runtime.py`
: Runtime wiring for automatic repair attempts and their side effects.

`chunklate/dummy_chunk.py`
: Decisions around creating replacement chunks such as `IHDR`, `IEND`, or
  fallback `IDAT` data.

`chunklate/dummy_chunk_runtime.py`
: Runtime wrapper for dummy chunk decisions.

`chunklate/idat.py`
: IDAT stream analysis and the `partial-idat-blackfill` salvage path for
  non-interlaced PNGs.

`chunklate/bruteforce.py`
: Candidate generation, byte edit modes, scan windows, ETA helpers, and
  `TwoBytes` dispatch for data bruteforce.

`chunklate/bruteforce_runtime.py`
: Scan execution helpers used by the bruteforce command path.

`chunklate/bruteforce_viewer.py`
: Optional preview flow while scanning candidates.

`chunklate/bruteforce_result.py`
: Result handling after bruteforce attempts.

`chunklate/smash_bruteforce.py`
: Runtime bridge for the `SmashBruteBrawl` command path.

`chunklate/full_chunk_forcer.py`
: Runtime support for full chunk brute force without relying on CRC first.

`chunklate/nearby.py` and `chunklate/nearby_runtime.py`
: Nearby chunk search, extra-byte removal, and related repair routing.

`chunklate/name_shift.py` and `chunklate/name_shift_runtime.py`
: Detection and repair of shifted chunk names caused by missing or extra bytes.

`chunklate/chunk_name_runtime.py`
: Runtime dispatch for chunk name validation, name guessing, prompt fallback,
  and automatic name replacement.

`chunklate/chunk_scanner.py` and `chunklate/magic_runtime.py`
: PNG signature search and hard magic byte recovery flow.

`chunklate/relics.py`, `chunklate/relics_runtime.py`, `chunklate/relics_ui.py`
: Repair-history analysis, route selection, and related user-facing choices.

## Palette Tools

`chunklate/palette.py`
: Palette byte helpers for building `PLTE` chunks and palette PNG candidates.

`chunklate/palette_ui.py`
: Tkinter-facing palette editor widgets and non-UI palette editor state.

`chunklate/palette_runtime.py`
: Palette count guessing, manual palette session setup, save handling, preview
  updates, randomization, and editor wiring.

## Output, Prompts, And Utilities

`chunklate/writer.py` and `chunklate/writer_runtime.py`
: Clone writing, output directory handling, save counting, `--output-dir`, and
  `--max-saves`.

`chunklate/output.py`
: Summary formatting and clone target naming helpers.

`chunklate/error_log.py`
: Error log formatting and append helpers.

`chunklate/ui.py`, `chunklate/ui_runtime.py`, `chunklate/stdio.py`
: Terminal output helpers, loading bars, and standard IO wrappers.

`chunklate/prompts.py` and `chunklate/question_runtime.py`
: Interactive prompts, automatic answers, and deterministic prompt handling for
  tests.

`chunklate/history.py`, `chunklate/sorting.py`, `chunklate/ancillary.py`,
`chunklate/ancillary_runtime.py`, `chunklate/libpng_check.py`,
`chunklate/libpng_runtime.py`
: Focused helpers for history snapshots, natural sorting, ancillary chunk
  metadata, and libpng output handling.

## IDAT Salvage

`partial-idat-blackfill` is an explicit salvage repair. When a non-interlaced
PNG has a partially readable IDAT zlib stream, Chunklate can keep complete
scanlines recovered before the zlib failure, fill the remaining scanlines with
black or transparent bytes, recompress a new IDAT stream, and rebuild a valid
PNG. It is a salvage image, not a reconstruction of unknown image content.

Current limits:

- Adam7/interlaced PNGs are not handled by this path.
- Partial scanlines are discarded.
- Missing image content is filled, not guessed.

## Tests

Run the full local validation:

```sh
./scripts/check.sh
```

Run the repair regression suite:

```sh
.venv/bin/python -m pytest tests/test_repairs.py
```

The tests use temporary output directories for generated files. Fixtures for
repair behavior live in `Png_Errors_handled_by_Chunklate_So_Far/`.
