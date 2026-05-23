# Chunklate Architecture

This document maps the current refactor. The goal is not to hide the legacy
script: `Chunklate.py` is still the entry point and orchestration layer. The new
modules isolate behavior that can be tested without running the whole CLI.

## Main Flow

`Chunklate.py` still owns the legacy runtime:

1. parse CLI options;
2. read the input PNG;
3. walk chunks;
4. update legacy globals;
5. call repair decisions;
6. write repair clones;
7. print the old interactive output.

The modules under `chunklate/` are helpers extracted from that flow. Most of
them are pure or close to pure; when a module still needs legacy behavior,
`Chunklate.py` keeps a wrapper around it.

## Module Map

`chunklate/png.py`
: PNG parser and byte helpers. This is the low-level chunk reader: signature,
chunk lengths, chunk names, CRC, structure checks, and helpers to rebuild PNG
chunks.

`chunklate/specs.py`
: Chunk specification helpers used by bruteforce and validation. This now owns
the old `GetSpec` data expansion: chunk fields, allowed values, ranges, color
type rules, and candidate generation inputs.

`chunklate/bruteforce.py`
: Pure helpers extracted from `SmashBruteBrawl`: mode resolution, candidate
bytes, edit windows, `TwoBytes` dispatch, candidate validation, CRASH resume,
and ETA math. `Chunklate.py` still owns the heavy loop, display, clone writing,
and checkpoint side effects.

`chunklate/chunk_info.py`
: Parsers for chunk payloads. It turns raw chunk data into structured values for
chunks such as `IHDR`, `gAMA`, `pHYs`, text chunks, `PLTE`, and others.

`chunklate/chunk_state.py`
: Bridge between parsed chunk info and the old globals. `ChunkInfoState` stores
the current IHDR/IDAT/PLTE/text state so `Chunklate.py` can keep legacy names
while the parsing logic becomes testable.

`chunklate/chunk_report.py`
: Output formatting for chunk information. It replaces direct report printing
inside `GetInfo` with functions that receive an `emit` callback.

`chunklate/chunk_order.py`
: PNG chunk ordering checks extracted from the legacy `CheckChunkOrder` logic.

`Chunklate.YouShallPass(...)`
: Validation dispatch for chunk payload rules. This function still lives in
`Chunklate.py`, but it now relies heavily on parser helpers from
`chunklate/chunk_info.py` and state synchronized through
`chunklate/chunk_state.py`.

`chunklate/checkpoint.py`
: Checkpoint state and decisions around what action should happen after a
detected problem. `Chunklate.py` still applies the resulting legacy side
effects.

`chunklate/decisions.py`
: Small decision helpers used where legacy code previously mixed boolean flags
and action names inline.

`chunklate/fixit_felix.py`
: Automatic repair planning and dispatch helpers. The module decides what
repair path should be attempted; `Chunklate.py` still performs legacy writes,
pauses, summaries, and UI side effects.

`chunklate/dummy_chunk.py`
: Decisions around missing or dummy chunks such as `IHDR`, `IEND`, and `IDAT`.
IDAT-specific salvage delegates to `chunklate/idat.py`.

`chunklate/idat.py`
: IDAT analysis and the explicit `partial-idat-blackfill` fallback. It can keep
complete recovered scanlines, fill the rest with black or transparent bytes,
recompress a new IDAT stream, and produce a valid salvage PNG for non-interlaced
cases.

`chunklate/relics.py`
: Extracted policy around `Relics`, `Pandemonium`, `PandoraBox`, and related
repair history. This is still a sensitive area because it controls how old
errors and previous fixes influence later decisions.

`chunklate/writer.py`
: Clone output writer. It handles output directories, `Folder_*` paths,
`--output-dir`, save counting, and `--max-saves`.

`chunklate/output.py`, `chunklate/stdio.py`, `chunklate/ui.py`
: Console output, standard IO wrappers, and terminal/UI formatting helpers.
They keep presentation concerns away from repair logic.

`chunklate/prompts.py`
: Testable interactive choices, including the legacy `WHO'S THAT POKEMON !?`
fallback path.

`chunklate/palette.py`, `chunklate/palette_ui.py`
: Palette logic and Tkinter-facing palette UI split apart. The UI path is kept
for interactive use; tests can exercise the non-UI pieces directly.

`chunklate/error_log.py`, `chunklate/history.py`, `chunklate/sorting.py`,
`chunklate/chunk_story.py`
: Small helpers for logging, history, sorting, and human-readable chunk stories.


## Testing Contract

The current safety net is:

```sh
./scripts/check.sh
```

The repair regression suite is especially important:

```sh
.venv/bin/python -m pytest tests/test_repairs.py
```

Tests must write only to temporary directories. Repair fixtures stay under
`Png_Errors_handled_by_Chunklate_So_Far/`, and generated clone outputs must not
land in the repository root.

## Refactor Rule

Prefer this shape for each legacy extraction:

1. add a pure helper in `chunklate/`;
2. add focused tests for the helper;
3. replace the matching block in `Chunklate.py` with a wrapper call;
4. run `./scripts/check.sh`;
5. commit the small behavior-preserving step.

Feature changes should be explicit and named in tests. Everything else should
preserve legacy behavior until a fixture proves the new behavior is intended.
