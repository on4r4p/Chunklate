 ![Alt Text](https://github.com/on4r4p/Chunklate/blob/ctf/Chunklate.gif)

## Description

**Chunklate** checks png images for file format corruption and fix them .

##### Work in progress May Not Work as Expected ATM !

**Chunklate**'s aim is to be able to provide those features:

- Get all information it can find from a PNG file.
- Repair or extract PNGs when the PNG signature is missing, shifted, or embedded
  after another file header.
- Repair wrong chunk length, chunk name/type, chunk CRC, and one-byte
  missing/extra chunk data cases.
- Repair or rebuild broken `IHDR` values from CRC evidence or IDAT scanline
  math, including wrong dimensions and invalid color metadata.
- Repair missing or malformed terminal structure such as missing `IEND` and
  trailing garbage after the PNG stream.
- Repair empty, missing, undersized, oversized, or malformed indexed `PLTE`
  chunks; optionally open the Tkinter PLTE editor when manual tuning is useful.
- Repair known ancillary payload issues for chunks such as `bKGD`, `cHRM`,
  `gAMA`, `gIFg`, `hIST`, `iTXt`, `oFFs`, `pHYs`, `sBIT`, `sCAL`, `sRGB`,
  `sTER`, `tIME`, `tRNS`, and `zTXt`.
- Repair duplicate singleton chunks such as duplicate `IHDR`, `PLTE`, `gAMA`,
  `sRGB`, `iCCP`, `pHYs`, `pCAL`, `sCAL`, `sBIT`, `bKGD`, `tRNS`, `hIST`,
  `sTER`, `oFFs`, and `eXIf`.
- Repair selected misplaced chunks, including misplaced `IHDR`, out-of-place
  `hIST`/`pCAL`/`sPLT`, and ancillary chunks interrupting consecutive `IDAT`
  chunks.
- Remove or rename unsafe unknown/private critical chunks when the PNG can be
  made structurally valid.
- Repair known bad sRGB/iCCP profile chunks and zero-value `gAMA`.
- Repair line-feed conversion damage, including NUL-stripped line-feed samples,
  and run heavier line-feed brute force probes when requested.
- Resume long Ultimate line-feed brute-force runs from local checkpoints and
  optionally split the exhaustive search across CPU workers.
- Keep a bounded visual gallery for ultimate line-feed brute-force candidates,
  including high-coverage `bad_adler` reconstructions whose original zlib
  trailer still does not match. A local reference can rank candidates with exact
  pixel distance, generic similar-image patch/hash scoring, or manual ROI
  scoring for related-but-not-identical screenshots.
- Resume and parallelize `SmashBruteBrawl` searches, including `TwoBytes`,
  while keeping prompts, previews, and final writes in the parent process.
- Repair PNG text metadata damage, including `tEXt` null bytes, `iTXt`
  keyword/compression fields, and `zTXt` compression method or zlib data-format
  byte errors.
- Salvage partially decompressible non-interlaced and Adam7 `IDAT` streams with
  `partial-idat-blackfill`.
- Save each modification in a different file and write a readable summary of
  the repair path.



## Usage

Install the runtime dependencies in a virtual environment:

    ./scripts/bootstrap_dev.sh
    . .venv/bin/activate

On Windows, use the cross-platform bootstrap directly:

    py scripts\bootstrap_dev.py
    .venv\Scripts\activate

Run Chunklate on a PNG file:

    chunklate -f path/to/file.png

Or run it directly from the repository:

    python Chunklate.py -f path/to/file.png

Current CLI:

    usage: Chunklate.py [-h] [-f FILE] [-c] [-p] [-d] [-df] [-dp] [-ep] [-sp] [-stfu] [-a] [--no-color] [--output-dir DIR] [--max-saves N]
                        [-workers min|normal|max|N] [-ulfr exact|similar PATH] [-ulfroi-edit] [-ulfsp] [-ulfgl N] [-ulfmc FLOAT]

    options:
      -h, --help    show this help message and exit
      -f, --file FILE    File path.
      -c, --CLEAR, --clear    CLEAR screen at each saves.
      -p, --pause    Pause at each saves.
      -d, --debug    Debug stuffs.
      -df, --debug-file    Append debug output to the normal summary file.
      -dp, --pause-debug    Pause at Debug stuffs.
      -ep, --pause-error    Pause at errors.
      -sp, --pause-dialogue    Pause at dialogues.
      -stfu, --shut-the-fuck-up    Show minimal output.
      -a, --auto    Auto Choose action.
      --no-color    Disable terminal colors.
      --output-dir DIR    Directory where Folder_* repair outputs are written.
      --max-saves N    Exit successfully after writing N repaired files.
      -workers min|normal|max|N    CPU workers for Ultimate and Smash: min, normal, max, or exact N.

    ultimate line-feed:
      -ulfr exact|similar PATH    Reference PNG and scoring mode for Ultimate candidates.
      -ulfroi-edit    Open the ROI editor before Ultimate.
      -ulfsp    Open live Ultimate candidate previews.
      -ulfgl N    Saved visual candidate count.
      -ulfmc FLOAT    Minimum gallery scanline coverage, 0..1.

## Development

Install or refresh all runtime and development dependencies:

    ./scripts/bootstrap_dev.sh

Run the smoke tests:

    .venv/bin/python -m pytest

Run the full local validation:

    ./scripts/check.sh

Run only the repair regression tests:

    .venv/bin/python -m pytest tests/test_repairs.py

Architecture overview:

    docs/architecture.md

Repair matrix:

    docs/repair_matrix.md

That file is the readable reference for the current repair coverage. The strict
regression source of truth is `tests/repair_matrix.py`; additional targeted
repair routes are covered by focused unit/runtime tests.

Or without pytest:

    ./tests/test_cli.py
    ./tests/test_checkpoint.py
    ./tests/test_dummy_chunk.py
    ./tests/test_png.py
    ./tests/test_output.py
    ./tests/test_relics_state.py
    ./tests/test_repairs.py

## Repair Notes

`partial-idat-blackfill` is an explicit fallback repair for PNGs
whose IDAT zlib stream can be decompressed only partially. Chunklate keeps the
complete filtered scanlines recovered before the zlib failure, fills the
remaining non-interlaced or Adam7 pass scanlines with black or transparent
bytes, recompresses a new IDAT stream, and recalculates length and CRC. This
makes a valid salvage PNG; it is not a claim that the original image content was
faithfully reconstructed.

Current v1 limits: partial rows are discarded, and PNG filter reconstruction is
not guessed beyond the complete filtered scanlines already recovered from zlib.

Before the heavy SuperMega/Ultimate line-feed probes, Chunklate now tries a
deterministic IDAT marker-chain repair when the PNG signature is damaged but
visible `IHDR`/`IDAT`/`IEND` headers remain. This path preserves IDAT chunks
byte-for-byte when their length, payload, and CRC already match, tests bounded
boundary hypotheses only on the suspect IDAT segment, and recalculates PNG CRCs
for rebuilt chunks. If the original Adler still does not match, the output is
reported as a rebuilt-Adler visual salvage rather than an original stream
recovery.

`UltimateMegaSuperLineFeedBruteForce` also maintains a separate visual
candidate gallery. This is not the resume checkpoint and it is not a complete
log of every candidate tested. It keeps the best bounded set of visually useful
candidates, defaulting to 100 entries with at least 95% usable scanline
coverage. A full `bad_adler` candidate can therefore be saved even when the
candidate's original zlib Adler trailer still mismatches.

Gallery previews are rebuilt PNGs: Chunklate recompresses the recovered
scanlines into a fresh IDAT stream with a rebuilt Adler trailer and marks the
artifact as `rebuilt_adler_preview`. These files are previews for visual
inspection, not proof that the original compressed stream or original Adler was
recovered.

The gallery writes:

    Folder_x.bad/Bruteforce_Previews/VisualCandidates/
    Folder_x.bad/_ULF.visual.json

When the gallery reaches its limit, better-ranked candidates still replace the
current worst entry. The limit only bounds the saved gallery size. Without
`-ulfr`, ranking uses structural signals and diversity hashes from
recovered scanlines and operations; with a reference PNG, Chunklate also adds a
pixel-distance or similar-layout `visual_score`. The visual score is only a
tie-break after structural quality, so a lower-scanline candidate should not
beat a more complete candidate only because it resembles the reference.

For similar references that are not the same image, manual ROI scoring can be
used with `-ulfr similar REF.png`. If no ROI JSON exists in interactive
mode, Chunklate opens a small Tkinter editor with the Ultimate source snapshot
on the left and the reference image on the right. If the reference dimensions
differ, Chunklate resizes that reference once to the candidate IHDR size before
ROI scoring.

![Ultimate similar reference ROI editor](https://i.ibb.co/Gf3TGjsW/image.png)

Typical run:

    python Chunklate.py -df -f bad.png -ulfr similar REF.png -ulfgl 500 -workers normal

The ROI editor supports:

- `paired`: draw one rectangle on each image. Chunklate compares those regions,
  allowing a small local shift on the candidate side.
- `search`: draw one rectangle on the reference, then press
  `Add Single Rectangle` and choose whole-image search. Chunklate searches for
  the closest matching region in each candidate, including nearby scales for
  different image sizes.
- `single`: draw one rectangle on the source snapshot, then press
  `Add Single Rectangle`. Chunklate compares that candidate region to the
  pre-Ultimate source snapshot, without relying on the reference.
- Same-position single reference: draw one rectangle on the reference, press
  `Add Single Rectangle`, then choose same position. Chunklate compares the same
  normalized area in the candidate and reference.
- `negative`: draw one rectangle on the source snapshot, then press
  `Add Negative Rectangle`. Chunklate penalizes noisy or artifact-heavy
  candidates in that region.
- `Draw Same Rectangle`: copy the current rectangle to the same normalized
  position on the other image.
- Edge clamping: selections can start outside the displayed image; if most of
  the dragged area overlaps the image, only the inside portion is kept.
- `Redo`: restore the last ROI removed with `Delete last`.
- Hover editor buttons or pause over a drawn ROI for 0.5 seconds to see what it
  does.

The mapping is saved as `Folder_x.bad/_ULF.reference_regions.json`. Manual ROI
scoring is still only a visual tie-break: Adler matches and structural
completeness stay stronger than resemblance to a reference.

### Ultimate Resume And CPU Workers

`UltimateMegaSuperLineFeedBruteForce` writes local resume artifacts in the
current output folder:

    Folder_x.bad/_ULF.progress.json
    Folder_x.bad/_ULF.checkpoint.jsonl
    Folder_x.bad/_ULF.Source.raw
    Folder_x.bad/_ULF.Source.png

`_ULF.progress.json` is the resume cursor. Newer checkpoints store shard
progress so a resumed exhaustive run can skip the checkpoint archive scan and
continue from the saved ranks. `_ULF.checkpoint.jsonl` remains a candidate
archive, not a startup requirement for fast resume.

Use `-workers` to split the exhaustive Ultimate search across CPU workers:

- `0` or `1`: serial mode.
- `min`: about `CPU / 4`.
- `normal`: about `CPU / 2`.
- `max`: about `CPU - 1`.
- exact `N`: use that many workers.

If no worker option is provided in interactive mode, Chunklate asks before
Ultimate starts. In auto or no-dialogue modes, it stays serial unless
`-workers` is set.
On `Ctrl+C`, Chunklate asks the workers to park their shards, writes the
progress checkpoint, flushes useful visual candidates, and exits with code
`130` so the next run can resume.

### SmashBruteBrawl Resume And CPU Workers

`SmashBruteBrawl` also writes local resume artifacts:

    Folder_x.bad/_SBB.progress.json
    Folder_x.bad/_SBB.Source.raw
    Folder_x.bad/_SBB.Source.png

`_SBB.progress.json` records the resolved candidate plan, backend, workers,
shards, cursor, and candidate-space hash. `_SBB.Source.raw` is the clean source
snapshot used for direct resume; `_SBB.Source.png` is written only when that
snapshot can be decoded as a PNG preview.

Use `-workers` to select the Smash CPU worker profile:

- `0` or `1`: legacy serial path.
- `min`: about `CPU / 4`.
- `normal`: about `CPU / 2`.
- `max`: about `CPU - 1`.
- exact `N`: use that many workers.

If no worker option is provided in interactive mode, Chunklate asks before
launching long Smash routes. Compatible Smash checkpoints are detected
automatically and Chunklate prompts before resuming or resetting them.

The parent process keeps all visible effects: prompts, previews, repaired files,
summaries, and checkpoint writes. Workers only test candidate shards and return
hits, cursors, counters, and errors. This applies to long `SmashBruteBrawl`
paths, including `TwoBytes`; the parent preserves legacy candidate priority
before accepting a hit. When the stored chunk CRC is trusted, workers can filter
candidates by checksum first, then the parent validates hits with the real
PNG/zlib path.

Files like `x00n0g01.png`, where `IHDR` is `0x0`, or `xdtn0g01.png`, which
contains only `IHDR`, `gAMA`, and `IEND`, are classified as impossible to
repair when no `IDAT` exists. There are no source pixels to recover from that
input.

## Planned Acceleration / TODO

- Add an OpenCL backend for `SmashBruteBrawl` when the target CRC is trusted:
  GPU batches would test `candidate -> CRC32 -> hit`, then CPU code would
  validate only the hits with PNG/zlib.
- Keep CPU serial and CPU worker backends as the reliable fallback when OpenCL
  is missing, the driver fails, the CRC is not trusted, or the candidate plan is
  not GPU-compatible.
- Add backend selection after the CPU backend layer is stable, for example
  `auto|cpu|parallel|opencl` plus an OpenCL batch-size option.
- Evaluate native C/Rust acceleration for mutation, CRC/Adler, and zlib hot
  paths before attempting a GPU zlib port.
- Keep Ultimate's first acceleration path CPU multiprocessing; GPU visual
  scoring is lower priority because ROI scoring only runs on useful candidates.

### In Memory Of Glenn Randers-Pehrson

![Glenn Randers-Pehrson](https://i.postimg.cc/yN5YTWwH/image.png)

(April 30, 1941 - October 2018)
