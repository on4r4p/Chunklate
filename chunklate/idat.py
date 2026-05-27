from __future__ import annotations

import zlib
from dataclasses import dataclass
import struct

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
    reason: str = ""

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


def analyze_idat_stream(data: bytes) -> IdatStreamAnalysis:
    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError as exc:
        return IdatStreamAnalysis(False, False, "unsupported", reason=str(exc))

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    ihdr_values = _parse_ihdr(ihdr)
    if ihdr_values is None:
        return IdatStreamAnalysis(False, False, "unsupported", reason="IHDR is missing or malformed")

    width, height, bit_depth, color_type, compression, filter_method, interlace = ihdr_values
    if width < 1 or height < 1:
        return IdatStreamAnalysis(False, False, "unsupported", reason="IHDR width/height must be positive")
    if compression != 0 or filter_method != 0:
        return IdatStreamAnalysis(False, False, "unsupported", reason="unsupported IHDR compression/filter method")
    if interlace != 0:
        return IdatStreamAnalysis(False, False, "unsupported_interlace", reason="interlaced PNG is not supported")
    if not png.valid_png_color_depth(bit_depth, color_type):
        return IdatStreamAnalysis(False, False, "unsupported", reason="unsupported bit depth/color type")

    scanline_size = png.png_scanline_size(width, bit_depth, color_type)
    if scanline_size is None:
        return IdatStreamAnalysis(False, False, "unsupported", reason="could not compute scanline size")

    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    idat_stream = b"".join(chunk.data for chunk in idat_chunks)
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
        reason=reason,
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
    if interlace != 0:
        return PartialIdatAnalysis(False, False, reason="interlaced PNG is not supported")
    if not png.valid_png_color_depth(bit_depth, color_type):
        return PartialIdatAnalysis(False, False, reason="unsupported bit depth/color type")

    scanline_size = png.png_scanline_size(width, bit_depth, color_type)
    if scanline_size is None:
        return PartialIdatAnalysis(False, False, reason="could not compute scanline size")

    idat_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    if len(idat_stream) == 0:
        return PartialIdatAnalysis(False, False, reason="IDAT stream is missing")

    decompressed, zlib_complete, error = _decompress_until_error(idat_stream)
    expected_size = scanline_size * height
    complete_scanlines, usable_scanlines = _count_usable_scanlines(decompressed, scanline_size, height)

    recovered_size = usable_scanlines * scanline_size
    complete = (
        zlib_complete
        and error == ""
        and len(decompressed) == expected_size
        and usable_scanlines == height
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
    if not analysis.partial:
        return None

    try:
        chunks = list(png.iter_chunks(data))
    except png.PngFormatError:
        return None

    black_scanline = b"\x00" + (b"\x00" * (analysis.scanline_size - 1))
    blackfill_count = analysis.height - analysis.usable_scanlines
    rebuilt_scanlines = analysis.recovered_scanlines + (black_scanline * blackfill_count)
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
        % (analysis.usable_scanlines, analysis.height),
        recovered_scanlines=analysis.usable_scanlines,
        total_scanlines=analysis.height,
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
    )
