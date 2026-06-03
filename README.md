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

    usage: Chunklate.py [-h] [-f FILE] [-c] [-p] [-d] [-df] [-dp] [-ep] [-sp]
                       [-stfu] [-a] [--no-color]
                       [--output-dir DIR] [--max-saves N]

    optional arguments:
      -h, --help            show this help message and exit
      -f FILE, --file FILE  File path.
      -c, --CLEAR, --clear  CLEAR screen at each saves.
      -p, --pause           Pause at each saves.
      -d, --debug           Debug stuffs.
      -dp, --pause-debug    Pause at Debug stuffs.
      -ep, --pause-error    Pause at errors.
      -sp, --pause-dialogue Pause at dialogues.
      -stfu, --shut-the-fuck-up Show minimal output.
      -a, --auto            Auto Choose action.
      --no-color            Disable terminal colors.
      --output-dir DIR      Directory where Folder_* repair outputs are written.
      --max-saves N         Exit successfully after writing N repaired files.

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

Files like `x00n0g01.png`, where `IHDR` is `0x0`, or `xdtn0g01.png`, which
contains only `IHDR`, `gAMA`, and `IEND`, are classified as impossible to
repair when no `IDAT` exists. There are no source pixels to recover from that
input.

## In Memory Of Glenn Randers-Pehrson

![Glenn Randers-Pehrson](https://i.postimg.cc/yN5YTWwH/image.png)
(April 30, 1941 - October 2018)