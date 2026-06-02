# Repair Matrix

This document summarizes the current repair contract. The source of truth is
`tests/repair_matrix.py` for strict fixture-level regressions. Additional
targeted repair routes are covered by focused tests in `tests/test_png.py`,
`tests/test_fixit_felix.py`, `tests/test_fixit_felix_runtime.py`, and the
related runtime test modules. This page is a readable map for humans.

Each fixture listed here is expected to produce a strict repaired PNG. Strict
means the output has a valid PNG structure and CRCs, passes Pillow verification
when Pillow is installed, satisfies repair-specific validators, and writes a
summary containing the declared repair markers.

Current validators also lock exact output shape where it matters: chunk order,
number of `IDAT` chunks, decompressed `IDAT` size, and exact `PLTE` size.

## Current Repair Families

Chunklate currently has automatic or guided repair routes for these corruption
families:

- PNG signature/header recovery: missing signatures, shifted signatures, files
  where a valid PNG starts after non-PNG bytes, and line-feed damaged
  signatures.
- Chunk framing: wrong chunk lengths, one missing or extra byte around chunk
  boundaries, bad CRCs, wrong chunk names/types, and known chunk type case
  errors.
- Terminal structure: missing `IEND`, malformed `IEND`, and trailing bytes
  after the PNG stream.
- `IHDR`: wrong length, duplicate `IHDR`, misplaced `IHDR`, missing `IHDR`,
  bad dimensions, invalid bit depth/color type/method values, and rebuilds from
  IDAT scanline math or stored CRC evidence.
- `PLTE`: missing indexed palettes, empty palettes, malformed palette length,
  undersized indexed palettes, too many entries for the indexed bit depth, and
  indexed palettes whose used entries collapse to one visible color. Chunklate
  can also offer the Tkinter PLTE editor for manual palette tuning. Indexed
  `PLTE` chunks that cannot preserve useful colors are rebuilt from the usable
  `IDAT` index range as grayscale palettes; in an interactive terminal
  Chunklate previews that result and can hand the palette over to the Tkinter
  editor.
  Empty non-indexed `PLTE` chunks and forbidden grayscale `PLTE` chunks are
  removed. Oversized optional truecolor `PLTE` chunks are truncated to the PNG
  maximum of 256 entries; malformed optional truecolor `PLTE` chunks are
  removed because RGB/RGBA pixels do not depend on them.
- Ancillary chunk payloads: length/value repairs for `bKGD`, `cHRM`, `gAMA`,
  `gIFg`, `hIST`, `iTXt`, `oFFs`, `pHYs`, `sBIT`, `sCAL`, `sRGB`, `sTER`,
  `tIME`, `tRNS`, and `zTXt`.
  Text metadata repairs include `tEXt` payload cleanup, `iTXt`
  keyword/compression field normalization, `zTXt` compression method
  normalization, and one-byte `zTXt` zlib data-format repair when the corrected
  stream decompresses and the rebuilt PNG validates.
- Chunk order: misplaced `IHDR`, `hIST` after `IDAT`, `pCAL` after `IDAT`,
  `sPLT` after `IDAT`, and ancillary chunks inserted between non-consecutive
  `IDAT` chunks. For IDAT interruptions Chunklate asks whether to move the
  ancillary chunk to a neutral position or remove safe-to-copy ancillary chunks.
- Duplicate singleton chunks: automatic cleanup for chunk types that may appear
  at most once, including `IHDR`, `PLTE`, `gAMA`, `sRGB`, `iCCP`, `pHYs`,
  `pCAL`, `sCAL`, `sBIT`, `bKGD`, `tRNS`, `hIST`, `sTER`, `oFFs`, and `eXIf`.
- Unsafe or unknown chunks: removal/renaming paths for unknown private critical
  chunks and known bad sRGB/iCCP profile chunks.
- IDAT/data stream salvage: partial non-interlaced and Adam7 IDAT recovery with
  `partial-idat-blackfill`, generic private compression method conversion via
  a bounded known-signature prefix probe (`zlib`, raw deflate, `gzip`, `bzip2`,
  `xz`/`lzma`, optional `zstd`/`brotli`/`lz4`, plus single-entry `zip`/`tar.*`
  containers). Multi-entry containers are accepted only when every plausible
  entry decodes to the same exact PNG scanlines; different valid payloads stay
  refused as ambiguous. Chunklate also handles normalization of invalid/private
  scanline filter bytes to filter type `0`, line-feed conversion repair,
  NUL-stripped line-feed structural reconstruction, and heavier line-feed brute
  force probes behind explicit prompts/budgets.

Known limits: a completely missing `IDAT` stream is not reconstructable from
nothing. Files with no image stream, such as zero-dimension `x00n0g01.png` or
`xdtn0g01.png` with only `IHDR`, `gAMA`, and `IEND`, are classified as
impossible to repair rather than converted into fake images.
Partial scanlines are discarded, and some targeted routes are covered by
unit/runtime tests before they are promoted to the strict fixture matrix below.

## Validation Levels

`32x32 indexed`
: order `IHDR,gAMA,PLTE,IDAT,IEND`, dimensions `32x32`, `PLTE` length `768`,
  one decompressible `IDAT` with decompressed length `1056`, non-zero `gAMA`.

`32x32 indexed, no gAMA`
: order `IHDR,PLTE,IDAT,IEND`, dimensions `32x32`, `PLTE` length `768`,
  one decompressible `IDAT` with decompressed length `1056`.

`32x32 no PLTE`
: order `IHDR,gAMA,IDAT,IEND`, dimensions `32x32`, no `PLTE`, non-zero
  `gAMA`, one decompressible `IDAT` with decompressed length `6176`.

`32x32 indexed, 4-bit palette`
: order `IHDR,gAMA,sBIT,PLTE,IDAT,IEND`, dimensions `32x32`, `PLTE`
  length `48`, one decompressible `IDAT` with decompressed length `544`,
  non-zero `gAMA`.

`260x195`
: order `IHDR,gAMA,cHRM,bKGD,tIME,IDAT*2,tEXt*2,IEND`, dimensions `260x195`,
  two `IDAT` chunks with decompressed length `202995`, non-zero `gAMA`.

`477x599`
: order `IHDR,gAMA,cHRM,bKGD,pHYs,tIME,IDAT*19,tEXt*2,IEND`, dimensions
  `477x599`, nineteen `IDAT` chunks with decompressed length `857768`,
  non-zero `gAMA`.

`272x170 without iCCP`
: order `IHDR,gAMA,cHRM,pHYs,IDAT*2,IEND`, dimensions `272x170`, no `iCCP`,
  two `IDAT` chunks with decompressed length `185130`, non-zero `gAMA`.

`1920x1200`
: order `IHDR,sBIT,IDAT*97,IEND`, dimensions `1920x1200`, ninety-seven
  `IDAT` chunks with decompressed length `9217200`.

`partial IDAT blackfill`
: order `IHDR,IDAT,IEND`, dimensions `1x10`, one rebuilt `IDAT` with
  decompressed length `40`.

`1642x1095`
: order `IHDR,sRGB,gAMA,pHYs,IDAT*4,IEND`, dimensions `1642x1095`, four
  `IDAT` chunks with decompressed length `5395065`, non-zero `gAMA`.

## Cases

| Fixture | Corruption | Expected Strategy | Validation Level |
| --- | --- | --- | --- |
| `Bad-Chunk-Lenght-Missing-Bit.png` | chunk length with one missing bit | recover chunk length | 32x32 indexed |
| `Bad-Chunk-Length-Missing-Bit.png` | chunk length with one missing bit | recover chunk length | 32x32 indexed |
| `Bad-Chunk-Length-Exceeding-Bit.png` | chunk length with one exceeding bit | recover chunk length | 32x32 indexed |
| `Classic-Bad-Chunk-Crc.png` | chunk CRC mismatch | repair CRC | 32x32 indexed |
| `Classic-Bad-Chunk-Length.png` | chunk length mismatch | repair chunk length | 32x32 indexed |
| `Good-Chunk-lenght-Missing-Bit.png` | chunk data with one missing bit and reliable length | recover missing byte from chunk data | 32x32 indexed |
| `IHDR-Messed-Up-Bad-Crc.png` | IHDR data corruption with bad CRC | repair IHDR | 260x195 |
| `IHDR-Wrong-Height-Above-Estimated-Max-Resolution.png` | IHDR height above estimated maximum | repair IHDR height | 477x599 |
| `IHDR-Wrong-Quick.png` | IHDR dimension corruption | repair IHDR quickly | 477x599 |
| `IHDR-Wrong-Width-Bad-Crc.png` | IHDR width corruption with bad CRC | repair IHDR width | 477x599 |
| `IHDR-Wrong-Width.png` | IHDR width corruption | repair IHDR width | 477x599 |
| `IHDR_Messed_Up_Crc_Valid.png` | IHDR data corruption with valid CRC | repair IHDR | 32x32 indexed |
| `IHDR_Missplaced.png` | IHDR placed after another chunk | move IHDR back to the first chunk position | 32x32 indexed |
| `IEND_Missing.png` | missing IEND chunk | append IEND | 260x195 |
| `IEND_Missing_And_Extra_Bytes.png` | missing IEND and trailing bytes | append IEND and remove extra bytes | 1920x1200 |
| `IDAT_Partial_Blackfill.png` | partially readable IDAT stream | partial-idat-blackfill | partial IDAT blackfill |
| `truncate_zlib_2.png` | truncated interlaced IDAT stream before missing IEND | partial-idat-blackfill | partial Adam7 IDAT blackfill |
| `IncorrectSrgbProfile.png` | known bad sRGB/iCCP profile | remove bad color profile chunk | 272x170 without iCCP |
| `Incorrect_Srgb_Profile.png` | known bad sRGB/iCCP profile | remove bad color profile chunk | 272x170 without iCCP |
| `Missplaced_Ihdr.png` | IHDR placed after another chunk | move IHDR back to the first chunk position | 32x32 indexed |
| `No_Png_Header.png` | missing PNG signature | restore PNG signature | 260x195 |
| `No_Png_Header_Corrupted_Length.png` | missing PNG signature and corrupted length | restore PNG signature and chunk length | 260x195 |
| `No_Png_Header_Missing_Chunk_Corrupted.png` | missing PNG signature and missing/corrupted IHDR | rebuild missing IHDR | 32x32 indexed with `hIST` present |
| `PLTE_Empty_Bad_Crc.png` | empty PLTE with bad CRC | repair empty PLTE | 32x32 no PLTE |
| `PLTE_Empty_Good_Crc.png` | empty PLTE with valid CRC | repair empty PLTE | 32x32 indexed |
| `plte_length_mod_three.png` | PLTE length is not divisible by three | rebuild malformed indexed PLTE | 32x32 indexed |
| `plte_too_many_entries.png` | PLTE contains too many entries for indexed bit depth | truncate useful indexed PLTE or rebuild low-diversity PLTE | 32x32 indexed, 4-bit palette |
| `plte_too_many_entries_2.png` | optional truecolor PLTE contains more than 256 entries | truncate optional truecolor PLTE | 32x32 truecolor |
| `Private_Critical_Chunk_Bad_Crc.png` | unknown private critical chunk with bad CRC | remove unsafe private critical chunk | 32x32 indexed without `baMA` |
| `Private_Critical_Chunk_Crc_Valid.png` | unknown private critical chunk with valid CRC | remove unsafe private critical chunk | 32x32 indexed without `baMA` |
| `Wrong-Chunk-Name-Bad-Crc.png` | wrong chunk name with bad CRC | repair chunk name | 1642x1095 |
| `Wrong-Chunk-Name-Crc-Valid.png` | wrong chunk name with valid CRC | repair chunk name | 32x32 indexed |
| `chunk_crc.png` | chunk CRC mismatch | repair CRC | 32x32 indexed |
| `chunk_private_critical.png` | unknown private critical chunk | remove unsafe private critical chunk | 32x32 indexed without `GaMA` |
| `chunk_private_critical_badcrc.png` | unknown private critical chunk with bad CRC | remove unsafe private critical chunk | 32x32 indexed without `baMA` |
| `chunk_private_critical_goodcrc.png` | unknown private critical chunk with valid CRC | remove unsafe private critical chunk | 32x32 indexed without `baMA` |
| `chunk_type.png` | wrong chunk type/name | repair chunk name | 32x32 indexed |
| `gama_zero.png` | gAMA chunk with zero value | repair gAMA | 32x32 without `gAMA` |
| `length_gama.png` | gAMA chunk with one missing byte | infer common gAMA payload | 32x32 indexed |
| `length_gifg.png` | gIFg chunk with one extra byte | trim gIFg payload | GIF-extension PNG with valid `gIFg` |
| `length_hist.png` | hIST chunk shorter than PLTE entry count | pad hIST payload | 32x32 indexed with `hIST` |
| `ihdr_image_size.png` | IHDR image size mismatch | repair IHDR dimensions | 32x32 indexed |
| `Unhandled-Critical-Chunk.png` | unknown unsafe critical chunk | remove unsafe critical chunk | 32x32 indexed, no gAMA, without `QpZZ` |

## Targeted But Not Yet Strict Matrix Cases

The following fixture families are covered by focused tests or are available as
automatic/guided routes, but are not all promoted to the strict fixture table
above yet:

- Ancillary length/value repairs: `length_bkgd_*`, `length_chrm`,
  `length_iend`, `length_ihdr`, `length_offs`, `length_phys`, `length_sbit*`,
  `length_srgb`, `length_ster`, `length_time`, and `length_trns_*`.
- Text metadata repairs: `text_trailing_null`, `itxt_keyword_length*`,
  `itxt_compression_flag`, `itxt_compression_method`,
  `ztxt_compression_method`, and `ztxt_data_format`.
- sCAL physical-scale metadata repairs: `scal_floating_point`,
  `scal_negative`, `scal_unit_specifier`, and `scal_zero`.
- Missing critical/structural routes: `missing_ihdr`, `missing_plte*`, and
  missing-IDAT diagnostics.
- IHDR value repairs: `xc1n0g08.png` has invalid color type `1`; IDAT scanline
  math now preserves its valid `32x32` dimensions and 8-bit depth while
  repairing the color type to grayscale `0`.
- Impossible terminal samples: `x00n0g01.png` has `IHDR` dimensions `0x0` and
  no `IDAT` stream, so there are no image pixels to recover.
- Duplicate singleton chunks: `multiple_bkgd`, `multiple_chrm`,
  `multiple_gama`, `multiple_hist`, `multiple_iccp`, `multiple_ihdr`,
  `multiple_offs`, `multiple_pcal`, `multiple_phys`, `multiple_plte`,
  `multiple_sbit`, `multiple_scal`, `multiple_srgb`, `multiple_ster`,
  `multiple_time`, and `multiple_trns`.
- Misplaced ancillary chunks: `*_after_idat`, `*_after_plte`, and
  `hist_before_plte` style cases.
- Non-consecutive IDAT chains: ancillary chunks between `IDAT` chunks can be
  moved after the final `IDAT` or removed when safe.
- Line-feed corruption fixtures: `badlinefeed1`, `linefeedcorruption*`, and
  `xlfn0g04` NUL-stripped line-feed reconstruction.
