![Chunklate demo](https://github.com/on4r4p/Chunklate/blob/ctf/Chunklate.gif)

# Chunklate

Chunklate is a work-in-progress PNG repair tool. It inspects broken PNG files,
tries known repair routes, saves each candidate in a `Folder_*` output folder,
and writes a readable summary of what happened.

It is useful for CTF-style PNG damage, partial image salvage, and guided brute
force searches. It is not magic: when image data is missing or the file is
structurally valid but visually wrong, Chunklate needs a strong checksum,
reference image, ROI, or user validation to know what the original image should
look like.

## Quick Start

Install the runtime dependencies:

```bash
./scripts/bootstrap_dev.sh
. .venv/bin/activate
```

On Windows:

```powershell
py scripts\bootstrap_dev.py
.venv\Scripts\activate
```

Run Chunklate:

```bash
python Chunklate.py -f path/to/file.png
```

Or, after installing the package entry point:

```bash
chunklate -f path/to/file.png
```

For long brute force runs:

```bash
python Chunklate.py -f bad.png -workers normal
```

For optional OpenGL acceleration when supported:

```bash
python Chunklate.py -f bad.png -gpu -workers normal
```

Optional GPU dependency:

```bash
python -m pip install -e ".[gpu]"
```

or:

```bash
python -m pip install "moderngl>=5.10"
```

## Arguments

```text
usage: Chunklate.py [-h] [-f FILE] [-c] [-p] [-d] [-df] [-dp] [-ep] [-sp]
                    [-stfu] [-a] [--no-color] [--output-dir DIR]
                    [--max-saves N] [-workers min|normal|max|N] [-gpu]
                    [-ddll N] [--ddl-crc-forge auto|off|force]
                    [--ddl-forge-bytes N] [--ddl-forge-window START:END]
                    [--ddl-deflate-mitm auto|off|force]
                    [-ulfr exact|similar PATH] [-ulfroi-edit] [-ulfsp]
                    [-ulfgl N] [-ulfmc FLOAT]
```

General options:

| Argument | What it does |
| --- | --- |
| `-f FILE` | PNG file to inspect or repair. |
| `-a` | Auto-choose safe/default answers when possible. |
| `-stfu` | Minimal terminal output. Prompts that matter can still appear. |
| `-c` | Clear the terminal after saves. |
| `-p` | Pause after saves. |
| `-sp` | Pause at dialogue messages. |
| `-ep` | Pause at errors. |
| `-d` | Print debug output in the terminal. |
| `-df` | Add debug output and terminal transcript context to the summary file. |
| `-dp` | Pause at debug messages. |
| `--no-color` | Disable terminal colors. |
| `--output-dir DIR` | Write `Folder_*` outputs under this directory. |
| `--max-saves N` | Stop after writing `N` repaired files. |

Performance and brute force:

| Argument | What it does |
| --- | --- |
| `-workers 0` or `-workers 1` | Serial mode. |
| `-workers min` | Use about `CPU / 4` workers. |
| `-workers normal` | Use about `CPU / 2` workers. |
| `-workers max` | Use about `CPU - 1` workers. |
| `-workers N` | Use exactly `N` CPU workers. |
| `-gpu` | Allow GPU acceleration when a compatible engine supports the current pass. CPU remains the fallback. |

DaedalusForce options:

| Argument | What it does |
| --- | --- |
| `-ddll N` | Start DaedalusForce at brute-force level `N`; useful to jump straight to level `2` for 4-byte Hermes windows after lower levels are already exhausted. |
| `--ddl-crc-forge auto` | Let HermesProbe try targeted IDAT CRC repairs before broad DaedalusForce. This is the default. |
| `--ddl-crc-forge off` | Skip HermesProbe CRC repair and go to the normal DaedalusForce path. |
| `--ddl-crc-forge force` | Let HermesProbe use wider targeted repair budgets. This can still be slow. |
| `--ddl-forge-bytes N` | Limit HermesProbe to one suspected byte count. |
| `--ddl-forge-window START:END` | Limit HermesProbe to one or more IDAT byte windows. This is useful when you already know the damaged area. |
| `--ddl-deflate-mitm auto` | Let HermesProbe use the deflate meet-in-the-middle V2 solver for longer IDAT edits. This is the default. |
| `--ddl-deflate-mitm off` | Disable the V2 deflate solver while keeping the other HermesProbe passes. |
| `--ddl-deflate-mitm force` | Use larger V2 solver budgets. Prefer this only with a tight byte window. |

Ultimate line-feed options:

| Argument | What it does |
| --- | --- |
| `-ulfr exact PATH` | Use a reference PNG for exact candidate scoring. |
| `-ulfr similar PATH` | Use a related/similar PNG for ROI or patch scoring. |
| `-ulfroi-edit` | Open the ROI editor before Ultimate scoring. |
| `-ulfsp` | Open live Ultimate candidate previews. |
| `-ulfgl N` | Keep up to `N` saved visual candidates. |
| `-ulfmc FLOAT` | Minimum visual gallery scanline coverage, from `0` to `1`. |

## Output Files

Chunklate writes repairs and artifacts next to the input by default:

```text
Folder_bad/
  bad.0_Fixed.png
  Summary_Of_bad
  Bruteforce_Previews/
  Debug_Payloads/
  _SBB.progress.json
  _ULF.progress.json
```

Important distinction:

- `*_Fixed.png` should mean a repair candidate passed the current write gate.
- `Bruteforce_Previews/` contains visual candidates, blackfill fallbacks, and
  unproven brute force artifacts.
- `Debug_Payloads/` contains payloads useful for debugging, not final repairs.
- `_SBB.progress.json` is the DaedalusForce resume checkpoint. The filename is
  kept for compatibility with existing runs. `_ULF.progress.json` is the
  Ultimate resume checkpoint.

## Tkinter Visual Helpers

Some repair routes need human visual judgement. When Chunklate cannot prove the
right pixels from PNG structure alone, it can open small Tkinter tools instead
of forcing a blind automatic choice.

### PLTE Palette Editor

When an indexed PNG has a missing, malformed, empty, or suspicious `PLTE`,
Chunklate may build a grayscale emergency palette first. If the preview is not
good enough, answer `no` at the palette prompt to open the Tkinter palette
editor. The editor lets you try preset palettes, randomize entries, adjust
individual palette sliders, then save the selected `PLTE` back through the
normal clone/checkpoint path.

![PLTE Tkinter palette editor](https://i.ibb.co/Vc4G7ZCP/Screenshot-From-2026-06-20-11-15-14.png)

### Ultimate Reference ROI Editor

For visually guided `IDAT` recovery, especially `UltimateMegaSuperLineFeedBruteForce`,
Chunklate can use a reference PNG. With `-ulfr similar PATH -ulfroi-edit`, the
Tkinter ROI editor lets you mark source/reference regions, same-position
regions, search regions, or negative regions. Those saved ROI mappings help the
visual scorer prefer candidates that look coherent instead of merely producing
more decompressed bytes.

![Ultimate reference ROI editor](https://i.ibb.co/tpnGjqYJ/Screenshot-From-2026-06-20-10-24-07.png)

## What Chunklate Repairs

Chunklate currently handles many structural PNG problems:

- Missing, shifted, or embedded PNG signatures.
- Wrong chunk length, chunk type/name, and chunk CRC.
- Missing `IEND`, trailing garbage, and some broken end-of-file cases.
- Broken `IHDR` values when CRC evidence or IDAT scanline math is strong enough.
- Empty, missing, undersized, oversized, or malformed indexed `PLTE` chunks.
- Duplicate singleton chunks such as `IHDR`, `PLTE`, `gAMA`, `sRGB`, `iCCP`,
  `pHYs`, `sBIT`, `bKGD`, `tRNS`, `hIST`, `sTER`, `oFFs`, and `eXIf`.
- Selected misplaced chunks, including ancillary chunks interrupting consecutive
  `IDAT` chunks.
- Known ancillary payload issues in chunks such as `bKGD`, `cHRM`, `gAMA`,
  `gIFg`, `hIST`, `iTXt`, `oFFs`, `pHYs`, `sBIT`, `sCAL`, `sRGB`, `sTER`,
  `tIME`, `tRNS`, `tEXt`, `zTXt`, and related metadata.
- Unsafe unknown/private critical chunks when removing or renaming them can make
  the PNG structurally valid.
- Known bad sRGB/iCCP profile chunks and zero-value `gAMA`.
- Some text metadata damage, including `tEXt` null bytes, `iTXt` field damage,
  and `zTXt` compression method or zlib data-format byte errors.
- Periodic byte corruption in PNG/IDAT-shaped files when a bounded periodic
  transform can be reversed and the whole PNG validates afterward.

## IDAT Salvage And Brute Force

`IDAT` is the compressed image data. This is the hard part.

Chunklate has four main IDAT paths:

- `partial-idat-blackfill`: salvage complete decompressed scanlines, fill the
  missing area with black/transparent bytes, rebuild a valid PNG. This is a
  fallback, not proof that the original pixels were recovered.
- `DaedalusForce`: brute force IDAT byte edits. It includes `HermesProbe`
  for targeted byte-window passes and `HephaestusForge` for heavier campaigns.
- `UltimateMegaSuperLineFeedBruteForce`: deeper line-feed conversion recovery
  with checkpoints, visual candidate galleries, optional reference scoring, and
  optional CPU workers.
- `periodic_tail_xor_counter`: despite the compatibility name, this is now a
  bounded periodic byte repair campaign. It tests XOR, add/sub counter families,
  little/big-endian counters, pair swaps, bit-not, nibble swaps, and one-bit
  rotations over likely periods/phases.

Periodic repair is intentionally conservative. It is triggered by periodic
damage symptoms such as `IDAT` CRC failure, `No NextChunk`, corrupt deflate, or
`BadCodeLengthHuffmanTree`, but it only accepts a candidate when the repaired
file has valid PNG structure, rebuilt CRC consistency, and a complete IDAT
decode. It does not use file names, challenge side files, or external container
context as proof.

GroundHogDay still tries the cheaper LF/CR and bounded SuperLineFeed probes, but
it does not launch MiniUltimate/UltimateLineFeed automatically from that loop.
Ultimate remains a separate heavier route with explicit checkpoints/options.

HermesProbe runs before broad DaedalusForce when the stored original `IDAT` CRC is useful.
For small edits it can solve the CRC directly. For larger edits it now also has
a deflate meet-in-the-middle V2 path: it reads the compressed stream structure
around the suspected area, keeps only deflate/Huffman shapes that can make sense,
then uses the CRC as a final constraint. That does not make 20-byte damage
trivial, but it avoids jumping straight to a blind full brute force when a
targeted structural search is still realistic.

If HermesProbe cannot prove a full PNG repair, Chunklate explains the handoff
before broad DaedalusForce. In interactive mode you can trust the detected DaedalusForce level,
choose a custom level/byte scope, go back to retry targeted repair, or accept a
blackfill fallback when one exists.

For brute force, Chunklate tries to keep the parent process responsible for all
visible effects: prompts, previews, final files, summaries, and checkpoint
writes. CPU workers and GPU kernels only test candidates and return possible
hits. The parent still validates the candidate PNG before accepting it.

## GPU Status

`-gpu` is a permission flag. It does not force GPU use.

Current status:

- OpenGL compute support is experimental.
- DaedalusForce/HermesProbe can use GPU CRC filtering for supported direct IDAT byte-window
  passes, including tiled rank spaces that go beyond 32-bit candidate counts.
- Ultimate has an OpenGL preflight that can suggest CR/LF and Adler-trailer
  offsets before the normal CPU search.
- CPU validation remains mandatory for every GPU hit.
- If OpenGL, `moderngl`, the driver, or the current candidate plan is not usable,
  Chunklate reports the reason and keeps using CPU workers.

## What It Does Not Repair Yet

Chunklate cannot reliably repair everything:

- If a PNG has no usable `IDAT`, there are no source pixels to recover.
- If the PNG is structurally valid but visually wrong, Chunklate usually needs a
  reference image, ROI, checksum, or human validation. It cannot guess the
  intended picture from structure alone.
- Missing decompressed bytes are not the same thing as missing compressed bytes.
  A tiny deflate error can make a large part of the image disappear.
- Large IDAT brute force spaces can still take hours, days, months, or worse.
- HermesProbe is targeted, not omniscient. If the suspected window is wrong or
  the corruption spans several IDAT chunks at once, it may still need another
  pass or a broader fallback.
- GPU acceleration is still being expanded. HermesProbe has the broadest GPU
  coverage; HephaestusForge and Ultimate still fall back to CPU for many passes.
- Blackfill output is a valid salvage image, not an exact original recovery.

## TODO

- Expand GPU coverage for HephaestusForge passes that can be represented as
  deterministic IDAT byte windows.
- Add stronger GPU/CPU parity tests for deeper byte-window levels.
- Improve ETA handling so Chunklate asks only before genuinely expensive passes.
- Keep improving HermesProbe deflate reverse parsing for harder 10+ byte IDAT
  corruptions.
- Improve visual scoring for structurally valid but visually suspicious PNGs.
- Keep growing the repair matrix for real corrupt PNG families.
- Continue preparing Ultimate for heavier GPU acceleration after the DaedalusForce GPU
  path is stable.
- Evaluate native C/Rust acceleration for mutation, CRC/Adler, and zlib hot
  paths.

## Development

Install or refresh dependencies:

```bash
./scripts/bootstrap_dev.sh
```

Run the full local validation:

```bash
./scripts/check.sh
```

Run pytest directly:

```bash
.venv/bin/python -m pytest
```

Useful docs:

```text
docs/architecture.md
docs/repair_matrix.md
```

The readable repair matrix lives in `docs/repair_matrix.md`. The strict
regression source of truth is `tests/repair_matrix.py`, plus focused unit and
runtime tests.

`Png_Errors_handled_by_Chunklate_So_Far/periodic_you_*.png` contains corruption fixtures .
They cover the new periodic families: legacy counter XOR, counter add/sub, endian counter
variants, pair swap, bit-not, nibble swap, one-bit rotations, and a four-byte
periodic counter case. Each fixture is expected to repair back to the original
bytes through the periodic route.

## In Memory Of Glenn Randers-Pehrson

![Glenn Randers-Pehrson](https://i.postimg.cc/yN5YTWwH/image.png)

(April 30, 1941 - October 2018)
