from __future__ import annotations

import zlib
from dataclasses import dataclass


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
