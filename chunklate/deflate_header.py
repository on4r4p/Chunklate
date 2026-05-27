from __future__ import annotations

from dataclasses import dataclass


CODE_LENGTH_ORDER = (16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15)


@dataclass(frozen=True)
class DeflateHeaderAnalysis:
    status: str
    bit_offset: int = 0
    byte_offset: int = 0
    bfinal: int | None = None
    btype: int | None = None
    hlit: int | None = None
    hdist: int | None = None
    hclen: int | None = None
    header_end_bit: int | None = None
    header_end_byte: int | None = None
    context_hex: str = ""
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def summary(self) -> str:
        parts = ["status=%s" % self.status]
        if self.byte_offset:
            parts.append("stream=0x%x" % self.byte_offset)
        if self.bit_offset:
            parts.append("bit=%s" % self.bit_offset)
        if self.btype is not None:
            parts.append("btype=%s" % self.btype)
        if self.hlit is not None:
            parts.append("HLIT=%s" % self.hlit)
        if self.hdist is not None:
            parts.append("HDIST=%s" % self.hdist)
        if self.hclen is not None:
            parts.append("HCLEN=%s" % self.hclen)
        if self.header_end_bit is not None:
            parts.append("header_end_bit=%s" % self.header_end_bit)
        if self.context_hex:
            parts.append("context=%s" % self.context_hex)
        if self.reason:
            parts.append("reason=%s" % self.reason)
        return "; ".join(parts)


class _NeedBits(Exception):
    pass


class _InvalidHuffman(Exception):
    pass


class BitReader:
    def __init__(self, data: bytes, *, start_byte: int = 0):
        self.data = data
        self.bit_offset = start_byte * 8

    def read(self, width: int) -> int:
        if width < 0:
            raise ValueError("width must be positive")
        value = 0
        for bit_index in range(width):
            byte_offset = self.bit_offset // 8
            if byte_offset >= len(self.data):
                raise _NeedBits
            bit = (self.data[byte_offset] >> (self.bit_offset % 8)) & 1
            value |= bit << bit_index
            self.bit_offset += 1
        return value

    @property
    def byte_offset(self) -> int:
        return self.bit_offset // 8


def _context(data: bytes, byte_offset: int, radius: int = 8) -> str:
    if not data:
        return ""
    center = min(max(0, byte_offset), max(0, len(data) - 1))
    start = max(0, center - radius)
    end = min(len(data), center + radius + 1)
    return data[start:end].hex()


def _bad(
    status: str,
    reader: BitReader | None,
    data: bytes,
    *,
    reason: str,
    bfinal: int | None = None,
    btype: int | None = None,
    hlit: int | None = None,
    hdist: int | None = None,
    hclen: int | None = None,
) -> DeflateHeaderAnalysis:
    bit_offset = reader.bit_offset if reader is not None else 0
    byte_offset = bit_offset // 8
    return DeflateHeaderAnalysis(
        status,
        bit_offset=bit_offset,
        byte_offset=byte_offset,
        bfinal=bfinal,
        btype=btype,
        hlit=hlit,
        hdist=hdist,
        hclen=hclen,
        context_hex=_context(data, byte_offset),
        reason=reason,
    )


def _reverse_bits(value: int, width: int) -> int:
    result = 0
    for _ in range(width):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result


def _validate_lengths(
    lengths: list[int],
    *,
    allow_single: bool = False,
    allow_incomplete: bool = False,
) -> str:
    used = [length for length in lengths if length > 0]
    if not used:
        return "empty Huffman tree"
    if len(used) == 1:
        return "" if allow_single else "single-symbol Huffman tree"

    max_bits = max(used)
    counts = [0] * (max_bits + 1)
    for length in used:
        counts[length] += 1

    left = 1
    for bits in range(1, max_bits + 1):
        left <<= 1
        left -= counts[bits]
        if left < 0:
            return "oversubscribed Huffman tree"
    if left > 0 and not allow_incomplete:
        return "incomplete Huffman tree"
    return ""


def _build_huffman_table(
    lengths: list[int],
    *,
    allow_single: bool = False,
    allow_incomplete: bool = False,
) -> tuple[dict[tuple[int, int], int], int]:
    validation_error = _validate_lengths(
        lengths,
        allow_single=allow_single,
        allow_incomplete=allow_incomplete,
    )
    if validation_error:
        raise _InvalidHuffman(validation_error)

    max_bits = max(lengths)
    counts = [0] * (max_bits + 1)
    for length in lengths:
        if length:
            counts[length] += 1

    next_code = [0] * (max_bits + 1)
    code = 0
    for bits in range(1, max_bits + 1):
        code = (code + counts[bits - 1]) << 1
        next_code[bits] = code

    table: dict[tuple[int, int], int] = {}
    for symbol, length in enumerate(lengths):
        if not length:
            continue
        canonical_code = next_code[length]
        next_code[length] += 1
        table[(_reverse_bits(canonical_code, length), length)] = symbol

    return table, max_bits


def _decode_symbol(reader: BitReader, table: dict[tuple[int, int], int], max_bits: int) -> int:
    code = 0
    for width in range(1, max_bits + 1):
        code |= reader.read(1) << (width - 1)
        symbol = table.get((code, width))
        if symbol is not None:
            return symbol
    raise _InvalidHuffman("code length stream contains an invalid symbol")


def _read_code_lengths(
    reader: BitReader,
    table: dict[tuple[int, int], int],
    max_bits: int,
    total: int,
) -> list[int]:
    lengths: list[int] = []
    while len(lengths) < total:
        symbol = _decode_symbol(reader, table, max_bits)
        if symbol <= 15:
            lengths.append(symbol)
            continue
        if symbol == 16:
            if not lengths:
                raise _InvalidHuffman("repeat code 16 has no previous length")
            repeat = reader.read(2) + 3
            lengths.extend([lengths[-1]] * repeat)
        elif symbol == 17:
            repeat = reader.read(3) + 3
            lengths.extend([0] * repeat)
        elif symbol == 18:
            repeat = reader.read(7) + 11
            lengths.extend([0] * repeat)
        else:
            raise _InvalidHuffman("invalid code length symbol %s" % symbol)

        if len(lengths) > total:
            raise _InvalidHuffman("code length repeat overflows the header")

    return lengths


def zlib_header_is_valid(stream: bytes) -> bool:
    if len(stream) < 2:
        return False
    cmf, flg = stream[0], stream[1]
    return (cmf & 0x0F) == 8 and (cmf >> 4) <= 7 and ((cmf << 8) + flg) % 31 == 0


def analyze_deflate_header(stream: bytes, *, zlib_wrapped: bool = True) -> DeflateHeaderAnalysis:
    start_byte = 2 if zlib_wrapped else 0
    if zlib_wrapped and not zlib_header_is_valid(stream):
        return DeflateHeaderAnalysis(
            "bad_zlib_header",
            byte_offset=0,
            context_hex=_context(stream, 0),
            reason="bad zlib header",
        )

    reader = BitReader(stream, start_byte=start_byte)
    try:
        bfinal = reader.read(1)
        btype = reader.read(2)
    except _NeedBits:
        return _bad("truncated_header", reader, stream, reason="truncated block header")

    if btype == 0:
        return DeflateHeaderAnalysis(
            "ok",
            bit_offset=reader.bit_offset,
            byte_offset=reader.byte_offset,
            bfinal=bfinal,
            btype=btype,
            header_end_bit=reader.bit_offset,
            header_end_byte=reader.byte_offset,
            context_hex=_context(stream, reader.byte_offset),
            reason="stored block header",
        )
    if btype == 1:
        return DeflateHeaderAnalysis(
            "ok",
            bit_offset=reader.bit_offset,
            byte_offset=reader.byte_offset,
            bfinal=bfinal,
            btype=btype,
            header_end_bit=reader.bit_offset,
            header_end_byte=reader.byte_offset,
            context_hex=_context(stream, reader.byte_offset),
            reason="fixed Huffman block",
        )
    if btype == 3:
        return _bad(
            "unsupported_block_type",
            reader,
            stream,
            reason="reserved deflate block type",
            bfinal=bfinal,
            btype=btype,
        )

    try:
        hlit = reader.read(5) + 257
        hdist = reader.read(5) + 1
        hclen = reader.read(4) + 4
    except _NeedBits:
        return _bad(
            "truncated_header",
            reader,
            stream,
            reason="truncated dynamic Huffman counts",
            bfinal=bfinal,
            btype=btype,
        )

    code_length_lengths = [0] * 19
    try:
        for index in range(hclen):
            code_length_lengths[CODE_LENGTH_ORDER[index]] = reader.read(3)
    except _NeedBits:
        return _bad(
            "truncated_header",
            reader,
            stream,
            reason="truncated code-length alphabet",
            bfinal=bfinal,
            btype=btype,
            hlit=hlit,
            hdist=hdist,
            hclen=hclen,
        )

    try:
        code_table, code_max_bits = _build_huffman_table(
            code_length_lengths,
            allow_single=True,
            allow_incomplete=True,
        )
        lengths = _read_code_lengths(reader, code_table, code_max_bits, hlit + hdist)
    except _NeedBits:
        return _bad(
            "truncated_header",
            reader,
            stream,
            reason="truncated dynamic Huffman lengths",
            bfinal=bfinal,
            btype=btype,
            hlit=hlit,
            hdist=hdist,
            hclen=hclen,
        )
    except _InvalidHuffman as exc:
        return _bad(
            "bad_code_length_tree",
            reader,
            stream,
            reason=str(exc),
            bfinal=bfinal,
            btype=btype,
            hlit=hlit,
            hdist=hdist,
            hclen=hclen,
        )

    literal_lengths = lengths[:hlit]
    distance_lengths = lengths[hlit:]
    literal_error = _validate_lengths(literal_lengths, allow_single=False)
    distance_error = _validate_lengths(distance_lengths, allow_single=True)
    if literal_error:
        return _bad(
            "invalid_huffman_lengths",
            reader,
            stream,
            reason="literal/length tree: %s" % literal_error,
            bfinal=bfinal,
            btype=btype,
            hlit=hlit,
            hdist=hdist,
            hclen=hclen,
        )
    if distance_error:
        return _bad(
            "invalid_huffman_lengths",
            reader,
            stream,
            reason="distance tree: %s" % distance_error,
            bfinal=bfinal,
            btype=btype,
            hlit=hlit,
            hdist=hdist,
            hclen=hclen,
        )
    if literal_lengths[256] == 0:
        return _bad(
            "invalid_huffman_lengths",
            reader,
            stream,
            reason="literal/length tree has no end-of-block symbol",
            bfinal=bfinal,
            btype=btype,
            hlit=hlit,
            hdist=hdist,
            hclen=hclen,
        )

    return DeflateHeaderAnalysis(
        "ok",
        bit_offset=reader.bit_offset,
        byte_offset=reader.byte_offset,
        bfinal=bfinal,
        btype=btype,
        hlit=hlit,
        hdist=hdist,
        hclen=hclen,
        header_end_bit=reader.bit_offset,
        header_end_byte=reader.byte_offset,
        context_hex=_context(stream, reader.byte_offset),
        reason="dynamic Huffman header",
    )
