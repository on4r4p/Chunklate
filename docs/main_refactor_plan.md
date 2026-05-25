# Main Refactor Plan

Current checkpoint after the small-wrapper extraction:

- Branch: `ctf`
- Last checked commit: `5b82322`
- `Chunklate.py`: 2613 lines
- Safety net: `./scripts/check.sh` reports `768 passed`

Largest remaining functions in `Chunklate.py`:

| Lines | Function |
| ---: | --- |
| 178 | `main` |
| 115 | `Tk_Manual_Plte` |
| 44 | `WriteClone` |
| 41 | `Ancillary` |
| 38 | `NearbyChunk` |
| 36 | `CheckChunkOrder` |
| 33 | `GetSpec` |
| 33 | `FullChunkForcerNoCrc` |
| 31 | `FixItFelix_No_NextChunk_Runtime` |
| 30 | `Tk_Save_Plte` |

## Why `main` Needs Its Own Plan

`main` is not just startup glue. It currently mixes:

- CLI option effects;
- global runtime resets;
- input file normalization;
- PNG signature recovery setup;
- per-file loop orchestration;
- chunk walking;
- libpng/checkpoint routing;
- final summary and exit behavior.

This makes it riskier than the recent wrapper extractions. The next pass should
split `main` by phase while keeping the same legacy globals and messages.

## Proposed Packages

1. Extract CLI option application into `chunklate/main_runtime.py`.
   Keep `ParseArg()` unchanged. Move the side-effect mapping from parsed options
   to runtime flags behind a tested helper.

2. Extract per-run global reset.
   Move the repeated reset/default values into one runtime helper that receives a
   mutable namespace. Tests should assert selected globals, not every historical
   variable at once.

3. Extract file loading and signature recovery setup.
   Keep repair behavior unchanged: only move the code that reads the file,
   prepares `DATAX`, sets `FILE_Origin`, `FILE_DIR`, `Sample_Name`, and applies
   existing PNG signature recovery decisions.

4. Extract the chunk-walk loop.
   Create a runtime helper that receives callbacks for `GetInfo`, `Checksum`,
   `CheckLength`, `CheckChunkName`, `CheckChunkOrder`, and `LibpngCheck`.
   Do not move those callbacks again in the same package.

5. Extract finalization.
   Move summary/footer/end behavior into a helper using the existing `Summarise`,
   `TheEnd`, `Candy`, and `PRINT` callbacks.

## Guardrails

- Keep `Chunklate.main(...)` as the public entry point.
- Keep all legacy names and global variables visible from `Chunklate.py`.
- Do not change prompt text, report text, clone names, or default output paths.
- Tests must use fake callbacks and `tmp_path`; no root output.
- Run `./scripts/check.sh` after each package.
