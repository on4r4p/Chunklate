#!/usr/bin/env python3
import json
import sys
import struct
import tempfile
import zlib
import math
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import deflate_header
from chunklate import deflate_probe
from chunklate import gpu_runtime
from chunklate import idat
from chunklate import idat_bruteforce
from chunklate import idat_kraft_opengl_backend
from chunklate import ultimate_opengl_backend
from chunklate.png import (
    IEND_CHUNK,
    PNG_SIGNATURE,
    build_png_chunk,
    iter_chunks,
    repair_idat_marker_chain_from_visible_headers,
    repair_linefeed_conversion,
    repair_overlong_chunk_length_to_next_header,
    validate_png_structure,
)


def build_rgb_png(width, height, filtered_scanlines, *, idat_data=None, idat_parts=None, interlace=0):
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, interlace)
    if idat_data is None:
        idat_data = zlib.compress(filtered_scanlines)
    if idat_parts is None:
        idat_parts = (idat_data,)
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + b"".join(build_png_chunk(b"IDAT", part) for part in idat_parts)
        + IEND_CHUNK
    )


def dynamic_filtered_rows(height=100):
    return b"".join(
        b"\x00" + bytes(((row * 3) % 256, (row * 7) % 256, (row * 11) % 256))
        for row in range(height)
    )


def dynamic_header_corrupt_png():
    filtered = dynamic_filtered_rows()
    compressed = bytearray(zlib.compress(filtered, 1))
    original = compressed[3]
    compressed[3] ^= 1 << 5
    return build_rgb_png(1, 100, filtered, idat_data=bytes(compressed)), 3, original


def dynamic_header_two_bit_corrupt_png(*, bits=(604, 618)):
    filtered = dynamic_filtered_rows()
    compressed = bytearray(zlib.compress(filtered, 1))
    original = bytes(compressed)
    for bit in bits:
        compressed[bit // 8] ^= 1 << (bit % 8)
    return build_rgb_png(1, 100, filtered, idat_data=bytes(compressed)), tuple(sorted(bits)), original


def first_symbol_length_token_corrupt_png():
    width = 20
    height = 100
    filtered = bytearray()
    for row in range(height):
        filtered.append(row % 5)
        for x in range(width * 3):
            filtered.append((row * 9 + x * 7 + 9) % 256)
    original_stream = zlib.compress(bytes(filtered), 6)
    reader = deflate_header.BitReader(original_stream, start_byte=2)
    reader.read(1)
    assert reader.read(2) == 2
    literal_table, literal_max, _distance_table, _distance_max = deflate_probe._read_dynamic_tables(reader)
    first_symbol, bit_start, bit_end = deflate_header._decode_symbol_with_bits(reader, literal_table, literal_max)
    assert first_symbol in (0, 1, 2, 3, 4)
    width_bits = bit_end - bit_start
    codes = {
        symbol: (code, width)
        for (code, width), symbol in literal_table.items()
    }
    replacement_symbol = next(
        symbol
        for symbol in range(257, 286)
        if symbol in codes and codes[symbol][1] == width_bits
    )
    code, width_bits = codes[replacement_symbol]
    replacement_bits = tuple((code >> index) & 1 for index in range(width_bits))
    corrupt_stream = idat_bruteforce._replace_stream_bits_preserve_length(
        original_stream,
        bit_start,
        bit_end,
        replacement_bits,
    )
    assert corrupt_stream is not None
    return build_rgb_png(width, height, bytes(filtered), idat_data=corrupt_stream), original_stream


def early_backref_length_token_corrupt_png(*, count: int = 1):
    width = 20
    height = 100
    filtered = bytearray()
    for row in range(height):
        filtered.append(row % 5)
        factor = 5 if int(count) <= 1 else 10
        for x in range(width * 3):
            filtered.append((row * factor + x * 7 + factor) % 256)
    original_stream = zlib.compress(bytes(filtered), 6)
    reader = deflate_header.BitReader(original_stream, start_byte=2)
    reader.read(1)
    assert reader.read(2) == 2
    literal_table, literal_max, _distance_table, _distance_max = deflate_probe._read_dynamic_tables(reader)
    first_symbol, _first_start, _first_end = deflate_header._decode_symbol_with_bits(reader, literal_table, literal_max)
    assert first_symbol in (0, 1, 2, 3, 4)
    codes = {
        symbol: (code, width)
        for (code, width), symbol in literal_table.items()
    }
    replacements = []
    for _index in range(max(1, int(count))):
        symbol, bit_start, bit_end = deflate_header._decode_symbol_with_bits(reader, literal_table, literal_max)
        assert 0 <= symbol <= 255
        width_bits = bit_end - bit_start
        replacement_symbol = next(
            symbol
            for symbol in range(257, 286)
            if symbol in codes and codes[symbol][1] == width_bits
        )
        replacements.append((bit_start, bit_end, replacement_symbol))
    corrupt_stream = original_stream
    for bit_start, bit_end, replacement_symbol in replacements:
        code, width_bits = codes[replacement_symbol]
        replacement_bits = tuple((code >> index) & 1 for index in range(width_bits))
        corrupt_stream = idat_bruteforce._replace_stream_bits_preserve_length(
            corrupt_stream,
            bit_start,
            bit_end,
            replacement_bits,
        )
        assert corrupt_stream is not None
    corrupt = build_rgb_png(width, height, bytes(filtered), idat_data=corrupt_stream)
    raw_prefix = idat_bruteforce.idat_partial_raw_prefix(corrupt_stream, max_output=16)
    assert len(raw_prefix.raw) == 1
    assert raw_prefix.raw[0] in (0, 1, 2, 3, 4)
    assert idat_bruteforce._locate_first_invalid_distance_backref(corrupt_stream) is not None
    return corrupt, original_stream


def dynamic_header_extra_bit_png():
    filtered = dynamic_filtered_rows()
    compressed = zlib.compress(filtered, 1)
    bit_offset = 87
    corrupted = idat_bruteforce._shift_stream_insert_bit(compressed, bit_offset, 0)
    assert corrupted is not None
    return build_rgb_png(1, 100, filtered, idat_data=corrupted), bit_offset, compressed


def dynamic_header_semantic_token_corrupt_png():
    filtered = dynamic_filtered_rows()
    compressed = zlib.compress(filtered, 1)
    bit_start = 618
    bit_end = 619
    corrupted = idat_bruteforce._replace_stream_bits_preserve_length(
        compressed,
        bit_start,
        bit_end,
        (1, 1, 0),
    )
    assert corrupted is not None
    return build_rgb_png(1, 100, filtered, idat_data=corrupted), bit_start, compressed


def dynamic_header_natural_alphabet_corrupt_png():
    filtered = dynamic_filtered_rows()
    compressed = zlib.compress(filtered, 1)
    trace = deflate_header.trace_dynamic_header(compressed)
    assert trace.status == "ok"
    values_by_symbol = {symbol: value for symbol, value in enumerate(trace.code_length_lengths)}
    replacements = []
    for index, (_standard_symbol, bit_start, bit_end) in enumerate(trace.code_length_bits):
        natural_symbol = index
        new_value = values_by_symbol.get(natural_symbol, 0)
        old_value = idat_bruteforce._stream_bits_value(compressed, bit_start, bit_end)
        if new_value != old_value:
            replacements.append(
                (
                    bit_start,
                    bit_end,
                    idat_bruteforce._bits_for_lsb_code(new_value, bit_end - bit_start),
                )
            )
    corrupted = idat_bruteforce._apply_stream_bit_replacements(compressed, replacements)
    assert corrupted is not None
    return build_rgb_png(1, 100, filtered, idat_data=corrupted), tuple(
        bit_start for bit_start, _bit_end, _bits in replacements
    ), compressed


def dynamic_header_crc_guided_bitset_corrupt_png(*, bits=(604, 618), split=True):
    filtered = dynamic_filtered_rows()
    compressed = zlib.compress(filtered, 1)
    if split:
        png_data = build_rgb_png(
            1,
            100,
            filtered,
            idat_data=compressed,
            idat_parts=(compressed[:256], compressed[256:]),
        )
    else:
        png_data = build_rgb_png(1, 100, filtered, idat_data=compressed)
    candidate = bytearray(png_data)
    idat_chunks = [chunk for chunk in iter_chunks(png_data) if chunk.chunk_type == b"IDAT"]
    for bit in bits:
        remaining = bit // 8
        for chunk in idat_chunks:
            if remaining < chunk.length:
                candidate[chunk.offset + 8 + remaining] ^= 1 << (bit % 8)
                break
            remaining -= chunk.length
    return bytes(candidate), tuple(sorted(bits)), compressed


def dynamic_header_crc_guided_semantic_corrupt_png():
    filtered = dynamic_filtered_rows()
    compressed = zlib.compress(filtered, 1)
    corrupted = idat_bruteforce._replace_stream_bits_preserve_length(
        compressed,
        618,
        619,
        (1, 1, 0),
    )
    assert corrupted is not None
    png_data = build_rgb_png(1, 100, filtered, idat_data=compressed)
    candidate = bytearray(png_data)
    idat_chunk = next(chunk for chunk in iter_chunks(png_data) if chunk.chunk_type == b"IDAT")
    candidate[idat_chunk.offset + 8 : idat_chunk.offset + 8 + idat_chunk.length] = corrupted
    return bytes(candidate), (618,), compressed


def dynamic_header_crc_guided_diagnostic_only_png():
    filtered = dynamic_filtered_rows()
    compressed = bytearray(zlib.compress(filtered, 1))
    compressed[77] ^= 0x80
    png_data = build_rgb_png(1, 100, filtered, idat_data=bytes(compressed))
    candidate = bytearray(png_data)
    idat_chunk = next(chunk for chunk in iter_chunks(png_data) if chunk.chunk_type == b"IDAT")
    bit = 620
    candidate[idat_chunk.offset + 8 + bit // 8] ^= 1 << (bit % 8)
    return bytes(candidate), (bit,), bytes(compressed)


def visual_scope_png(width=96, height=64, *, variant="scope"):
    from io import BytesIO
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)
    if variant == "scope":
        for x in range(0, width, max(1, width // 8)):
            draw.line((x, 0, x, height), fill=(55, 55, 55, 255))
        for y in range(0, height, max(1, height // 6)):
            draw.line((0, y, width, y), fill=(45, 45, 45, 255))
        draw.rectangle((width * 3 // 4, 4, width - 4, height * 3 // 4), outline=(180, 180, 180, 255))
        draw.line((0, height * 3 // 4, width, height * 3 // 4), fill=(255, 180, 0, 255))
        draw.line(
            (
                width // 6,
                height * 2 // 3,
                width // 4,
                height // 4,
                width // 2,
                height // 4,
                width * 5 // 8,
                height * 2 // 3,
            ),
            fill=(210, 210, 0, 255),
            width=2,
        )
        draw.line((width // 9, height // 3, width // 9, height * 5 // 6), fill=(0, 220, 220, 255), width=2)
        draw.line((width * 4 // 5, height // 5, width * 4 // 5, height * 5 // 6), fill=(220, 0, 220, 255), width=2)
    else:
        for index in range(0, min(width, height), 7):
            draw.line((0, index, width, height - index), fill=(180, 20, 20, 255), width=2)
        draw.ellipse((width // 3, height // 3, width * 2 // 3, height * 2 // 3), outline=(20, 180, 20, 255), width=3)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def split_bytes(data, *sizes):
    parts = []
    offset = 0
    for size in sizes:
        parts.append(data[offset:offset + size])
        offset += size
    parts.append(data[offset:])
    return tuple(parts)


def truncate_idat_1_fixture_bytes():
    for path in (
        ROOT / "brokenjavapngsuite" / "truncate_idat_1.png",
        ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "truncate_idat_1.png",
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "truncate_idat_1.png",
    ):
        if path.exists():
            return path.read_bytes()
    raise FileNotFoundError("truncate_idat_1.png fixture not found")


def truncate_zlib_fixture_bytes():
    for path in (
        ROOT / "brokenjavapngsuite" / "truncate_zlib.png",
        ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "truncate_zlib.png",
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "truncate_zlib.png",
    ):
        if path.exists():
            return path.read_bytes()
    raise FileNotFoundError("truncate_zlib.png fixture not found")


def truncate_zlib_2_fixture_bytes():
    for path in (
        ROOT / "brokenjavapngsuite" / "truncate_zlib_2.png",
        ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "truncate_zlib_2.png",
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "truncate_zlib_2.png",
    ):
        if path.exists():
            return path.read_bytes()
    raise FileNotFoundError("truncate_zlib_2.png fixture not found")


def find_truncated_candidate(filtered, predicate, *, width=1, height=10):
    compressed = zlib.compress(filtered, level=0)
    for cut in range(2, len(compressed)):
        candidate = build_rgb_png(width, height, filtered, idat_data=compressed[:cut])
        analysis = idat.analyze_partial_idat(candidate)
        if predicate(analysis):
            return candidate, analysis
    raise AssertionError("could not build truncated IDAT candidate")


def test_dummy_scanline_preserves_legacy_sample_width():
    assert idat.dummy_scanline("8") == (
        b"\x01",
        b"\x00",
        b"\x00\x01\x01\x01",
    )
    assert idat.dummy_scanline("16") == (
        b"\x01\x00",
        b"\x00",
        b"\x00\x01\x00\x01\x00\x01\x00",
    )


def test_idat_zlib_header_skips_interlaced_streams_like_legacy_todo():
    assert idat.idat_zlib_header("789cabcd", "0") == "789c"
    assert idat.idat_zlib_header("789cabcd", "1") == ""


def test_zlib_header_info_reads_window_and_legacy_compression_level():
    best = idat.zlib_header_info("78da")
    default = idat.zlib_header_info("789c")
    invalid = idat.zlib_header_info("bad")

    assert best.valid is True
    assert best.cinfo == 7
    assert best.window_kb == 32
    assert best.flevel == 3
    assert best.compression_level == 9
    assert default.valid is True
    assert default.window_kb == 32
    assert default.compression_level == -1
    assert invalid.valid is False


def test_build_dummy_idat_probe_decompresses_debug_stream_and_idat_stream():
    stream_payload = b"\x00abc"
    probe = idat.build_dummy_idat_probe(
        zlib.compress(stream_payload).hex(),
        bit_depth="8",
        interlace="0",
    )

    assert probe.header == "789c"
    assert probe.scanline == b"\x00\x01\x01\x01"
    assert probe.decompressed == probe.scanline
    assert probe.idat_decompressed == stream_payload
    assert probe.idat_decompressed_error == ""


def test_build_dummy_idat_probe_reports_invalid_stream_without_raising():
    probe = idat.build_dummy_idat_probe("not-hex", bit_depth="8", interlace="0")

    assert probe.header == "not-"
    assert probe.decompressed == probe.scanline
    assert probe.idat_decompressed == b""
    assert probe.idat_decompressed_error != ""


def test_analyze_partial_idat_reports_complete_non_interlaced_stream():
    filtered = b"\x00abc" + b"\x00def"
    analysis = idat.analyze_partial_idat(build_rgb_png(1, 2, filtered))

    assert analysis.supported is True
    assert analysis.complete is True
    assert analysis.partial is False
    assert analysis.width == 1
    assert analysis.height == 2
    assert analysis.scanline_size == 4
    assert analysis.complete_scanlines == 2
    assert analysis.usable_scanlines == 2
    assert analysis.recovered_scanlines == filtered
    assert analysis.decompression_error == ""


def test_analyze_partial_idat_concatenates_complete_multi_idat_stream():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    compressed = zlib.compress(filtered)
    candidate = build_rgb_png(
        1,
        3,
        filtered,
        idat_data=compressed,
        idat_parts=split_bytes(compressed, 2, 4),
    )

    analysis = idat.analyze_partial_idat(candidate)

    assert analysis.supported is True
    assert analysis.complete is True
    assert analysis.partial is False
    assert analysis.usable_scanlines == 3
    assert analysis.recovered_scanlines == filtered
    assert analysis.idat_stream_size == len(compressed)


def test_analyze_partial_idat_keeps_good_scanlines_until_truncated_stream_error():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    _candidate, truncated = find_truncated_candidate(
        filtered,
        lambda analysis: analysis.usable_scanlines > 0 and analysis.decompression_error,
    )

    assert truncated.supported is True
    assert truncated.complete is False
    assert truncated.partial is True
    assert truncated.usable_scanlines >= 1
    assert truncated.recovered_scanlines.startswith(filtered[:4])
    assert truncated.decompression_error == "incomplete zlib stream"


def test_analyze_partial_idat_recovers_truncated_multi_idat_stream():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    compressed = zlib.compress(filtered, level=0)
    split = max(3, len(compressed) // 3)
    truncated_stream = compressed[:-3]
    candidate = build_rgb_png(
        1,
        10,
        filtered,
        idat_data=truncated_stream,
        idat_parts=split_bytes(truncated_stream, split, split),
    )

    analysis = idat.analyze_partial_idat(candidate)
    repair = idat.rebuild_partial_idat_blackfill(candidate)

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.partial is True
    assert analysis.usable_scanlines > 0
    assert analysis.recovered_scanlines.startswith(filtered[:4])
    assert analysis.decompression_error == "incomplete zlib stream"
    assert repair is not None
    assert validate_png_structure(repair.data).ok


def test_analyze_partial_idat_reports_bad_adler_with_recovered_scanlines():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(3))
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF

    analysis = idat.analyze_partial_idat(build_rgb_png(1, 3, filtered, idat_data=bytes(compressed)))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.partial is True
    assert analysis.usable_scanlines == 3
    assert analysis.recovered_scanlines == filtered
    assert analysis.decompression_error


def test_analyze_partial_idat_rejects_broken_zlib_header_without_scanlines():
    filtered = b"\x00abc"
    compressed = bytearray(zlib.compress(filtered))
    compressed[0] = 0
    compressed[1] = 0

    analysis = idat.analyze_partial_idat(build_rgb_png(1, 1, filtered, idat_data=bytes(compressed)))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.partial is False
    assert analysis.usable_scanlines == 0
    assert analysis.recovered_scanlines == b""
    assert analysis.decompression_error
    assert idat.rebuild_partial_idat_blackfill(build_rgb_png(1, 1, filtered, idat_data=bytes(compressed))) is None


def test_analyze_partial_idat_discards_partial_scanline_tail():
    scanline_size = 7
    filtered = b"".join(
        b"\x00" + bytes((row, row, row, row, row, row))
        for row in range(4)
    )
    _candidate, analysis = find_truncated_candidate(
        filtered,
        lambda analysis: (
            analysis.usable_scanlines >= 1
            and analysis.decompression_error
            and analysis.decompressed_size % scanline_size != 0
        ),
        width=2,
        height=4,
    )

    assert analysis.complete is False
    assert analysis.partial is True
    assert analysis.complete_scanlines == analysis.usable_scanlines
    assert len(analysis.recovered_scanlines) == analysis.usable_scanlines * scanline_size
    assert analysis.recovered_scanlines == filtered[:len(analysis.recovered_scanlines)]


def test_analyze_partial_idat_repairs_interlaced_stream_with_adam7_blackfill():
    filtered = b"\x00abc"
    compressed = zlib.compress(filtered)
    candidate = build_rgb_png(1, 1, filtered, idat_data=compressed[:-1], interlace=1)
    analysis = idat.analyze_partial_idat(candidate)
    repair = idat.rebuild_partial_idat_blackfill(candidate)

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.usable_scanlines == 1
    assert repair is not None
    assert repair.recovered_scanlines == 1
    assert repair.total_scanlines == 1
    assert validate_png_structure(repair.data).ok


def test_rebuild_partial_idat_blackfill_repairs_truncated_adam7_fixture():
    candidate = truncate_zlib_2_fixture_bytes()
    normalized = idat.normalize_truncated_idat_at_eof(candidate)

    assert normalized is not None
    repair = idat.rebuild_partial_idat_blackfill(normalized.data)

    assert repair is not None
    assert repair.strategy == "partial-idat-blackfill recovered 113/131 scanlines"
    assert repair.width == 91
    assert repair.height == 69
    assert repair.recovered_scanlines == 113
    assert repair.total_scanlines == 131
    assert validate_png_structure(repair.data).ok


def test_analyze_partial_idat_reports_invalid_stream_without_scanlines():
    analysis = idat.analyze_partial_idat(build_rgb_png(1, 1, b"\x00abc", idat_data=b"bad"))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.partial is False
    assert analysis.usable_scanlines == 0
    assert analysis.recovered_scanlines == b""
    assert analysis.decompression_error != ""


def test_rebuild_partial_idat_blackfill_keeps_prefix_and_fills_remaining_rows():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    compressed = zlib.compress(filtered)
    repair = None
    for cut in range(2, len(compressed)):
        candidate = build_rgb_png(1, 10, filtered, idat_data=compressed[:cut])
        repair = idat.rebuild_partial_idat_blackfill(candidate)
        if repair is not None:
            break

    assert repair is not None
    assert "partial-idat-blackfill" in repair.strategy
    assert repair.recovered_scanlines >= 1
    assert repair.total_scanlines == 10
    assert validate_png_structure(repair.data).ok

    chunks = list(iter_chunks(repair.data))
    rebuilt_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    rebuilt_filtered = zlib.decompress(rebuilt_stream)
    recovered_size = repair.recovered_scanlines * 4

    assert rebuilt_filtered[:recovered_size] == filtered[:recovered_size]
    assert rebuilt_filtered[recovered_size:] == b"\x00\x00\x00\x00" * (
        10 - repair.recovered_scanlines
    )


def test_rebuild_partial_idat_blackfill_handles_valid_empty_stream():
    empty_stream_png = build_rgb_png(1, 2, b"\x00abc\x00def", idat_data=zlib.compress(b""))

    repair = idat.rebuild_partial_idat_blackfill(empty_stream_png)

    assert repair is not None
    assert repair.strategy == "partial-idat-blackfill recovered 0/2 scanlines"
    assert repair.recovered_scanlines == 0
    assert repair.total_scanlines == 2
    assert validate_png_structure(repair.data).ok

    chunks = list(iter_chunks(repair.data))
    rebuilt_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    assert zlib.decompress(rebuilt_stream) == b"\x00\x00\x00\x00" * 2


def test_rebuild_idat_from_donor_replaces_zero_scanline_idat():
    broken = truncate_idat_1_fixture_bytes()
    donor = (ROOT / "schaik-javapng-samples" / "basn0g01.png").read_bytes()

    repair = idat.rebuild_idat_from_donor(
        broken,
        donor,
        donor_label="basn0g01.png",
        donor_path="schaik-javapng-samples/basn0g01.png",
    )

    assert repair is not None
    assert repair.strategy == "idat-donor-basn0g01"
    assert repair.width == 32
    assert repair.height == 32
    assert validate_png_structure(repair.data).ok

    fixed_stream = b"".join(
        chunk.data for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"IDAT"
    )
    donor_stream = b"".join(
        chunk.data for chunk in iter_chunks(donor) if chunk.chunk_type == b"IDAT"
    )
    assert zlib.decompress(fixed_stream) == zlib.decompress(donor_stream)


def test_rebuild_idat_from_donor_rejects_incompatible_shape():
    broken = truncate_idat_1_fixture_bytes()
    incompatible = build_rgb_png(1, 1, b"\x00abc")

    assert idat.rebuild_idat_from_donor(broken, incompatible) is None


def test_rebuild_synthetic_idat_builds_diagnostic_image_from_ihdr():
    broken = truncate_idat_1_fixture_bytes()

    repair = idat.rebuild_synthetic_idat(broken)

    assert repair is not None
    assert repair.strategy == "idat-synthetic-diagnostic"
    assert repair.width == 32
    assert repair.height == 32
    assert validate_png_structure(repair.data).ok

    stream = b"".join(chunk.data for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"IDAT")
    raw = zlib.decompress(stream)
    assert len(raw) == 160
    assert raw != b"\x00" * 160


def test_normalize_truncated_idat_at_eof_rebuilds_analyzable_png():
    broken = truncate_zlib_fixture_bytes()

    normalized = idat.normalize_truncated_idat_at_eof(broken)

    assert normalized is not None
    assert normalized.declared_length == 433
    assert normalized.available_length == 24
    assert normalized.missing_bytes == 409
    assert validate_png_structure(normalized.data, require_decodable_idat=False).ok
    assert not validate_png_structure(normalized.data).ok
    analysis = idat.analyze_partial_idat(normalized.data)
    assert analysis.supported is True
    assert analysis.usable_scanlines == 0


def test_rebuild_zero_scanline_placeholder_handles_truncated_zlib_normalization():
    broken = truncate_zlib_fixture_bytes()
    normalized = idat.normalize_truncated_idat_at_eof(broken)
    assert normalized is not None

    repair = idat.rebuild_zero_scanline_placeholder(normalized.data)

    assert repair is not None
    assert repair.strategy == "zero-scanline-placeholder recovered 0/32 scanlines"
    assert validate_png_structure(repair.data).ok
    stream = b"".join(chunk.data for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"IDAT")
    raw = zlib.decompress(stream)
    assert raw == b"\x00" * 1056


def test_rebuild_tolerant_idat_salvage_keeps_rows_after_bad_filters():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None
    realigned = repair_overlong_chunk_length_to_next_header(linefeed.data)
    assert realigned is not None

    blackfill = idat.rebuild_partial_idat_blackfill(realigned.data)
    repair = idat.rebuild_tolerant_idat_salvage(realigned.data)

    assert blackfill is not None
    assert blackfill.recovered_scanlines == 145
    assert repair is not None
    assert repair.recovered_scanlines == 495
    assert repair.total_scanlines == 503
    assert "reused previous row for 8 bad filter rows" in repair.strategy
    assert validate_png_structure(repair.data).ok

    chunks = list(iter_chunks(repair.data))
    rebuilt_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    rebuilt_filtered = zlib.decompress(rebuilt_stream)

    assert len(rebuilt_filtered) == 503 * 2401
    assert {rebuilt_filtered[row * 2401] for row in range(503)} == {0}
    assert rebuilt_filtered[145 * 2401 : 146 * 2401] == rebuilt_filtered[144 * 2401 : 145 * 2401]


def test_idat_marker_chain_repair_preserves_valid_idat_chunks_byte_for_byte():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None

    repairs = repair_idat_marker_chain_from_visible_headers(linefeed.data)

    assert repairs
    best = repairs[0]
    assert "IDAT@0x21" in best.preserved_chunks
    assert "IDAT@0x202d" in best.rebuilt_chunks
    assert validate_png_structure(best.data, require_decodable_idat=False).ok

    repaired_first_idat = next(chunk for chunk in iter_chunks(best.data) if chunk.chunk_type == b"IDAT")
    original_first_idat = linefeed.data[
        repaired_first_idat.offset : repaired_first_idat.offset + 12 + repaired_first_idat.length
    ]
    rebuilt_first_idat = best.data[
        repaired_first_idat.offset : repaired_first_idat.offset + 12 + repaired_first_idat.length
    ]

    assert rebuilt_first_idat == original_first_idat


def test_idat_marker_chain_repair_generates_declared_payload_and_shorten_variants():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None

    repairs = repair_idat_marker_chain_from_visible_headers(linefeed.data)

    assert len(repairs) == 2
    assert any(repair.declared_payload_chunks == ("IDAT@0x202d",) for repair in repairs)
    assert any(repair.shortened_chunks == ("IDAT@0x202d",) for repair in repairs)
    assert all("XBt" not in ",".join(repair.rebuilt_chunks) for repair in repairs)
    assert all(validate_png_structure(repair.data, require_decodable_idat=False).ok for repair in repairs)


def test_idat_marker_chain_fixture_prefers_declared_payload_visual_salvage():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None

    repairs = repair_idat_marker_chain_from_visible_headers(linefeed.data)
    declared = next(repair for repair in repairs if repair.declared_payload_chunks)
    shortened = next(repair for repair in repairs if repair.shortened_chunks)
    declared_salvage = idat.rebuild_tolerant_idat_salvage(declared.data)
    shortened_salvage = idat.rebuild_tolerant_idat_salvage(shortened.data)

    assert declared_salvage is not None
    assert shortened_salvage is not None
    assert declared_salvage.recovered_scanlines == 498
    assert shortened_salvage.recovered_scanlines == 495


def test_idat_linefeed_cr_insert_probe_improves_salvage_candidate():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None
    realigned = repair_overlong_chunk_length_to_next_header(linefeed.data)
    assert realigned is not None
    first_error_offset = idat_bruteforce.first_idat_problem_stream_offset(realigned.data)
    assert first_error_offset == 0x3EE9

    result = idat_bruteforce.probe_idat_linefeed_cr_insertions(
        realigned.data,
        window_radius=4096,
    )

    assert result.best is not None
    assert result.strategy == "linefeed-cr-insert"
    assert result.before.usable_scanlines == 145
    assert result.best.after.usable_scanlines == 503

    repair = idat.rebuild_partial_idat_blackfill(result.best.data)
    assert repair is not None
    assert repair.recovered_scanlines == 503
    assert repair.total_scanlines == 503
    assert validate_png_structure(repair.data).ok

    full = idat_bruteforce.probe_idat_linefeed_cr_insertions_full(
        result.best.data,
        start_offset=first_error_offset,
    )
    assert full.strategy == "linefeed-cr-insert-full"
    assert full.window_start == first_error_offset
    assert full.tested_candidates > 0

    super_probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        result.best.data,
        start_offset=first_error_offset,
        linefeed_budget=100,
        structural_budget=100,
        local_bit_budget=32,
        local_byte_budget=64,
        heavy_byte_budget=64,
        beam_width=2,
        max_depth=1,
    )
    assert super_probe.strategy == "SuperMegaLineFeedForceOfDeath"
    assert super_probe.error_anchor_offset == first_error_offset
    assert super_probe.pre_error_backtrack == idat_bruteforce.adaptive_pre_error_backtrack(super_probe.window_end)
    assert super_probe.search_start_offset == max(0, first_error_offset - super_probe.pre_error_backtrack)
    assert super_probe.tested_candidates > full.tested_candidates
    assert super_probe.target_adler is not None
    assert super_probe.state_count >= 1
    assert super_probe.visited_count >= super_probe.state_count
    assert {phase.name for phase in super_probe.phases} >= {
        "phase1-linefeed-global",
        "phase2-crlf-structural",
        "phase3-deflate-bit",
        "phase3-deflate-byte",
        "phase4-heavy-byte-window",
        "phase5-adler-target",
    }
    summary = idat_bruteforce.super_mega_linefeed_probe_summary_line(super_probe)
    assert "SuperMegaLineFeedForceOfDeath" in summary
    assert "target_adler=0x" in summary
    assert "source_crc=" in summary


def test_super_mega_linefeed_force_recovers_multiple_crlf_deletions():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    assert len(crlf_offsets) >= 2
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    assert start_offset is not None

    probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        corrupt,
        start_offset=start_offset,
        pre_error_backtrack=64,
        linefeed_budget=100,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        beam_width=4,
        max_depth=4,
    )

    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_match"
    assert len(probe.best.operations) == 2
    assert [operation.kind for operation in probe.best.operations] == [
        "insert-cr-before-lf",
        "insert-cr-before-lf",
    ]
    assert probe.states[0].state_id == 0
    assert probe.best.parent_id is not None
    assert probe.best.source_offsets == tuple(operation.stream_offset for operation in probe.best.operations)
    assert probe.visited_count <= probe.tested_candidates + 1
    assert zlib.decompress(b"".join(chunk.data for chunk in iter_chunks(probe.best.data) if chunk.chunk_type == b"IDAT")) == filtered


def test_linefeed_lf_insert_mutations_insert_lf_near_error():
    stream = b"abcdef"

    mutations = list(
        idat_bruteforce._linefeed_lf_insert_mutations(
            stream,
            center=2,
            search_start=0,
            backtrack=2,
            forward=1,
        )
    )

    assert mutations[0] == (
        b"ab\ncdef",
        idat_bruteforce.SuperMegaLinefeedOperation("insert-lf-near-error", 2, b"", b"\n"),
    )
    assert idat_bruteforce._count_linefeed_lf_insert_mutations(
        stream,
        center=2,
        search_start=0,
        backtrack=2,
        forward=1,
    ) == 4


def test_ultimate_operation_pool_includes_direct_lf_insertions():
    operations = idat_bruteforce._ultimate_operation_pool(
        b"abcdef",
        (2,),
        target_adler=None,
        computed_adler=None,
    )

    assert idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-lf", 2, b"", b"\n") in operations


def test_idat_crc_evidence_summary_reports_stored_crc_mismatches():
    clean = build_rgb_png(1, 1, b"\x00abc")
    chunk = next(chunk for chunk in iter_chunks(clean) if chunk.chunk_type == b"IDAT")
    crc_start = chunk.offset + 8 + chunk.length
    corrupt_crc = clean[:crc_start] + b"\x12\x34\x56\x78" + clean[crc_start + 4 :]

    lines = idat_bruteforce.idat_crc_evidence_summary_lines(corrupt_crc)

    assert lines[0].startswith("-IDAT CRC evidence: chunks=1; current_crc_ok=0; stored_crc_mismatch=1")
    assert "stored=12345678" in lines[1]
    assert "stored-original?" in lines[1]


def test_super_mega_linefeed_force_uses_known_gap_phase_before_broad_search():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    assert len(crlf_offsets) >= 2
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        corrupt,
        start_offset=start_offset,
        known_gap_bytes=2,
        known_gap_window_start=0,
        known_gap_window_end=len(compressed),
        known_gap_budget=256,
        linefeed_budget=0,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        adler_budget=0,
        beam_width=1,
        max_depth=1,
    )

    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_match"
    assert probe.phases[0].name == "phase0-known-gap-linefeed"
    assert probe.best.operations[0].kind == "known-gap-insert-2-crs-before-lfs"


def test_super_mega_linefeed_force_reports_budget_exhausted_but_keeps_best_candidate():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        corrupt,
        start_offset=start_offset,
        pre_error_backtrack=64,
        linefeed_budget=1,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        beam_width=1,
        max_depth=4,
    )

    assert probe.budget_exhausted is True
    assert probe.best is not None
    assert probe.best.after.usable_scanlines >= probe.before.usable_scanlines


def test_super_mega_linefeed_force_keeps_best_when_original_adler_target_is_wrong():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))

    probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        corrupt,
        start_offset=len(compressed) - 4,
        linefeed_budget=0,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        adler_budget=4,
        beam_width=1,
        max_depth=1,
    )

    assert probe.target_adler is not None
    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_mismatch"
    assert probe.best.after.crc_provenance == "rebuilt_by_chunklate"
    assert "set-zlib-trailer-to-computed-adler" in idat_bruteforce.super_mega_linefeed_candidate_summary_line(probe.best)
    assert "original Adler target was not recovered" in idat_bruteforce.super_mega_linefeed_probe_summary_line(probe)


def test_ultimate_linefeed_suspect_offsets_prioritize_error_and_linefeeds():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    offsets = idat_bruteforce.ultimate_linefeed_suspect_offsets(
        corrupt,
        start_offset=start_offset,
        max_offsets=8,
    )

    assert start_offset in offsets
    assert any(bytes(compressed)[offset] == 0x0A for offset in offsets if offset < len(compressed))


def test_ultimate_linefeed_estimate_counts_theoretical_combinations():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    estimate = idat_bruteforce.estimate_ultimate_linefeed_search(
        corrupt,
        start_offset=start_offset,
        max_depth=4,
        max_offsets=8,
    )

    assert estimate.operation_count > 0
    assert estimate.suspect_offsets
    assert estimate.total_combinations == sum(
        math.comb(estimate.operation_count, depth)
        for depth in range(1, min(estimate.operation_count, 4) + 1)
    )


def test_ultimate_linefeed_estimate_merges_gpu_suspect_offsets_first():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    gpu_offset = max(0, len(compressed) - 4)

    estimate = idat_bruteforce.estimate_ultimate_linefeed_search(
        corrupt,
        start_offset=start_offset,
        max_depth=4,
        max_offsets=8,
        gpu_suspect_offsets=(gpu_offset,),
    )

    assert estimate.suspect_offsets[0] == gpu_offset
    assert start_offset in estimate.suspect_offsets
    assert estimate.operation_count > 0


def test_ultimate_linefeed_budget_modes_apply_divisors_without_upper_cap():
    total = 7_012_540_641

    assert idat_bruteforce.ultimate_linefeed_combination_count(5, 4) == 30
    assert idat_bruteforce._combination_indices_at_rank(5, 3, 0) == (0, 1, 2)
    assert idat_bruteforce._combination_indices_at_rank(5, 3, 1) == (0, 1, 3)
    assert idat_bruteforce._combination_indices_at_rank(5, 3, 9) == (2, 3, 4)
    assert idat_bruteforce._combination_indices_at_rank(5, 3, 10) is None
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "quick").budget == 70_126
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "normal").budget == 140_251
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "deep").budget == 701_255
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "very deep").budget == 7_012_541
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "very_deep").budget == 7_012_541
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "deeeeeeep").budget == 70_125_407
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "abyssal").budget == 701_254_065
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "inception").budget == 3_506_270_321
    assert idat_bruteforce.ultimate_linefeed_budget_decision(100, "normal").budget == 100
    assert idat_bruteforce.ultimate_linefeed_budget_decision(10**15, "deep").budget == 100_000_000_000

    manual = idat_bruteforce.ultimate_linefeed_budget_decision(total, "manual", manual_budget=1234)
    unbounded = idat_bruteforce.ultimate_linefeed_budget_decision(total, "unbounded")
    aborted = idat_bruteforce.ultimate_linefeed_budget_decision(total, "abort")

    assert manual.budget == 1234
    assert unbounded.budget is None
    assert unbounded.coverage == 100.0
    assert aborted.aborted is True
    try:
        idat_bruteforce.ultimate_linefeed_budget_decision(total, "manual", manual_budget=0)
    except ValueError:
        pass
    else:
        raise AssertionError("manual budget zero should be rejected")


def test_ultimate_progress_round_trips_parallel_shards(tmp_path):
    progress_path = str(tmp_path / "_ULF.progress.json")
    shard = {
        "pool_index": 1,
        "depth": 3,
        "start_rank": 50_000,
        "end_rank": 100_000,
        "next_rank": 75_000,
        "tested": 25_000,
        "pruned": 12,
        "status": "pending",
    }

    idat_bruteforce._write_ultimate_progress(
        progress_path,
        source_hash="source",
        target_adler=1234,
        start_offset=42,
        max_depth=4,
        max_offsets=8,
        operation_pool_hash="merged",
        focused_operation_pool_hash="focused",
        broad_operation_pool_hash="broad",
        phase="exhaustive",
        depth=3,
        pool_index=1,
        combination_rank=75_000,
        combination_indices=(1, 2, 3),
        tested_candidates=25_000,
        pruned_candidates=12,
        state_count=9,
        budget=100_000,
        parallel_workers=3,
        shard_size=50_000,
        shards=(shard,),
        attempted_candidates=90_000,
    )

    loaded, warning = idat_bruteforce._load_ultimate_progress(
        progress_path,
        source_hash="source",
        target_adler=1234,
        start_offset=42,
        max_depth=4,
        max_offsets=8,
        operation_pool_hash="merged",
        focused_operation_pool_hash="focused",
        broad_operation_pool_hash="broad",
    )

    assert warning == ""
    assert loaded is not None
    assert loaded.version == idat_bruteforce.ULTIMATE_LINEFEED_PROGRESS_VERSION
    assert loaded.parallel_workers == 3
    assert loaded.shard_size == 50_000
    assert loaded.shards == (shard,)
    assert loaded.attempted_candidates == 25_000
    assert idat_bruteforce.ultimate_progress_attempted_floor(loaded) == 25_000


def test_ultimate_hidden_tmp_path_is_unique_per_write(tmp_path):
    target = str(tmp_path / "_ULF.progress.json")

    first = idat_bruteforce._hidden_tmp_path(target)
    second = idat_bruteforce._hidden_tmp_path(target)

    assert first != second
    assert first.endswith(".tmp")
    assert second.endswith(".tmp")
    assert str(tmp_path) in first


def test_ultimate_progress_normalizes_pending_shard_cursor(tmp_path):
    progress_path = str(tmp_path / "_ULF.progress.json")
    idat_bruteforce._write_ultimate_progress(
        progress_path,
        source_hash="source",
        target_adler=1234,
        start_offset=42,
        max_depth=4,
        max_offsets=8,
        operation_pool_hash="merged",
        focused_operation_pool_hash="focused",
        broad_operation_pool_hash="broad",
        phase="exhaustive",
        depth=3,
        pool_index=1,
        combination_rank=0,
        combination_indices=None,
        tested_candidates=0,
        pruned_candidates=0,
        state_count=1,
        budget=None,
        parallel_workers=8,
        shard_size=50_000,
        shards=(
            {
                "pool_index": 1,
                "depth": 3,
                "start_rank": 100_000,
                "end_rank": 150_000,
                "next_rank": 123_456,
                "tested": 0,
                "status": "running",
            },
        ),
        attempted_candidates=16_000_000,
    )

    record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert record["attempted_candidates"] == 23_456
    assert record["shards"][0]["tested"] == 23_456
    loaded, warning = idat_bruteforce._load_ultimate_progress(
        progress_path,
        source_hash="source",
        target_adler=1234,
        start_offset=42,
        max_depth=4,
        max_offsets=8,
        operation_pool_hash="merged",
        focused_operation_pool_hash="focused",
        broad_operation_pool_hash="broad",
    )
    assert warning == ""
    assert idat_bruteforce.ultimate_progress_attempted_floor(loaded) == 23_456


def test_ultimate_parallel_worker_runs_shard_without_rank_holes():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:1]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    before = idat.analyze_idat_stream(corrupt)
    suspect_offsets = idat_bruteforce.ultimate_linefeed_suspect_offsets(
        corrupt,
        start_offset=idat_bruteforce.first_idat_problem_stream_offset(corrupt),
        max_offsets=4,
    )
    operation_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        suspect_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    assert len(operation_pool) >= 3

    context = {
        "chunks": chunks,
        "root_stream": root_stream,
        "before": before,
        "operation_pools": (operation_pool,),
        "target_adler": before.stored_adler,
        "root_parent_score": idat_bruteforce.super_mega_linefeed_score(before, 0),
        "visual_min_coverage": 0.0,
        "visual_gallery_limit": 5,
    }
    idat_bruteforce._ultimate_parallel_worker_init(context)
    result = idat_bruteforce._ultimate_parallel_worker_run(
        {
            "pool_index": 0,
            "depth": 1,
            "start_rank": 0,
            "end_rank": 3,
            "next_rank": 0,
            "tested": 0,
            "pruned": 0,
            "status": "pending",
        }
    )

    assert result.error == ""
    assert result.tested == 3
    assert result.next_rank == 3
    assert result.shard["start_rank"] == 0
    assert result.shard["end_rank"] == 3


def test_ultimate_parallel_worker_stops_from_shared_event_before_more_work():
    class FakeProgressQueue:
        def __init__(self):
            self.messages = []

        def put_nowait(self, message):
            self.messages.append(message)

    class FakeStopEvent:
        def is_set(self):
            return True

    filtered = b"".join(b"\x00" + bytes((row % 256, 0, 0)) for row in range(16))
    corrupt = build_rgb_png(1, 16, filtered)
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    before = idat.analyze_idat_stream(corrupt)
    operation_pool = tuple(
        idat_bruteforce.SuperMegaLinefeedOperation(
            "test-insert-cr",
            offset,
            b"",
            b"\r",
        )
        for offset in range(80)
    )
    progress_queue = FakeProgressQueue()

    context = {
        "chunks": chunks,
        "root_stream": root_stream,
        "before": before,
        "operation_pools": (operation_pool,),
        "target_adler": before.stored_adler,
        "progress_queue": progress_queue,
        "stop_event": FakeStopEvent(),
        "root_parent_score": idat_bruteforce.super_mega_linefeed_score(before, 0),
        "visual_min_coverage": 0.0,
        "visual_gallery_limit": 0,
    }
    idat_bruteforce._ultimate_parallel_worker_init(context)
    result = idat_bruteforce._ultimate_parallel_worker_run(
        {
            "pool_index": 0,
            "depth": 1,
            "start_rank": 0,
            "end_rank": 80,
            "next_rank": 0,
            "tested": 0,
            "pruned": 0,
            "status": "pending",
        }
    )

    assert result.error == ""
    assert result.tested == 0
    assert result.next_rank == 0
    assert progress_queue.messages[-1]["next_rank"] == 0
    assert progress_queue.messages[-1]["attempted"] == 0


def test_ultimate_shutdown_parallel_executor_stops_processes_and_queue():
    class FakeStopEvent:
        def __init__(self):
            self.set_called = False

        def set(self):
            self.set_called = True

    class FakeProcess:
        def __init__(self):
            self.terminated = False
            self.join_timeout = None

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def join(self, timeout):
            self.join_timeout = timeout

    class FakeExecutor:
        def __init__(self, process):
            self._processes = {1: process}
            self.shutdown_args = None

        def shutdown(self, **kwargs):
            self.shutdown_args = kwargs

    class FakeQueue:
        def __init__(self):
            self.cancelled = False
            self.closed = False

        def get_nowait(self):
            raise idat_bruteforce.queue.Empty

        def cancel_join_thread(self):
            self.cancelled = True

        def close(self):
            self.closed = True

    stop_event = FakeStopEvent()
    process = FakeProcess()
    executor = FakeExecutor(process)
    progress_queue = FakeQueue()

    idat_bruteforce._ultimate_shutdown_parallel_executor(
        executor,
        progress_queue=progress_queue,
        stop_event=stop_event,
        grace_seconds=0.01,
    )

    assert stop_event.set_called is True
    assert executor.shutdown_args == {"wait": False, "cancel_futures": True}
    assert process.terminated is True
    assert process.join_timeout is not None
    assert progress_queue.cancelled is True
    assert progress_queue.closed is True


def test_ultimate_parallel_worker_reports_progress_before_shard_end(monkeypatch):
    class FakeProgressQueue:
        def __init__(self):
            self.messages = []

        def put_nowait(self, message):
            self.messages.append(message)

    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(180))
    corrupt = build_rgb_png(1, 180, filtered, idat_data=zlib.compress(filtered, level=0))
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    before = idat.analyze_idat_stream(corrupt)
    operation_pool = tuple(
        idat_bruteforce.SuperMegaLinefeedOperation(
            "test-insert-cr",
            offset,
            b"",
            b"\r",
        )
        for offset in range(120)
    )
    monkeypatch.setattr(idat_bruteforce, "ULTIMATE_LINEFEED_PARALLEL_PROGRESS_STEP", 10)
    progress_queue = FakeProgressQueue()

    context = {
        "chunks": chunks,
        "root_stream": root_stream,
        "before": before,
        "operation_pools": (operation_pool,),
        "target_adler": before.stored_adler,
        "progress_queue": progress_queue,
        "root_parent_score": idat_bruteforce.super_mega_linefeed_score(before, 0),
        "visual_min_coverage": 0.0,
        "visual_gallery_limit": 0,
    }
    idat_bruteforce._ultimate_parallel_worker_init(context)
    result = idat_bruteforce._ultimate_parallel_worker_run(
        {
            "pool_index": 0,
            "depth": 1,
            "start_rank": 0,
            "end_rank": 120,
            "next_rank": 0,
            "tested": 0,
            "pruned": 0,
            "status": "pending",
        }
    )

    assert result.error == ""
    assert progress_queue.messages
    assert progress_queue.messages[0]["attempted"] >= 10
    assert progress_queue.messages[0]["next_rank"] < result.next_rank


def test_ultimate_parallel_worker_reports_progress_through_pruned_ranges(monkeypatch):
    class FakeProgressQueue:
        def __init__(self):
            self.messages = []

        def put_nowait(self, message):
            self.messages.append(message)

    filtered = b"".join(b"\x00" + bytes((row % 256, 0, 0)) for row in range(16))
    corrupt = build_rgb_png(1, 16, filtered)
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    before = idat.analyze_idat_stream(corrupt)
    operation_pool = tuple(
        idat_bruteforce.SuperMegaLinefeedOperation(
            "test-missing-old-byte",
            len(root_stream) + 1 + offset,
            b"\xff",
            b"\x00",
        )
        for offset in range(40)
    )
    monkeypatch.setattr(idat_bruteforce, "ULTIMATE_LINEFEED_PARALLEL_PROGRESS_STEP", 10)
    progress_queue = FakeProgressQueue()

    context = {
        "chunks": chunks,
        "root_stream": root_stream,
        "before": before,
        "operation_pools": (operation_pool,),
        "target_adler": before.stored_adler,
        "progress_queue": progress_queue,
        "root_parent_score": idat_bruteforce.super_mega_linefeed_score(before, 0),
        "visual_min_coverage": 0.0,
        "visual_gallery_limit": 0,
    }
    idat_bruteforce._ultimate_parallel_worker_init(context)
    result = idat_bruteforce._ultimate_parallel_worker_run(
        {
            "pool_index": 0,
            "depth": 1,
            "start_rank": 0,
            "end_rank": 40,
            "next_rank": 0,
            "tested": 0,
            "pruned": 0,
            "status": "pending",
        }
    )

    assert result.error == ""
    assert result.tested == 0
    assert result.pruned == 40
    assert progress_queue.messages
    assert progress_queue.messages[0]["tested"] == 0
    assert progress_queue.messages[0]["attempted"] >= 10
    assert progress_queue.messages[0]["next_rank"] < result.next_rank


def test_ultimate_linefeed_preview_callback_only_receives_valid_complete_candidates():
    calls = []
    valid = SimpleNamespace(after=SimpleNamespace(supported=True, complete=True))
    incomplete = SimpleNamespace(after=SimpleNamespace(supported=True, complete=False))
    unsupported = SimpleNamespace(after=SimpleNamespace(supported=False, complete=True))

    idat_bruteforce._preview_ultimate_candidate_if_valid(
        valid,
        12,
        100,
        lambda *args: calls.append(args),
    )
    idat_bruteforce._preview_ultimate_candidate_if_valid(
        incomplete,
        13,
        100,
        lambda *args: calls.append(args),
    )
    idat_bruteforce._preview_ultimate_candidate_if_valid(
        unsupported,
        14,
        100,
        lambda *args: calls.append(args),
    )
    idat_bruteforce._preview_ultimate_candidate_if_valid(
        valid,
        15,
        100,
        lambda *args: (_ for _ in ()).throw(RuntimeError("preview failed")),
    )

    assert calls == [(valid, 12, 100)]


def test_rebuild_visual_idat_preview_recompresses_full_bad_adler_candidate():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))

    before = idat.analyze_idat_stream(corrupt)
    repair = idat.rebuild_visual_idat_preview(corrupt)

    assert before.status == "bad_adler"
    assert before.usable_scanlines == 3
    assert repair is not None
    assert repair.strategy.startswith("rebuilt_adler_preview")
    assert validate_png_structure(repair.data).ok
    rebuilt = idat.analyze_idat_stream(repair.data)
    assert rebuilt.complete is True
    assert rebuilt.adler_status == "adler_match"
    assert zlib.decompress(
        b"".join(chunk.data for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"IDAT")
    ) == filtered


def test_rebuild_tolerant_idat_preview_includes_complete_bad_filter_rows():
    filtered = b"\x00abc" + b"\x00def" + b"\x11ghi"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))

    before = idat.analyze_idat_stream(corrupt)
    repair = idat.rebuild_tolerant_idat_preview(corrupt)

    assert before.status == "bad_adler"
    assert before.usable_scanlines == 2
    assert before.complete_scanlines == 3
    assert repair is not None
    assert repair.recovered_scanlines == 3
    assert repair.total_scanlines == 3
    assert "usable without filter repair=2" in repair.strategy
    assert "replaced 1 complete bad-filter row" in repair.strategy
    assert validate_png_structure(repair.data).ok
    rebuilt = idat.analyze_idat_stream(repair.data)
    assert rebuilt.complete is True
    rebuilt_raw = zlib.decompress(
        b"".join(chunk.data for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"IDAT")
    )
    assert rebuilt_raw == b"\x00abc" + b"\x00def" + b"\x00def"


def test_ultimate_visual_gallery_keeps_equal_score_distinct_operations():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    analysis = idat.analyze_idat_stream(corrupt)
    first = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        analysis,
        analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
    )
    second = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-remove-cr", 8, b"\r", b""),),
        analysis,
        analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
    )

    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        first,
        tested=10,
        reference_image=None,
        min_coverage=0.95,
        limit=100,
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        gallery,
        second,
        tested=11,
        reference_image=None,
        min_coverage=0.95,
        limit=100,
    )

    assert len(gallery) == 2
    assert {item.operation_hash for item in gallery} == {
        idat_bruteforce._ultimate_operation_hash(first.operations),
        idat_bruteforce._ultimate_operation_hash(second.operations),
    }


def test_ultimate_visual_gallery_limit_evicts_worst_candidate():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    partial = build_rgb_png(1, 3, filtered, idat_data=zlib.compress(filtered[:8]))
    partial_analysis = idat.analyze_idat_stream(partial)
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    full = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    full_analysis = idat.analyze_idat_stream(full)
    worse = idat_bruteforce.SuperMegaLinefeedCandidate(
        partial,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        partial_analysis,
        partial_analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(partial_analysis, 1),
    )
    better = idat_bruteforce.SuperMegaLinefeedCandidate(
        full,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        full_analysis,
        full_analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(full_analysis, 1),
    )

    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        worse,
        tested=10,
        reference_image=None,
        min_coverage=0.0,
        limit=1,
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        gallery,
        better,
        tested=11,
        reference_image=None,
        min_coverage=0.0,
        limit=1,
    )

    assert len(gallery) == 1
    assert gallery[0].candidate.state_id == 2
    assert gallery[0].candidate.after.usable_scanlines == 3


def test_ultimate_visual_gallery_skips_structural_downgrade_before_limit(monkeypatch):
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    full = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    full_analysis = idat.analyze_idat_stream(full)
    partial = build_rgb_png(1, 3, filtered, idat_data=zlib.compress(filtered[:8]))
    partial_analysis = idat.analyze_idat_stream(partial)
    better = idat_bruteforce.SuperMegaLinefeedCandidate(
        full,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        full_analysis,
        full_analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(full_analysis, 1),
    )
    worse = idat_bruteforce.SuperMegaLinefeedCandidate(
        partial,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        partial_analysis,
        partial_analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(partial_analysis, 1),
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        better,
        tested=10,
        reference_image=None,
        min_coverage=0.0,
        limit=100,
    )
    calls = []

    def fail_if_scored(*args, **kwargs):
        calls.append((args, kwargs))
        return None

    monkeypatch.setattr(
        idat_bruteforce,
        "_ultimate_visual_candidate_from_candidate",
        fail_if_scored,
    )

    updated = idat_bruteforce._remember_ultimate_visual_candidate(
        gallery,
        worse,
        tested=11,
        reference_image=None,
        min_coverage=0.0,
        limit=100,
    )

    assert updated == gallery
    assert calls == []


def test_ultimate_visual_gallery_backfills_lower_tier_on_forced_flush():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    full = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    full_analysis = idat.analyze_idat_stream(full)
    partial = build_rgb_png(1, 3, filtered, idat_data=zlib.compress(filtered[:8]))
    partial_analysis = idat.analyze_idat_stream(partial)
    better = idat_bruteforce.SuperMegaLinefeedCandidate(
        full,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        full_analysis,
        full_analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(full_analysis, 1),
    )
    weaker = idat_bruteforce.SuperMegaLinefeedCandidate(
        partial,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        partial_analysis,
        partial_analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(partial_analysis, 1),
    )

    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        better,
        tested=10,
        reference_image=None,
        min_coverage=0.0,
        limit=3,
    )
    skipped = idat_bruteforce._remember_ultimate_visual_candidate(
        gallery,
        weaker,
        tested=11,
        reference_image=None,
        min_coverage=0.0,
        limit=3,
    )
    backfill = idat_bruteforce._remember_ultimate_visual_backfill_candidate(
        (),
        weaker,
        tested=11,
        min_coverage=0.0,
        limit=3,
    )
    filled = idat_bruteforce._fill_ultimate_visual_gallery_from_backfill(
        skipped,
        backfill,
        reference_image=None,
        reference_mode="exact",
        min_coverage=0.0,
        limit=3,
    )

    assert skipped == gallery
    assert len(filled) == 2
    assert [candidate.candidate.state_id for candidate in filled] == [2, 1]


def test_ultimate_visual_gallery_structure_beats_reference_rank():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    partial = build_rgb_png(1, 3, filtered, idat_data=zlib.compress(filtered[:8]))
    partial_analysis = idat.analyze_idat_stream(partial)
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    full = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    full_analysis = idat.analyze_idat_stream(full)
    visually_close = idat_bruteforce.SuperMegaLinefeedCandidate(
        partial,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        partial_analysis,
        partial_analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(partial_analysis, 1),
        visual_score=0.0,
    )
    visually_bad_full = idat_bruteforce.SuperMegaLinefeedCandidate(
        full,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        full_analysis,
        full_analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(full_analysis, 1),
        visual_score=100.0,
    )

    close_rank = idat_bruteforce._ultimate_visual_candidate_rank(
        visually_close,
        coverage=visually_close.after.usable_scanlines / visually_close.after.height,
        visual_score=visually_close.visual_score,
    )
    bad_full_rank = idat_bruteforce._ultimate_visual_candidate_rank(
        visually_bad_full,
        coverage=visually_bad_full.after.usable_scanlines / visually_bad_full.after.height,
        visual_score=visually_bad_full.visual_score,
    )

    assert bad_full_rank < close_rank


def test_ultimate_top_candidates_structure_beats_reference_rank():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    partial = build_rgb_png(1, 3, filtered, idat_data=zlib.compress(filtered[:8]))
    partial_analysis = idat.analyze_idat_stream(partial)
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    full = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    full_analysis = idat.analyze_idat_stream(full)
    visually_close = idat_bruteforce.SuperMegaLinefeedCandidate(
        partial,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        partial_analysis,
        partial_analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(partial_analysis, 1),
        visual_score=0.0,
    )
    visually_bad_full = idat_bruteforce.SuperMegaLinefeedCandidate(
        full,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        full_analysis,
        full_analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(full_analysis, 1),
        visual_score=100.0,
    )

    top = idat_bruteforce._remember_ultimate_top_candidate((), visually_bad_full, limit=1)
    top = idat_bruteforce._remember_ultimate_top_candidate(top, visually_close, limit=1)

    assert top[0].state_id == 2


def test_ultimate_top_candidates_reference_rank_breaks_structural_ties():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    analysis = idat.analyze_idat_stream(corrupt)
    visually_close = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        analysis,
        analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
        visual_score=0.0,
    )
    visually_bad = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        analysis,
        analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
        visual_score=100.0,
    )

    top = idat_bruteforce._remember_ultimate_top_candidate((), visually_bad, limit=1)
    top = idat_bruteforce._remember_ultimate_top_candidate(top, visually_close, limit=1)

    assert top[0].state_id == 1


def test_ultimate_checkpoint_seed_candidates_ignore_gallery_limit_on_resume():
    filtered = b"\x00abc"
    png_data = build_rgb_png(1, 1, filtered)
    analysis = idat.analyze_idat_stream(png_data)
    candidates = tuple(
        idat_bruteforce.SuperMegaLinefeedCandidate(
            png_data,
            (),
            analysis,
            analysis,
            state_id=index,
            score=(0, 400 - index, 1, 1, 1, 0, 0, 0),
        )
        for index in range(400)
    )

    seeds = idat_bruteforce._ultimate_checkpoint_seed_candidates(
        candidates,
        beam_width=8,
        visual_gallery_limit=1000,
    )
    seed_ids = {candidate.state_id for candidate in seeds}

    assert len(seeds) == 16
    assert set(range(8)).issubset(seed_ids)
    assert set(range(392, 400)).issubset(seed_ids)
    assert 300 not in seed_ids


def test_ultimate_visual_gallery_write_removes_obsolete_previews(tmp_path):
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    analysis = idat.analyze_idat_stream(corrupt)
    candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        analysis,
        analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        candidate,
        tested=10,
        reference_image=None,
        min_coverage=0.95,
        limit=100,
    )
    gallery_path = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.visual.json"
    preview_dir = tmp_path / "Bruteforce_Previews" / "VisualCandidates"
    preview_dir.mkdir(parents=True)
    stale = preview_dir / "_VisualCandidate_999_stale.png"
    stale.write_bytes(b"stale")

    written, count = idat_bruteforce._write_ultimate_visual_gallery(
        str(gallery_path),
        gallery,
        limit=1,
        reference_mode="similar",
        reference_regions_path="Folder_x.bad/_ULF.reference_regions.json",
        source_hash="source",
        phase="complete",
        depth=1,
        tested_candidates=10,
        state_count=2,
    )

    previews = list(preview_dir.glob("_VisualCandidate_*.png"))
    assert count == 1
    assert len(written) == 1
    assert not stale.exists()
    assert len(previews) == 1
    assert validate_png_structure(previews[0].read_bytes()).ok
    record = json.loads(gallery_path.read_text(encoding="utf-8"))
    assert record["preview_count"] == 1
    assert record["reference_mode"] == "similar"
    assert record["limit"] == 1
    assert record["visual_gallery_limit"] == 1
    assert record["reference_regions_path"] == "Folder_x.bad/_ULF.reference_regions.json"
    assert record["candidates"][0]["preview_kind"] == "rebuilt_adler_preview"
    assert "visual_score_kind" in record["candidates"][0]
    assert "matched_patch_count" in record["candidates"][0]


def test_ultimate_visual_gallery_load_preserves_existing_resume_previews(tmp_path):
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    analysis = idat.analyze_idat_stream(corrupt)
    candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        analysis,
        analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        candidate,
        tested=10,
        reference_image=None,
        min_coverage=0.95,
        limit=10,
    )
    gallery_path = tmp_path / "_ULF.visual.json"
    written, count = idat_bruteforce._write_ultimate_visual_gallery(
        str(gallery_path),
        gallery,
        limit=10,
        source_hash="source",
        phase="complete",
        tested_candidates=10,
        state_count=2,
    )

    assert count == 1
    assert Path(written[0].preview_path).exists()

    restored = idat_bruteforce._load_ultimate_visual_gallery(
        str(gallery_path),
        source_hash="source",
        limit=10,
    )
    assert len(restored) == 1
    assert restored[0].preview_data == written[0].preview_data
    assert idat_bruteforce._load_ultimate_visual_gallery(
        str(gallery_path),
        source_hash="other-source",
        limit=10,
    ) == ()

    rewritten, rewritten_count = idat_bruteforce._write_ultimate_visual_gallery(
        str(gallery_path),
        restored,
        limit=10,
        source_hash="source",
        phase="exhaustive",
        tested_candidates=20,
        state_count=3,
    )

    previews = list((tmp_path / "Bruteforce_Previews" / "VisualCandidates").glob("_VisualCandidate_*.png"))
    assert rewritten_count == 1
    assert len(rewritten) == 1
    assert len(previews) == 1
    assert validate_png_structure(previews[0].read_bytes()).ok
    record = json.loads(gallery_path.read_text(encoding="utf-8"))
    assert record["preview_count"] == 1
    assert record["candidates"][0]["visual_hash"] == written[0].visual_hash


def test_ultimate_visual_gallery_touch_updates_progress_without_cleaning_previews(tmp_path):
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    analysis = idat.analyze_idat_stream(corrupt)
    candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        analysis,
        analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        candidate,
        tested=10,
        reference_image=None,
        min_coverage=0.95,
        limit=10,
    )
    gallery_path = tmp_path / "_ULF.visual.json"
    written, count = idat_bruteforce._write_ultimate_visual_gallery(
        str(gallery_path),
        gallery,
        limit=10,
        source_hash="source",
        phase="exhaustive",
        tested_candidates=10,
        state_count=2,
    )
    preview_dir = tmp_path / "Bruteforce_Previews" / "VisualCandidates"
    stale = preview_dir / "_VisualCandidate_999_stale.png"
    stale.write_bytes(b"stale")

    assert count == 1
    assert Path(written[0].preview_path).exists()
    assert idat_bruteforce._touch_ultimate_visual_gallery_progress(
        str(gallery_path),
        source_hash="source",
        reference_mode="similar",
        reference_regions_path="Folder_x.bad/_ULF.reference_regions.json",
        phase="exhaustive",
        depth=4,
        tested_candidates=99,
        state_count=123,
        limit=10,
    ) is True

    record = json.loads(gallery_path.read_text(encoding="utf-8"))
    assert record["tested_candidates"] == 99
    assert record["state_count"] == 123
    assert record["depth"] == 4
    assert record["reference_mode"] == "similar"
    assert record["reference_regions_path"] == "Folder_x.bad/_ULF.reference_regions.json"
    assert record["preview_count"] == 1
    assert record["candidates"][0]["visual_hash"] == written[0].visual_hash
    assert Path(written[0].preview_path).exists()
    assert stale.exists()

    assert idat_bruteforce._touch_ultimate_visual_gallery_progress(
        str(gallery_path),
        source_hash="other-source",
        tested_candidates=1000,
    ) is False
    assert json.loads(gallery_path.read_text(encoding="utf-8"))["tested_candidates"] == 99


def test_ultimate_linefeed_progress_checkpoint_round_trips(tmp_path):
    progress = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.progress.json"
    operation_pool = (
        idat_bruteforce.SuperMegaLinefeedOperation("ultimate-remove-cr", 4, b"\r", b""),
    )
    pool_hash = idat_bruteforce._ultimate_operation_pool_hash(operation_pool)

    idat_bruteforce._write_ultimate_progress(
        str(progress),
        source_hash="source",
        target_adler=123,
        start_offset=7,
        max_depth=4,
        max_offsets=128,
        operation_pool_hash=pool_hash,
        focused_operation_pool_hash=pool_hash,
        broad_operation_pool_hash=pool_hash,
        phase="exhaustive",
        depth=2,
        pool_index=1,
        combination_rank=42,
        combination_indices=(4, 9),
        tested_candidates=100,
        pruned_candidates=12,
        state_count=44,
        budget=1000,
    )

    loaded, warning = idat_bruteforce._load_ultimate_progress(
        str(progress),
        source_hash="source",
        target_adler=123,
        start_offset=7,
        max_depth=4,
        max_offsets=128,
        operation_pool_hash=pool_hash,
        focused_operation_pool_hash=pool_hash,
        broad_operation_pool_hash=pool_hash,
    )
    mismatched, mismatch_warning = idat_bruteforce._load_ultimate_progress(
        str(progress),
        source_hash="other",
        target_adler=123,
        start_offset=7,
        max_depth=4,
        max_offsets=128,
        operation_pool_hash=pool_hash,
        focused_operation_pool_hash=pool_hash,
        broad_operation_pool_hash=pool_hash,
    )

    assert warning == ""
    assert loaded is not None
    assert loaded.phase == "exhaustive"
    assert loaded.combination_rank == 42
    assert loaded.combination_indices == (4, 9)
    assert loaded.tested_candidates == 100
    assert mismatched is None
    assert "source_hash mismatch" in mismatch_warning


def test_ultimate_linefeed_combination_indices_resume_without_restarting():
    indices = list(idat_bruteforce._combination_indices_from(5, 2, (1, 3)))

    assert indices == [(1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]
    assert idat_bruteforce._next_combination_indices((3, 4), 5, 2) is None
    assert idat_bruteforce._combination_rank((1, 3), 5, 2) == 5


def test_ultimate_progress_shard_preserves_optional_gpu_backend_fields():
    shard = idat_bruteforce._normalize_ultimate_progress_shard(
        {
            "backend": "opengl",
            "pool_index": 1,
            "depth": 2,
            "start_rank": 10,
            "end_rank": 20,
            "next_rank": 14,
            "status": "pending",
        }
    )

    assert shard["backend"] == "opengl"
    assert shard["start_rank"] == 10
    assert shard["next_rank"] == 14
    assert shard["tested"] == 4


def test_ultimate_gpu_analysis_candidates_are_confirmed_with_idat_analyzer(monkeypatch):
    filtered = b"\x00abc"
    good_stream = zlib.compress(filtered)
    corrupt_stream = bytearray(good_stream)
    corrupt_stream[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 1, filtered, idat_data=bytes(corrupt_stream))
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    before = idat.analyze_idat_stream(corrupt)
    operation = idat_bruteforce.SuperMegaLinefeedOperation(
        "restore-adler-byte",
        len(corrupt_stream) - 1,
        bytes((corrupt_stream[-1],)),
        bytes((good_stream[-1],)),
    )
    monkeypatch.setattr(
        ultimate_opengl_backend,
        "explain_analysis",
        lambda plan, gpu_config: ultimate_opengl_backend.UltimateOpenGLDecision(
            True,
            "mock OpenGL ready",
        ),
    )
    monkeypatch.setattr(
        ultimate_opengl_backend,
        "run_analysis_gpu",
        lambda plan, gpu_config: ultimate_opengl_backend._run_analysis_host(plan),
    )

    candidates, warning = idat_bruteforce._ultimate_gpu_analysis_candidates(
        chunks=chunks,
        root_stream=root_stream,
        before=before,
        operation_pools=((operation,),),
        target_adler=zlib.adler32(filtered) & 0xFFFFFFFF,
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
        max_depth=1,
    )

    assert warning == ""
    assert len(candidates) == 1
    assert candidates[0].after.complete is True
    assert candidates[0].after.adler_status == "adler_match"
    assert idat.analyze_idat_stream(candidates[0].data).complete is True


def test_ultimate_gpu_analysis_resumes_done_opengl_shards(monkeypatch):
    filtered = b"\x00abc"
    stream = zlib.compress(filtered)
    source = build_rgb_png(1, 1, filtered, idat_data=stream)
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(source)
    before = idat.analyze_idat_stream(source)
    operations = tuple(
        idat_bruteforce.SuperMegaLinefeedOperation(
            "noop-%s" % index,
            index,
            bytes((root_stream[index],)),
            bytes((root_stream[index],)),
        )
        for index in range(3)
    )
    progress = idat_bruteforce.UltimateLinefeedProgress(
        "progress.json",
        idat_bruteforce._stream_state_key(root_stream),
        before.stored_adler,
        None,
        1,
        8,
        "pool",
        "focused",
        "broad",
        "exhaustive",
        1,
        0,
        1,
        None,
        1,
        0,
        1,
        None,
        0.0,
        shards=(
            {
                "backend": "opengl",
                "pool_index": 0,
                "depth": 1,
                "start_rank": 0,
                "end_rank": 1,
                "next_rank": 1,
                "status": "done",
                "shard_size": 1,
            },
        ),
        version=idat_bruteforce.ULTIMATE_LINEFEED_PROGRESS_VERSION,
        attempted_candidates=1,
    )
    plans = []
    callbacks = []

    monkeypatch.setattr(ultimate_opengl_backend, "ULTIMATE_OPENGL_ANALYSIS_SHARD_SIZE", 1)
    monkeypatch.setattr(
        ultimate_opengl_backend,
        "explain_analysis",
        lambda plan, gpu_config: ultimate_opengl_backend.UltimateOpenGLDecision(True, "mock"),
    )

    def fake_run(plan, gpu_config):
        plans.append((plan.start_rank, plan.end_rank))
        return ultimate_opengl_backend.UltimateOpenGLAnalysisResult(
            (),
            1,
            0,
            plan.start_rank,
            plan.bounded_end_rank,
            plan.bounded_end_rank,
            covered_rank_count=plan.bounded_end_rank - plan.start_rank,
            shader_used=True,
        )

    monkeypatch.setattr(ultimate_opengl_backend, "run_analysis_gpu", fake_run)

    candidates, warning = idat_bruteforce._ultimate_gpu_analysis_candidates(
        chunks=chunks,
        root_stream=root_stream,
        before=before,
        operation_pools=(operations,),
        target_adler=before.stored_adler,
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
        max_depth=1,
        progress_resume=progress,
        shard_callback=lambda shard: callbacks.append(dict(shard)),
    )

    assert candidates == ()
    assert warning == ""
    assert plans == [(1, 2), (2, 3)]
    assert [callback["status"] for callback in callbacks] == ["running", "done", "running", "done"]
    assert callbacks[-1]["backend"] == "opengl"


def test_ultimate_linefeed_bruteforce_resumes_progress_checkpoint(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(120))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets):
        del compressed[offset]

    corrupt = build_rgb_png(1, 120, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"
    progress = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.progress.json"
    before = idat.analyze_idat_stream(corrupt)
    _chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    suspect_offsets = idat_bruteforce.ultimate_linefeed_suspect_offsets(
        corrupt,
        start_offset=start_offset,
        max_offsets=64,
    )
    focused_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        suspect_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    broad_offsets = idat_bruteforce._ultimate_exhaustive_linefeed_offsets(
        root_stream,
        suspect_offsets=suspect_offsets,
        anchor=start_offset,
        max_offsets=max(64, min(len(root_stream), 64 * 8, 2048)),
    )
    broad_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        broad_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    merged_pool = idat_bruteforce._merge_ultimate_operations(focused_pool, broad_pool)
    idat_bruteforce._write_ultimate_progress(
        str(progress),
        source_hash=idat_bruteforce._stream_state_key(root_stream),
        target_adler=before.stored_adler,
        start_offset=start_offset,
        max_depth=2,
        max_offsets=64,
        operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(merged_pool),
        focused_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(focused_pool),
        broad_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(broad_pool),
        phase="exhaustive",
        depth=1,
        pool_index=1,
        combination_rank=10,
        combination_indices=(10,),
        tested_candidates=50,
        pruned_candidates=5,
        state_count=7,
        budget=60,
    )

    progress_calls = []
    original_load = idat_bruteforce._load_ultimate_checkpoint

    def fail_checkpoint_load(*args, **kwargs):
        raise AssertionError("v2 exhaustive progress should not scan the checkpoint archive")

    try:
        idat_bruteforce._load_ultimate_checkpoint = fail_checkpoint_load
        probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
            corrupt,
            start_offset=start_offset,
            checkpoint_path=str(checkpoint),
            progress_path=str(progress),
            max_depth=2,
            max_offsets=64,
            budget=60,
            beam_width=1,
            progress=lambda *args: progress_calls.append(args),
        )
    finally:
        idat_bruteforce._load_ultimate_checkpoint = original_load

    assert probe.progress_resumed is True
    assert probe.progress_path == str(progress)
    assert probe.tested_candidates == 60
    assert probe.budget_exhausted is True
    assert progress_calls[0] == ("UltimateMegaSuperLineFeedBruteForce", 50, 60)
    assert ("UltimateMegaSuperLineFeedBruteForce", 0, 60) not in progress_calls


def test_ultimate_linefeed_fast_resume_status_and_progress_floor(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(120))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets):
        del compressed[offset]

    corrupt = build_rgb_png(1, 120, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    checkpoint = tmp_path / "_ULF.checkpoint.jsonl"
    progress = tmp_path / "_ULF.progress.json"
    before = idat.analyze_idat_stream(corrupt)
    _chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    suspect_offsets = idat_bruteforce.ultimate_linefeed_suspect_offsets(
        corrupt,
        start_offset=start_offset,
        max_offsets=64,
    )
    focused_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        suspect_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    broad_offsets = idat_bruteforce._ultimate_exhaustive_linefeed_offsets(
        root_stream,
        suspect_offsets=suspect_offsets,
        anchor=start_offset,
        max_offsets=max(64, min(len(root_stream), 64 * 8, 2048)),
    )
    broad_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        broad_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    merged_pool = idat_bruteforce._merge_ultimate_operations(focused_pool, broad_pool)
    idat_bruteforce._write_ultimate_progress(
        str(progress),
        source_hash=idat_bruteforce._stream_state_key(root_stream),
        target_adler=before.stored_adler,
        start_offset=start_offset,
        max_depth=2,
        max_offsets=64,
        operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(merged_pool),
        focused_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(focused_pool),
        broad_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(broad_pool),
        phase="exhaustive",
        depth=1,
        pool_index=1,
        combination_rank=10,
        combination_indices=(10,),
        tested_candidates=50,
        pruned_candidates=5,
        state_count=7,
        budget=60,
        parallel_workers=4,
        shard_size=idat_bruteforce.ULTIMATE_LINEFEED_PARALLEL_SHARD_SIZE,
        shards=[
            {
                "pool_index": 1,
                "depth": 1,
                "start_rank": 0,
                "end_rank": len(merged_pool),
                "next_rank": min(10, len(merged_pool)),
                "status": "pending",
            }
        ],
        attempted_candidates=50,
    )

    progress_calls = []
    resume_statuses = []
    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
        max_depth=2,
        max_offsets=64,
        budget=60,
        beam_width=1,
        progress=lambda *args: progress_calls.append(args),
        resume_status=lambda status: resume_statuses.append(status),
    )

    assert probe.fast_resume_used is True
    assert probe.attempted_floor == 50
    assert probe.committed_count == 50
    assert probe.matched_shards == 1
    assert resume_statuses[0]["fast_resume_used"] is True
    assert resume_statuses[0]["attempted_floor"] == 50
    assert progress_calls[0] == ("UltimateMegaSuperLineFeedBruteForce", 50, 60)


def test_ultimate_linefeed_rejects_incompatible_fast_resume_shards(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(120))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets):
        del compressed[offset]

    corrupt = build_rgb_png(1, 120, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    checkpoint = tmp_path / "_ULF.checkpoint.jsonl"
    progress = tmp_path / "_ULF.progress.json"
    before = idat.analyze_idat_stream(corrupt)
    _chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    suspect_offsets = idat_bruteforce.ultimate_linefeed_suspect_offsets(
        corrupt,
        start_offset=start_offset,
        max_offsets=64,
    )
    focused_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        suspect_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    broad_offsets = idat_bruteforce._ultimate_exhaustive_linefeed_offsets(
        root_stream,
        suspect_offsets=suspect_offsets,
        anchor=start_offset,
        max_offsets=max(64, min(len(root_stream), 64 * 8, 2048)),
    )
    broad_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        broad_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    merged_pool = idat_bruteforce._merge_ultimate_operations(focused_pool, broad_pool)
    idat_bruteforce._write_ultimate_progress(
        str(progress),
        source_hash=idat_bruteforce._stream_state_key(root_stream),
        target_adler=before.stored_adler,
        start_offset=start_offset,
        max_depth=2,
        max_offsets=64,
        operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(merged_pool),
        focused_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(focused_pool),
        broad_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(broad_pool),
        phase="exhaustive",
        depth=1,
        pool_index=1,
        combination_rank=10,
        combination_indices=(10,),
        tested_candidates=50,
        pruned_candidates=5,
        state_count=7,
        budget=0,
        parallel_workers=4,
        shard_size=idat_bruteforce.ULTIMATE_LINEFEED_PARALLEL_SHARD_SIZE,
        shards=[
            {
                "pool_index": 99,
                "depth": 1,
                "start_rank": 0,
                "end_rank": 50000,
                "next_rank": 250,
                "status": "pending",
            }
        ],
        attempted_candidates=50,
    )

    progress_calls = []
    resume_statuses = []
    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
        max_depth=2,
        max_offsets=64,
        budget=0,
        beam_width=1,
        progress=lambda *args: progress_calls.append(args),
        resume_status=lambda status: resume_statuses.append(status),
    )

    assert probe.fast_resume_used is False
    assert "cursor shards" in probe.fast_resume_rejected_reason
    assert resume_statuses[0]["fast_resume_used"] is False
    assert "cursor shards" in resume_statuses[0]["fast_resume_rejected_reason"]
    assert progress_calls[0] == ("UltimateMegaSuperLineFeedBruteForce", 0, 1)


def test_ultimate_linefeed_complete_progress_does_not_scan_or_relaunch(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(120))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets):
        del compressed[offset]

    corrupt = build_rgb_png(1, 120, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"
    progress = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.progress.json"
    before = idat.analyze_idat_stream(corrupt)
    _chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    suspect_offsets = idat_bruteforce.ultimate_linefeed_suspect_offsets(
        corrupt,
        start_offset=start_offset,
        max_offsets=64,
    )
    focused_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        suspect_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    broad_offsets = idat_bruteforce._ultimate_exhaustive_linefeed_offsets(
        root_stream,
        suspect_offsets=suspect_offsets,
        anchor=start_offset,
        max_offsets=max(64, min(len(root_stream), 64 * 8, 2048)),
    )
    broad_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        broad_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    merged_pool = idat_bruteforce._merge_ultimate_operations(focused_pool, broad_pool)
    idat_bruteforce._write_ultimate_progress(
        str(progress),
        source_hash=idat_bruteforce._stream_state_key(root_stream),
        target_adler=before.stored_adler,
        start_offset=start_offset,
        max_depth=2,
        max_offsets=64,
        operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(merged_pool),
        focused_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(focused_pool),
        broad_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(broad_pool),
        phase="complete",
        depth=2,
        pool_index=1,
        combination_rank=50,
        combination_indices=None,
        tested_candidates=50,
        pruned_candidates=5,
        state_count=7,
        budget=None,
    )
    original_load = idat_bruteforce._load_ultimate_checkpoint

    def fail_checkpoint_load(*args, **kwargs):
        raise AssertionError("complete progress should not scan the checkpoint archive")

    try:
        idat_bruteforce._load_ultimate_checkpoint = fail_checkpoint_load
        probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
            corrupt,
            start_offset=start_offset,
            checkpoint_path=str(checkpoint),
            progress_path=str(progress),
            max_depth=2,
            max_offsets=64,
            budget=None,
            beam_width=1,
            ultimate_workers=2,
        )
    finally:
        idat_bruteforce._load_ultimate_checkpoint = original_load

    assert probe.progress_resumed is True
    assert probe.tested_candidates == 50
    assert probe.best is None
    assert probe.reason == "previous Ultimate run already marked this search complete"


def test_ultimate_linefeed_probe_draws_progress_before_checkpoint_load(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(8))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    del compressed[crlf_offsets[0]]
    corrupt = build_rgb_png(1, 8, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    calls = []
    original_load = idat_bruteforce._load_ultimate_checkpoint

    def fake_load(*args, **kwargs):
        assert calls == [("UltimateMegaSuperLineFeedBruteForce", 0, 1)]
        return [], set(), 1, 0

    try:
        idat_bruteforce._load_ultimate_checkpoint = fake_load
        idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
            corrupt,
            start_offset=start_offset,
            checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
            max_depth=1,
            max_offsets=2,
            budget=0,
            progress=lambda *args: calls.append(args),
        )
    finally:
        idat_bruteforce._load_ultimate_checkpoint = original_load


def test_load_ultimate_checkpoint_emits_resume_progress(tmp_path):
    clean = build_rgb_png(1, 1, b"\x00abc")
    before = idat.analyze_idat_stream(clean)
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(clean)
    source_hash = idat_bruteforce._stream_state_key(root_stream)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"
    operations = (
        idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 0, b"", b"\r"),
        idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 1, b"", b"\r"),
    )
    with open(checkpoint, "w", encoding="utf-8") as file:
        for state_id, operation in enumerate(operations, start=1):
            file.write(
                json.dumps(
                    {
                        "source_hash": source_hash,
                        "state_id": state_id,
                        "operations": [idat_bruteforce._operation_to_json(operation)],
                    }
                )
                + "\n"
            )

    calls = []
    original_monotonic = idat_bruteforce.time.monotonic
    ticks = iter((0.0, 3.0, 6.0, 9.0))
    try:
        idat_bruteforce.time.monotonic = lambda: next(ticks, 9.0)
        loaded, _visited, _next_state_id, resumed = idat_bruteforce._load_ultimate_checkpoint(
            str(checkpoint),
            source_hash=source_hash,
            root_stream=root_stream,
            chunks=chunks,
            before=before,
            target_adler=before.stored_adler,
            progress=lambda *args: calls.append(args),
            progress_total=100,
        )
    finally:
        idat_bruteforce.time.monotonic = original_monotonic

    assert len(loaded) == 2
    assert resumed == 2
    assert calls[0] == ("UltimateMegaSuperLineFeedBruteForce", 1, 100)
    assert calls[-1] == ("UltimateMegaSuperLineFeedBruteForce", 4, 100)


def test_load_ultimate_checkpoint_limits_candidate_rebuild(tmp_path, monkeypatch):
    filtered = dynamic_filtered_rows(100)
    clean = build_rgb_png(1, 100, filtered)
    before = idat.analyze_idat_stream(clean)
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(clean)
    source_hash = idat_bruteforce._stream_state_key(root_stream)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"
    with open(checkpoint, "w", encoding="utf-8") as file:
        for state_id in range(20):
            old_byte = root_stream[state_id : state_id + 1]
            new_byte = bytes((old_byte[0] ^ 0x01,))
            operation = idat_bruteforce.SuperMegaLinefeedOperation(
                "bit-flip",
                state_id,
                old_byte,
                new_byte,
            )
            stream = idat_bruteforce._replay_operations(root_stream, (operation,))
            assert stream is not None
            file.write(
                json.dumps(
                    {
                        "source_hash": source_hash,
                        "stream_hash": idat_bruteforce._stream_state_key(stream),
                        "state_id": state_id,
                        "operations": [idat_bruteforce._operation_to_json(operation)],
                        "score": [0, 20 - state_id, state_id, state_id, 1, 0, 0, 0],
                        "status": "bad_adler",
                        "adler_status": "adler_mismatch",
                        "usable_scanlines": 20 - state_id,
                    }
                )
                + "\n"
            )

    calls = []
    replay_calls = []
    real_analyze = idat_bruteforce.idat.analyze_idat_stream
    real_replay = idat_bruteforce._replay_operations

    def counting_analyze(*args, **kwargs):
        calls.append(args)
        return real_analyze(*args, **kwargs)

    def counting_replay(*args, **kwargs):
        replay_calls.append(args)
        return real_replay(*args, **kwargs)

    monkeypatch.setattr(idat_bruteforce.idat, "analyze_idat_stream", counting_analyze)
    monkeypatch.setattr(idat_bruteforce, "_replay_operations", counting_replay)
    monkeypatch.setattr(idat_bruteforce, "ULTIMATE_LINEFEED_PROGRESS_STEP", 2)
    progress_calls = []
    loaded, visited, next_state_id, resumed = idat_bruteforce._load_ultimate_checkpoint(
        str(checkpoint),
        source_hash=source_hash,
        root_stream=root_stream,
        chunks=chunks,
        before=before,
        target_adler=before.stored_adler,
        progress=lambda *args: progress_calls.append(args),
        progress_total=100,
        candidate_limit=3,
        beam_width=2,
    )

    loaded_ids = {candidate.state_id for candidate in loaded}
    assert resumed == 20
    assert len(visited) == 20
    assert next_state_id == 20
    assert len(loaded) == 5
    assert len(calls) == 5
    assert len(replay_calls) == 5
    assert progress_calls[-1] == ("UltimateMegaSuperLineFeedBruteForce", 25, 100)
    assert {18, 19}.issubset(loaded_ids)
    assert {0, 1, 2}.issubset(loaded_ids)
    assert 10 not in loaded_ids


def test_ultimate_linefeed_eta_uses_twenty_humor_buckets():
    assert len(idat_bruteforce.ULTIMATE_LINEFEED_ETA_PHRASES) == 20
    assert idat_bruteforce.ultimate_linefeed_eta(200, candidates_per_second=100) == (
        idat_bruteforce.UltimateLinefeedEta(
            candidates_per_second=100,
            seconds=2.0,
            duration="2s",
            phrase="Barely enough time to look dramatic.",
        )
    )
    assert idat_bruteforce.ultimate_linefeed_eta_duration(3_506_270_321 / 100) == "1y 40d"
    assert idat_bruteforce.ultimate_linefeed_eta_phrase(10**19) == (
        "We will be dead before this finishes... but who cares."
    )
    assert idat_bruteforce.ultimate_linefeed_eta(None).phrase == (
        "No finish line. The fish has entered mythology."
    )


def test_ultimate_linefeed_universe_atom_comparison_lines():
    lines = idat_bruteforce.ultimate_linefeed_universe_atom_comparison_lines(
        7_012_540_641
    )

    assert lines == (
        "known universe atoms: about 10^80",
        "combination scale: about 1.43e70 times smaller",
    )
    assert idat_bruteforce.ultimate_linefeed_universe_atom_comparison_lines(0)[1] == (
        "combination scale: no candidates estimated"
    )
    assert idat_bruteforce.ultimate_linefeed_universe_atom_comparison_lines(10**81)[1] == (
        "combination scale: about 1e1 times larger"
    )


def test_ultimate_linefeed_bruteforce_recovers_multi_step_original_adler(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(checkpoint),
        max_depth=3,
        max_offsets=64,
        budget=2000,
        beam_width=8,
    )

    assert probe.strategy == "UltimateMegaSuperLineFeedBruteForce"
    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_match"
    assert probe.reached_depth == 2
    assert probe.visited_count <= probe.tested_candidates + 1
    assert checkpoint.exists()
    assert "target_adler=0x" in idat_bruteforce.ultimate_linefeed_probe_summary_line(probe)
    assert "UltimateMegaSuperLineFeedBruteForce candidate" in idat_bruteforce.ultimate_linefeed_candidate_summary_line(probe.best)
    assert zlib.decompress(b"".join(chunk.data for chunk in iter_chunks(probe.best.data) if chunk.chunk_type == b"IDAT")) == filtered


def test_ultimate_linefeed_bruteforce_recovers_four_step_original_adler(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:4]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=4,
        max_offsets=16,
        budget=10000,
        beam_width=4,
    )

    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_match"
    assert len(probe.best.operations) == 4
    assert probe.reached_depth == 4


def test_ultimate_linefeed_bruteforce_resumes_checkpoint(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"

    first = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(checkpoint),
        max_depth=1,
        max_offsets=64,
        budget=32,
        beam_width=8,
    )
    second = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(checkpoint),
        max_depth=2,
        max_offsets=64,
        budget=2000,
        beam_width=8,
    )

    assert first.best is not None
    assert second.resumed_states > 0
    assert second.best is not None
    assert second.best.after.adler_status == "adler_match"


def test_ultimate_linefeed_bruteforce_keeps_plausible_result_without_original_adler(tmp_path):
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=len(compressed) - 4,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=1,
        max_offsets=16,
        budget=256,
        beam_width=4,
    )

    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_mismatch"
    assert probe.top_candidates
    assert probe.visual_candidates
    assert probe.visual_preview_count <= probe.visual_gallery_limit
    assert probe.visual_gallery_path.endswith(".visual.json")
    assert validate_png_structure(probe.visual_candidates[0].preview_data).ok
    assert "original Adler target was not recovered" in idat_bruteforce.ultimate_linefeed_probe_summary_line(probe)


def test_ultimate_linefeed_visual_gallery_limit_zero_disables_gallery(tmp_path):
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=len(compressed) - 4,
        checkpoint_path=str(checkpoint),
        max_depth=1,
        max_offsets=16,
        budget=256,
        beam_width=4,
        visual_gallery_limit=0,
    )

    assert probe.best is not None
    assert probe.visual_gallery_limit == 0
    assert probe.visual_gallery_path == ""
    assert probe.visual_candidates == ()
    assert probe.visual_preview_count == 0
    assert not (tmp_path / "_UltimateMegaSuperLineFeedBruteForce.visual.json").exists()


def test_ultimate_linefeed_sigint_flushes_visual_gallery(tmp_path):
    import signal

    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"
    progress_path = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.progress.json"
    visual_path = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.visual.json"
    sent = False
    captured_handler = {"handler": None}

    def progress(_stage, tested, _budget):
        return None

    original_signal = idat_bruteforce.signal.signal
    original_getsignal = idat_bruteforce.signal.getsignal
    original_preview = idat_bruteforce._preview_ultimate_candidate_if_valid

    def fake_getsignal(signum):
        if signum == signal.SIGINT:
            return original_getsignal(signum)
        return original_getsignal(signum)

    def fake_signal(signum, handler):
        if signum == signal.SIGINT:
            captured_handler["handler"] = handler
            return original_getsignal(signum)
        return original_signal(signum, handler)

    def preview_then_interrupt(*args, **kwargs):
        nonlocal sent
        original_preview(*args, **kwargs)
        if captured_handler["handler"] is not None and not sent:
            sent = True
            captured_handler["handler"](signal.SIGINT, None)

    interrupted = False
    try:
        idat_bruteforce.signal.getsignal = fake_getsignal
        idat_bruteforce.signal.signal = fake_signal
        idat_bruteforce._preview_ultimate_candidate_if_valid = preview_then_interrupt
        idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
            corrupt,
            start_offset=idat_bruteforce.first_idat_problem_stream_offset(corrupt),
            checkpoint_path=str(checkpoint),
            progress_path=str(progress_path),
            max_depth=2,
            max_offsets=16,
            budget=4,
            beam_width=1,
            progress=progress,
            candidate_preview=lambda *_args: None,
        )
    except idat_bruteforce.UltimateLinefeedInterrupted:
        interrupted = True
    finally:
        idat_bruteforce.signal.getsignal = original_getsignal
        idat_bruteforce.signal.signal = original_signal
        idat_bruteforce._preview_ultimate_candidate_if_valid = original_preview

    assert interrupted is True
    assert progress_path.exists()
    assert visual_path.exists()
    record = json.loads(visual_path.read_text(encoding="utf-8"))
    assert record["preview_count"] > 0
    preview_dir = tmp_path / "Bruteforce_Previews" / "VisualCandidates"
    previews = list(preview_dir.glob("_VisualCandidate_*.png"))
    assert previews
    assert validate_png_structure(previews[0].read_bytes()).ok


def test_ultimate_linefeed_backfill_flush_progress_counts_kept_candidates():
    clean = build_rgb_png(1, 2, b"\x00abc" + b"\x00def")
    analysis = idat.analyze_idat_stream(clean)
    candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        clean,
        (),
        analysis,
        analysis,
        state_id=1,
        parent_id=0,
        source_offsets=(),
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 0),
    )
    backfill = idat_bruteforce.UltimateVisualBackfillCandidate(
        candidate,
        tested_candidates=12,
        structural_rank=(0, 0, 0),
        coverage=1.0,
    )
    calls = []

    filled = idat_bruteforce._fill_ultimate_visual_gallery_from_backfill(
        (),
        (backfill,),
        reference_image=None,
        reference_mode="exact",
        min_coverage=0.0,
        limit=123,
        progress=lambda current, total: calls.append((current, total)),
    )

    assert len(filled) == 1
    assert calls == [(1, 123)]


def test_ultimate_linefeed_visual_reference_scores_local_png(tmp_path):
    clean = build_rgb_png(1, 1, b"\x00abc")
    analysis = idat.analyze_idat_stream(clean)
    candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        clean,
        (),
        analysis,
        analysis,
    )
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(clean)

    reference_image, warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    scored = idat_bruteforce._attach_ultimate_visual_score(candidate, reference_image)
    missing_image, missing_warning = idat_bruteforce._load_ultimate_reference_image(
        str(tmp_path / "missing.png")
    )

    assert warning == ""
    assert scored.visual_score == 0.0
    assert scored.visual_score_kind == "exact_rgba"
    assert scored.matched_patch_count == 0
    assert missing_image is None
    assert "could not load visual reference" in missing_warning


def test_ultimate_linefeed_similar_reference_scores_different_sizes(tmp_path):
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(visual_scope_png(96, 64, variant="scope"))
    reference_image, warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))

    similar = visual_scope_png(160, 96, variant="scope")
    unrelated = visual_scope_png(160, 96, variant="unrelated")
    similar_score = idat_bruteforce._ultimate_visual_score(
        similar,
        reference_image,
        reference_mode="similar",
    )
    unrelated_score = idat_bruteforce._ultimate_visual_score(
        unrelated,
        reference_image,
        reference_mode="similar",
    )
    exact_score = idat_bruteforce._ultimate_visual_score(
        similar,
        reference_image,
        reference_mode="exact",
    )

    assert warning == ""
    assert similar_score.kind == "similar_auto_patch"
    assert similar_score.matched_patch_count > 0
    assert similar_score.score is not None
    assert unrelated_score.score is not None
    assert similar_score.score < unrelated_score.score
    assert exact_score.kind == "exact_rgba"
    assert math.isinf(exact_score.score)


def test_ultimate_linefeed_similar_reference_resizes_once_to_ihdr_size(tmp_path):
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(visual_scope_png(96, 64, variant="scope"))
    reference_image, warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    source_data = visual_scope_png(160, 96, variant="scope")

    similar_context = idat_bruteforce._ultimate_visual_reference(
        reference_image,
        reference_mode="similar",
        source_data=source_data,
    )
    exact_context = idat_bruteforce._ultimate_visual_reference(
        reference_image,
        reference_mode="exact",
        source_data=source_data,
    )

    assert warning == ""
    assert tuple(similar_context.image.size) == (160, 96)
    assert tuple(exact_context.image.size) == (96, 64)


def test_ultimate_reference_regions_loads_clamped_schema(tmp_path):
    reference_path = tmp_path / "reference.png"
    source = visual_scope_png(96, 64, variant="scope")
    reference_path.write_bytes(source)
    reference_image, _warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    record = {
        "version": idat_bruteforce.ULTIMATE_LINEFEED_REFERENCE_REGION_VERSION,
        "candidate": {
            "size": [96, 64],
            "hash": idat_bruteforce._ultimate_image_hash_from_bytes(source),
        },
        "reference": {
            "size": [96, 64],
            "hash": idat_bruteforce._ultimate_image_hash_from_image(reference_image),
        },
        "regions": [
            {
                "candidate_region": [-1.0, 0.1, 0.7, 1.5],
                "reference_region": [0.0, 0.0, 1.0, 1.0],
                "weight": 2,
                "label": "scope",
                "match_mode": "search_candidate",
            }
        ],
    }
    regions_path = tmp_path / "_ULF.reference_regions.json"
    regions_path.write_text(json.dumps(record), encoding="utf-8")

    mapping, warning = idat_bruteforce.load_ultimate_reference_regions(
        str(regions_path),
        candidate_data=source,
        reference_image=reference_image,
    )

    assert warning == ""
    assert mapping is not None
    assert mapping.regions[0].candidate_region == (0.0, 0.1, 0.7, 1.0)
    assert mapping.regions[0].reference_region == (0.0, 0.0, 1.0, 1.0)
    assert mapping.regions[0].weight == 2.0
    assert mapping.regions[0].match_mode == "search"


def test_ultimate_linefeed_similar_manual_roi_scores_region_pairs(tmp_path):
    reference = visual_scope_png(96, 64, variant="scope")
    similar = visual_scope_png(160, 96, variant="scope")
    unrelated = visual_scope_png(160, 96, variant="unrelated")
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(reference)
    reference_image, _warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    regions = idat_bruteforce.UltimateReferenceRegions(
        path=str(tmp_path / "_ULF.reference_regions.json"),
        regions=(
            idat_bruteforce.UltimateReferenceRegion(
                candidate_region=(0.0, 0.0, 1.0, 1.0),
                reference_region=(0.0, 0.0, 1.0, 1.0),
                weight=1.0,
                label="scope",
            ),
        ),
    )
    context = idat_bruteforce._ultimate_visual_reference(
        reference_image,
        reference_mode="similar",
        reference_regions=regions,
    )

    similar_score = idat_bruteforce._ultimate_visual_score(
        similar,
        context,
        reference_mode="similar",
    )
    unrelated_score = idat_bruteforce._ultimate_visual_score(
        unrelated,
        context,
        reference_mode="similar",
    )

    assert similar_score.kind == "similar_manual_roi"
    assert similar_score.matched_patch_count == 1
    assert similar_score.score is not None
    assert unrelated_score.score is not None
    assert similar_score.score < unrelated_score.score


def test_ultimate_linefeed_similar_manual_roi_searches_single_reference_region(tmp_path):
    from io import BytesIO
    from PIL import Image, ImageDraw

    def band_png(width, height, *, band_top, noise=False):
        image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        draw = ImageDraw.Draw(image)
        if noise:
            for index in range(0, max(width, height), 5):
                draw.line((0, index, width, height - index), fill=(180, 20, 20, 255), width=2)
        else:
            top = int(height * band_top)
            bottom = min(height - 1, top + max(4, height // 8))
            draw.rectangle((0, top, width - 1, bottom), fill=(230, 230, 0, 255))
            for x in range(0, width, max(1, width // 8)):
                draw.line((x, top, x, bottom), fill=(90, 90, 0, 255), width=1)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    reference = band_png(96, 64, band_top=0.78)
    similar = band_png(160, 96, band_top=0.24)
    unrelated = band_png(160, 96, band_top=0.24, noise=True)
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(reference)
    reference_image, _warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    regions = idat_bruteforce.UltimateReferenceRegions(
        path=str(tmp_path / "_ULF.reference_regions.json"),
        regions=(
            idat_bruteforce.UltimateReferenceRegion(
                candidate_region=(0.0, 0.0, 1.0, 1.0),
                reference_region=(0.0, 0.72, 1.0, 0.95),
                weight=1.0,
                label="single reference band",
                match_mode="search_candidate",
            ),
        ),
    )
    context = idat_bruteforce._ultimate_visual_reference(
        reference_image,
        reference_mode="similar",
        reference_regions=regions,
    )

    similar_score = idat_bruteforce._ultimate_visual_score(
        similar,
        context,
        reference_mode="similar",
    )
    unrelated_score = idat_bruteforce._ultimate_visual_score(
        unrelated,
        context,
        reference_mode="similar",
    )

    assert similar_score.kind == "similar_manual_roi"
    assert similar_score.matched_patch_count == 1
    assert similar_score.score is not None
    assert unrelated_score.score is not None
    assert similar_score.score < unrelated_score.score


def test_ultimate_linefeed_similar_manual_roi_search_handles_scale_change(tmp_path):
    from io import BytesIO
    from PIL import Image, ImageDraw

    def marker_png(width, height, *, box):
        image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle(box, fill=(230, 230, 0, 255))
        draw.line((box[0], box[1], box[2], box[3]), fill=(80, 80, 0, 255), width=2)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    reference = marker_png(120, 90, box=(18, 18, 54, 54))
    similar = marker_png(240, 180, box=(118, 88, 190, 160))
    unrelated = marker_png(240, 180, box=(8, 8, 36, 36))
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(reference)
    reference_image, _warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    regions = idat_bruteforce.UltimateReferenceRegions(
        path=str(tmp_path / "_ULF.reference_regions.json"),
        regions=(
            idat_bruteforce.UltimateReferenceRegion(
                candidate_region=(0.0, 0.0, 1.0, 1.0),
                reference_region=(0.12, 0.12, 0.48, 0.60),
                weight=1.0,
                label="scaled marker",
                match_mode="search",
            ),
        ),
    )
    context = idat_bruteforce._ultimate_visual_reference(
        reference_image,
        reference_mode="similar",
        reference_regions=regions,
    )

    similar_score = idat_bruteforce._ultimate_visual_score(similar, context, reference_mode="similar")
    unrelated_score = idat_bruteforce._ultimate_visual_score(unrelated, context, reference_mode="similar")

    assert similar_score.score is not None
    assert unrelated_score.score is not None
    assert similar_score.score < unrelated_score.score


def test_ultimate_linefeed_paired_roi_local_search_handles_small_shift():
    from PIL import Image, ImageDraw

    reference = Image.new("RGBA", (80, 60), (0, 0, 0, 255))
    candidate = Image.new("RGBA", (80, 60), (0, 0, 0, 255))
    ImageDraw.Draw(reference).rectangle((28, 20, 44, 36), fill=(230, 230, 0, 255))
    ImageDraw.Draw(candidate).rectangle((34, 20, 50, 36), fill=(230, 230, 0, 255))
    region = (0.30, 0.25, 0.60, 0.70)
    reference_crop = idat_bruteforce._ultimate_crop_region(reference, region)
    exact_score = idat_bruteforce._ultimate_roi_pair_score(
        idat_bruteforce._ultimate_crop_region(candidate, region),
        reference_crop,
    )
    shifted_score = idat_bruteforce._ultimate_paired_region_score(candidate, region, reference_crop)

    assert shifted_score < exact_score


def test_ultimate_linefeed_single_roi_uses_source_snapshot(tmp_path):
    reference = visual_scope_png(96, 64, variant="scope")
    source = visual_scope_png(96, 64, variant="scope")
    similar = visual_scope_png(96, 64, variant="scope")
    unrelated = visual_scope_png(96, 64, variant="unrelated")
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(reference)
    reference_image, _warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    regions = idat_bruteforce.UltimateReferenceRegions(
        path=str(tmp_path / "_ULF.reference_regions.json"),
        regions=(
            idat_bruteforce.UltimateReferenceRegion(
                candidate_region=(0.0, 0.0, 1.0, 1.0),
                reference_region=(0.0, 0.0, 1.0, 1.0),
                weight=1.0,
                label="source only",
                match_mode="single",
            ),
        ),
    )
    context = idat_bruteforce._ultimate_visual_reference(
        reference_image,
        reference_mode="similar",
        reference_regions=regions,
        source_data=source,
    )

    similar_score = idat_bruteforce._ultimate_visual_score(similar, context, reference_mode="similar")
    unrelated_score = idat_bruteforce._ultimate_visual_score(unrelated, context, reference_mode="similar")

    assert similar_score.score is not None
    assert unrelated_score.score is not None
    assert similar_score.score < unrelated_score.score


def test_ultimate_linefeed_negative_roi_penalizes_noisy_candidate(tmp_path):
    from io import BytesIO
    from PIL import Image, ImageDraw

    def noise_png(noise=False):
        image = Image.new("RGBA", (80, 60), (0, 0, 0, 255))
        draw = ImageDraw.Draw(image)
        if noise:
            for index in range(0, 80, 4):
                draw.line((index, 0, 80 - index // 2, 60), fill=(255, 255, 0, 255), width=1)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    reference = visual_scope_png(80, 60, variant="scope")
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(reference)
    reference_image, _warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    regions = idat_bruteforce.UltimateReferenceRegions(
        path=str(tmp_path / "_ULF.reference_regions.json"),
        regions=(
            idat_bruteforce.UltimateReferenceRegion(
                candidate_region=(0.0, 0.0, 1.0, 1.0),
                reference_region=(0.0, 0.0, 1.0, 1.0),
                weight=1.0,
                label="quiet area",
                match_mode="negative",
            ),
        ),
    )
    context = idat_bruteforce._ultimate_visual_reference(
        reference_image,
        reference_mode="similar",
        reference_regions=regions,
    )

    clean_score = idat_bruteforce._ultimate_visual_score(noise_png(False), context, reference_mode="similar")
    noisy_score = idat_bruteforce._ultimate_visual_score(noise_png(True), context, reference_mode="similar")

    assert clean_score.score is not None
    assert noisy_score.score is not None
    assert clean_score.score < noisy_score.score


def test_ultimate_linefeed_bruteforce_spends_budget_when_no_terminal_match(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(120))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets):
        del compressed[offset]

    corrupt = build_rgb_png(1, 120, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    progress_calls = []

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=2,
        max_offsets=128,
        budget=300,
        beam_width=1,
        progress=lambda stage, tested, budget: progress_calls.append((stage, tested, budget)),
    )

    assert probe.tested_candidates == 300
    assert probe.budget_exhausted is True
    assert probe.best is not None
    assert probe.best.after.adler_status != "adler_match"
    assert ("UltimateMegaSuperLineFeedBruteForce", 100, 300) in progress_calls
    assert ("UltimateMegaSuperLineFeedBruteForce", 200, 300) in progress_calls
    assert ("UltimateMegaSuperLineFeedBruteForce", 300, 300) in progress_calls


def test_ultimate_linefeed_parallel_progress_updates_before_result_shards_finish(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(120))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets):
        del compressed[offset]

    corrupt = build_rgb_png(1, 120, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    progress_calls = []

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(tmp_path / "_ULF.checkpoint.jsonl"),
        progress_path=str(tmp_path / "_ULF.progress.json"),
        max_depth=2,
        max_offsets=128,
        budget=500,
        beam_width=1,
        ultimate_workers=2,
        progress=lambda stage, tested, budget: progress_calls.append((stage, tested, budget)),
    )

    assert probe.tested_candidates == 500
    assert probe.budget_exhausted is True
    displayed = [tested for _stage, tested, _budget in progress_calls]
    assert displayed == sorted(displayed)
    assert ("UltimateMegaSuperLineFeedBruteForce", 100, 500) in progress_calls
    assert ("UltimateMegaSuperLineFeedBruteForce", 200, 500) in progress_calls


def test_ultimate_linefeed_bruteforce_broadens_small_focused_space(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(120))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:4]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 120, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=2,
        max_offsets=8,
        budget=250,
        beam_width=1,
    )

    assert probe.tested_candidates == 250
    assert probe.budget_exhausted is True
    assert probe.best is not None
    assert probe.best.after.adler_status != "adler_match"


def test_ultimate_linefeed_bruteforce_skips_clean_complete_idat(tmp_path):
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(8))
    clean = build_rgb_png(1, 8, filtered)

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        clean,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        budget=500,
    )

    assert probe.best is None
    assert probe.tested_candidates == 0
    assert probe.budget_exhausted is False
    assert probe.reason == "IDAT stream is already complete with matching Adler"


def test_ultimate_linefeed_bruteforce_accepts_unbounded_budget(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(8))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    del compressed[crlf_offsets[0]]

    corrupt = build_rgb_png(1, 8, filtered, idat_data=bytes(compressed))

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=1,
        max_offsets=2,
        budget=None,
        beam_width=1,
    )

    assert probe.tested_candidates > 0
    assert probe.budget_exhausted is False


def test_rebuild_partial_idat_blackfill_ignores_complete_or_unusable_streams():
    complete = build_rgb_png(1, 1, b"\x00abc")
    invalid = build_rgb_png(1, 1, b"\x00abc", idat_data=b"bad")

    assert idat.rebuild_partial_idat_blackfill(complete) is None
    assert idat.rebuild_partial_idat_blackfill(invalid) is None
    assert idat.rebuild_tolerant_idat_salvage(complete) is None
    assert idat.rebuild_tolerant_idat_salvage(invalid) is None


def test_analyze_idat_stream_reports_complete_stream():
    filtered = b"\x00abc" + b"\x00def"
    analysis = idat.analyze_idat_stream(build_rgb_png(1, 2, filtered))

    assert analysis.supported is True
    assert analysis.complete is True
    assert analysis.status == "complete"
    assert analysis.idat_chunk_count == 1
    assert analysis.compressed_size > 0
    assert analysis.decompressed_size == 8
    assert analysis.expected_size == 8
    assert analysis.complete_scanlines == 2
    assert analysis.usable_scanlines == 2
    assert analysis.zlib_error == ""
    assert analysis.error_offset is None
    assert analysis.stored_adler == zlib.adler32(filtered)
    assert analysis.computed_adler == zlib.adler32(filtered)
    assert analysis.adler_status == "adler_match"
    assert analysis.crc_provenance == "original_crc_ok"
    assert analysis.source_kind == "original"


def test_zlib_trailer_adler_extracts_target_from_idat_stream():
    filtered = b"\x00abc"
    compressed = zlib.compress(filtered)

    assert idat.zlib_trailer_adler(compressed) == zlib.adler32(filtered)
    assert idat.format_adler(zlib.adler32(filtered)).startswith("0x")
    assert idat.zlib_trailer_adler(b"bad") is None


def test_analyze_idat_stream_marks_rebuilt_adler_provenance():
    filtered = b"\x00abc"
    analysis = idat.analyze_idat_stream(
        build_rgb_png(1, 1, filtered),
        source_kind="clone",
        crc_provenance="rebuilt_by_chunklate",
    )

    assert analysis.complete is True
    assert analysis.adler_status == "adler_rebuilt"
    assert analysis.crc_provenance == "rebuilt_by_chunklate"
    assert analysis.source_kind == "clone"


def test_analyze_idat_stream_reports_corrupt_deflate():
    filtered = b"\x00abc"
    analysis = idat.analyze_idat_stream(build_rgb_png(1, 1, filtered, idat_data=b"\x78\x9c\xff\xff"))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.status == "corrupt_deflate"
    assert analysis.zlib_error
    assert analysis.error_offset is not None
    assert analysis.error_context_hex


def test_analyze_idat_stream_attaches_deflate_header_diagnosis():
    candidate, _offset, _original = dynamic_header_corrupt_png()

    analysis = idat.analyze_idat_stream(candidate)

    assert analysis.status == "corrupt_deflate"
    assert analysis.decompressed_size == 0
    assert analysis.usable_scanlines == 0
    assert analysis.deflate_header is not None
    assert analysis.deflate_header.status == "bad_code_length_tree"


def test_analyze_idat_stream_maps_error_to_multi_idat_file_offset():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[2] ^= 0xFF
    candidate = build_rgb_png(
        1,
        2,
        filtered,
        idat_data=bytes(compressed),
        idat_parts=split_bytes(bytes(compressed), 5),
    )

    analysis = idat.analyze_idat_stream(candidate)
    chunks = list(iter_chunks(candidate))
    idat_chunks = [chunk for chunk in chunks if chunk.chunk_type == b"IDAT"]

    assert analysis.status == "corrupt_deflate"
    assert analysis.error_offset is not None
    assert analysis.error_idat_index == 2
    assert analysis.error_idat_offset == analysis.error_offset - len(idat_chunks[0].data)
    assert analysis.error_file_offset == idat_chunks[1].offset + 8 + analysis.error_idat_offset


def test_idat_deflate_probe_repairs_single_byte_corruption():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    original = compressed[2]
    compressed[2] ^= 0xFF
    candidate = build_rgb_png(
        1,
        2,
        filtered,
        idat_data=bytes(compressed),
        idat_parts=split_bytes(bytes(compressed), 5),
    )

    result = idat_bruteforce.probe_idat_deflate_byte_candidates(candidate, window_radius=8)

    assert result.best is not None
    assert result.best.stream_offset == 2
    assert result.best.new_byte == original
    assert result.best.after.complete is True
    assert idat.analyze_idat_stream(result.best.data).complete is True


def test_deflate_header_probe_repairs_header_corruption():
    candidate, stream_offset, original = dynamic_header_corrupt_png()

    result = idat_bruteforce.probe_deflate_header_candidates(candidate, budget=1000)

    assert result.best is not None
    assert result.strategy == "deflate-header"
    assert result.best.stream_offset == stream_offset
    assert result.best.new_byte == original
    assert result.best.after.usable_scanlines == 100
    assert result.best.after.complete is True


def test_deflate_header_probe_repairs_extra_header_byte():
    filtered = dynamic_filtered_rows()
    compressed = zlib.compress(filtered, 1)
    stream_offset = 3
    candidate = build_rgb_png(
        1,
        100,
        filtered,
        idat_data=compressed[:stream_offset] + b"\x00" + compressed[stream_offset:],
    )

    result = idat_bruteforce.probe_deflate_header_candidates(candidate)

    assert result.best is not None
    assert result.best.edit_kind == "remove"
    assert result.best.stream_offset == stream_offset
    assert result.best.old_bytes == b"\x00"
    assert result.best.after.complete is True


def test_deflate_header_probe_repairs_missing_header_byte():
    filtered = dynamic_filtered_rows()
    compressed = zlib.compress(filtered, 1)
    stream_offset = 3
    missing = compressed[stream_offset : stream_offset + 1]
    candidate = build_rgb_png(
        1,
        100,
        filtered,
        idat_data=compressed[:stream_offset] + compressed[stream_offset + 1 :],
    )

    result = idat_bruteforce.probe_deflate_header_candidates(candidate)

    assert result.best is not None
    assert result.best.edit_kind == "insert"
    assert result.best.stream_offset == stream_offset
    assert result.best.new_bytes == missing
    assert result.best.after.complete is True


def test_dynamic_huffman_header_probe_repairs_two_bit_length_corruption():
    candidate, bits, _original = dynamic_header_two_bit_corrupt_png()
    before = idat.analyze_idat_stream(candidate)

    assert before.status == "corrupt_deflate"
    assert before.decompressed_size == 0
    assert before.deflate_header is not None
    assert before.deflate_header.status == "invalid_huffman_lengths"

    result = idat_bruteforce.probe_dynamic_huffman_header_candidates(
        candidate,
        budget=1000,
        max_bits=80,
    )

    assert result.best is not None
    assert result.strategy == "dynamic-huffman-header"
    assert result.best.edit_kind == "bit-flip-set"
    assert result.best.bit_offsets == bits
    assert result.best.after.complete is True
    assert result.best.after.usable_scanlines == 100
    idat_chunks = [chunk for chunk in iter_chunks(result.best.data) if chunk.chunk_type == b"IDAT"]
    assert idat_chunks
    assert all(chunk.crc == chunk.computed_crc for chunk in idat_chunks)


def test_dynamic_huffman_header_probe_keeps_zero_scanline_candidate_diagnostic_only():
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png(bits=(604, 22))
    before = idat.analyze_idat_stream(candidate)

    assert before.deflate_header is not None
    assert before.deflate_header.status == "invalid_huffman_lengths"
    result = idat_bruteforce.probe_dynamic_huffman_header_candidates(
        candidate,
        budget=2000,
        max_bits=80,
    )

    assert result.best is None
    assert result.diagnostic_best is not None
    assert result.diagnostic_best.after.decompressed_size > result.before.decompressed_size
    assert result.diagnostic_best.after.usable_scanlines == 0
    assert idat_bruteforce.diagnostic_candidate_summary_lines(result)


def test_idat_local_deflate_diagnostic_reports_dynamic_huffman_context():
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()
    before = idat.analyze_idat_stream(candidate)

    lines = idat_bruteforce.idat_local_deflate_diagnostic_summary_lines(
        candidate,
        analysis=before,
    )

    assert any(line.startswith("-IDAT local deflate diagnostic:") for line in lines)
    assert any("HLIT=" in line and "HDIST=" in line and "HCLEN=" in line for line in lines)
    assert any(line.startswith("-IDAT dynamic Huffman suspect bytes:") for line in lines)
    assert any(line.startswith("-IDAT dynamic Huffman token suspects:") for line in lines)


def test_idat_local_deflate_probe_keeps_search_bounded_and_scores_progress():
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()

    result = idat_bruteforce.probe_idat_deflate_local_candidates(
        candidate,
        budget=1200,
        max_bits=80,
    )

    assert result.strategy == "deflate-local"
    assert result.tested_candidates <= 1200
    assert result.window_start == 0
    assert result.window_end <= 0x120
    assert result.best is not None or result.diagnostic_best is not None


def test_idat_local_deflate_png_filter_mode_prefers_filter_rows(monkeypatch):
    before_raw = b"\x00abc" + b"\xffdef" + b"\xffghi"
    noisy_raw = before_raw + (b"x" * 80)
    filtered_raw = b"\x00abc" + b"\x04def" + b"\xffghi"
    before_data = build_rgb_png(1, 3, before_raw, idat_data=zlib.compress(before_raw))
    noisy_data = build_rgb_png(1, 3, noisy_raw, idat_data=zlib.compress(noisy_raw))
    filtered_data = build_rgb_png(1, 3, filtered_raw, idat_data=zlib.compress(filtered_raw))
    before = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        width=1,
        height=3,
        bit_depth=8,
        color_type=2,
        scanline_size=4,
        expected_size=12,
        decompressed_size=len(before_raw),
        complete_scanlines=3,
        usable_scanlines=1,
        error_offset=5,
    )
    noisy_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        width=1,
        height=3,
        bit_depth=8,
        color_type=2,
        scanline_size=4,
        expected_size=12,
        decompressed_size=len(noisy_raw),
        complete_scanlines=3,
        usable_scanlines=1,
        error_offset=6,
    )
    filtered_after = idat.IdatStreamAnalysis(
        supported=True,
        complete=False,
        status="corrupt_deflate",
        width=1,
        height=3,
        bit_depth=8,
        color_type=2,
        scanline_size=4,
        expected_size=12,
        decompressed_size=len(filtered_raw),
        complete_scanlines=3,
        usable_scanlines=1,
        error_offset=7,
    )
    diagnostic = idat_bruteforce.IdatLocalDeflateDiagnostic(
        before=before,
        trace=SimpleNamespace(byte_offset=0, summary="mock dynamic trace"),
        stream_size=16,
        stream_offset=0,
        file_offset=0,
        idat_index=1,
        idat_offset=0,
        window_start=0,
        window_end=1,
        context_hex="",
    )

    monkeypatch.setattr(idat_bruteforce.idat, "analyze_idat_stream", lambda _data: before)
    monkeypatch.setattr(idat_bruteforce, "idat_local_deflate_diagnostic", lambda *_args, **_kwargs: diagnostic)
    monkeypatch.setattr(
        idat_bruteforce,
        "mutate_idat_stream_edit",
        lambda _data, _offset, edit_kind, **_kwargs: idat_bruteforce.IdatDeflateCandidate(
            data=filtered_data if edit_kind == "insert" else noisy_data,
            stream_offset=0,
            file_offset=0,
            idat_index=1,
            idat_offset=0,
            old_byte=0,
            new_byte=0,
            before=before,
            after=filtered_after if edit_kind == "insert" else noisy_after,
            edit_kind=edit_kind,
            old_bytes=b"\x00",
            new_bytes=b"\x04" if edit_kind == "insert" else b"",
        ),
    )
    monkeypatch.setattr(idat_bruteforce, "mutate_idat_stream_byte", lambda *_args, **_kwargs: None)

    result = idat_bruteforce.probe_idat_deflate_local_candidates(
        before_data,
        budget=2,
        score_mode="png-filter",
    )

    assert result.strategy == "deflate-local-png-filter"
    assert result.best is not None
    assert result.best.data == filtered_data
    assert "score_mode=png-filter" in result.reason


def test_idat_png_filter_literal_repair_fixes_direct_row_filter_bytes():
    rows = (
        b"\x00abc",
        b"\xd1def",
        b"\x78ghi",
        b"\x4ejkl",
    )
    filtered_raw = b"".join(rows)
    compressor = zlib.compressobj(0)
    stored_idat = compressor.compress(filtered_raw) + compressor.flush()
    data = build_rgb_png(1, 4, filtered_raw, idat_data=stored_idat)
    before = idat.analyze_idat_stream(data)

    result = idat_bruteforce.probe_idat_png_filter_literal_repair(
        data,
        max_rows=8,
        max_repairs=8,
    )

    assert before.usable_scanlines == 1
    assert result.strategy == "png-filter-literal-repair"
    assert result.best is not None
    assert len(result.chain) == 3
    assert result.window_start > 0
    assert result.window_end > result.window_start
    after = idat.analyze_idat_stream(result.best.data)
    stream = idat_bruteforce._all_chunks_and_idat_stream(result.best.data)[1]
    raw = idat_bruteforce.idat_partial_raw_prefix(stream, max_output=64).raw
    raw_score = idat_bruteforce.score_png_raw_prefix(raw, after)
    assert after.usable_scanlines == 4
    assert raw_score.valid_filter_rows == 4
    assert all(candidate.new_bytes == b"\x00" for candidate in result.chain)
    assert idat_bruteforce.candidate_summary_lines(result)[-1].startswith(
        "-IDAT deflate candidate:"
    )


def test_idat_png_filter_literal_repair_searches_near_mapped_filter_byte():
    filtered_raw = bytes.fromhex("018da4bb009eb5cc01afc6dd00c0d7ee")
    corrupt_idat = bytes.fromhex(
        "780102ec5db29b61ded6338ceb8fdd653870fd1d00428408e5"
    )
    data = build_rgb_png(1, 4, filtered_raw, idat_data=corrupt_idat)
    before = idat.analyze_idat_stream(data)

    result = idat_bruteforce.probe_idat_png_filter_literal_repair(
        data,
        max_rows=8,
        max_repairs=3,
        search_radius=16,
        candidate_budget=8000,
    )

    assert before.status == "bad_adler"
    assert before.usable_scanlines == 0
    assert before.decompressed_size > 0
    assert result.best is not None
    assert len(result.chain) == 1
    assert result.best.stream_offset == 2
    assert result.best.old_bytes == b"\x02"
    assert result.best.new_bytes == b"\x63"
    assert result.best.after.complete
    assert result.best.after.usable_scanlines == 4


def test_idat_deep_beam_chases_depth_two_progress():
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()

    result = idat_bruteforce.probe_idat_deflate_deep_beam(
        candidate,
        budget=5000,
        max_depth=2,
        beam_width=8,
        top_candidates=4,
        workers=1,
        checkpoint_every=999999,
    )

    assert result.strategy == "deep-beam"
    assert result.workers == 1
    assert result.reached_depth == 2
    assert result.best is not None
    assert len(result.best.operations) >= 2
    assert result.best.after.decompressed_size > result.before.decompressed_size
    assert idat_bruteforce.deep_beam_candidate_summary_lines(result)


def test_idat_raw_prefix_score_prefers_png_filter_over_longer_noise():
    bad_raw = b"\xbd" + b"x" * 200
    good_raw = b"\x00abc"
    bad_data = build_rgb_png(1, 1, bad_raw, idat_data=zlib.compress(bad_raw))
    good_data = build_rgb_png(1, 1, good_raw, idat_data=zlib.compress(good_raw))
    bad_analysis = idat.analyze_idat_stream(bad_data)
    good_analysis = idat.analyze_idat_stream(good_data)
    _bad_chunks, bad_stream = idat_bruteforce._all_chunks_and_idat_stream(bad_data)
    _good_chunks, good_stream = idat_bruteforce._all_chunks_and_idat_stream(good_data)

    bad_prefix = idat_bruteforce.idat_partial_raw_prefix(bad_stream)
    good_prefix = idat_bruteforce.idat_partial_raw_prefix(good_stream)
    bad_raw_score = idat_bruteforce.score_png_raw_prefix(bad_prefix.raw, bad_analysis)
    good_raw_score = idat_bruteforce.score_png_raw_prefix(good_prefix.raw, good_analysis)
    bad_score = idat_bruteforce._deep_beam_score(
        bad_analysis,
        bad_stream,
        0,
        data=bad_data,
        original_idat_count=1,
    )
    good_score = idat_bruteforce._deep_beam_score(
        good_analysis,
        good_stream,
        0,
        data=good_data,
        original_idat_count=1,
    )

    assert bad_raw_score.first_filter_ok is False
    assert good_raw_score.first_filter_ok is True
    assert good_raw_score.rank > bad_raw_score.rank
    assert good_score > bad_score


def test_idat_raw_prefix_score_counts_multiple_scanline_filters():
    raw = b"\x00abc\x04def\x09ghi"
    data = build_rgb_png(1, 3, raw, idat_data=zlib.compress(raw))
    analysis = idat.analyze_idat_stream(data)

    score = idat_bruteforce.score_png_raw_prefix(raw, analysis)

    assert analysis.scanline_size == 4
    assert score.checked_filter_rows == 3
    assert score.valid_filter_rows == 2


def test_idat_raw_png_oracle_rejects_noise_first_filter():
    bad_raw = b"\xbdxxx"
    good_raw = b"\x04xxx"
    bad_data = build_rgb_png(1, 1, bad_raw, idat_data=zlib.compress(bad_raw))
    good_data = build_rgb_png(1, 1, good_raw, idat_data=zlib.compress(good_raw))
    bad_analysis = idat.analyze_idat_stream(bad_data)
    good_analysis = idat.analyze_idat_stream(good_data)
    _bad_chunks, bad_stream = idat_bruteforce._all_chunks_and_idat_stream(bad_data)
    _good_chunks, good_stream = idat_bruteforce._all_chunks_and_idat_stream(good_data)

    bad = idat_bruteforce.raw_png_oracle_decision(bad_stream, bad_analysis)
    good = idat_bruteforce.raw_png_oracle_decision(good_stream, good_analysis)

    assert bad.rejected is True
    assert "first raw byte" in bad.reject_reason
    assert good.rejected is False
    assert good.png_plausible is True
    assert good.rank > bad.rank


def test_idat_deep_beam_default_budget_is_ten_million():
    assert idat_bruteforce.DEEP_BEAM_DEFAULT_BUDGET == 10_000_000


def test_idat_deep_beam_auto_workers_are_memory_capped():
    assert idat_bruteforce._deep_beam_workers("auto") <= idat_bruteforce.DEEP_BEAM_AUTO_WORKER_LIMIT
    assert idat_bruteforce._deep_beam_workers(None) <= idat_bruteforce.DEEP_BEAM_AUTO_WORKER_LIMIT


def test_idat_deep_beam_cpu_batch_default_and_clamp():
    assert idat_bruteforce.DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE == 128
    assert idat_bruteforce._deep_beam_cpu_batch_size(0, 1, 999) == 256
    assert idat_bruteforce._deep_beam_cpu_batch_size(10_000, 4, 999) == 256
    assert (
        idat_bruteforce._deep_beam_cpu_batch_size(
            10_000,
            4,
            idat_bruteforce.DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE,
        )
        == 256
    )
    assert (
        idat_bruteforce._deep_beam_cpu_batch_size(
            64,
            4,
            idat_bruteforce.DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE,
        )
        == 32
    )


def test_idat_deep_beam_in_flight_batches_scale_with_workers():
    assert idat_bruteforce._deep_beam_worker_in_flight_limit(4, 100) == 4
    assert idat_bruteforce._deep_beam_worker_in_flight_limit(8, 100) == 8
    assert (
        idat_bruteforce._deep_beam_worker_in_flight_limit(32, 100)
        == idat_bruteforce.DEEP_BEAM_WORKER_IN_FLIGHT_LIMIT
    )
    assert idat_bruteforce._deep_beam_worker_in_flight_limit(8, 3) == 3


def test_idat_deep_beam_checkpoint_resume_round_trips(tmp_path=None):
    if tmp_path is None:
        with tempfile.TemporaryDirectory() as directory:
            return test_idat_deep_beam_checkpoint_resume_round_trips(Path(directory))

    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()
    checkpoint = tmp_path / "_deep_beam.checkpoint.jsonl"
    progress = tmp_path / "_deep_beam.progress.json"

    first = idat_bruteforce.probe_idat_deflate_deep_beam(
        candidate,
        budget=900,
        max_depth=1,
        beam_width=4,
        top_candidates=3,
        workers=1,
        checkpoint_every=100,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
    )
    second = idat_bruteforce.probe_idat_deflate_deep_beam(
        candidate,
        budget=300,
        max_depth=1,
        beam_width=4,
        top_candidates=3,
        workers=1,
        checkpoint_every=100,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
    )

    assert first.top_candidates
    assert checkpoint.exists()
    assert progress.exists()
    assert second.progress_resumed is True
    assert second.top_candidates
    assert second.visited_count >= len(first.top_candidates)


def test_idat_deep_beam_byte_successors_prune_per_parent(monkeypatch):
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()
    before = idat.analyze_idat_stream(candidate)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    parent = idat_bruteforce.IdatDeepBeamCandidate(
        data=candidate,
        stream=stream,
        operations=(),
        before=before,
        after=before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=idat_bruteforce._deep_beam_score(
            before,
            stream,
            0,
            data=candidate,
            original_idat_count=original_idat_count,
        ),
    )
    fake_candidates = []
    for index in range(10):
        new_byte = (stream[0] + index + 1) & 0xFF
        variant_stream = bytes((new_byte,)) + stream[1:]
        variant_data = idat_bruteforce._rebuild_with_single_idat_stream(chunks, variant_stream)
        fake_candidates.append(
            idat_bruteforce.IdatDeflateCandidate(
                data=variant_data,
                stream_offset=0,
                file_offset=0,
                idat_index=1,
                idat_offset=0,
                old_byte=stream[0],
                new_byte=new_byte,
                before=before,
                after=idat.analyze_idat_stream(variant_data),
                edit_kind="replace",
                old_bytes=stream[:1],
                new_bytes=bytes((new_byte,)),
            )
        )

    monkeypatch.setattr(
        idat_bruteforce,
        "_deep_beam_mutation_specs",
        lambda *_args, **_kwargs: tuple(("replace", index, index) for index in range(10)),
    )

    def consume_all(_data, _before, _specs, *, consume, **_kwargs):
        consume(tuple(fake_candidates))

    monkeypatch.setattr(idat_bruteforce, "_deep_beam_consume_validated_specs", consume_all)

    successors, tested, _backend, _warning = idat_bruteforce._deep_beam_byte_bit_successors(
        parent,
        before=before,
        state_id_start=1,
        original_idat_count=original_idat_count,
        max_offsets=128,
        max_bits=192,
        widened_limit=0x120,
        budget_left=10,
        workers=1,
        successor_limit=3,
    )

    assert tested == 10
    assert len(successors) == 3


def test_idat_periodic_model_refuses_hash_mismatch(tmp_path):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    model = tmp_path / "model.json"
    model.write_text(
        json.dumps(
            {
                "version": 1,
                "convoy_stream_hash": "not-this-stream",
                "xors": [1],
                "deltas": [1],
            }
        )
    )

    result = idat_bruteforce.probe_idat_periodic_corruption_model(
        candidate,
        convoy_model_path=str(model),
        budget=100,
    )

    assert result.best is None
    assert result.tested_candidates == 0
    assert "does not match" in result.reason


def test_idat_huffman_oracle_progress_same_budget_skips(tmp_path):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    progress = tmp_path / "huffman.progress.json"
    checkpoint = tmp_path / "huffman.checkpoint.jsonl"
    progress.write_text(
        json.dumps(
            {
                "version": 1,
                "source_hash": idat_bruteforce._stream_state_key(stream),
                "strategy": "dynamic-huffman-png-oracle",
                "tested_candidates": 123,
                "budget": 750000,
                "exhausted": True,
            }
        )
    )

    result = idat_bruteforce.probe_idat_dynamic_huffman_png_oracle_solver(
        candidate,
        budget=750000,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
    )

    assert result.tested_candidates == 123
    assert result.budget_exhausted is True
    assert "already exhausted" in result.reason


def test_idat_huffman_oracle_accepts_frontier_seeds_without_restarting_from_root():
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    before = idat.analyze_idat_stream(candidate)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    seed_stream = bytes((stream[0] ^ 1,)) + stream[1:]
    seed_data = idat_bruteforce._rebuild_with_single_idat_stream(chunks, seed_stream)
    seed_analysis = idat.analyze_idat_stream(seed_data)
    seed = idat_bruteforce.IdatDeepBeamCandidate(
        data=seed_data,
        stream=seed_stream,
        operations=(
            idat_bruteforce.IdatDeepBeamOperation(
                "test-seed",
                0,
                stream[:1],
                seed_stream[:1],
            ),
        ),
        before=before,
        after=seed_analysis,
        state_id=99,
        parent_id=0,
        source_offsets=(0,),
        score=idat_bruteforce._deep_beam_score(
            seed_analysis,
            seed_stream,
            1,
            data=seed_data,
            original_idat_count=original_idat_count,
        ),
    )

    result = idat_bruteforce.probe_idat_dynamic_huffman_png_oracle_solver(
        candidate,
        budget=0,
        seed_candidates=(seed,),
    )

    assert result.seed_count == 1
    assert result.top_candidates == (seed,)
    assert "seeds=1" in idat_bruteforce.huffman_oracle_summary_line(result)


def test_idat_huffman_kraft_progress_same_budget_skips(tmp_path):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    progress = tmp_path / "kraft.progress.json"
    checkpoint = tmp_path / "kraft.checkpoint.jsonl"
    progress.write_text(
        json.dumps(
            {
                "version": 1,
                "source_hash": idat_bruteforce._stream_state_key(stream),
                "strategy": "huffman-kraft",
                "tested_candidates": 321,
                "budget": idat_bruteforce.HUFFMAN_KRAFT_DEFAULT_BUDGET,
                "exhausted": True,
            }
        )
    )

    result = idat_bruteforce.probe_idat_huffman_kraft_solver(
        candidate,
        budget=idat_bruteforce.HUFFMAN_KRAFT_DEFAULT_BUDGET,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
    )

    assert result.tested_candidates == 321
    assert result.budget_exhausted is True
    assert "already exhausted" in result.reason


def test_idat_huffman_kraft_memory_guard_resume_degrades_workers_and_gpu(tmp_path):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    before = idat.analyze_idat_stream(candidate)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    seed_stream = bytes((stream[0] ^ 1,)) + stream[1:]
    seed_data = idat_bruteforce._rebuild_with_single_idat_stream(chunks, seed_stream)
    seed = idat_bruteforce.IdatDeepBeamCandidate(
        data=seed_data,
        stream=seed_stream,
        operations=(
            idat_bruteforce.IdatDeepBeamOperation(
                "test-seed",
                0,
                stream[:1],
                seed_stream[:1],
            ),
        ),
        before=before,
        after=idat.analyze_idat_stream(seed_data),
        state_id=42,
        parent_id=0,
        source_offsets=(0,),
        score=(1,),
    )
    progress = tmp_path / "kraft.progress.json"
    checkpoint = tmp_path / "kraft.checkpoint.jsonl"
    progress.write_text(
        json.dumps(
            {
                "version": 1,
                "source_hash": idat_bruteforce._stream_state_key(stream),
                "strategy": "huffman-kraft",
                "tested_candidates": 100,
                "budget": 1000,
                "exhausted": False,
                "reason": "stop=memory_guard; depth=2",
            }
        )
    )

    result = idat_bruteforce.probe_idat_huffman_kraft_solver(
        candidate,
        budget=0,
        workers=12,
        gpu=True,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
        seed_candidates=(seed,),
    )

    assert result.workers <= idat_bruteforce.HUFFMAN_KRAFT_THROTTLE_WORKER_LIMIT
    assert result.gpu_status == "off"
    assert result.memory_mode == "resume-degraded"
    assert result.top_candidates
    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["memory_mode"] == "resume-degraded"
    assert payload["effective_batch_size"] == idat_bruteforce.HUFFMAN_KRAFT_HARD_THROTTLE_BATCH_SIZE


def test_idat_huffman_kraft_token_checkpoint_replays_without_full_stream(tmp_path):
    candidate, _bits, _original = dynamic_header_semantic_token_corrupt_png()
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    before = idat.analyze_idat_stream(candidate)
    root = idat_bruteforce._frontier_root_candidate(
        data=candidate,
        stream=stream,
        before=before,
        original_idat_count=1,
    )
    trace = deflate_header.trace_dynamic_header(stream)
    operation = next(
        op
        for op in idat_bruteforce._huffman_kraft_token_operations(stream, trace, max_tokens=8)
        if idat_bruteforce._huffman_kraft_candidate_from_operation(
            root,
            op,
            chunks=chunks,
            before=before,
            state_id=1,
            original_idat_count=1,
        )
        is not None
    )
    kraft_candidate = idat_bruteforce._huffman_kraft_candidate_from_operation(
        root,
        operation,
        chunks=chunks,
        before=before,
        state_id=1,
        original_idat_count=1,
    )
    assert kraft_candidate is not None

    checkpoint = tmp_path / "kraft.checkpoint.jsonl"
    source_hash = idat_bruteforce._stream_state_key(stream)
    idat_bruteforce._append_frontier_checkpoint(
        str(checkpoint),
        kraft_candidate,
        source_hash=source_hash,
        source_stream=stream,
    )

    record = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert "stream" not in record
    replayed, _operations = idat_bruteforce._deep_beam_stream_from_record(
        record,
        source_stream=stream,
    )
    assert replayed == kraft_candidate.stream


def test_idat_huffman_kraft_resume_without_progress_infers_checkpoint_budget(tmp_path, monkeypatch):
    candidate, _bits, _original = dynamic_header_semantic_token_corrupt_png()
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    before = idat.analyze_idat_stream(candidate)
    root = idat_bruteforce._frontier_root_candidate(
        data=candidate,
        stream=stream,
        before=before,
        original_idat_count=1,
    )
    trace = deflate_header.trace_dynamic_header(stream)
    operation = next(
        op
        for op in idat_bruteforce._huffman_kraft_token_operations(stream, trace, max_tokens=8)
        if idat_bruteforce._huffman_kraft_candidate_from_operation(
            root,
            op,
            chunks=chunks,
            before=before,
            state_id=1,
            original_idat_count=1,
        )
        is not None
    )
    kraft_candidate = idat_bruteforce._huffman_kraft_candidate_from_operation(
        root,
        operation,
        chunks=chunks,
        before=before,
        state_id=1,
        original_idat_count=1,
    )
    assert kraft_candidate is not None

    checkpoint = tmp_path / "kraft.checkpoint.jsonl"
    progress = tmp_path / "kraft.progress.json"
    source_hash = idat_bruteforce._stream_state_key(stream)
    idat_bruteforce._append_frontier_checkpoint(
        str(checkpoint),
        kraft_candidate,
        source_hash=source_hash,
        source_stream=stream,
    )
    monkeypatch.setattr(idat_bruteforce, "HUFFMAN_KRAFT_CHECKPOINT_EVERY", 25)

    result = idat_bruteforce.probe_idat_huffman_kraft_solver(
        candidate,
        budget=30,
        max_depth=1,
        beam_width=4,
        top_candidates=1,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
    )

    assert result.tested_candidates >= 25
    assert progress.exists()
    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["tested_candidates"] >= 25
    assert payload["source_hash"] == source_hash


def test_idat_huffman_kraft_flushes_progress_on_exception(tmp_path, monkeypatch):
    candidate, _bits, _original = dynamic_header_semantic_token_corrupt_png()
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    checkpoint = tmp_path / "kraft.checkpoint.jsonl"
    progress = tmp_path / "kraft.progress.json"
    source_hash = idat_bruteforce._stream_state_key(stream)
    checkpoint.write_text("", encoding="utf-8")
    progress.write_text(
        json.dumps(
            {
                "version": 1,
                "source_hash": source_hash,
                "strategy": "huffman-kraft",
                "tested_candidates": 123,
                "budget": 200,
                "exhausted": False,
            }
        ),
        encoding="utf-8",
    )

    def boom(*_args, **_kwargs):
        raise RuntimeError("kraft boom")

    monkeypatch.setattr(idat_bruteforce, "_huffman_kraft_validate_operations", boom)

    try:
        idat_bruteforce.probe_idat_huffman_kraft_solver(
            candidate,
            budget=200,
            max_depth=1,
            beam_width=4,
            top_candidates=2,
            checkpoint_path=str(checkpoint),
            progress_path=str(progress),
        )
    except RuntimeError as exc:
        assert "kraft boom" in str(exc)
    else:
        raise AssertionError("expected kraft solver exception")

    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["tested_candidates"] == 123
    assert payload["exhausted"] is False
    assert payload["reason"] == "huffman kraft aborted: RuntimeError: kraft boom"
    assert payload["source_hash"] == source_hash


def test_idat_huffman_kraft_creates_worker_pool_per_run(monkeypatch):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    created = []
    shutdowns = []

    class FakeExecutor:
        def __init__(self, **kwargs):
            created.append(kwargs)

        def shutdown(self, **kwargs):
            shutdowns.append(kwargs)

    monkeypatch.setattr(idat_bruteforce, "ProcessPoolExecutor", FakeExecutor)

    result = idat_bruteforce.probe_idat_huffman_kraft_solver(
        candidate,
        budget=10,
        max_depth=1,
        beam_width=2,
        top_candidates=2,
        workers=4,
    )

    assert result.workers == 4
    assert created == [
        {
            "max_workers": 4,
            "initializer": idat_bruteforce._deep_beam_worker_init,
        }
    ]
    assert shutdowns == [{"cancel_futures": True}]


def test_idat_huffman_kraft_workers_keep_deterministic_top_candidates():
    candidate, _bits, _original = dynamic_header_semantic_token_corrupt_png()

    single = idat_bruteforce.probe_idat_huffman_kraft_solver(
        candidate,
        budget=200,
        max_depth=1,
        beam_width=8,
        top_candidates=4,
        workers=1,
    )
    parallel = idat_bruteforce.probe_idat_huffman_kraft_solver(
        candidate,
        budget=200,
        max_depth=1,
        beam_width=8,
        top_candidates=4,
        workers=4,
    )

    single_hashes = [idat_bruteforce._stream_state_key(candidate.stream) for candidate in single.top_candidates]
    parallel_hashes = [idat_bruteforce._stream_state_key(candidate.stream) for candidate in parallel.top_candidates]
    assert parallel.workers == 4
    assert parallel_hashes == single_hashes


def test_idat_huffman_kraft_gpu_prefilter_reports_active(monkeypatch):
    candidate, _bits, _original = dynamic_header_semantic_token_corrupt_png()

    class FakeSession:
        def __init__(self, config):
            self.config = config

        def run(self, plan):
            return idat_kraft_opengl_backend.KraftOpenGLResult(
                hit_indices=tuple(range(plan.operation_count)),
                tested=plan.operation_count,
                shards=1,
                status="opengl-active",
                reason="fake active",
            )

        def close(self):
            pass

    monkeypatch.setattr(idat_kraft_opengl_backend, "KraftOpenGLSession", FakeSession)

    result = idat_bruteforce.probe_idat_huffman_kraft_solver(
        candidate,
        budget=100,
        max_depth=1,
        beam_width=4,
        top_candidates=3,
        workers=1,
        gpu=True,
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
    )

    assert result.gpu_status == "opengl-active"
    assert result.gpu_shards >= 1
    assert result.gpu_hits >= 1


def test_idat_huffman_kraft_gpu_prefilter_caps_hits(monkeypatch):
    candidate, _bits, _original = dynamic_header_semantic_token_corrupt_png()
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    trace = deflate_header.trace_dynamic_header(stream)
    operations = idat_bruteforce._huffman_kraft_token_operations(stream, trace, max_tokens=96)
    compact = tuple(
        item
        for item in (
            idat_bruteforce._huffman_kraft_compact_operation(index + 1, operation)
            for index, operation in enumerate(operations)
        )
        if item is not None
    )
    assert len(compact) > idat_bruteforce.HUFFMAN_KRAFT_GPU_HIT_LIMIT

    class FakeSession:
        def run(self, plan):
            return idat_kraft_opengl_backend.KraftOpenGLResult(
                hit_indices=tuple(range(plan.operation_count)),
                tested=plan.operation_count,
                shards=1,
                status="opengl-active",
                reason="fake active",
            )

    filtered, _shards, hits, status = idat_bruteforce._huffman_kraft_gpu_prefilter_compact_operations(
        stream,
        compact,
        gpu_session=FakeSession(),
    )

    assert status == "opengl-active"
    assert hits == idat_bruteforce.HUFFMAN_KRAFT_GPU_HIT_LIMIT
    assert len(filtered) == idat_bruteforce.HUFFMAN_KRAFT_GPU_HIT_LIMIT


def test_idat_huffman_kraft_memory_guard_keeps_progress_resumable(tmp_path, monkeypatch):
    candidate, _bits, _original = dynamic_header_semantic_token_corrupt_png()
    progress = tmp_path / "kraft.progress.json"

    monkeypatch.setattr(idat_bruteforce, "_deep_beam_memory_guard_tripped", lambda: True)

    result = idat_bruteforce.probe_idat_huffman_kraft_solver(
        candidate,
        budget=100,
        max_depth=1,
        beam_width=4,
        top_candidates=2,
        progress_path=str(progress),
        workers=1,
    )

    assert "memory_mode=hard" in result.reason
    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["memory_mode"] == "hard"
    assert payload["memory_throttle_events"] >= 1
    assert payload["resumable"] is True


def test_idat_first_filter_literal_solver_repairs_first_symbol(tmp_path):
    candidate, _original_stream = first_symbol_length_token_corrupt_png()
    checkpoint = tmp_path / "first_filter.checkpoint.jsonl"
    progress = tmp_path / "first_filter.progress.json"

    result = idat_bruteforce.probe_idat_first_filter_literal_solver(
        candidate,
        budget=10,
        top_candidates=5,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
    )

    assert result.first_filter_hits >= 1
    assert result.png_plausible >= 1
    assert result.top_candidates
    top = result.top_candidates[0]
    oracle = idat_bruteforce.raw_png_oracle_decision(top.stream, top.after, max_output=16)
    assert oracle.first_filter_ok is True
    assert top.operations[-1].kind == "first-filter-literal"
    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["strategy"] == "first-filter-literal"
    assert payload["first_filter_hits"] >= 1
    assert checkpoint.exists()


def test_idat_first_filter_literal_empty_progress_does_not_block_new_seeds(tmp_path):
    candidate, _original_stream = first_symbol_length_token_corrupt_png()
    before = idat.analyze_idat_stream(candidate)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    checkpoint = tmp_path / "first_filter.checkpoint.jsonl"
    progress = tmp_path / "first_filter.progress.json"
    progress.write_text(
        json.dumps(
            {
                "version": 1,
                "source_hash": idat_bruteforce._stream_state_key(stream),
                "strategy": "first-filter-literal",
                "tested_candidates": 5,
                "budget": 10,
                "exhausted": True,
                "top_count": 0,
            }
        ),
        encoding="utf-8",
    )
    seed = idat_bruteforce._frontier_root_candidate(
        data=candidate,
        stream=stream,
        before=before,
        original_idat_count=sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT"),
    )

    result = idat_bruteforce.probe_idat_first_filter_literal_solver(
        candidate,
        budget=10,
        top_candidates=5,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
        seed_candidates=(seed,),
    )

    assert result.first_filter_hits >= 1
    assert result.top_candidates
    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["first_filter_hits"] >= 1
    assert payload["top_count"] >= 1


def test_idat_first_filter_literal_allows_variable_width_rewrite(monkeypatch):
    clean = build_rgb_png(1, 1, b"\x00abc")
    before = idat.analyze_idat_stream(clean)
    parent = idat_bruteforce.IdatDeepBeamCandidate(
        data=b"",
        stream=b"\xff\xff",
        operations=(),
        before=before,
        after=before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=(),
    )

    monkeypatch.setattr(
        idat_bruteforce,
        "_dynamic_first_literal_symbol",
        lambda _stream: (111, 0, 5, {(0, 3): 0}, 3),
    )

    def candidate_from_stream(parent, stream, operation, **kwargs):
        return idat_bruteforce.IdatDeepBeamCandidate(
            data=b"",
            stream=stream,
            operations=parent.operations + (operation,),
            before=before,
            after=before,
            state_id=kwargs["state_id"],
            parent_id=parent.state_id,
            source_offsets=parent.source_offsets + (operation.stream_offset,),
            score=(1,),
        )

    monkeypatch.setattr(idat_bruteforce, "_frontier_candidate_from_stream", candidate_from_stream)
    monkeypatch.setattr(
        idat_bruteforce,
        "raw_png_oracle_decision",
        lambda *_args, **_kwargs: SimpleNamespace(first_filter_ok=True),
    )

    candidate = idat_bruteforce._first_filter_literal_candidate(
        parent,
        0,
        chunks=(),
        before=before,
        state_id=1,
        original_idat_count=1,
    )

    assert candidate is not None
    assert candidate.stream != parent.stream
    assert candidate.operations[-1].kind == "first-filter-literal"
    assert len(candidate.operations[-1].bit_offsets) == 5
    assert candidate.operations[-1].new_bytes == b"\x00\x00\x00"


def test_idat_first_filter_literal_uses_kraft_closure_parent(tmp_path, monkeypatch):
    corrupt, _original_stream = first_symbol_length_token_corrupt_png()
    before = idat.analyze_idat_stream(corrupt)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    root = idat_bruteforce._frontier_root_candidate(
        data=corrupt,
        stream=stream,
        before=before,
        original_idat_count=sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT"),
    )
    closure_operation = idat_bruteforce.IdatDeepBeamOperation(
        "huffman-kraft-closure-distance",
        1,
        b"\x00",
        b"\x01",
        (8,),
    )
    closure_parent = idat_bruteforce.IdatDeepBeamCandidate(
        data=root.data,
        stream=stream + b"\x00",
        operations=(closure_operation,),
        before=before,
        after=before,
        state_id=1,
        parent_id=root.state_id,
        source_offsets=(1,),
        score=(1,),
    )
    final_operation = idat_bruteforce.IdatDeepBeamOperation(
        "first-filter-literal",
        2,
        b"\x00",
        b"\x00",
        (16,),
    )
    final_candidate = idat_bruteforce.IdatDeepBeamCandidate(
        data=root.data,
        stream=stream + b"\x01",
        operations=(closure_operation, final_operation),
        before=before,
        after=before,
        state_id=2,
        parent_id=closure_parent.state_id,
        source_offsets=(1, 2),
        score=(2,),
    )

    monkeypatch.setattr(
        idat_bruteforce,
        "_huffman_kraft_closure_operations",
        lambda *_args, **_kwargs: (closure_operation,),
    )
    monkeypatch.setattr(
        idat_bruteforce,
        "_huffman_kraft_candidate_from_operation",
        lambda *_args, **_kwargs: closure_parent,
    )
    monkeypatch.setattr(
        idat_bruteforce.deflate_header,
        "trace_dynamic_header",
        lambda _stream: SimpleNamespace(
            status="ok",
            btype=2,
            tokens=(),
            length_count=316,
            header_end_bit=64,
            literal_lengths=(1, 1),
            distance_lengths=(1, 1),
            literal_error="",
            distance_error="",
        ),
    )

    def first_filter_candidate(parent, *_args, **_kwargs):
        if parent.stream == closure_parent.stream:
            return final_candidate
        return None

    monkeypatch.setattr(idat_bruteforce, "_first_filter_literal_candidate", first_filter_candidate)
    monkeypatch.setattr(
        idat_bruteforce,
        "raw_png_oracle_decision",
        lambda *_args, **_kwargs: SimpleNamespace(first_filter_ok=True),
    )

    result = idat_bruteforce.probe_idat_first_filter_literal_solver(
        corrupt,
        budget=10,
        checkpoint_path=str(tmp_path / "first_filter.checkpoint.jsonl"),
        progress_path=str(tmp_path / "first_filter.progress.json"),
        seed_candidates=(root,),
    )

    assert result.closure_hits == 1
    assert result.first_filter_hits == 1
    assert result.top_candidates == (final_candidate,)


def test_idat_kraft_backref_repair_uses_kraft_seed_and_writes_progress(tmp_path, monkeypatch):
    corrupt, _bits, _original = dynamic_header_semantic_token_corrupt_png()
    before = idat.analyze_idat_stream(corrupt)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    root = idat_bruteforce._frontier_root_candidate(
        data=corrupt,
        stream=stream,
        before=before,
        original_idat_count=1,
    )
    repaired_raw = dynamic_filtered_rows(4)
    repaired_data = build_rgb_png(1, 4, repaired_raw)
    _repaired_chunks, repaired_stream = idat_bruteforce._all_chunks_and_idat_stream(repaired_data)
    repaired_after = idat.analyze_idat_stream(repaired_data)
    operation = idat_bruteforce.IdatDeepBeamOperation(
        "kraft-backref-distance",
        7,
        b"\x00",
        b"\x01",
        (56, 57),
    )
    repaired_candidate = idat_bruteforce.IdatDeepBeamCandidate(
        data=repaired_data,
        stream=repaired_stream,
        operations=(operation,),
        before=before,
        after=repaired_after,
        state_id=1,
        parent_id=root.state_id,
        score=(repaired_after.usable_scanlines, 1),
    )
    invalid = idat_bruteforce._InvalidDistanceBackref(
        token_index=3,
        bit_start=56,
        bit_end=58,
        output_before=4,
        length=3,
        distance_symbol=4,
        distance=9,
        distance_table={},
    )

    monkeypatch.setattr(idat_bruteforce, "_locate_first_invalid_distance_backref", lambda *_args, **_kwargs: invalid)
    monkeypatch.setattr(idat_bruteforce, "_kraft_backref_distance_operations", lambda *_args, **_kwargs: (operation,))
    monkeypatch.setattr(idat_bruteforce, "_kraft_backref_candidate_from_operation", lambda *_args, **_kwargs: repaired_candidate)

    checkpoint = tmp_path / "kraft_backref.checkpoint.jsonl"
    progress = tmp_path / "kraft_backref.progress.json"
    result = idat_bruteforce.probe_idat_kraft_backref_repair(
        corrupt,
        budget=10,
        max_depth=1,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
        seed_candidates=(root,),
    )

    assert result.best == repaired_candidate
    assert result.top_candidates == (repaired_candidate,)
    assert result.tested_candidates == 1
    assert result.repaired_backrefs == 1
    assert checkpoint.exists()
    progress_payload = json.loads(progress.read_text(encoding="utf-8"))
    assert progress_payload["strategy"] == "kraft-backref-repair"
    assert progress_payload["tested_candidates"] == 1
    assert progress_payload["source_hash"] == idat_bruteforce._stream_state_key(stream)


def test_idat_kraft_backref_repair_can_rewrite_early_length_token_to_literal(tmp_path):
    corrupt, _original_stream = early_backref_length_token_corrupt_png()
    before = idat.analyze_idat_stream(corrupt)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    seed = idat_bruteforce._frontier_root_candidate(
        data=corrupt,
        stream=stream,
        before=before,
        original_idat_count=sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT"),
    )
    invalid = idat_bruteforce._locate_first_invalid_distance_backref(stream)
    assert invalid is not None
    literal_ops = idat_bruteforce._kraft_backref_literal_operations(stream, invalid, max_operations=64)
    assert literal_ops
    assert all(operation.kind == "kraft-backref-literal" for operation in literal_ops)

    checkpoint = tmp_path / "kraft_backref.checkpoint.jsonl"
    progress = tmp_path / "kraft_backref.progress.json"
    result = idat_bruteforce.probe_idat_kraft_backref_repair(
        corrupt,
        budget=128,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
        seed_candidates=(seed,),
    )

    assert result.top_candidates
    assert result.png_prefix_hits >= 1
    assert result.top_candidates[0].operations[-1].kind == "kraft-backref-literal"
    repaired_raw = idat_bruteforce.idat_partial_raw_prefix(result.top_candidates[0].stream, max_output=32).raw
    assert len(repaired_raw) > 1
    assert repaired_raw[0] in (0, 1, 2, 3, 4)


def test_idat_kraft_backref_repair_chains_literal_repairs_by_depth(tmp_path):
    corrupt, _original_stream = early_backref_length_token_corrupt_png(count=2)
    before = idat.analyze_idat_stream(corrupt)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    seed = idat_bruteforce._frontier_root_candidate(
        data=corrupt,
        stream=stream,
        before=before,
        original_idat_count=sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT"),
    )

    shallow = idat_bruteforce.probe_idat_kraft_backref_repair(
        corrupt,
        budget=256,
        max_depth=1,
        top_candidates=8,
        seed_candidates=(seed,),
    )
    deep = idat_bruteforce.probe_idat_kraft_backref_repair(
        corrupt,
        budget=512,
        max_depth=2,
        top_candidates=8,
        seed_candidates=(seed,),
    )

    assert shallow.top_candidates
    assert deep.top_candidates
    shallow_raw = idat_bruteforce.idat_partial_raw_prefix(shallow.top_candidates[0].stream, max_output=64).raw
    deep_raw = idat_bruteforce.idat_partial_raw_prefix(deep.top_candidates[0].stream, max_output=64).raw
    assert deep.reached_depth >= 2
    assert len(deep_raw) > len(shallow_raw)
    assert deep.top_candidates[0].operations[-1].kind == "kraft-backref-literal"


def test_idat_kraft_backref_without_seeds_does_not_mark_exhausted(tmp_path):
    corrupt, _bits, _original = dynamic_header_semantic_token_corrupt_png()
    progress = tmp_path / "kraft_backref.progress.json"

    result = idat_bruteforce.probe_idat_kraft_backref_repair(
        corrupt,
        budget=10,
        progress_path=str(progress),
    )

    assert result.best is None
    assert result.tested_candidates == 0
    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["strategy"] == "kraft-backref-repair"
    assert payload["exhausted"] is False
    assert payload["reason"] == "no Kraft seed candidates available"


def test_idat_material_improvement_accepts_more_bytes_after_usable_scanline():
    before = idat.IdatStreamAnalysis(
        True,
        False,
        "bad_adler",
        height=850,
        decompressed_size=4925,
        usable_scanlines=1,
    )
    after = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=850,
        decompressed_size=5203,
        usable_scanlines=1,
    )
    already_full_scanlines_before = idat.IdatStreamAnalysis(
        True,
        False,
        "bad_adler",
        height=2,
        decompressed_size=8,
        usable_scanlines=2,
    )
    already_full_scanlines_after = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=2,
        decompressed_size=40,
        usable_scanlines=2,
    )
    zero_scanline_before = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        decompressed_size=3646,
        usable_scanlines=0,
    )
    zero_scanline_after = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        decompressed_size=4165,
        usable_scanlines=0,
    )

    assert idat_bruteforce.is_material_improvement(before, after)
    assert not idat_bruteforce.is_material_improvement(
        already_full_scanlines_before,
        already_full_scanlines_after,
    )
    assert not idat_bruteforce.is_material_improvement(zero_scanline_before, zero_scanline_after)


def test_idat_single_pass_prefers_bit_probe_after_usable_scanline(monkeypatch):
    calls = []
    before = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        decompressed_size=4925,
        usable_scanlines=1,
        error_offset=1011,
    )
    bit_result = idat_bruteforce.IdatDeflateProbeResult(
        before,
        object(),
        0,
        1,
        1,
        False,
        "post-scanline-bit",
    )

    def analyze(_data):
        calls.append(("analyze",))
        return before

    def bit_probe(_data, **kwargs):
        calls.append(("bit", kwargs.get("strategy")))
        return bit_result

    def byte_probe(*_args, **_kwargs):
        raise AssertionError("byte probes should not run when post-scanline bit probe improves")

    monkeypatch.setattr(idat_bruteforce.idat, "analyze_idat_stream", analyze)
    monkeypatch.setattr(idat_bruteforce, "probe_idat_deflate_bit_candidates", bit_probe)
    monkeypatch.setattr(idat_bruteforce, "probe_idat_deflate_byte_candidates", byte_probe)

    result = idat_bruteforce.probe_idat_deflate_single_pass(b"unused")

    assert result is bit_result
    assert calls == [("analyze",), ("bit", "post-scanline-bit")]


def test_idat_stored_block_length_repair_fixes_len_nlen_pair(tmp_path):
    raw = b"\x00\x00\x00\x00\xff"
    stream = (
        b"\x78\x01"
        + b"\x01"
        + (len(raw)).to_bytes(2, "little")
        + (0).to_bytes(2, "little")
        + raw
        + zlib.adler32(raw).to_bytes(4, "big")
    )
    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    corrupt = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", stream)
        + IEND_CHUNK
    )
    before = idat.analyze_idat_stream(corrupt)
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    seed = idat_bruteforce._frontier_root_candidate(
        data=corrupt,
        stream=root_stream,
        before=before,
        original_idat_count=sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT"),
    )
    checkpoint = tmp_path / "stored_block.checkpoint.jsonl"
    progress = tmp_path / "stored_block.progress.json"

    result = idat_bruteforce.probe_idat_stored_block_length_repair(
        corrupt,
        budget=256,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
        seed_candidates=(seed,),
    )

    assert result.best is not None
    assert result.best.after.complete
    assert result.best.after.usable_scanlines == 1
    assert result.best.operations[-1].kind == "stored-block-len-nlen"
    assert result.best.operations[-1].new_bytes == b"\x05\x00\xfa\xff"
    assert result.repaired_blocks >= 1
    assert result.png_prefix_hits >= 1
    assert checkpoint.exists()
    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["strategy"] == "stored-block-length-repair"
    assert payload["route_version"] == idat_bruteforce.STORED_BLOCK_ROUTE_VERSION
    assert payload["source_hash"] == idat_bruteforce._stream_state_key(root_stream)


def test_idat_kraft_backref_locator_continues_after_stored_block():
    literal_table, _literal_max, distance_table, _distance_max = deflate_probe._FIXED_TABLES

    def symbol_bits(symbol, table):
        code, width = idat_bruteforce._huffman_symbol_codes(table)[symbol]
        return tuple((code >> index) & 1 for index in range(width))

    raw = b"abcdefghij"
    stored_header_bits = [0, 0, 0]
    while len(stored_header_bits) % 8:
        stored_header_bits.append(0)
    stored_header = bytes(
        sum(bit << index for index, bit in enumerate(stored_header_bits[offset : offset + 8]))
        for offset in range(0, len(stored_header_bits), 8)
    )
    fixed_bits = [1, 1, 0]
    fixed_bits.extend(symbol_bits(257, literal_table))
    fixed_bits.extend(symbol_bits(31, distance_table))
    while len(fixed_bits) % 8:
        fixed_bits.append(0)
    fixed_block = bytes(
        sum(bit << index for index, bit in enumerate(fixed_bits[offset : offset + 8]))
        for offset in range(0, len(fixed_bits), 8)
    )
    stream = (
        b"\x78\x01"
        + stored_header
        + len(raw).to_bytes(2, "little")
        + (len(raw) ^ 0xFFFF).to_bytes(2, "little")
        + raw
        + fixed_block
    )

    invalid = idat_bruteforce._locate_first_invalid_distance_backref(stream, max_tokens=100)

    assert invalid is not None
    assert invalid.output_before == len(raw)
    assert invalid.length == 3
    assert invalid.distance_symbol == 31
    assert invalid.bit_start > 8 * (2 + 5 + len(raw))
    assert idat_bruteforce._kraft_backref_distance_operations(stream, invalid, max_operations=4)


def test_idat_kraft_locator_finds_invalid_literal_after_stored_block():
    literal_table, _literal_max, _distance_table, _distance_max = deflate_probe._FIXED_TABLES

    def symbol_bits(symbol, table):
        code, width = idat_bruteforce._huffman_symbol_codes(table)[symbol]
        return tuple((code >> index) & 1 for index in range(width))

    raw = b"abcdefghij"
    stored_header = b"\x00"
    fixed_bits = [1, 1, 0]
    fixed_bits.extend(symbol_bits(287, literal_table))
    while len(fixed_bits) % 8:
        fixed_bits.append(0)
    fixed_block = bytes(
        sum(bit << index for index, bit in enumerate(fixed_bits[offset : offset + 8]))
        for offset in range(0, len(fixed_bits), 8)
    )
    stream = (
        b"\x78\x01"
        + stored_header
        + len(raw).to_bytes(2, "little")
        + (len(raw) ^ 0xFFFF).to_bytes(2, "little")
        + raw
        + fixed_block
    )

    invalid = idat_bruteforce._locate_first_invalid_literal_length_symbol(stream, max_tokens=100)

    assert invalid is not None
    assert invalid.output_before == len(raw)
    assert invalid.symbol == 287
    operations = idat_bruteforce._kraft_invalid_literal_symbol_operations(stream, invalid, max_operations=4)
    assert operations
    assert operations[0].kind == "kraft-invalid-literal"


def test_idat_kraft_locator_finds_reserved_block_type_after_stored_block():
    raw = b"abcdefghij"
    stream = (
        b"\x78\x01"
        + b"\x00"
        + len(raw).to_bytes(2, "little")
        + (len(raw) ^ 0xFFFF).to_bytes(2, "little")
        + raw
        + b"\x07"
    )

    reserved = idat_bruteforce._locate_reserved_deflate_block_type(stream)

    assert reserved is not None
    assert reserved.output_before == len(raw)
    operations = idat_bruteforce._kraft_reserved_block_type_operations(stream, reserved, max_operations=6)
    assert len(operations) == 6
    assert operations[0].kind == "kraft-block-header-btype"


def test_idat_kraft_backref_caps_operations_per_seed(monkeypatch):
    corrupt, _bits, _original = dynamic_header_semantic_token_corrupt_png()
    before = idat.analyze_idat_stream(corrupt)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    seed = idat_bruteforce._frontier_root_candidate(
        data=corrupt,
        stream=stream,
        before=before,
        original_idat_count=sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT"),
    )
    calls = []

    monkeypatch.setattr(
        idat_bruteforce,
        "_locate_first_invalid_distance_backref",
        lambda *_args, **_kwargs: object(),
    )

    def literal_ops(_stream, _invalid, *, max_operations):
        calls.append(("literal", max_operations))
        return ()

    def distance_ops(_stream, _invalid, *, max_operations):
        calls.append(("distance", max_operations))
        return ()

    monkeypatch.setattr(idat_bruteforce, "_kraft_backref_literal_operations", literal_ops)
    monkeypatch.setattr(idat_bruteforce, "_kraft_backref_distance_operations", distance_ops)

    result = idat_bruteforce.probe_idat_kraft_backref_repair(
        corrupt,
        budget=idat_bruteforce.KRAFT_BACKREF_MAX_OPERATIONS_PER_SEED + 1000,
        seed_candidates=(seed,),
    )

    assert calls == [
        ("literal", idat_bruteforce.KRAFT_BACKREF_MAX_OPERATIONS_PER_SEED),
        ("distance", idat_bruteforce.KRAFT_BACKREF_MAX_OPERATIONS_PER_SEED),
    ]
    assert result.tested_candidates == 0
    assert "per_seed_limit=%s" % idat_bruteforce.KRAFT_BACKREF_MAX_OPERATIONS_PER_SEED in result.reason


def test_idat_affine_corruption_refuses_hash_mismatch(tmp_path):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    model = tmp_path / "model.json"
    model.write_text(
        json.dumps(
            {
                "version": 1,
                "convoy_stream_hash": "not-this-stream",
                "xors": [1],
                "deltas": [1],
                "byte_repairs": [],
            }
        )
    )

    result = idat_bruteforce.probe_idat_affine_corruption_model(
        candidate,
        convoy_model_path=str(model),
        budget=100,
    )

    assert result.best is None
    assert result.tested_candidates == 0
    assert "does not match" in result.reason


def _write_matching_affine_model(path, data: bytes):
    _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "convoy_stream_hash": idat_bruteforce._stream_state_key(stream),
                "xors": [1],
                "deltas": [],
                "byte_repairs": [],
            }
        ),
        encoding="utf-8",
    )


def test_idat_affine_corruption_uses_worker_pool(tmp_path, monkeypatch):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    model = tmp_path / "model.json"
    _write_matching_affine_model(model, candidate)
    created = []
    shutdowns = []

    class FakeExecutor:
        def __init__(self, **kwargs):
            created.append(kwargs)

        def shutdown(self, **kwargs):
            shutdowns.append(kwargs)

    monkeypatch.setattr(idat_bruteforce, "ProcessPoolExecutor", FakeExecutor)

    result = idat_bruteforce.probe_idat_affine_corruption_model(
        candidate,
        convoy_model_path=str(model),
        budget=8,
        workers=4,
    )

    assert result.workers == 4
    assert result.cpu_batches >= 1
    assert created == [
        {
            "max_workers": 4,
            "initializer": idat_bruteforce._deep_beam_worker_init,
        }
    ]
    assert shutdowns == [{"cancel_futures": True}]


def test_idat_affine_corruption_gpu_prefilter_can_cover_specs(tmp_path, monkeypatch):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    model = tmp_path / "model.json"
    _write_matching_affine_model(model, candidate)

    def fake_gpu(
        parent,
        *,
        before,
        state_id_start,
        original_idat_count,
        depth,
        specs,
        budget_left,
        checkpoint_every,
        gpu_config,
        gpu_done_shards,
        workers,
        worker_executor=None,
        cpu_batch_size=idat_bruteforce.DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE,
        gpu_shard_size=idat_bruteforce.DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE,
        gpu_session=None,
        timing=None,
        compatible=None,
    ):
        assert state_id_start >= 1
        return [], len(specs), True, "opengl-active", "", set(range(len(specs)))

    monkeypatch.setattr(idat_bruteforce, "_deep_beam_gpu_byte_successors", fake_gpu)

    result = idat_bruteforce.probe_idat_affine_corruption_model(
        candidate,
        convoy_model_path=str(model),
        budget=12,
        workers=1,
        gpu=True,
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
    )

    assert result.gpu_status == "opengl-active"
    assert result.gpu_shards == 1
    assert result.gpu_hits == 0
    assert result.cpu_batches == 0
    assert result.tested_candidates == result.projected_hits


def test_idat_affine_projection_adapts_to_late_local_deflate_error():
    chunks = (
        idat_bruteforce.png.PngChunk(8, 0x500, b"IDAT", bytes(0x500), 0),
        idat_bruteforce.png.PngChunk(0x520, 0x500, b"IDAT", bytes(0x500), 0),
    )
    root_stream = bytes(0xA00)
    before = idat.analyze_idat_stream(build_rgb_png(1, 1, b"\x00abc"))
    diagnostic = idat_bruteforce.IdatLocalDeflateDiagnostic(
        before=before,
        trace=deflate_header.DynamicHeaderTrace("invalid_huffman_lengths"),
        stream_size=len(root_stream),
        stream_offset=0x340,
        file_offset=None,
        idat_index=1,
        idat_offset=0x340,
        window_start=0x320,
        window_end=0x360,
        context_hex="",
        suspect_byte_offsets=(0x345,),
    )

    projected = idat_bruteforce._projected_model_offsets(root_stream, chunks, diagnostic)
    locals_by_chunk = {
        index: {local for candidate_index, _stream_offset, local in projected if candidate_index == index}
        for index, _chunk, _start, _end in idat_bruteforce._idat_stream_ranges_by_index(chunks)
    }

    assert 0x6E in locals_by_chunk[0]
    assert 0x340 in locals_by_chunk[0]
    assert 0x345 in locals_by_chunk[1]
    assert max(locals_by_chunk[0]) > 0x120


def test_idat_crc_periodic_refuses_hash_mismatch(tmp_path):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    model = tmp_path / "model.json"
    model.write_text(
        json.dumps(
            {
                "version": 1,
                "convoy_stream_hash": "not-this-stream",
                "xors": [1],
                "deltas": [1],
            }
        )
    )

    result = idat_bruteforce.probe_idat_crc_periodic_payload_solver(
        candidate,
        convoy_model_path=str(model),
        budget=100,
    )

    assert result.best is None
    assert result.tested_candidates == 0
    assert "does not match" in result.reason


def test_idat_global_crc_residue_refuses_hash_mismatch(tmp_path):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    model = tmp_path / "model.json"
    model.write_text(
        json.dumps(
            {
                "version": 1,
                "convoy_stream_hash": "not-this-stream",
                "xors": [1],
                "deltas": [1],
                "byte_repairs": [],
            }
        )
    )

    result = idat_bruteforce.probe_idat_global_crc_residue_solver(
        candidate,
        convoy_model_path=str(model),
        budget=100,
    )

    assert result.best is None
    assert result.tested_candidates == 0
    assert "does not match" in result.reason


def test_idat_deflate_resync_salvage_writes_progress(tmp_path):
    candidate, _stream_offset, _original = dynamic_header_corrupt_png()
    progress = tmp_path / "salvage.progress.json"
    preview = tmp_path / "salvage.ppm"

    result = idat_bruteforce.probe_deflate_resync_salvage(
        candidate,
        budget=64,
        progress_path=str(progress),
        preview_path=str(preview),
    )

    assert result.strategy == "deflate-resync-salvage"
    assert result.tested_candidates <= 64
    assert progress.exists()
    state = idat_bruteforce.deflate_salvage_progress_state(candidate, str(progress))
    assert state.available is True
    assert state.source_matches is True
    assert state.exhausted is True


def test_idat_periodic_model_repairs_model_xor_without_deep_beam(tmp_path):
    candidate, stream_offset, original_byte = dynamic_header_corrupt_png()
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    corrupt_byte = stream[stream_offset]
    model = tmp_path / "model.json"
    progress = tmp_path / "periodic.progress.json"
    checkpoint = tmp_path / "periodic.checkpoint.jsonl"
    model.write_text(
        json.dumps(
            {
                "version": 1,
                "convoy_stream_hash": idat_bruteforce._stream_state_key(stream),
                "xors": [corrupt_byte ^ original_byte],
                "deltas": [],
                "byte_repairs": [],
            }
        )
    )

    result = idat_bruteforce.probe_idat_periodic_corruption_model(
        candidate,
        convoy_model_path=str(model),
        budget=500,
        max_depth=1,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
    )

    assert result.strategy == "periodic-corruption-model"
    assert result.best is not None
    assert result.best.after.complete is True
    assert result.best.after.usable_scanlines == 100
    assert any(operation.kind == "periodic-bit-flip" for operation in result.best.operations)
    assert checkpoint.exists()
    assert progress.exists()
    state = idat_bruteforce.periodic_model_progress_state(candidate, str(progress))
    assert state.available is True
    assert state.source_matches is True
    assert state.exhausted is True


def test_idat_deep_beam_gpu_prefilter_hits_are_validated_by_cpu(monkeypatch):
    filtered = b"\x00abc"
    good_stream = zlib.compress(filtered)
    corrupt_stream = bytearray(good_stream)
    corrupt_stream[-1] ^= 0xFF
    data = build_rgb_png(1, 1, filtered, idat_data=bytes(corrupt_stream))
    before = idat.analyze_idat_stream(data)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    parent = idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(),
        before=before,
        after=before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=idat_bruteforce._deep_beam_score(
            before,
            stream,
            0,
            data=data,
            original_idat_count=original_idat_count,
        ),
    )

    monkeypatch.setattr(
        ultimate_opengl_backend,
        "explain_analysis",
        lambda plan, gpu_config: ultimate_opengl_backend.UltimateOpenGLDecision(True, "mock"),
    )

    def fake_run(plan, gpu_config, **_kwargs):
        hit = ultimate_opengl_backend.UltimateOpenGLAnalysisHit(
            0,
            1,
            plan.start_rank,
            (0,),
            "complete",
            len(filtered),
            1,
            None,
            None,
            None,
            "adler_match",
            (1, 1, 1),
            ("host-deflate-required",),
        )
        return ultimate_opengl_backend.UltimateOpenGLAnalysisResult(
            (hit,),
            1,
            0,
            plan.start_rank,
            plan.bounded_end_rank,
            plan.bounded_end_rank,
            covered_rank_count=plan.bounded_end_rank - plan.start_rank,
            shader_used=True,
        )

    monkeypatch.setattr(ultimate_opengl_backend, "run_analysis_gpu", fake_run)

    successors, tested, used_gpu, backend, warning, covered = idat_bruteforce._deep_beam_gpu_byte_successors(
        parent,
        before=before,
        state_id_start=1,
        original_idat_count=original_idat_count,
        depth=1,
        specs=(("replace", len(stream) - 1, good_stream[-1]),),
        budget_left=10,
        checkpoint_every=10,
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
        gpu_done_shards=set(),
        workers=1,
    )

    assert used_gpu is True
    assert backend == "opengl-active"
    assert warning == ""
    assert tested == 1
    assert covered == {0}
    assert len(successors) == 1
    assert successors[0].operations[-1].kind == "gpu-replace"
    assert successors[0].after.complete is True


def test_idat_deep_beam_batch_validation_matches_spec_by_spec():
    filtered = b"\x00abc"
    good_stream = zlib.compress(filtered)
    corrupt_stream = bytearray(good_stream)
    corrupt_stream[-1] ^= 0xFF
    data = build_rgb_png(1, 1, filtered, idat_data=bytes(corrupt_stream))
    before = idat.analyze_idat_stream(data)
    specs = (
        ("replace", len(good_stream) - 1, good_stream[-1]),
        ("insert", 0, 0x00),
        ("remove", 0, 0),
    )

    batched = idat_bruteforce._deep_beam_apply_mutation_batch((data, before, specs))
    singles = tuple(
        idat_bruteforce._deep_beam_apply_mutation_spec((data, before, spec))
        for spec in specs
    )

    assert tuple(None if item is None else item.data for item in batched) == tuple(
        None if item is None else item.data for item in singles
    )
    assert tuple(None if item is None else item.after.status for item in batched) == tuple(
        None if item is None else item.after.status for item in singles
    )


def test_idat_deep_beam_gpu_shard_size_is_independent_from_checkpoint(tmp_path, monkeypatch):
    filtered = b"\x00abc"
    good_stream = zlib.compress(filtered)
    corrupt_stream = bytearray(good_stream)
    corrupt_stream[-1] ^= 0xFF
    data = build_rgb_png(1, 1, filtered, idat_data=bytes(corrupt_stream))
    before = idat.analyze_idat_stream(data)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    parent = idat_bruteforce.IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(),
        before=before,
        after=before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=idat_bruteforce._deep_beam_score(
            before,
            stream,
            0,
            data=data,
            original_idat_count=original_idat_count,
        ),
    )
    specs = tuple(("replace", index, stream[index] ^ 1) for index in range(5))
    calls = []

    monkeypatch.setattr(
        ultimate_opengl_backend,
        "explain_analysis",
        lambda plan, gpu_config: ultimate_opengl_backend.UltimateOpenGLDecision(True, "mock"),
    )

    def fake_run(plan, gpu_config, **kwargs):
        calls.append((plan.start_rank, plan.bounded_end_rank, kwargs.get("max_ranks")))
        return ultimate_opengl_backend.UltimateOpenGLAnalysisResult(
            (),
            plan.bounded_end_rank - plan.start_rank,
            0,
            plan.start_rank,
            plan.bounded_end_rank,
            plan.bounded_end_rank,
            covered_rank_count=plan.bounded_end_rank - plan.start_rank,
            shader_used=True,
        )

    monkeypatch.setattr(ultimate_opengl_backend, "run_analysis_gpu", fake_run)
    done_shards: set[str] = set()
    timing = idat_bruteforce.IdatDeepBeamRuntimeStats()

    successors, tested, used_gpu, backend, warning, covered = idat_bruteforce._deep_beam_gpu_byte_successors(
        parent,
        before=before,
        state_id_start=1,
        original_idat_count=original_idat_count,
        depth=1,
        specs=specs,
        budget_left=5,
        checkpoint_every=2,
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
        gpu_done_shards=done_shards,
        workers=1,
        gpu_shard_size=3,
        timing=timing,
    )

    assert successors == []
    assert used_gpu is True
    assert backend == "opengl-active"
    assert warning == ""
    assert tested == 5
    assert covered == set(range(5))
    assert calls == [(0, 3, 3), (3, 5, 2)]
    assert timing.gpu_shards == 2

    progress = tmp_path / "_deep_beam.progress.json"
    source_hash = idat_bruteforce._stream_state_key(stream)
    idat_bruteforce._write_deep_beam_progress(
        str(progress),
        source_hash=source_hash,
        tested=tested,
        depth=1,
        max_depth=1,
        budget=5,
        state_count=1,
        visited_count=1,
        best=None,
        workers=1,
        gpu_backend=backend,
        gpu_done_shards=done_shards,
        gpu_shard_size=3,
        timing=timing,
    )
    loaded = idat_bruteforce._load_deep_beam_progress(
        str(progress),
        source_hash=source_hash,
        gpu_shard_size=2,
    )
    assert loaded.resumed is True
    assert loaded.gpu_done_shards == set()
    assert loaded.tested_candidates == tested


def test_idat_deep_beam_creates_one_worker_pool_per_run(monkeypatch):
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()
    created = []
    shutdowns = []

    class FakeExecutor:
        def __init__(self, **kwargs):
            created.append(kwargs)

        def shutdown(self, **_kwargs):
            shutdowns.append(_kwargs)

    monkeypatch.setattr(idat_bruteforce, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(
        idat_bruteforce,
        "_deep_beam_byte_bit_successors",
        lambda *_args, **_kwargs: ([], 0, "off", ""),
    )

    result = idat_bruteforce.probe_idat_deflate_deep_beam(
        candidate,
        budget=20,
        max_depth=3,
        beam_width=2,
        top_candidates=2,
        workers=4,
        checkpoint_every=999999,
    )

    assert result.workers == 4
    assert created == [
        {
            "max_workers": 4,
            "initializer": idat_bruteforce._deep_beam_worker_init,
        }
    ]
    assert shutdowns == [{}]


def test_idat_deep_beam_resume_keeps_committed_progress_floor(tmp_path, monkeypatch):
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    source_hash = idat_bruteforce._stream_state_key(stream)
    checkpoint = tmp_path / "_deep_beam.checkpoint.jsonl"
    progress = tmp_path / "_deep_beam.progress.json"
    checkpoint.write_text(
        json.dumps(
            {
                "source_hash": source_hash,
                "stream_hash": source_hash + "-candidate",
                "state_id": 1500,
                "parent_id": 0,
                "depth": 1,
                "stream": stream.hex(),
                "operations": [],
                "score": [0],
                "status": "corrupt_deflate",
                "usable_scanlines": 0,
                "decompressed": 0,
                "error_offset": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    idat_bruteforce._write_deep_beam_progress(
        str(progress),
        source_hash=source_hash,
        tested=1234,
        depth=1,
        max_depth=5,
        budget=5000,
        state_count=1200,
        visited_count=1100,
        best=None,
        workers=1,
    )

    monkeypatch.setattr(
        idat_bruteforce,
        "_deep_beam_byte_bit_successors",
        lambda *_args, **_kwargs: ([], 0, "off", ""),
    )

    progress_calls = []
    result = idat_bruteforce.probe_idat_deflate_deep_beam(
        candidate,
        budget=5000,
        max_depth=5,
        beam_width=2,
        top_candidates=2,
        workers=1,
        checkpoint_every=999999,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
        progress=lambda stage, tested, total: progress_calls.append((stage, tested, total)),
    )

    assert result.progress_resumed is True
    assert result.tested_candidates >= 1500
    assert progress_calls[0] == ("deep-beam", 1500, 5000)
    record = json.loads(progress.read_text(encoding="utf-8"))
    assert record["tested_candidates"] >= 1500


def test_idat_deep_beam_soft_depth_stops_at_hard_guard(monkeypatch):
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()
    before = idat.analyze_idat_stream(candidate)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    operation = idat_bruteforce.IdatDeepBeamOperation("replace", 0, stream[:1], stream[:1])
    checkpoint_candidate = idat_bruteforce.IdatDeepBeamCandidate(
        data=candidate,
        stream=stream,
        operations=(operation,) * 5,
        before=before,
        after=before,
        state_id=42,
        parent_id=1,
        source_offsets=(0,) * 5,
        score=idat_bruteforce._deep_beam_score(
            before,
            stream,
            5,
            data=candidate,
            original_idat_count=original_idat_count,
        ),
    )
    depths = []
    hard_guard_candidate = idat_bruteforce.IdatDeepBeamCandidate(
        data=candidate,
        stream=stream + b"\x00",
        operations=(operation,) * 6,
        before=before,
        after=before,
        state_id=43,
        parent_id=42,
        source_offsets=(0,) * 6,
        score=checkpoint_candidate.score,
    )

    monkeypatch.setattr(
        idat_bruteforce,
        "_load_deep_beam_checkpoint",
        lambda *_args, **_kwargs: ([checkpoint_candidate], {idat_bruteforce._stream_state_key(stream)}, 43, 1),
    )

    def record_depth(*_args, **kwargs):
        depths.append(kwargs["depth"])
        return ([hard_guard_candidate] if kwargs["depth"] == 6 else [], 1, "off", "")

    monkeypatch.setattr(idat_bruteforce, "_deep_beam_byte_bit_successors", record_depth)
    monkeypatch.setattr(
        idat_bruteforce,
        "_deep_beam_subprobe_successors",
        lambda *_args, **_kwargs: ([], 0),
    )

    result = idat_bruteforce.probe_idat_deflate_deep_beam(
        candidate,
        budget=50,
        max_depth=5,
        beam_width=2,
        top_candidates=2,
        workers=1,
        checkpoint_every=999999,
    )

    assert depths == [6]
    assert result.reached_depth == 6
    assert "soft_max_depth=5" in result.reason
    assert "hard_depth_limit=6" in result.reason
    assert "stop=hard depth limit reached" in result.reason


def test_idat_deep_beam_loads_compact_checkpoint_record_without_stream(tmp_path):
    filtered = b"\x00abc"
    source_stream = zlib.compress(filtered)
    new_stream = bytes((source_stream[0] ^ 1,)) + source_stream[1:]
    data = build_rgb_png(1, 1, filtered, idat_data=source_stream)
    before = idat.analyze_idat_stream(data)
    chunks, _stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    source_hash = idat_bruteforce._stream_state_key(source_stream)
    checkpoint = tmp_path / "_deep_beam.checkpoint.jsonl"
    operation = idat_bruteforce.IdatDeepBeamOperation(
        "replace",
        0,
        source_stream[:1],
        new_stream[:1],
    )
    checkpoint.write_text(
        json.dumps(
            {
                "version": 3,
                "source_hash": source_hash,
                "stream_hash": idat_bruteforce._stream_state_key(new_stream),
                "state_id": 7,
                "parent_id": 0,
                "depth": 1,
                "operations": [idat_bruteforce._deep_beam_operation_to_json(operation)],
                "score": [0],
                "status": "corrupt_deflate",
                "usable_scanlines": 0,
                "decompressed": 0,
                "error_offset": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    candidates, visited, next_state_id, resumed = idat_bruteforce._load_deep_beam_checkpoint(
        str(checkpoint),
        source_hash=source_hash,
        source_stream=source_stream,
        chunks=chunks,
        before=before,
        original_idat_count=1,
        candidate_limit=4,
        max_operation_depth=2,
    )

    assert resumed == 1
    assert next_state_id == 8
    assert visited == {idat_bruteforce._stream_state_key(new_stream)}
    assert len(candidates) == 1
    assert candidates[0].stream == new_stream
    assert candidates[0].operations == (operation,)


def test_idat_deep_beam_checkpoint_loader_keeps_only_recent_candidates(tmp_path):
    filtered = b"\x00abc"
    source_stream = zlib.compress(filtered)
    data = build_rgb_png(1, 1, filtered, idat_data=source_stream)
    before = idat.analyze_idat_stream(data)
    chunks, _stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    source_hash = idat_bruteforce._stream_state_key(source_stream)
    checkpoint = tmp_path / "_deep_beam.checkpoint.jsonl"

    records = []
    for state_id in range(1, 21):
        new_byte = (source_stream[0] + state_id) & 0xFF
        new_stream = bytes((new_byte,)) + source_stream[1:]
        operation = idat_bruteforce.IdatDeepBeamOperation(
            "replace",
            0,
            source_stream[:1],
            bytes((new_byte,)),
        )
        records.append(
            json.dumps(
                {
                    "version": 3,
                    "source_hash": source_hash,
                    "stream_hash": idat_bruteforce._stream_state_key(new_stream),
                    "state_id": state_id,
                    "parent_id": 0,
                    "depth": 1,
                    "operations": [idat_bruteforce._deep_beam_operation_to_json(operation)],
                },
                sort_keys=True,
            )
        )
    checkpoint.write_text("\n".join(records) + "\n", encoding="utf-8")

    candidates, visited, next_state_id, resumed = idat_bruteforce._load_deep_beam_checkpoint(
        str(checkpoint),
        source_hash=source_hash,
        source_stream=source_stream,
        chunks=chunks,
        before=before,
        original_idat_count=1,
        candidate_limit=3,
        max_operation_depth=2,
    )

    assert resumed == 20
    assert len(visited) == 20
    assert next_state_id == 21
    assert [candidate.state_id for candidate in candidates] == [18, 19, 20]


def test_idat_deep_beam_resume_compacts_legacy_stream_checkpoint(tmp_path, monkeypatch):
    filtered = b"\x00abc"
    source_stream = bytearray(zlib.compress(filtered))
    source_stream[-1] ^= 0xFF
    source_stream = bytes(source_stream)
    new_stream = bytes((source_stream[0] ^ 1,)) + source_stream[1:]
    data = build_rgb_png(1, 1, filtered, idat_data=source_stream)
    source_hash = idat_bruteforce._stream_state_key(source_stream)
    checkpoint = tmp_path / "_deep_beam.checkpoint.jsonl"
    operation = idat_bruteforce.IdatDeepBeamOperation(
        "replace",
        0,
        source_stream[:1],
        new_stream[:1],
    )
    checkpoint.write_text(
        json.dumps(
            {
                "source_hash": source_hash,
                "stream_hash": idat_bruteforce._stream_state_key(new_stream),
                "state_id": 7,
                "parent_id": 0,
                "depth": 1,
                "stream": new_stream.hex(),
                "operations": [idat_bruteforce._deep_beam_operation_to_json(operation)],
                "score": [0],
                "status": "corrupt_deflate",
                "usable_scanlines": 0,
                "decompressed": 0,
                "error_offset": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        idat_bruteforce,
        "_deep_beam_byte_bit_successors",
        lambda *_args, **_kwargs: ([], 0, "off", ""),
    )
    monkeypatch.setattr(
        idat_bruteforce,
        "_deep_beam_subprobe_successors",
        lambda *_args, **_kwargs: ([], 0),
    )

    result = idat_bruteforce.probe_idat_deflate_deep_beam(
        data,
        budget=1,
        max_depth=1,
        beam_width=2,
        top_candidates=2,
        workers=1,
        checkpoint_every=999999,
        checkpoint_path=str(checkpoint),
    )

    assert result.progress_resumed is True
    compact_records = [
        json.loads(line)
        for line in checkpoint.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert compact_records
    assert all("stream" not in record for record in compact_records)
    assert all(record.get("version") == 3 for record in compact_records)


def test_idat_deep_beam_keyboard_interrupt_closes_gpu_session(monkeypatch):
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()
    closed = []

    class FakeSession:
        def __init__(self, _gpu_config):
            pass

        def close(self):
            closed.append(True)

    monkeypatch.setattr(ultimate_opengl_backend, "UltimateOpenGLAnalysisSession", FakeSession)

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(idat_bruteforce, "_deep_beam_byte_bit_successors", interrupt)

    result = idat_bruteforce.probe_idat_deflate_deep_beam(
        candidate,
        budget=20,
        max_depth=1,
        beam_width=2,
        top_candidates=2,
        workers=1,
        gpu=True,
        checkpoint_every=999999,
    )

    assert result.interrupted is True
    assert closed == [True]


def test_idat_deep_beam_keyboard_interrupt_cancels_worker_pool(monkeypatch):
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()
    created = []
    shutdowns = []

    class FakeExecutor:
        _processes = {}

        def __init__(self, **kwargs):
            created.append(kwargs)

        def shutdown(self, **kwargs):
            shutdowns.append(kwargs)

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(idat_bruteforce, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(idat_bruteforce, "_deep_beam_byte_bit_successors", interrupt)

    result = idat_bruteforce.probe_idat_deflate_deep_beam(
        candidate,
        budget=20,
        max_depth=1,
        beam_width=2,
        top_candidates=2,
        workers=4,
        checkpoint_every=999999,
    )

    assert result.interrupted is True
    assert created == [
        {
            "max_workers": 4,
            "initializer": idat_bruteforce._deep_beam_worker_init,
        }
    ]
    assert shutdowns == [{"wait": False, "cancel_futures": True}]


def test_idat_deep_beam_keyboard_interrupt_flushes_progress(tmp_path, monkeypatch):
    candidate, _bits, _original = dynamic_header_two_bit_corrupt_png()
    checkpoint = tmp_path / "_deep_beam.checkpoint.jsonl"
    progress = tmp_path / "_deep_beam.progress.json"

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(idat_bruteforce, "_deep_beam_byte_bit_successors", interrupt)

    result = idat_bruteforce.probe_idat_deflate_deep_beam(
        candidate,
        budget=20,
        max_depth=1,
        beam_width=2,
        top_candidates=2,
        workers=1,
        checkpoint_every=5,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
    )

    assert result.interrupted is True
    assert progress.exists()
    record = json.loads(progress.read_text(encoding="utf-8"))
    assert record["interrupted"] is True
    assert checkpoint.exists()


def test_idat_deep_beam_scores_crc_guided_diagnostic_without_promoting_to_best():
    candidate, bits, _original = dynamic_header_crc_guided_diagnostic_only_png()
    before = idat.analyze_idat_stream(candidate)
    chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    root = idat_bruteforce.IdatDeepBeamCandidate(
        data=candidate,
        stream=stream,
        operations=(),
        before=before,
        after=before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=idat_bruteforce._deep_beam_score(
            before,
            stream,
            0,
            data=candidate,
            original_idat_count=original_idat_count,
        ),
    )

    crc_probe = idat_bruteforce.probe_dynamic_huffman_crc_guided_candidates(
        candidate,
        budget=5000,
        max_solutions_per_group=64,
    )
    deep_candidate = idat_bruteforce._deep_beam_candidate_from_deflate_candidate(
        root,
        crc_probe.diagnostic_best,
        before=before,
        state_id=1,
        original_idat_count=original_idat_count,
        kind="crc-guided-diagnostic",
    )

    assert crc_probe.best is None
    assert deep_candidate is not None
    assert deep_candidate.operations[-1].kind == "crc-guided-diagnostic"
    assert deep_candidate.operations[-1].bit_offsets == bits
    assert deep_candidate.score > root.score
    assert idat_bruteforce._idat_crc_match_count_for_original_shape(root.data, original_idat_count) == 0
    assert idat_bruteforce._idat_crc_match_count_for_original_shape(deep_candidate.data, original_idat_count) == 1
    assert deep_candidate.after.usable_scanlines == 0
    assert deep_candidate.after.decompressed_size == 0
    assert not idat_bruteforce.is_material_improvement(before, deep_candidate.after)


def test_dynamic_huffman_bitshift_probe_repairs_extra_header_bit():
    candidate, bit_offset, _original = dynamic_header_extra_bit_png()
    before = idat.analyze_idat_stream(candidate)

    assert before.status == "corrupt_deflate"
    assert before.decompressed_size == 0
    assert before.deflate_header is not None
    assert before.deflate_header.status == "invalid_huffman_lengths"

    result = idat_bruteforce.probe_dynamic_huffman_bitshift_candidates(
        candidate,
        budget=3000,
    )

    assert result.best is not None
    assert result.strategy == "dynamic-huffman-bitshift"
    assert result.best.edit_kind == "bit-delete"
    assert result.best.bit_offsets == (bit_offset,)
    assert result.best.after.complete is True
    assert result.best.after.usable_scanlines == 100
    assert "valid_dynamic_headers=1" in result.reason


def test_dynamic_huffman_semantic_probe_repairs_token_corruption():
    candidate, bit_offset, _original = dynamic_header_semantic_token_corrupt_png()
    before = idat.analyze_idat_stream(candidate)

    assert before.status == "corrupt_deflate"
    assert before.decompressed_size == 0
    assert before.usable_scanlines == 0
    assert before.deflate_header is not None
    assert before.deflate_header.status == "invalid_huffman_lengths"
    assert before.deflate_header.btype == 2

    result = idat_bruteforce.probe_dynamic_huffman_semantic_candidates(
        candidate,
        budget=12000,
        max_tokens=220,
    )

    assert result.best is not None
    assert result.strategy == "dynamic-huffman-semantic"
    assert result.best.edit_kind == "semantic-token"
    assert result.best.bit_offsets == (bit_offset,)
    assert result.best.after.complete is True
    assert result.best.after.usable_scanlines == 100
    assert "semantic_headers=" in result.reason
    assert "valid_headers=1" in result.reason
    idat_chunks = [chunk for chunk in iter_chunks(result.best.data) if chunk.chunk_type == b"IDAT"]
    assert idat_chunks
    assert all(chunk.crc == chunk.computed_crc for chunk in idat_chunks)
    _chunks, repaired_stream = idat_bruteforce._idat_chunks_and_stream(result.best.data)
    repaired_header = deflate_header.analyze_deflate_header(repaired_stream)
    assert repaired_header.ok is True
    assert repaired_header.btype == 2


def test_dynamic_huffman_alphabet_probe_repairs_natural_order_corruption():
    candidate, bit_offsets, _original = dynamic_header_natural_alphabet_corrupt_png()
    before = idat.analyze_idat_stream(candidate)
    _chunks, corrupted_stream = idat_bruteforce._idat_chunks_and_stream(candidate)
    natural_trace = deflate_header.trace_dynamic_header(
        corrupted_stream,
        code_length_order=tuple(range(19)),
    )

    assert before.status == "corrupt_deflate"
    assert before.decompressed_size == 0
    assert before.deflate_header is not None
    assert before.deflate_header.status == "bad_code_length_tree"
    assert before.deflate_header.btype == 2
    assert natural_trace.status == "ok"

    result = idat_bruteforce.probe_dynamic_huffman_alphabet_candidates(candidate, budget=9000)

    assert result.best is not None
    assert result.strategy == "dynamic-huffman-alphabet"
    assert result.best.edit_kind == "alphabet-order"
    assert result.best.bit_offsets == bit_offsets
    assert result.best.after.complete is True
    assert result.best.after.usable_scanlines == 100
    assert "orders=1" in result.reason
    assert "valid_headers=1" in result.reason
    idat_chunks = [chunk for chunk in iter_chunks(result.best.data) if chunk.chunk_type == b"IDAT"]
    assert idat_chunks
    assert all(chunk.crc == chunk.computed_crc for chunk in idat_chunks)
    _chunks, repaired_stream = idat_bruteforce._idat_chunks_and_stream(result.best.data)
    repaired_header = deflate_header.analyze_deflate_header(repaired_stream)
    assert repaired_header.ok is True
    assert repaired_header.btype == 2


def test_dynamic_huffman_crc_guided_probe_repairs_crc_preserved_bitset_corruption():
    candidate, bits, _original = dynamic_header_crc_guided_bitset_corrupt_png(
        bits=(604, 618),
        split=True,
    )
    before = idat.analyze_idat_stream(candidate)
    original_idat_count = len([chunk for chunk in iter_chunks(candidate) if chunk.chunk_type == b"IDAT"])

    assert before.status == "corrupt_deflate"
    assert before.decompressed_size == 0
    assert before.usable_scanlines == 0
    assert before.deflate_header is not None
    assert before.deflate_header.status == "invalid_huffman_lengths"
    assert before.deflate_header.btype == 2
    assert any(
        chunk.chunk_type == b"IDAT" and chunk.crc != chunk.computed_crc
        for chunk in iter_chunks(candidate)
    )

    result = idat_bruteforce.probe_dynamic_huffman_crc_guided_candidates(
        candidate,
        budget=1000,
        max_solutions_per_group=64,
    )

    assert result.best is not None
    assert result.strategy == "dynamic-huffman-crc-guided"
    assert result.best.edit_kind == "crc-guided-bitset"
    assert result.best.bit_offsets == bits
    assert result.best.after.complete is True
    assert result.best.after.usable_scanlines == 100
    assert "crc_solutions=" in result.reason
    assert "valid_headers=1" in result.reason
    repaired_chunks = [chunk for chunk in iter_chunks(result.best.data) if chunk.chunk_type == b"IDAT"]
    assert len(repaired_chunks) == original_idat_count
    assert all(chunk.crc == chunk.computed_crc for chunk in repaired_chunks)
    _chunks, repaired_stream = idat_bruteforce._idat_chunks_and_stream(result.best.data)
    repaired_header = deflate_header.analyze_deflate_header(repaired_stream)
    assert repaired_header.ok is True
    assert repaired_header.btype == 2


def test_dynamic_huffman_crc_guided_probe_repairs_crc_preserved_semantic_corruption():
    candidate, bits, _original = dynamic_header_crc_guided_semantic_corrupt_png()
    before = idat.analyze_idat_stream(candidate)

    assert before.status == "corrupt_deflate"
    assert before.decompressed_size == 0
    assert before.usable_scanlines == 0
    assert before.deflate_header is not None
    assert before.deflate_header.status == "invalid_huffman_lengths"
    assert before.deflate_header.btype == 2

    result = idat_bruteforce.probe_dynamic_huffman_crc_guided_candidates(
        candidate,
        budget=2000,
        max_solutions_per_group=64,
    )

    assert result.best is not None
    assert result.strategy == "dynamic-huffman-crc-guided"
    assert result.best.edit_kind == "crc-guided-semantic"
    assert result.best.bit_offsets == bits
    assert result.best.after.complete is True
    assert result.best.after.usable_scanlines == 100
    repaired_chunks = [chunk for chunk in iter_chunks(result.best.data) if chunk.chunk_type == b"IDAT"]
    assert repaired_chunks
    assert all(chunk.crc == chunk.computed_crc for chunk in repaired_chunks)
    _chunks, repaired_stream = idat_bruteforce._idat_chunks_and_stream(result.best.data)
    repaired_header = deflate_header.analyze_deflate_header(repaired_stream)
    assert repaired_header.ok is True
    assert repaired_header.btype == 2


def test_dynamic_huffman_crc_guided_keeps_zero_scanline_candidate_diagnostic_only():
    candidate, bits, _original = dynamic_header_crc_guided_diagnostic_only_png()
    before = idat.analyze_idat_stream(candidate)

    assert before.status == "corrupt_deflate"
    assert before.decompressed_size == 0
    assert before.usable_scanlines == 0
    assert before.deflate_header is not None
    assert before.deflate_header.status == "invalid_huffman_lengths"
    assert before.deflate_header.btype == 2

    result = idat_bruteforce.probe_dynamic_huffman_crc_guided_candidates(
        candidate,
        budget=5000,
        max_solutions_per_group=64,
    )

    assert result.best is None
    assert result.diagnostic_best is not None
    assert result.diagnostic_best.edit_kind == "crc-guided-bitset"
    assert result.diagnostic_best.bit_offsets == bits
    assert result.diagnostic_best.after.usable_scanlines == 0
    assert result.diagnostic_best.after.decompressed_size == 0
    repaired_chunks = [chunk for chunk in iter_chunks(result.diagnostic_best.data) if chunk.chunk_type == b"IDAT"]
    assert repaired_chunks
    assert all(chunk.crc == chunk.computed_crc for chunk in repaired_chunks)
    assert idat_bruteforce.diagnostic_candidate_summary_lines(result)


def test_deflate_header_probe_runs_dynamic_huffman_phase_for_two_bit_corruption():
    candidate, bits, _original = dynamic_header_two_bit_corrupt_png()

    result = idat_bruteforce.probe_deflate_header_candidates(candidate, budget=5000)

    assert result.best is not None
    assert result.strategy == "deflate-header"
    assert result.best.bit_offsets == bits
    assert result.best.after.complete is True
    assert any(subprobe.strategy == "dynamic-huffman-header" for subprobe in result.subprobes)
    assert any(
        "strategy=dynamic-huffman-header" in line
        for line in idat_bruteforce.probe_detail_summary_lines(result)
    )


def test_deflate_header_probe_runs_dynamic_huffman_bitshift_phase():
    candidate, bit_offset, _original = dynamic_header_extra_bit_png()

    result = idat_bruteforce.probe_deflate_header_candidates(candidate, budget=6000)

    assert result.best is not None
    assert result.strategy == "deflate-header"
    assert result.best.edit_kind == "bit-delete"
    assert result.best.bit_offsets == (bit_offset,)
    assert result.best.after.complete is True
    assert any(subprobe.strategy == "dynamic-huffman-bitshift" for subprobe in result.subprobes)
    assert any(
        "strategy=dynamic-huffman-bitshift" in line
        for line in idat_bruteforce.probe_detail_summary_lines(result)
    )


def test_deflate_header_probe_runs_dynamic_huffman_semantic_phase():
    candidate, bit_offset, _original = dynamic_header_semantic_token_corrupt_png()

    result = idat_bruteforce.probe_deflate_header_candidates(candidate, budget=20000)

    assert result.best is not None
    assert result.strategy == "deflate-header"
    assert result.best.edit_kind == "semantic-token"
    assert result.best.bit_offsets == (bit_offset,)
    assert result.best.after.complete is True
    assert any(subprobe.strategy == "dynamic-huffman-bitshift" for subprobe in result.subprobes)
    assert any(subprobe.strategy == "dynamic-huffman-header" for subprobe in result.subprobes)
    assert any(subprobe.strategy == "dynamic-huffman-semantic" for subprobe in result.subprobes)
    assert any(
        "strategy=dynamic-huffman-semantic" in line and "semantic_headers=" in line
        for line in idat_bruteforce.probe_detail_summary_lines(result)
    )


def test_deflate_header_probe_runs_dynamic_huffman_alphabet_phase():
    candidate, bit_offsets, _original = dynamic_header_natural_alphabet_corrupt_png()

    result = idat_bruteforce.probe_deflate_header_candidates(candidate, budget=30000)

    assert result.best is not None
    assert result.strategy == "deflate-header"
    assert result.best.edit_kind == "alphabet-order"
    assert result.best.bit_offsets == bit_offsets
    assert result.best.after.complete is True
    assert any(subprobe.strategy == "dynamic-huffman-alphabet" for subprobe in result.subprobes)
    assert any(
        "strategy=dynamic-huffman-alphabet" in line and "valid_headers=1" in line
        for line in idat_bruteforce.probe_detail_summary_lines(result)
    )


def test_deflate_header_probe_runs_dynamic_huffman_crc_guided_phase():
    candidate, bits, _original = dynamic_header_crc_guided_bitset_corrupt_png(
        bits=(604, 618, 620),
        split=True,
    )
    original_idat_count = len([chunk for chunk in iter_chunks(candidate) if chunk.chunk_type == b"IDAT"])

    result = idat_bruteforce.probe_deflate_header_candidates(candidate, budget=30000)

    assert result.best is not None
    assert result.strategy == "deflate-header"
    assert result.best.edit_kind == "crc-guided-bitset"
    assert result.best.bit_offsets == bits
    assert result.best.after.complete is True
    assert any(subprobe.strategy == "dynamic-huffman-crc-guided" for subprobe in result.subprobes)
    assert any(
        "strategy=dynamic-huffman-crc-guided" in line and "crc_solutions=" in line
        for line in idat_bruteforce.probe_detail_summary_lines(result)
    )
    repaired_chunks = [chunk for chunk in iter_chunks(result.best.data) if chunk.chunk_type == b"IDAT"]
    assert len(repaired_chunks) == original_idat_count
    assert all(chunk.crc == chunk.computed_crc for chunk in repaired_chunks)


def test_deflate_header_probe_does_not_accept_header_only_progress_without_scanlines():
    candidate = build_rgb_png(1, 1, b"\x00abc", idat_data=b"\x78\x9c\xff\xff")

    result = idat_bruteforce.probe_deflate_header_candidates(candidate, budget=128)

    assert result.best is None
    assert result.diagnostic_best is not None
    assert result.diagnostic_best.after.decompressed_size > result.before.decompressed_size
    assert result.diagnostic_best.after.usable_scanlines == 0
    assert idat_bruteforce.diagnostic_candidate_summary_lines(result)
    assert result.strategy == "deflate-header"


def test_idat_deflate_strategy_queue_uses_material_progress_only():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[2] ^= 0xFF
    candidate = build_rgb_png(
        1,
        2,
        filtered,
        idat_data=bytes(compressed),
        idat_parts=split_bytes(bytes(compressed), 5),
    )

    result = idat_bruteforce.probe_idat_deflate_strategy_queue(candidate)

    assert result.best is not None
    assert result.strategy in {"strict-byte", "pre-error-bit", "wide-byte"}
    assert result.best.after.complete is True


def test_idat_deflate_strategy_queue_chases_multiple_material_steps():
    filtered = b"\x00\x00\x00\x00" + b"\x00\x01\x01\x01"
    compressed = bytearray(zlib.compress(filtered))
    original_deflate_byte = compressed[2]
    original_adler_byte = compressed[-4]
    compressed[2] ^= 0xFF
    compressed[-4] ^= 0xFF
    candidate = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))

    result = idat_bruteforce.probe_idat_deflate_strategy_queue(candidate, max_steps=4)

    assert result.best is not None
    assert result.strategy == "chase"
    assert len(result.chain) == 2
    assert [(step.stream_offset, step.new_byte) for step in result.chain] == [
        (2, original_deflate_byte),
        (len(compressed) - 4, original_adler_byte),
    ]
    assert result.best.after.complete is True
    assert idat.analyze_idat_stream(result.best.data).complete is True


def test_idat_deflate_heavy_probe_reports_progress_and_repairs_candidate():
    calls = []
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    original = compressed[2]
    compressed[2] ^= 0xFF
    candidate = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))

    result = idat_bruteforce.probe_idat_deflate_heavy_candidates(
        candidate,
        backtrack=8,
        forward=8,
        budget=5000,
        progress=lambda loop, budget, build: calls.append((loop, budget, build)),
    )

    assert result.best is not None
    assert result.best.stream_offset == 2
    assert result.best.new_byte == original
    assert result.best.after.complete is True
    assert calls[0] == (0, 5000, True)
    assert calls[-1][2] is False


def test_idat_deflate_probe_ignores_candidates_without_progress():
    candidate = build_rgb_png(1, 1, b"\x00abc", idat_data=b"\x78\x9c\xff\xff")

    result = idat_bruteforce.probe_idat_deflate_byte_candidates(candidate, window_radius=1, budget=4)

    assert result.best is None
    assert result.budget_exhausted is True


def test_idat_deflate_strategy_queue_reports_no_candidate_without_progress():
    compressed = bytearray(zlib.compress(b"\x00abc"))
    compressed[0] = 0
    compressed[1] = 0
    candidate = build_rgb_png(1, 1, b"\x00abc", idat_data=bytes(compressed))

    result = idat_bruteforce.probe_idat_deflate_strategy_queue(candidate)

    assert result.best is None
    assert result.strategy == "strategy-queue"
    assert result.reason == "IDAT error offset is unknown"


def test_idat_deflate_probe_does_not_treat_error_offset_drift_as_progress():
    before = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        error_offset=114,
    )
    after = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        error_offset=115,
    )

    assert idat_bruteforce.is_material_improvement(before, after) is False


def test_idat_deflate_probe_does_not_treat_decompressed_bytes_without_scanlines_as_progress():
    before = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=28,
    )
    after = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        decompressed_size=2048,
        complete_scanlines=3,
        usable_scanlines=0,
        error_offset=740,
    )

    assert idat_bruteforce.is_material_improvement(before, after) is False


def test_idat_deflate_probe_treats_new_usable_scanline_as_progress():
    before = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        usable_scanlines=0,
    )
    after = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        usable_scanlines=1,
    )

    assert idat_bruteforce.is_material_improvement(before, after) is True


def test_analyze_idat_stream_reports_bad_zlib_header():
    filtered = b"\x00abc"
    compressed = bytearray(zlib.compress(filtered))
    compressed[0] = 0
    compressed[1] = 0

    analysis = idat.analyze_idat_stream(build_rgb_png(1, 1, filtered, idat_data=bytes(compressed)))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.status == "bad_zlib_header"
    assert analysis.reason == "bad zlib header"
    assert analysis.error_offset is None


def test_analyze_idat_stream_reports_bad_adler():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(3))
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF

    analysis = idat.analyze_idat_stream(build_rgb_png(1, 3, filtered, idat_data=bytes(compressed)))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.status == "bad_adler"
    assert analysis.partial is True
    assert analysis.usable_scanlines == 3
    assert analysis.recovered_scanlines == filtered
    assert analysis.error_offset is not None
    assert analysis.stored_adler != zlib.adler32(filtered)
    assert analysis.computed_adler == zlib.adler32(filtered)
    assert analysis.adler_status == "adler_mismatch"


def test_analyze_idat_stream_reports_trailing_data():
    filtered = dynamic_filtered_rows(height=2)
    compressed = zlib.compress(filtered) + b"\xa5\x5a"

    analysis = idat.analyze_idat_stream(build_rgb_png(1, 2, filtered, idat_data=compressed))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.status == "trailing_data"
    assert analysis.decompressed_size == len(filtered)
    assert analysis.error_offset == len(compressed) - 2
    assert analysis.computed_adler == zlib.adler32(filtered)


def test_sbb_idat_diagnostic_reports_large_blackfill_gap():
    data = (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "IDAT_Corruption_2.png").read_bytes()

    diagnostic = idat.analyze_sbb_idat_diagnostic(data, crc_target_trusted=False)

    assert diagnostic.supported is True
    assert (diagnostic.width, diagnostic.height) == (900, 580)
    assert diagnostic.color_label == "RGB"
    assert diagnostic.bit_depth == 8
    assert diagnostic.expected_decompressed_size == 1_566_580
    assert diagnostic.decompressed_size == 1_491_984
    assert diagnostic.missing_decompressed_size == 74_596
    assert diagnostic.complete_scanlines == 552
    assert diagnostic.total_scanlines == 580
    assert diagnostic.partial_scanline_bytes == 1032
    assert diagnostic.success_estimate == "low"
    assert diagnostic.recommended_repair_family == "missing"
    assert diagnostic.hephaestus_order == ("Insert", "Replace", "Remove")
    assert diagnostic.cheap_twobytes_viable is False


def test_sbb_idat_diagnostic_marks_complete_stream_as_visual_reference_case():
    filtered = dynamic_filtered_rows(height=2)
    diagnostic = idat.analyze_sbb_idat_diagnostic(
        build_rgb_png(1, 2, filtered),
        crc_target_trusted=True,
    )

    assert diagnostic.supported is True
    assert diagnostic.success_estimate == "low"
    assert diagnostic.crc_target_useful is False
    assert diagnostic.requires_visual_reference is True
    assert diagnostic.recommended_repair_family == "replace"
    assert diagnostic.hephaestus_order == ("Replace", "Insert", "Remove")


def test_sbb_idat_fixtures_keep_original_crc_targets():
    fixture_expectations = {
        "SBB_IDAT_1Byte_Replace.png": ("replace", ("Replace", "Insert", "Remove")),
        "SBB_IDAT_1Byte_Missing.png": ("missing", ("Insert", "Replace", "Remove")),
        "SBB_IDAT_1Byte_Extra.png": ("extra", ("Remove", "Replace", "Insert")),
        "SBB_IDAT_2Byte_Replace.png": ("replace", ("Replace", "Insert", "Remove")),
        "SBB_IDAT_2Byte_Missing.png": ("missing", ("Insert", "Replace", "Remove")),
        "SBB_IDAT_2Byte_Extra.png": ("extra", ("Remove", "Replace", "Insert")),
        "SBB_IDAT_4Byte_Replace.png": ("replace", ("Replace", "Insert", "Remove")),
        "SBB_IDAT_4Byte_Missing.png": ("missing", ("Insert", "Replace", "Remove")),
        "SBB_IDAT_4Byte_Extra.png": ("extra", ("Remove", "Replace", "Insert")),
    }
    for fixture_name, (family, order) in fixture_expectations.items():
        data = (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / fixture_name).read_bytes()
        idat_chunks = [chunk for chunk in iter_chunks(data) if chunk.chunk_type == b"IDAT"]
        diagnostic = idat.analyze_sbb_idat_diagnostic(data, crc_target_trusted=True)

        assert len(idat_chunks) == 1
        assert idat_chunks[0].crc_ok is False
        assert diagnostic.success_estimate in {"good", "maybe"}
        assert diagnostic.recommended_repair_family == family
        assert diagnostic.hephaestus_order == order


def test_analyze_idat_stream_reports_incomplete_stream():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    _candidate, partial = find_truncated_candidate(
        filtered,
        lambda analysis: analysis.usable_scanlines > 0 and analysis.decompression_error,
    )

    analysis = idat.analyze_idat_stream(_candidate)

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.status == "incomplete_stream"
    assert analysis.partial is True
    assert analysis.usable_scanlines == partial.usable_scanlines
    assert analysis.error_offset == analysis.compressed_size


def test_analyze_idat_stream_reports_unsupported_interlace():
    filtered = b"\x00abc"
    analysis = idat.analyze_idat_stream(build_rgb_png(1, 1, filtered, interlace=1))

    assert analysis.supported is False
    assert analysis.complete is False
    assert analysis.status == "unsupported_interlace"
    assert analysis.reason == "interlaced PNG is not supported"


def main():
    checks = [
        ("Dummy scanline", test_dummy_scanline_preserves_legacy_sample_width),
        ("Zlib header", test_idat_zlib_header_skips_interlaced_streams_like_legacy_todo),
        ("Zlib header info", test_zlib_header_info_reads_window_and_legacy_compression_level),
        ("Dummy probe", test_build_dummy_idat_probe_decompresses_debug_stream_and_idat_stream),
        ("Invalid stream", test_build_dummy_idat_probe_reports_invalid_stream_without_raising),
        (
            "Partial IDAT complete stream",
            test_analyze_partial_idat_reports_complete_non_interlaced_stream,
        ),
        (
            "Partial IDAT complete multi-IDAT stream",
            test_analyze_partial_idat_concatenates_complete_multi_idat_stream,
        ),
        (
            "Partial IDAT truncated stream",
            test_analyze_partial_idat_keeps_good_scanlines_until_truncated_stream_error,
        ),
        (
            "Partial IDAT truncated multi-IDAT stream",
            test_analyze_partial_idat_recovers_truncated_multi_idat_stream,
        ),
        (
            "Partial IDAT bad Adler",
            test_analyze_partial_idat_reports_bad_adler_with_recovered_scanlines,
        ),
        (
            "Partial IDAT broken zlib header",
            test_analyze_partial_idat_rejects_broken_zlib_header_without_scanlines,
        ),
        (
            "Partial IDAT scanline tail",
            test_analyze_partial_idat_discards_partial_scanline_tail,
        ),
        (
            "Partial IDAT Adam7 blackfill",
            test_analyze_partial_idat_repairs_interlaced_stream_with_adam7_blackfill,
        ),
        (
            "Partial IDAT truncate_zlib_2 Adam7 fixture",
            test_rebuild_partial_idat_blackfill_repairs_truncated_adam7_fixture,
        ),
        (
            "Partial IDAT invalid stream",
            test_analyze_partial_idat_reports_invalid_stream_without_scanlines,
        ),
        (
            "Partial IDAT blackfill repair",
            test_rebuild_partial_idat_blackfill_keeps_prefix_and_fills_remaining_rows,
        ),
        (
            "Partial IDAT blackfill empty valid stream",
            test_rebuild_partial_idat_blackfill_handles_valid_empty_stream,
        ),
        (
            "IDAT donor repair",
            test_rebuild_idat_from_donor_replaces_zero_scanline_idat,
        ),
        (
            "IDAT donor incompatible shape",
            test_rebuild_idat_from_donor_rejects_incompatible_shape,
        ),
        (
            "IDAT synthetic diagnostic",
            test_rebuild_synthetic_idat_builds_diagnostic_image_from_ihdr,
        ),
        (
            "Truncated IDAT normalization",
            test_normalize_truncated_idat_at_eof_rebuilds_analyzable_png,
        ),
        (
            "Zero-scanline placeholder",
            test_rebuild_zero_scanline_placeholder_handles_truncated_zlib_normalization,
        ),
        (
            "Partial IDAT tolerant salvage",
            test_rebuild_tolerant_idat_salvage_keeps_rows_after_bad_filters,
        ),
        (
            "IDAT marker-chain preserves chunks",
            test_idat_marker_chain_repair_preserves_valid_idat_chunks_byte_for_byte,
        ),
        (
            "IDAT marker-chain variants",
            test_idat_marker_chain_repair_generates_declared_payload_and_shorten_variants,
        ),
        (
            "IDAT marker-chain fixture ranking",
            test_idat_marker_chain_fixture_prefers_declared_payload_visual_salvage,
        ),
        (
            "IDAT linefeed CR insert probe",
            test_idat_linefeed_cr_insert_probe_improves_salvage_candidate,
        ),
        (
            "SuperMega multi CRLF",
            test_super_mega_linefeed_force_recovers_multiple_crlf_deletions,
        ),
        (
            "SuperMega known gap",
            test_super_mega_linefeed_force_uses_known_gap_phase_before_broad_search,
        ),
        (
            "SuperMega budget exhausted",
            test_super_mega_linefeed_force_reports_budget_exhausted_but_keeps_best_candidate,
        ),
        (
            "SuperMega wrong Adler target",
            test_super_mega_linefeed_force_keeps_best_when_original_adler_target_is_wrong,
        ),
        (
            "Ultimate suspect offsets",
            test_ultimate_linefeed_suspect_offsets_prioritize_error_and_linefeeds,
        ),
        (
            "Ultimate live preview callback",
            test_ultimate_linefeed_preview_callback_only_receives_valid_complete_candidates,
        ),
        (
            "Ultimate progress checkpoint",
            test_ultimate_linefeed_progress_checkpoint_round_trips,
        ),
        (
            "Ultimate combination resume indices",
            test_ultimate_linefeed_combination_indices_resume_without_restarting,
        ),
        (
            "Ultimate progress resume",
            test_ultimate_linefeed_bruteforce_resumes_progress_checkpoint,
        ),
        (
            "Ultimate sigint visual flush",
            test_ultimate_linefeed_sigint_flushes_visual_gallery,
        ),
        (
            "Ultimate backfill flush progress",
            test_ultimate_linefeed_backfill_flush_progress_counts_kept_candidates,
        ),
        (
            "Ultimate visual reference rank",
            test_ultimate_visual_gallery_structure_beats_reference_rank,
        ),
        (
            "Ultimate top reference rank",
            test_ultimate_top_candidates_structure_beats_reference_rank,
            test_ultimate_top_candidates_reference_rank_breaks_structural_ties,
        ),
        (
            "Partial IDAT blackfill ignored cases",
            test_rebuild_partial_idat_blackfill_ignores_complete_or_unusable_streams,
        ),
        ("IDAT stream complete", test_analyze_idat_stream_reports_complete_stream),
        ("IDAT stream target Adler", test_zlib_trailer_adler_extracts_target_from_idat_stream),
        ("IDAT stream rebuilt Adler", test_analyze_idat_stream_marks_rebuilt_adler_provenance),
        ("IDAT stream corrupt deflate", test_analyze_idat_stream_reports_corrupt_deflate),
        (
            "IDAT stream deflate header diagnosis",
            test_analyze_idat_stream_attaches_deflate_header_diagnosis,
        ),
        ("IDAT stream error mapping", test_analyze_idat_stream_maps_error_to_multi_idat_file_offset),
        ("IDAT deflate byte probe repair", test_idat_deflate_probe_repairs_single_byte_corruption),
        ("IDAT deflate header probe repair", test_deflate_header_probe_repairs_header_corruption),
        (
            "IDAT dynamic Huffman two-bit repair",
            test_dynamic_huffman_header_probe_repairs_two_bit_length_corruption,
        ),
        (
            "IDAT dynamic Huffman diagnostic-only",
            test_dynamic_huffman_header_probe_keeps_zero_scanline_candidate_diagnostic_only,
        ),
        (
            "IDAT local deflate diagnostic",
            test_idat_local_deflate_diagnostic_reports_dynamic_huffman_context,
        ),
        (
            "IDAT local deflate probe",
            test_idat_local_deflate_probe_keeps_search_bounded_and_scores_progress,
        ),
        (
            "IDAT PNG filter literal repair",
            test_idat_png_filter_literal_repair_fixes_direct_row_filter_bytes,
        ),
        (
            "IDAT PNG filter mapped byte repair",
            test_idat_png_filter_literal_repair_searches_near_mapped_filter_byte,
        ),
        (
            "IDAT deep beam depth two",
            test_idat_deep_beam_chases_depth_two_progress,
        ),
        (
            "IDAT deep beam default budget",
            test_idat_deep_beam_default_budget_is_ten_million,
        ),
        (
            "IDAT deep beam checkpoint resume",
            test_idat_deep_beam_checkpoint_resume_round_trips,
        ),
        (
            "IDAT deep beam GPU prefilter",
            test_idat_deep_beam_gpu_prefilter_hits_are_validated_by_cpu,
        ),
        (
            "IDAT deep beam batch validation",
            test_idat_deep_beam_batch_validation_matches_spec_by_spec,
        ),
        (
            "IDAT deep beam GPU shard size",
            test_idat_deep_beam_gpu_shard_size_is_independent_from_checkpoint,
        ),
        (
            "IDAT deep beam worker pool",
            test_idat_deep_beam_creates_one_worker_pool_per_run,
        ),
        (
            "IDAT deep beam resume progress floor",
            test_idat_deep_beam_resume_keeps_committed_progress_floor,
        ),
        (
            "IDAT deep beam extends past soft max depth",
            test_idat_deep_beam_resume_extends_past_soft_max_depth,
        ),
        (
            "IDAT deep beam interrupt closes GPU",
            test_idat_deep_beam_keyboard_interrupt_closes_gpu_session,
        ),
        (
            "IDAT deep beam interrupt progress",
            test_idat_deep_beam_keyboard_interrupt_flushes_progress,
        ),
        (
            "IDAT deep beam CRC diagnostic score",
            test_idat_deep_beam_scores_crc_guided_diagnostic_without_promoting_to_best,
        ),
        (
            "IDAT dynamic Huffman bitshift repair",
            test_dynamic_huffman_bitshift_probe_repairs_extra_header_bit,
        ),
        (
            "IDAT stored block length repair",
            test_idat_stored_block_length_repair_fixes_len_nlen_pair,
        ),
        (
            "IDAT Kraft backref locator multi block",
            test_idat_kraft_backref_locator_continues_after_stored_block,
        ),
        (
            "IDAT Kraft invalid literal locator",
            test_idat_kraft_locator_finds_invalid_literal_after_stored_block,
        ),
        (
            "IDAT Kraft reserved block locator",
            test_idat_kraft_locator_finds_reserved_block_type_after_stored_block,
        ),
        (
            "IDAT deflate header dynamic phase",
            test_deflate_header_probe_runs_dynamic_huffman_phase_for_two_bit_corruption,
        ),
        (
            "IDAT deflate header bitshift phase",
            test_deflate_header_probe_runs_dynamic_huffman_bitshift_phase,
        ),
        (
            "IDAT deflate header probe no scanlines",
            test_deflate_header_probe_does_not_accept_header_only_progress_without_scanlines,
        ),
        ("IDAT deflate strategy queue repair", test_idat_deflate_strategy_queue_uses_material_progress_only),
        (
            "IDAT deflate strategy queue chase",
            test_idat_deflate_strategy_queue_chases_multiple_material_steps,
        ),
        (
            "IDAT deflate heavy probe repair",
            test_idat_deflate_heavy_probe_reports_progress_and_repairs_candidate,
        ),
        ("IDAT deflate byte probe no progress", test_idat_deflate_probe_ignores_candidates_without_progress),
        (
            "IDAT deflate strategy queue no progress",
            test_idat_deflate_strategy_queue_reports_no_candidate_without_progress,
        ),
        (
            "IDAT deflate byte probe ignores offset-only drift",
            test_idat_deflate_probe_does_not_treat_error_offset_drift_as_progress,
        ),
        (
            "IDAT deflate byte probe ignores bytes without scanlines",
            test_idat_deflate_probe_does_not_treat_decompressed_bytes_without_scanlines_as_progress,
        ),
        (
            "IDAT deflate byte probe accepts usable scanline",
            test_idat_deflate_probe_treats_new_usable_scanline_as_progress,
        ),
        ("IDAT stream bad zlib header", test_analyze_idat_stream_reports_bad_zlib_header),
        ("IDAT stream bad Adler", test_analyze_idat_stream_reports_bad_adler),
        ("IDAT stream trailing data", test_analyze_idat_stream_reports_trailing_data),
        ("SBB IDAT diagnostic blackfill gap", test_sbb_idat_diagnostic_reports_large_blackfill_gap),
        ("SBB IDAT diagnostic trusted target", test_sbb_idat_diagnostic_marks_trusted_small_crc_target_good),
        ("SBB IDAT fixtures CRC target", test_sbb_idat_fixtures_keep_original_crc_targets),
        ("IDAT stream incomplete", test_analyze_idat_stream_reports_incomplete_stream),
        ("IDAT stream unsupported interlace", test_analyze_idat_stream_reports_unsupported_interlace),
    ]

    print("Running IDAT tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"IDAT tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
