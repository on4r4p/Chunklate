from __future__ import annotations

import zlib
from dataclasses import dataclass
import struct

from . import deflate_header
from . import png


@dataclass(frozen=True)
class ZlibHeaderInfo:
    header: str
    valid: bool
    cinfo: int | None = None
    window_kb: int | str = ""
    flevel: int | None = None
    compression_level: int = -1


@dataclass(frozen=True)
class DummyIdatProbe:
    pixel: bytes
    filter_byte: bytes
    scanline: bytes
    header: str
    header_info: ZlibHeaderInfo
    compressed: bytes
    adler: bytes
    raw_deflate_with_adler: bytes
    decompressed: bytes
    idat_decompressed: bytes
    idat_decompressed_error: str = ""


@dataclass(frozen=True)
class PartialIdatAnalysis:
    supported: bool
    complete: bool
    width: int = 0
    height: int = 0
    bit_depth: int = 0
    color_type: int = 0
    scanline_size: int = 0
    expected_size: int = 0
    decompressed_size: int = 0
    complete_scanlines: int = 0
    usable_scanlines: int = 0
    recovered_scanlines: bytes = b""
    idat_stream_size: int = 0
    decompression_error: str = ""
    reason: str = ""

    @property
    def partial(self) -> bool:
        return self.supported and not self.complete and self.usable_scanlines > 0


@dataclass(frozen=True)
class IdatStreamAnalysis:
    supported: bool
    complete: bool
    status: str
    width: int = 0
    height: int = 0
    bit_depth: int = 0
    color_type: int = 0
    scanline_size: int = 0
    expected_size: int = 0
    compressed_size: int = 0
    decompressed_size: int = 0
    complete_scanlines: int = 0
    usable_scanlines: int = 0
    idat_chunk_count: int = 0
    recovered_scanlines: bytes = b""
    zlib_error: str = ""
    error_offset: int | None = None
    error_idat_index: int | None = None
    error_idat_offset: int | None = None
    error_file_offset: int | None = None
    error_context_hex: str = ""
    reason: str = ""
    deflate_header: deflate_header.DeflateHeaderAnalysis | None = None
    stored_adler: int | None = None
    computed_adler: int | None = None
    adler_status: str = "adler_unknown"
    crc_provenance: str = "original_crc_ok"
    source_kind: str = "original"

    @property
    def partial(self) -> bool:
        return self.supported and not self.complete and self.usable_scanlines > 0


@dataclass(frozen=True)
class PartialIdatBlackfillRepair:
    data: bytes
    strategy: str
    recovered_scanlines: int
    total_scanlines: int
    width: int
    height: int
    bit_depth: int
    color_type: int


@dataclass(frozen=True)
class IdatDonorRepair:
    data: bytes
    strategy: str
    donor_label: str
    donor_path: str
    width: int
    height: int
    bit_depth: int
    color_type: int


@dataclass(frozen=True)
class SyntheticIdatRepair:
    data: bytes
    strategy: str
    synthetic_pattern: str
    width: int
    height: int
    bit_depth: int
    color_type: int


@dataclass(frozen=True)
class TruncatedIdatNormalization:
    data: bytes
    declared_length: int
    available_length: int
    chunk_offset: int
    missing_bytes: int


@dataclass(frozen=True)
class TolerantScanlineSalvage:
    filtered_scanlines: bytes
    recovered_scanlines: int
    total_scanlines: int
    invalid_filter_rows: tuple[int, ...]
    repeated_rows: int


def dummy_scanline(bit_depth: str | int, samples: int = 3) -> tuple[bytes, bytes, bytes]:
    depth = int(bit_depth)
    if depth > 8:
        pixel = int(1).to_bytes(2, "little")
    else:
        pixel = int(1).to_bytes(1, "big")

    filter_byte = int(0).to_bytes(1, "big")
    return pixel, filter_byte, filter_byte + (pixel * samples)


def idat_zlib_header(datastream: str, interlace: str | int) -> str:
    if str(interlace) == "1":
        return ""
    return datastream[:4].lower()


def zlib_header_info(header: str) -> ZlibHeaderInfo:
    normalized = header[:4].lower()
    try:
        header_bytes = bytes.fromhex(normalized)
    except ValueError:
        return ZlibHeaderInfo(header=normalized, valid=False)

    if len(header_bytes) != 2:
        return ZlibHeaderInfo(header=normalized, valid=False)

    cmf, flg = header_bytes
    compression_method = cmf & 0x0F
    cinfo = cmf >> 4
    valid = compression_method == 8 and cinfo <= 7 and ((cmf << 8) + flg) % 31 == 0
    if not valid:
        return ZlibHeaderInfo(header=normalized, valid=False, cinfo=cinfo)

    flevel = flg >> 6
    # Legacy DummyChunk only forced level 9 for the 78da header. Other zlib
    # headers keep zlib's default level so the generated debug stream stays safe.
    compression_level = 9 if normalized == "78da" else -1
    window_kb = int((2 ** (cinfo + 8)) / 1024)
    return ZlibHeaderInfo(
        header=normalized,
        valid=True,
        cinfo=cinfo,
        window_kb=window_kb,
        flevel=flevel,
        compression_level=compression_level,
    )


def build_dummy_idat_probe(
    datastream: str,
    bit_depth: str | int,
    interlace: str | int,
) -> DummyIdatProbe:
    pixel, filter_byte, scanline = dummy_scanline(bit_depth)
    header = idat_zlib_header(datastream, interlace)
    header_info = zlib_header_info(header)

    compressor = zlib.compressobj(header_info.compression_level, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed = compressor.compress(scanline) + compressor.flush()
    adler = zlib.adler32(scanline).to_bytes(4, "big")
    raw_deflate_with_adler = compressed + adler

    decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    decompressed = decompressor.decompress(raw_deflate_with_adler)

    try:
        idat_decompressed = zlib.decompress(bytes.fromhex(datastream))
        idat_decompressed_error = ""
    except (ValueError, zlib.error) as exc:
        idat_decompressed = b""
        idat_decompressed_error = str(exc)

    return DummyIdatProbe(
        pixel=pixel,
        filter_byte=filter_byte,
        scanline=scanline,
        header=header,
        header_info=header_info,
        compressed=compressed,
        adler=adler,
        raw_deflate_with_adler=raw_deflate_with_adler,
        decompressed=decompressed,
        idat_decompressed=idat_decompressed,
        idat_decompressed_error=idat_decompressed_error,
    )


def _decompress_until_error_details(stream: bytes) -> tuple[bytes, bool, str, int | None]:
    decompressor = zlib.decompressobj()
    decompressed = bytearray()

    try:
        for offset, value in enumerate(stream):
            decompressed.extend(decompressor.decompress(bytes((value,))))
    except zlib.error as exc:
        return bytes(decompressed), False, str(exc), offset

    if not decompressor.eof:
        return bytes(decompressed), False, "incomplete zlib stream", len(stream)

    try:
        decompressed.extend(decompressor.flush())
    except zlib.error as exc:
        return bytes(decompressed), False, str(exc), None

    return bytes(decompressed), True, "", None


def _decompress_until_error(stream: bytes) -> tuple[bytes, bool, str]:
    decompressed, complete, error, _offset = _decompress_until_error_details(stream)
    return decompressed, complete, error


def _parse_ihdr(ihdr: png.PngChunk | None) -> tuple[int, int, int, int, int, int, int] | None:
    if ihdr is None or ihdr.chunk_type != b"IHDR" or ihdr.length != 13:
        return None
    return struct.unpack("!IIBBBBB", ihdr.data)


def _count_usable_scanlines(decompressed: bytes, scanline_size: int, height: int) -> tuple[int, int]:
    complete_scanlines = min(height, len(decompressed) // scanline_size)

    usable_scanlines = 0
    for row in range(complete_scanlines):
        if decompressed[row * scanline_size] not in range(5):
            break
        usable_scanlines += 1

    return complete_scanlines, usable_scanlines


def _adam7_pass_scanline_sizes(width: int, height: int, bit_depth: int, color_type: int) -> tuple[int, ...] | None:
    passes = (
        (0, 0, 8, 8),
        (4, 0, 8, 8),
        (0, 4, 4, 8),
        (2, 0, 4, 4),
        (0, 2, 2, 4),
        (1, 0, 2, 2),
        (0, 1, 1, 2),
    )
    scanline_sizes: list[int] = []
    for x_start, y_start, x_step, y_step in passes:
        pass_width = 0 if width <= x_start else (width - x_start + x_step - 1) // x_step
        pass_height = 0 if height <= y_start else (height - y_start + y_step - 1) // y_step
        if pass_width == 0 or pass_height == 0:
            continue
        scanline_size = png.png_scanline_size(pass_width, bit_depth, color_type)
        if scanline_size is None:
            return None
        scanline_sizes.extend([scanline_size] * pass_height)
    return tuple(scanline_sizes)


def _count_usable_variable_scanlines(decompressed: bytes, scanline_sizes: tuple[int, ...]) -> tuple[int, int, int]:
    offset = 0
    complete_scanlines = 0
    usable_scanlines = 0
    recovered_size = 0
    for scanline_size in scanline_sizes:
        if len(decompressed) - offset < scanline_size:
            break
        complete_scanlines += 1
        if decompressed[offset] not in range(5):
            break
        offset += scanline_size
        recovered_size = offset
        usable_scanlines += 1
    return complete_scanlines, usable_scanlines, recovered_size


def _idat_stream(chunks: list[png.PngChunk]) -> bytes:
    return b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")


def _first_chunk_payload(chunks: list[png.PngChunk], chunk_type: bytes) -> bytes | None:
    for chunk in chunks:
        if chunk.chunk_type == chunk_type:
            return chunk.data
    return None


def _safe_donor_strategy_label(label: str) -> str:
    stem = label.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if stem.lower().endswith(".png"):
        stem = stem[:-4]
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in stem)
    safe = safe.strip("._-")
    return safe[:64] or "local"


def _scaled_sample(value: int, maximum_input: int, bit_depth: int) -> int:
    if maximum_input <= 0:
        return 0
    return (value * ((1 << bit_depth) - 1)) // maximum_input


def _pack_subbyte_samples(samples: list[int], bit_depth: int) -> bytes:
    samples_per_byte = 8 // bit_depth
    mask = (1 << bit_depth) - 1
    out = bytearray()
    current = 0
    filled = 0
    for sample in samples:
        shift = 8 - bit_depth - (filled * bit_depth)
        current |= (sample & mask) << shift
        filled += 1
        if filled == samples_per_byte:
            out.append(current)
            current = 0
            filled = 0
    if filled:
        out.append(current)
    return bytes(out)


def _encode_png_samples(samples: list[int], bit_depth: int) -> bytes:
    if bit_depth < 8:
        return _pack_subbyte_samples(samples, bit_depth)
    if bit_depth == 8:
        return bytes(samples)
    if bit_depth == 16:
        return b"".join(sample.to_bytes(2, "big") for sample in samples)
    raise ValueError("unsupported PNG bit depth")


def _diagnostic_value(x: int, y: int, width: int, height: int, maximum: int) -> int:
    denominator = max(1, width + height - 2)
    return ((x + y) * maximum) // denominator


def _synthetic_pixel_samples(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
    palette_entries: int,
) -> list[int] | None:
    max_sample = (1 << bit_depth) - 1
    if color_type == 0:
        return [_diagnostic_value(x, y, width, height, max_sample)]
    if color_type == 2:
        return [
            _scaled_sample(x, width - 1, bit_depth),
            _scaled_sample(y, height - 1, bit_depth),
            _diagnostic_value(x, y, width, height, max_sample),
        ]
    if color_type == 3:
        max_index = min(max_sample, palette_entries - 1)
        if max_index < 0:
            return None
        return [_diagnostic_value(x, y, width, height, max_index)]
    if color_type == 4:
        return [
            _diagnostic_value(x, y, width, height, max_sample),
            max_sample,
        ]
    if color_type == 6:
        return [
            _scaled_sample(x, width - 1, bit_depth),
            _scaled_sample(y, height - 1, bit_depth),
            _diagnostic_value(x, y, width, height, max_sample),
            max_sample,
        ]
    return None


def _synthetic_diagnostic_scanlines(
    *,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
    palette_entries: int = 0,
) -> bytes | None:
    rows = bytearray()
    for y in range(height):
        samples: list[int] = []
        for x in range(width):
            pixel = _synthetic_pixel_samples(
                x=x,
                y=y,
                width=width,
                height=height,
                bit_depth=bit_depth,
                color_type=color_type,
                palette_entries=palette_entries,
            )
            if pixel is None:
                return None
            samples.extend(pixel)
        rows.append(0)
        try:
            rows.extend(_encode_png_samples(samples, bit_depth))
        except ValueError:
            return None
    return bytes(rows)


def normalize_truncated_idat_at_eof(data: bytes) -> TruncatedIdatNormalization | None:
    if not data.startswith(png.PNG_SIGNATURE):
        return None

    fixed = bytearray(png.PNG_SIGNATURE)
    pos = len(png.PNG_SIGNATURE)
    while pos + 8 <= len(data):
        chunk_offset = pos
        declared_length = struct.unpack("!I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        payload_start = pos + 8
        payload_end = payload_start + declared_length
        crc_end = payload_end + 4

        if crc_end <= len(data):
            fixed.extend(data[pos:crc_end])
            pos = crc_end
            continue

        if chunk_type != b"IDAT":
            return None

        available_payload = data[payload_start:]
        if len(available_payload) >= declared_length:
            return None

        fixed.extend(png.build_png_chunk(b"IDAT", available_payload))
        fixed.extend(png.IEND_CHUNK)
        return TruncatedIdatNormalization(
            data=bytes(fixed),
            declared_length=declared_length,
            available_length=len(available_payload),
            chunk_offset=chunk_offset,
            missing_bytes=declared_length - len(available_payload),
        )

    return None


def _tolerant_filter0_scanlines(
    decompressed: bytes,
    *,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
) -> TolerantScanlineSalvage | None:
    scanline_size = png.png_scanline_size(width, bit_depth, color_type)
    if scanline_size is None:
        return None

    row_data_size = scanline_size - 1
    bits_per_pixel = png.PNG_COLOR_SAMPLES[color_type] * bit_depth
    bytes_per_pixel = max(1, (bits_per_pixel + 7) // 8)
    complete_scanlines = min(height, len(decompressed) // scanline_size)

    previous = bytearray(row_data_size)
    rebuilt = bytearray()
    invalid_filter_rows: list[int] = []
    recovered_scanlines = 0
    repeated_rows = 0

    for row_index in range(height):
        if row_index >= complete_scanlines:
            rebuilt.extend(b"\x00" + bytes(previous))
            invalid_filter_rows.append(row_index)
            repeated_rows += 1
            continue

        row_start = row_index * scanline_size
        filter_type = decompressed[row_start]
        filtered_row = decompressed[row_start + 1 : row_start + scanline_size]
        row = bytearray(row_data_size)

        if filter_type not in range(5):
            rebuilt.extend(b"\x00" + bytes(previous))
            invalid_filter_rows.append(row_index)
            repeated_rows += 1
            continue

        for index, value in enumerate(filtered_row):
            left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = previous[index]
            up_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0

            if filter_type == 0:
                repaired = value
            elif filter_type == 1:
                repaired = value + left
            elif filter_type == 2:
                repaired = value + up
            elif filter_type == 3:
                repaired = value + ((left + up) // 2)
            else:
                repaired = value + png._paeth_predictor(left, up, up_left)

            row[index] = repaired & 0xFF

        rebuilt.extend(b"\x00" + bytes(row))
        previous = row
        recovered_scanlines += 1

    return TolerantScanlineSalvage(
        filtered_scanlines=bytes(rebuilt),
        recovered_scanlines=recovered_scanlines,
        total_scanlines=height,
        invalid_filter_rows=tuple(invalid_filter_rows),
        repeated_rows=repeated_rows,
    )


def _idat_stream_status(error: str, *, complete: bool, decompressed_size: int, expected_size: int) -> str:
    if complete and error == "" and decompressed_size == expected_size:
        return "complete"
    if error == "incomplete zlib stream":
        return "incomplete_stream"
    if "incorrect data check" in error:
        return "bad_adler"
    if error:
        return "corrupt_deflate"
    return "partial"


def _idat_error_location(
    idat_chunks: tuple[png.PngChunk, ...],
    error_offset: int | None,
) -> tuple[int | None, int | None, int | None]:
    if error_offset is None or not idat_chunks:
        return None, None, None

    remaining = max(0, error_offset)
    for index, chunk in enumerate(idat_chunks, start=1):
        if remaining < chunk.length:
            return index, remaining, chunk.offset + 8 + remaining
        remaining -= chunk.length

    if remaining == 0:
        last_chunk = idat_chunks[-1]
        return (
            len(idat_chunks),
            last_chunk.length,
            last_chunk.offset + 8 + last_chunk.length,
        )

    return None, None, None


def _idat_error_context(idat_stream: bytes, error_offset: int | None, radius: int = 8) -> str:
    if error_offset is None or not idat_stream:
        return ""

    center = min(max(0, error_offset), max(0, len(idat_stream) - 1))
    start = max(0, center - radius)
    end = min(len(idat_stream), center + radius + 1)
    return idat_stream[start:end].hex()


def zlib_trailer_adler(idat_stream: bytes) -> int | None:
    if len(idat_stream) < 6:
        return None
    if not zlib_header_info(idat_stream[:2].hex()).valid:
        return None
    return int.from_bytes(idat_stream[-4:], "big")


def format_adler(value: int | None) -> str:
    if value is None:
        return "unknown"
    return "0x%08x" % value


def _computed_adler_for_status(status: str, decompressed: bytes) -> int | None:
    if status in ("complete", "bad_adler"):
        return zlib.adler32(decompressed) & 0xFFFFFFFF
    return None


def _adler_status(
    *,
    stored_adler: int | None,
    computed_adler: int | None,
    target_adler: int | None,
    source_kind: str,
) -> str:
    if computed_adler is None:
        return "adler_unknown"
    if target_adler is not None:
        return "adler_match" if computed_adler == target_adler else "adler_mismatch"
    if stored_adler is None:
        return "adler_unknown"
    if source_kind in ("clone", "rebuilt_candidate"):
        return "adler_rebuilt" if computed_adler == stored_adler else "adler_mismatch"
    return "adler_match" if computed_adler == stored_adler else "adler_mismatch"


def _idat_crc_provenance(
    idat_chunks: tuple[png.PngChunk, ...],
    crc_provenance: str | None,
) -> str:
    if crc_provenance is not None:
        return crc_provenance
    if not idat_chunks:
        return "original_crc_bad"
    if all(chunk.crc_ok for chunk in idat_chunks):
        return "original_crc_ok"
    return "original_crc_bad"


def analyze_idat_stream(
    data: bytes,
    *,
    source_kind: str = "original",
    crc_provenance: str | None = None,
    target_adler: int | None = None,
) -> IdatStreamAnalysis:
    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError as exc:
        return IdatStreamAnalysis(
            False,
            False,
            "unsupported",
            reason=str(exc),
            crc_provenance=crc_provenance or "original_crc_bad",
            source_kind=source_kind,
        )

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    resolved_crc_provenance = _idat_crc_provenance(idat_chunks, crc_provenance)
    ihdr_values = _parse_ihdr(ihdr)
    if ihdr_values is None:
        return IdatStreamAnalysis(
            False,
            False,
            "unsupported",
            reason="IHDR is missing or malformed",
            crc_provenance=resolved_crc_provenance,
            source_kind=source_kind,
        )

    width, height, bit_depth, color_type, compression, filter_method, interlace = ihdr_values
    if width < 1 or height < 1:
        return IdatStreamAnalysis(
            False,
            False,
            "unsupported",
            reason="IHDR width/height must be positive",
            crc_provenance=resolved_crc_provenance,
            source_kind=source_kind,
        )
    if compression != 0 or filter_method != 0:
        return IdatStreamAnalysis(
            False,
            False,
            "unsupported",
            reason="unsupported IHDR compression/filter method",
            crc_provenance=resolved_crc_provenance,
            source_kind=source_kind,
        )
    if interlace != 0:
        return IdatStreamAnalysis(
            False,
            False,
            "unsupported_interlace",
            reason="interlaced PNG is not supported",
            crc_provenance=resolved_crc_provenance,
            source_kind=source_kind,
        )
    if not png.valid_png_color_depth(bit_depth, color_type):
        return IdatStreamAnalysis(
            False,
            False,
            "unsupported",
            reason="unsupported bit depth/color type",
            crc_provenance=resolved_crc_provenance,
            source_kind=source_kind,
        )

    scanline_size = png.png_scanline_size(width, bit_depth, color_type)
    if scanline_size is None:
        return IdatStreamAnalysis(
            False,
            False,
            "unsupported",
            reason="could not compute scanline size",
            crc_provenance=resolved_crc_provenance,
            source_kind=source_kind,
        )

    idat_stream = b"".join(chunk.data for chunk in idat_chunks)
    stored_adler = zlib_trailer_adler(idat_stream)
    expected_size = scanline_size * height
    base = {
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "color_type": color_type,
        "scanline_size": scanline_size,
        "expected_size": expected_size,
        "compressed_size": len(idat_stream),
        "idat_chunk_count": len(idat_chunks),
        "stored_adler": stored_adler,
        "crc_provenance": resolved_crc_provenance,
        "source_kind": source_kind,
    }

    if len(idat_stream) == 0:
        return IdatStreamAnalysis(False, False, "unsupported", reason="IDAT stream is missing", **base)

    if len(idat_stream) < 2 or not zlib_header_info(idat_stream[:2].hex()).valid:
        return IdatStreamAnalysis(
            True,
            False,
            "bad_zlib_header",
            reason="bad zlib header",
            **base,
        )

    decompressed, zlib_complete, error, error_offset = _decompress_until_error_details(idat_stream)
    error_idat_index, error_idat_offset, error_file_offset = _idat_error_location(
        idat_chunks,
        error_offset,
    )
    complete_scanlines, usable_scanlines = _count_usable_scanlines(decompressed, scanline_size, height)
    recovered_size = usable_scanlines * scanline_size
    status = _idat_stream_status(
        error,
        complete=zlib_complete,
        decompressed_size=len(decompressed),
        expected_size=expected_size,
    )
    complete = status == "complete" and usable_scanlines == height
    reason = error
    if status == "partial" and len(decompressed) != expected_size:
        reason = "zlib stream completed with unexpected decompressed size"
    elif status == "partial" and usable_scanlines != height:
        reason = "zlib stream completed with unusable scanlines"
    header_analysis = None
    if status == "corrupt_deflate" and len(decompressed) == 0:
        header_analysis = deflate_header.analyze_deflate_header(idat_stream)
    computed_adler = _computed_adler_for_status(status, decompressed)
    resolved_adler_status = _adler_status(
        stored_adler=stored_adler,
        computed_adler=computed_adler,
        target_adler=target_adler,
        source_kind=source_kind,
    )

    return IdatStreamAnalysis(
        True,
        complete,
        "complete" if complete else status,
        decompressed_size=len(decompressed),
        complete_scanlines=complete_scanlines,
        usable_scanlines=usable_scanlines,
        recovered_scanlines=decompressed[:recovered_size],
        zlib_error=error,
        error_offset=error_offset,
        error_idat_index=error_idat_index,
        error_idat_offset=error_idat_offset,
        error_file_offset=error_file_offset,
        error_context_hex=_idat_error_context(idat_stream, error_offset),
        reason=reason,
        deflate_header=header_analysis,
        computed_adler=computed_adler,
        adler_status=resolved_adler_status,
        **base,
    )


def analyze_partial_idat(data: bytes) -> PartialIdatAnalysis:
    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError as exc:
        return PartialIdatAnalysis(False, False, reason=str(exc))

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    ihdr_values = _parse_ihdr(ihdr)
    if ihdr_values is None:
        return PartialIdatAnalysis(False, False, reason="IHDR is missing or malformed")

    width, height, bit_depth, color_type, compression, filter_method, interlace = ihdr_values
    if width < 1 or height < 1:
        return PartialIdatAnalysis(False, False, reason="IHDR width/height must be positive")
    if compression != 0 or filter_method != 0:
        return PartialIdatAnalysis(False, False, reason="unsupported IHDR compression/filter method")
    if not png.valid_png_color_depth(bit_depth, color_type):
        return PartialIdatAnalysis(False, False, reason="unsupported bit depth/color type")

    scanline_sizes: tuple[int, ...]
    if interlace == 0:
        scanline_size = png.png_scanline_size(width, bit_depth, color_type)
        if scanline_size is None:
            return PartialIdatAnalysis(False, False, reason="could not compute scanline size")
        scanline_sizes = tuple([scanline_size] * height)
    elif interlace == 1:
        scanline_sizes = _adam7_pass_scanline_sizes(width, height, bit_depth, color_type) or ()
        scanline_size = 0
    else:
        return PartialIdatAnalysis(False, False, reason="unsupported IHDR interlace method")
    if not scanline_sizes:
        return PartialIdatAnalysis(False, False, reason="could not compute scanline size")

    idat_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    if len(idat_stream) == 0:
        return PartialIdatAnalysis(False, False, reason="IDAT stream is missing")

    decompressed, zlib_complete, error = _decompress_until_error(idat_stream)
    expected_size = sum(scanline_sizes)
    if interlace == 0:
        complete_scanlines, usable_scanlines = _count_usable_scanlines(decompressed, scanline_size, height)
        recovered_size = usable_scanlines * scanline_size
        total_scanlines = height
    else:
        complete_scanlines, usable_scanlines, recovered_size = _count_usable_variable_scanlines(decompressed, scanline_sizes)
        total_scanlines = len(scanline_sizes)
    complete = (
        zlib_complete
        and error == ""
        and len(decompressed) == expected_size
        and usable_scanlines == total_scanlines
    )

    return PartialIdatAnalysis(
        supported=True,
        complete=complete,
        width=width,
        height=height,
        bit_depth=bit_depth,
        color_type=color_type,
        scanline_size=scanline_size,
        expected_size=expected_size,
        decompressed_size=len(decompressed),
        complete_scanlines=complete_scanlines,
        usable_scanlines=usable_scanlines,
        recovered_scanlines=decompressed[:recovered_size],
        idat_stream_size=len(idat_stream),
        decompression_error=error,
        reason="" if complete or usable_scanlines > 0 else error,
    )


def rebuild_partial_idat_blackfill(data: bytes) -> PartialIdatBlackfillRepair | None:
    analysis = analyze_partial_idat(data)
    can_blackfill_from_short_valid_stream = (
        analysis.supported
        and not analysis.complete
        and analysis.decompression_error == ""
        and 0 <= analysis.decompressed_size < analysis.expected_size
    )
    if not analysis.partial and not can_blackfill_from_short_valid_stream:
        return None

    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError:
        return None

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    ihdr_values = _parse_ihdr(ihdr)
    if ihdr_values is None:
        return None
    _width, _height, bit_depth, color_type, _compression, _filter_method, interlace = ihdr_values
    if interlace == 0:
        scanline_sizes = tuple([analysis.scanline_size] * analysis.height)
    else:
        scanline_sizes = _adam7_pass_scanline_sizes(analysis.width, analysis.height, bit_depth, color_type) or ()
    if not scanline_sizes:
        return None

    blackfill_scanlines = b"".join(
        b"\x00" + (b"\x00" * (scanline_size - 1))
        for scanline_size in scanline_sizes[analysis.usable_scanlines :]
    )
    rebuilt_scanlines = analysis.recovered_scanlines + blackfill_scanlines
    rebuilt_idat = zlib.compress(rebuilt_scanlines)

    fixed = bytearray(png.PNG_SIGNATURE)
    idat_written = False
    for chunk in chunks:
        if chunk.chunk_type == b"IDAT":
            if not idat_written:
                fixed.extend(png.build_png_chunk(b"IDAT", rebuilt_idat))
                idat_written = True
            continue
        fixed.extend(png.build_png_chunk(chunk.chunk_type, chunk.data))

    return PartialIdatBlackfillRepair(
        data=bytes(fixed),
        strategy="partial-idat-blackfill recovered %s/%s scanlines"
        % (analysis.usable_scanlines, len(scanline_sizes)),
        recovered_scanlines=analysis.usable_scanlines,
        total_scanlines=len(scanline_sizes),
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
    )


def rebuild_visual_idat_preview(data: bytes) -> PartialIdatBlackfillRepair | None:
    analysis = analyze_partial_idat(data)
    if not analysis.supported or analysis.usable_scanlines <= 0:
        return None

    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError:
        return None

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    ihdr_values = _parse_ihdr(ihdr)
    if ihdr_values is None:
        return None
    _width, _height, bit_depth, color_type, _compression, _filter_method, interlace = ihdr_values
    if interlace == 0:
        scanline_sizes = tuple([analysis.scanline_size] * analysis.height)
    elif interlace == 1:
        scanline_sizes = _adam7_pass_scanline_sizes(analysis.width, analysis.height, bit_depth, color_type) or ()
    else:
        return None
    if not scanline_sizes:
        return None

    blackfill_scanlines = b"".join(
        b"\x00" + (b"\x00" * (scanline_size - 1))
        for scanline_size in scanline_sizes[analysis.usable_scanlines :]
    )
    rebuilt_scanlines = analysis.recovered_scanlines + blackfill_scanlines
    if len(rebuilt_scanlines) != analysis.expected_size:
        return None
    rebuilt_idat = zlib.compress(rebuilt_scanlines)

    fixed = bytearray(png.PNG_SIGNATURE)
    idat_written = False
    for chunk in chunks:
        if chunk.chunk_type == b"IDAT":
            if not idat_written:
                fixed.extend(png.build_png_chunk(b"IDAT", rebuilt_idat))
                idat_written = True
            continue
        fixed.extend(png.build_png_chunk(chunk.chunk_type, chunk.data))

    if not idat_written:
        return None
    fixed_data = bytes(fixed)
    if not png.validate_png_structure(fixed_data).ok:
        return None

    return PartialIdatBlackfillRepair(
        data=fixed_data,
        strategy="rebuilt_adler_preview recovered %s/%s scanlines"
        % (analysis.usable_scanlines, len(scanline_sizes)),
        recovered_scanlines=analysis.usable_scanlines,
        total_scanlines=len(scanline_sizes),
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
    )


def rebuild_idat_from_donor(
    data: bytes,
    donor_data: bytes,
    *,
    donor_label: str = "local",
    donor_path: str = "",
) -> IdatDonorRepair | None:
    source_analysis = analyze_partial_idat(data)
    if (
        not source_analysis.supported
        or source_analysis.complete
        or source_analysis.usable_scanlines != 0
    ):
        return None

    donor_analysis = analyze_partial_idat(donor_data)
    if (
        not donor_analysis.supported
        or not donor_analysis.complete
        or donor_analysis.width != source_analysis.width
        or donor_analysis.height != source_analysis.height
        or donor_analysis.bit_depth != source_analysis.bit_depth
        or donor_analysis.color_type != source_analysis.color_type
    ):
        return None

    try:
        source_chunks = list(png.iter_chunks(data))
        donor_chunks = list(png.iter_chunks(donor_data))
    except png.PngFormatError:
        return None

    source_ihdr = next((chunk for chunk in source_chunks if chunk.chunk_type == b"IHDR"), None)
    donor_ihdr = next((chunk for chunk in donor_chunks if chunk.chunk_type == b"IHDR"), None)
    if source_ihdr is None or donor_ihdr is None or source_ihdr.data != donor_ihdr.data:
        return None

    if source_analysis.color_type == 3:
        source_plte = _first_chunk_payload(source_chunks, b"PLTE")
        donor_plte = _first_chunk_payload(donor_chunks, b"PLTE")
        if source_plte is None or source_plte != donor_plte:
            return None

    donor_stream = _idat_stream(donor_chunks)
    if not donor_stream:
        return None

    try:
        donor_scanlines = zlib.decompress(donor_stream)
    except zlib.error:
        return None

    usable = _count_usable_scanlines(
        donor_scanlines,
        source_analysis.scanline_size,
        source_analysis.height,
    )[1]
    if len(donor_scanlines) != source_analysis.expected_size or usable != source_analysis.height:
        return None

    fixed = bytearray(png.PNG_SIGNATURE)
    idat_written = False
    for chunk in source_chunks:
        if chunk.chunk_type == b"IDAT":
            if not idat_written:
                fixed.extend(png.build_png_chunk(b"IDAT", donor_stream))
                idat_written = True
            continue
        fixed.extend(png.build_png_chunk(chunk.chunk_type, chunk.data))

    if not idat_written:
        return None

    fixed_data = bytes(fixed)
    if not png.validate_png_structure(fixed_data).ok:
        return None

    strategy_label = _safe_donor_strategy_label(donor_label)
    return IdatDonorRepair(
        data=fixed_data,
        strategy="idat-donor-%s" % strategy_label,
        donor_label=donor_label,
        donor_path=donor_path,
        width=source_analysis.width,
        height=source_analysis.height,
        bit_depth=source_analysis.bit_depth,
        color_type=source_analysis.color_type,
    )


def rebuild_synthetic_idat(data: bytes, *, pattern: str = "diagnostic") -> SyntheticIdatRepair | None:
    if pattern != "diagnostic":
        return None

    analysis = analyze_partial_idat(data)
    if not analysis.supported or analysis.complete or analysis.usable_scanlines != 0:
        return None

    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError:
        return None

    palette_entries = 0
    if analysis.color_type == 3:
        plte_payload = _first_chunk_payload(chunks, b"PLTE")
        if plte_payload is None or len(plte_payload) < 3 or len(plte_payload) % 3 != 0:
            return None
        palette_entries = len(plte_payload) // 3

    scanlines = _synthetic_diagnostic_scanlines(
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
        palette_entries=palette_entries,
    )
    if scanlines is None or len(scanlines) != analysis.expected_size:
        return None

    fixed = bytearray(png.PNG_SIGNATURE)
    idat_written = False
    rebuilt_idat = zlib.compress(scanlines)
    for chunk in chunks:
        if chunk.chunk_type == b"IDAT":
            if not idat_written:
                fixed.extend(png.build_png_chunk(b"IDAT", rebuilt_idat))
                idat_written = True
            continue
        fixed.extend(png.build_png_chunk(chunk.chunk_type, chunk.data))

    if not idat_written:
        return None

    fixed_data = bytes(fixed)
    if not png.validate_png_structure(fixed_data).ok:
        return None

    return SyntheticIdatRepair(
        data=fixed_data,
        strategy="idat-synthetic-diagnostic",
        synthetic_pattern=pattern,
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
    )


def rebuild_zero_scanline_placeholder(data: bytes) -> PartialIdatBlackfillRepair | None:
    analysis = analyze_partial_idat(data)
    if not analysis.supported or analysis.complete or analysis.usable_scanlines != 0:
        return None

    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError:
        return None

    placeholder_scanline = b"\x00" * analysis.scanline_size
    rebuilt_scanlines = placeholder_scanline * analysis.height
    rebuilt_idat = zlib.compress(rebuilt_scanlines)

    fixed = bytearray(png.PNG_SIGNATURE)
    idat_written = False
    for chunk in chunks:
        if chunk.chunk_type == b"IDAT":
            if not idat_written:
                fixed.extend(png.build_png_chunk(b"IDAT", rebuilt_idat))
                idat_written = True
            continue
        fixed.extend(png.build_png_chunk(chunk.chunk_type, chunk.data))

    if not idat_written:
        return None

    fixed_data = bytes(fixed)
    if not png.validate_png_structure(fixed_data).ok:
        return None

    return PartialIdatBlackfillRepair(
        data=fixed_data,
        strategy="zero-scanline-placeholder recovered 0/%s scanlines" % analysis.height,
        recovered_scanlines=0,
        total_scanlines=analysis.height,
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
    )


def rebuild_invalid_filter_type_as_filter0(data: bytes) -> PartialIdatBlackfillRepair | None:
    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError:
        return None

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    ihdr_values = _parse_ihdr(ihdr)
    if ihdr_values is None:
        return None

    width, height, bit_depth, color_type, compression, filter_method, interlace = ihdr_values
    if width < 1 or height < 1:
        return None
    if compression != 0 or filter_method != 0 or interlace != 0:
        return None
    if not png.valid_png_color_depth(bit_depth, color_type):
        return None

    scanline_size = png.png_scanline_size(width, bit_depth, color_type)
    if scanline_size is None:
        return None

    idat_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    if len(idat_stream) == 0:
        return None

    try:
        decompressed = zlib.decompress(idat_stream)
    except zlib.error:
        return None

    expected_size = scanline_size * height
    if len(decompressed) != expected_size:
        return None

    rebuilt_scanlines = bytearray(decompressed)
    invalid_rows: list[int] = []
    for row_index in range(height):
        filter_offset = row_index * scanline_size
        if rebuilt_scanlines[filter_offset] not in range(5):
            rebuilt_scanlines[filter_offset] = 0
            invalid_rows.append(row_index)

    if not invalid_rows:
        return None

    rebuilt_idat = zlib.compress(bytes(rebuilt_scanlines))
    fixed = bytearray(png.PNG_SIGNATURE)
    idat_written = False
    for chunk in chunks:
        if chunk.chunk_type == b"IDAT":
            if not idat_written:
                fixed.extend(png.build_png_chunk(b"IDAT", rebuilt_idat))
                idat_written = True
            continue
        fixed.extend(png.build_png_chunk(chunk.chunk_type, chunk.data))

    return PartialIdatBlackfillRepair(
        data=bytes(fixed),
        strategy="idat-filter0-normalize replaced %s invalid scanline filter bytes"
        % len(invalid_rows),
        recovered_scanlines=height,
        total_scanlines=height,
        width=width,
        height=height,
        bit_depth=bit_depth,
        color_type=color_type,
    )


def rebuild_tolerant_idat_salvage(data: bytes) -> PartialIdatBlackfillRepair | None:
    analysis = analyze_partial_idat(data)
    if not analysis.partial:
        return None

    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError:
        return None

    idat_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    decompressed, _zlib_complete, _error = _decompress_until_error(idat_stream)
    if len(decompressed) < analysis.expected_size:
        return None
    salvage = _tolerant_filter0_scanlines(
        decompressed,
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
    )
    if salvage is None:
        return None
    if not salvage.invalid_filter_rows:
        return None
    if salvage.recovered_scanlines <= analysis.usable_scanlines:
        return None

    rebuilt_idat = zlib.compress(salvage.filtered_scanlines)
    fixed = bytearray(png.PNG_SIGNATURE)
    idat_written = False
    for chunk in chunks:
        if chunk.chunk_type == b"IDAT":
            if not idat_written:
                fixed.extend(png.build_png_chunk(b"IDAT", rebuilt_idat))
                idat_written = True
            continue
        fixed.extend(png.build_png_chunk(chunk.chunk_type, chunk.data))

    return PartialIdatBlackfillRepair(
        data=bytes(fixed),
        strategy=(
            "partial-idat-tolerant-row-salvage decoded %s/%s scanlines; "
            "reused previous row for %s bad filter rows"
        )
        % (
            salvage.recovered_scanlines,
            salvage.total_scanlines,
            salvage.repeated_rows,
        ),
        recovered_scanlines=salvage.recovered_scanlines,
        total_scanlines=salvage.total_scanlines,
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
    )
