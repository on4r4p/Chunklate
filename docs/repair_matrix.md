# Repair Matrix

This document summarizes the current repair contract. The source of truth is
`tests/repair_matrix.py`; this page is a readable map for humans.

Each fixture listed here is expected to produce a strict repaired PNG. Strict
means the output has a valid PNG structure and CRCs, passes Pillow verification
when Pillow is installed, satisfies repair-specific validators, and writes a
summary containing the declared repair markers.

Current validators also lock exact output shape where it matters: chunk order,
number of `IDAT` chunks, decompressed `IDAT` size, and exact `PLTE` size.

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
| `IncorrectSrgbProfile.png` | known bad sRGB/iCCP profile | remove bad color profile chunk | 272x170 without iCCP |
| `Incorrect_Srgb_Profile.png` | known bad sRGB/iCCP profile | remove bad color profile chunk | 272x170 without iCCP |
| `Missplaced_Ihdr.png` | IHDR placed after another chunk | move IHDR back to the first chunk position | 32x32 indexed |
| `No_Png_Header.png` | missing PNG signature | restore PNG signature | 260x195 |
| `No_Png_Header_Corrupted_Length.png` | missing PNG signature and corrupted length | restore PNG signature and chunk length | 260x195 |
| `No_Png_Header_Missing_Chunk_Corrupted.png` | missing PNG signature and missing/corrupted IHDR | rebuild missing IHDR | 32x32 indexed with `hIST` present |
| `PLTE_Empty_Bad_Crc.png` | empty PLTE with bad CRC | repair empty PLTE | 32x32 no PLTE |
| `PLTE_Empty_Good_Crc.png` | empty PLTE with valid CRC | repair empty PLTE | 32x32 indexed |
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
| `ihdr_image_size.png` | IHDR image size mismatch | repair IHDR dimensions | 32x32 indexed |
| `Unhandled-Critical-Chunk.png` | unknown unsafe critical chunk | remove unsafe critical chunk | 32x32 indexed, no gAMA, without `QpZZ` |
