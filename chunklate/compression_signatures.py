from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable
import bz2
import gzip
import importlib
import io
import lzma
import tarfile
import zipfile
import zlib


MAX_MISSING_PREFIX_BYTES = 3
CONTAINER_ENTRY_LIMIT = 16


@dataclass(frozen=True)
class DecodedMember:
    data: bytes
    member_name: str | None = None


@dataclass(frozen=True)
class CompressionFormat:
    name: str
    signatures: tuple[bytes, ...]
    decoder: Callable[[bytes, int | None], tuple[DecodedMember, ...]] | None
    order: int
    optional_module: str | None = None
    aliases: tuple[str, ...] = ()
    diagnostic_only: bool = False
    try_without_signature: bool = False
    container: bool = False
    max_missing_prefix_bytes: int = MAX_MISSING_PREFIX_BYTES


@dataclass(frozen=True)
class CompressionSignatureHit:
    format_name: str
    signature: bytes
    added_prefix: bytes
    missing_prefix_bytes: int
    signature_bytes_present: int
    order: int
    optional_module: str | None = None
    diagnostic_only: bool = False
    supported: bool = True


@dataclass(frozen=True)
class DecodedCompressionPayload:
    format_name: str
    decoded: bytes
    added_prefix: bytes
    missing_prefix_bytes: int
    signature: bytes
    signature_bytes_present: int
    order: int
    payload: bytes
    member_name: str | None = None
    container: bool = False
    optional_module: str | None = None


def _module_available(module_name: str | None) -> bool:
    if module_name is None:
        return True
    try:
        importlib.import_module(module_name)
    except ImportError:
        return False
    return True


def _bounded_output(data: bytes, max_output_size: int | None) -> bytes:
    if max_output_size is not None and len(data) > max_output_size:
        raise ValueError("decompressed output is larger than the expected PNG scanlines")
    return data


def _zlib_decompress(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    return (DecodedMember(_bounded_output(zlib.decompress(data), max_output_size)),)


def _raw_deflate_decompress(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    return (DecodedMember(_bounded_output(zlib.decompress(data, -15), max_output_size)),)


def _gzip_decompress(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    return (DecodedMember(_bounded_output(gzip.decompress(data), max_output_size)),)


def _bzip2_decompress(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    return (DecodedMember(_bounded_output(bz2.decompress(data), max_output_size)),)


def _xz_lzma_decompress(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    return (DecodedMember(_bounded_output(lzma.decompress(data), max_output_size)),)


def _zstd_decompress(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    zstandard = importlib.import_module("zstandard")
    decompressor = zstandard.ZstdDecompressor()
    with decompressor.stream_reader(io.BytesIO(data)) as reader:
        decoded = reader.read(-1 if max_output_size is None else max_output_size + 1)
    return (DecodedMember(_bounded_output(decoded, max_output_size)),)


def _brotli_decompress(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    brotli = importlib.import_module("brotli")
    return (DecodedMember(_bounded_output(brotli.decompress(data), max_output_size)),)


def _lz4_decompress(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    lz4_frame = importlib.import_module("lz4.frame")
    return (DecodedMember(_bounded_output(lz4_frame.decompress(data), max_output_size)),)


def _zip_members(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    members: list[DecodedMember] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if max_output_size is not None and info.file_size > max_output_size:
                continue
            with archive.open(info) as handle:
                payload = handle.read(-1 if max_output_size is None else max_output_size + 1)
            members.append(DecodedMember(_bounded_output(payload, max_output_size), info.filename))
            if len(members) >= CONTAINER_ENTRY_LIMIT:
                break
    return tuple(members)


def _tar_members_from_fileobj(
    fileobj: io.BytesIO,
    mode: str,
    max_output_size: int | None,
) -> tuple[DecodedMember, ...]:
    members: list[DecodedMember] = []
    with tarfile.open(fileobj=fileobj, mode=mode) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            if max_output_size is not None and member.size > max_output_size:
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            with handle:
                payload = handle.read(-1 if max_output_size is None else max_output_size + 1)
            members.append(DecodedMember(_bounded_output(payload, max_output_size), member.name))
            if len(members) >= CONTAINER_ENTRY_LIMIT:
                break
    return tuple(members)


def _tar_gzip_members(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    return _tar_members_from_fileobj(io.BytesIO(data), "r:gz", max_output_size)


def _tar_bzip2_members(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    return _tar_members_from_fileobj(io.BytesIO(data), "r:bz2", max_output_size)


def _tar_xz_members(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    return _tar_members_from_fileobj(io.BytesIO(data), "r:xz", max_output_size)


def _tar_from_decoded_bytes(decoded: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    return _tar_members_from_fileobj(io.BytesIO(decoded), "r:", max_output_size)


def _tar_zstd_members(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    decoded = _zstd_decompress(data, None)[0].data
    return _tar_from_decoded_bytes(decoded, max_output_size)


def _tar_brotli_members(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    decoded = _brotli_decompress(data, None)[0].data
    return _tar_from_decoded_bytes(decoded, max_output_size)


def _tar_lz4_members(data: bytes, max_output_size: int | None) -> tuple[DecodedMember, ...]:
    decoded = _lz4_decompress(data, None)[0].data
    return _tar_from_decoded_bytes(decoded, max_output_size)


BZIP2_SIGNATURES = tuple(b"BZh" + bytes((level,)) for level in b"123456789")


DECODABLE_FORMATS: tuple[CompressionFormat, ...] = (
    CompressionFormat(
        "zlib",
        (),
        _zlib_decompress,
        order=0,
        aliases=("deflate",),
        try_without_signature=True,
    ),
    CompressionFormat(
        "raw-deflate",
        (),
        _raw_deflate_decompress,
        order=1,
        aliases=("deflate",),
        try_without_signature=True,
    ),
    CompressionFormat("gzip", (b"\x1f\x8b\x08",), _gzip_decompress, order=2),
    CompressionFormat("bzip2", BZIP2_SIGNATURES, _bzip2_decompress, order=3),
    CompressionFormat("xz/lzma", (b"\xfd7zXZ\x00", b"\x5d\x00\x00"), _xz_lzma_decompress, order=4),
    CompressionFormat("zstd", (b"\x28\xb5\x2f\xfd",), _zstd_decompress, order=5, optional_module="zstandard"),
    CompressionFormat("brotli", (), _brotli_decompress, order=6, optional_module="brotli", try_without_signature=True),
    CompressionFormat("lz4", (b"\x04\x22\x4d\x18",), _lz4_decompress, order=7, optional_module="lz4.frame"),
    CompressionFormat(
        "zip",
        (b"PK\x03\x04",),
        _zip_members,
        order=8,
        aliases=("jar", "war", "ear", "apk"),
        container=True,
    ),
    CompressionFormat("tar.gz", (b"\x1f\x8b\x08",), _tar_gzip_members, order=9, container=True),
    CompressionFormat("tar.bz2", BZIP2_SIGNATURES, _tar_bzip2_members, order=10, container=True),
    CompressionFormat("tar.xz", (b"\xfd7zXZ\x00",), _tar_xz_members, order=11, container=True),
    CompressionFormat(
        "tar.zst",
        (b"\x28\xb5\x2f\xfd",),
        _tar_zstd_members,
        order=12,
        optional_module="zstandard",
        container=True,
    ),
    CompressionFormat(
        "tar.br",
        (),
        _tar_brotli_members,
        order=13,
        optional_module="brotli",
        try_without_signature=True,
        container=True,
    ),
    CompressionFormat(
        "tar.lz4",
        (b"\x04\x22\x4d\x18",),
        _tar_lz4_members,
        order=14,
        optional_module="lz4.frame",
        container=True,
    ),
)


DIAGNOSTIC_ONLY_FORMATS: tuple[CompressionFormat, ...] = (
    CompressionFormat("compress", (b"\x1f\x9d", b"\x1f\xa0"), None, order=100, diagnostic_only=True),
    CompressionFormat("lzip", (b"LZIP",), None, order=101, diagnostic_only=True),
    CompressionFormat("lrzip", (b"LRZI",), None, order=102, diagnostic_only=True),
    CompressionFormat("rzip", (b"RZIP",), None, order=103, diagnostic_only=True),
    CompressionFormat("lzop", (b"\x89LZO\x00\x0d\x0a\x1a\x0a",), None, order=104, diagnostic_only=True),
    CompressionFormat("snappy", (b"sNaPpY",), None, order=105, diagnostic_only=True),
    CompressionFormat("zpaq", (b"zPQ", b"7kSt"), None, order=106, diagnostic_only=True),
    CompressionFormat("7z", (b"7z\xbc\xaf\x27\x1c",), None, order=107, diagnostic_only=True),
    CompressionFormat("rar", (b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00"), None, order=108, diagnostic_only=True),
    CompressionFormat("arj", (b"\x60\xea",), None, order=109, diagnostic_only=True),
    CompressionFormat("cab", (b"MSCF",), None, order=110, diagnostic_only=True),
    CompressionFormat("ace", (b"**ACE**",), None, order=111, diagnostic_only=True),
    CompressionFormat("zoo", (b"ZOO", b"\xdc\xa7\xc4\xfd"), None, order=112, diagnostic_only=True),
    CompressionFormat("arc", (b"\x1a",), None, order=113, diagnostic_only=True),
    CompressionFormat("lha/lzh", (b"-lh", b"-lz"), None, order=114, diagnostic_only=True),
    CompressionFormat("sit/sitx", (b"SIT!", b"StuffIt", b"StuffIt X"), None, order=115, diagnostic_only=True),
)


COMPRESSION_DIAGNOSTIC_VOCABULARY: tuple[str, ...] = (
    "DCT",
    "Huffman",
    "Arithmetic coding",
    "RLE",
    "PackBits",
    "LZW",
    "Deflate",
    "Zlib",
    "LZ77",
    "LZ78",
    "Wavelet",
    "Delta encoding",
    "Predictive coding",
    "Palette indexing",
    "Chroma subsampling",
    "Vector quantization",
    "Block compression",
    "CCITT Group 3",
    "CCITT Group 4",
    "JBIG",
    "JBIG2",
    "Fax compression",
    "TGA RLE",
    "PCX RLE",
    "ILBM",
    "HAM",
    "SGI RLE",
)


def known_compression_formats() -> tuple[str, ...]:
    names: list[str] = []
    for compression_format in DECODABLE_FORMATS + DIAGNOSTIC_ONLY_FORMATS:
        names.append(compression_format.name)
        names.extend(compression_format.aliases)
    names.extend(COMPRESSION_DIAGNOSTIC_VOCABULARY)
    return tuple(dict.fromkeys(names))


def _payload_candidates(
    data: bytes,
    compression_format: CompressionFormat,
) -> Iterable[tuple[bytes, bytes, int, bytes, int]]:
    if compression_format.try_without_signature:
        yield data, b"", 0, b"", 0

    for signature in compression_format.signatures:
        max_missing = min(compression_format.max_missing_prefix_bytes, len(signature) - 1)
        for missing_prefix_bytes in range(0, max_missing + 1):
            present_suffix = signature[missing_prefix_bytes:]
            if not present_suffix or not data.startswith(present_suffix):
                continue
            added_prefix = signature[:missing_prefix_bytes]
            yield (
                added_prefix + data,
                added_prefix,
                missing_prefix_bytes,
                signature,
                len(signature) - missing_prefix_bytes,
            )


def detect_known_compression_signatures(data: bytes) -> tuple[CompressionSignatureHit, ...]:
    hits: list[CompressionSignatureHit] = []
    seen: set[tuple[str, bytes, int]] = set()
    for compression_format in DECODABLE_FORMATS + DIAGNOSTIC_ONLY_FORMATS:
        for _payload, added_prefix, missing, signature, present in _payload_candidates(data, compression_format):
            if not signature:
                continue
            key = (compression_format.name, signature, missing)
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                CompressionSignatureHit(
                    format_name=compression_format.name,
                    signature=signature,
                    added_prefix=added_prefix,
                    missing_prefix_bytes=missing,
                    signature_bytes_present=present,
                    order=compression_format.order,
                    optional_module=compression_format.optional_module,
                    diagnostic_only=compression_format.diagnostic_only,
                    supported=(
                        not compression_format.diagnostic_only
                        and _module_available(compression_format.optional_module)
                    ),
                )
            )
    return tuple(
        sorted(
            hits,
            key=lambda hit: (
                -hit.signature_bytes_present,
                hit.missing_prefix_bytes,
                hit.order,
                hit.format_name,
            ),
        )
    )


def decode_known_compression_payloads(
    data: bytes,
    *,
    max_output_size: int | None = None,
) -> tuple[DecodedCompressionPayload, ...]:
    decoded_payloads: list[DecodedCompressionPayload] = []
    seen_payloads: set[tuple[str, bytes, int, str | None]] = set()

    for compression_format in DECODABLE_FORMATS:
        if compression_format.decoder is None:
            continue
        if not _module_available(compression_format.optional_module):
            continue

        seen_candidates: set[tuple[bytes, bytes, int, bytes]] = set()
        for payload, added_prefix, missing, signature, present in _payload_candidates(data, compression_format):
            candidate_key = (payload, added_prefix, missing, signature)
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)

            try:
                members = compression_format.decoder(payload, max_output_size)
            except Exception:
                continue

            for member in members:
                key = (compression_format.name, member.data, missing, member.member_name)
                if key in seen_payloads:
                    continue
                seen_payloads.add(key)
                decoded_payloads.append(
                    DecodedCompressionPayload(
                        format_name=compression_format.name,
                        decoded=member.data,
                        added_prefix=added_prefix,
                        missing_prefix_bytes=missing,
                        signature=signature,
                        signature_bytes_present=present,
                        order=compression_format.order,
                        payload=payload,
                        member_name=member.member_name,
                        container=compression_format.container,
                        optional_module=compression_format.optional_module,
                    )
                )

    return tuple(
        sorted(
            decoded_payloads,
            key=lambda decoded: (
                -decoded.signature_bytes_present,
                decoded.missing_prefix_bytes,
                decoded.order,
                decoded.format_name,
                decoded.member_name or "",
            ),
        )
    )
