#!/usr/bin/env python3
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import deflate_header


def dynamic_payload():
    return (b"hello world this is a long text with many words and punctuation " * 100)


def dynamic_stream():
    compressed = zlib.compress(dynamic_payload(), 1)
    analysis = deflate_header.analyze_deflate_header(compressed)
    assert analysis.status == "ok"
    assert analysis.btype == 2
    return compressed


def test_analyze_deflate_header_reports_dynamic_header():
    analysis = deflate_header.analyze_deflate_header(dynamic_stream())

    assert analysis.status == "ok"
    assert analysis.btype == 2
    assert analysis.hlit is not None
    assert analysis.hdist is not None
    assert analysis.hclen is not None
    assert analysis.header_end_bit is not None
    assert "dynamic Huffman header" in analysis.summary


def test_analyze_deflate_header_reports_bad_code_length_tree():
    compressed = bytearray(dynamic_stream())
    compressed[3] ^= 1 << 5

    analysis = deflate_header.analyze_deflate_header(bytes(compressed))

    assert analysis.status == "bad_code_length_tree"
    assert analysis.byte_offset >= 2
    assert analysis.context_hex
    assert "oversubscribed Huffman tree" in analysis.reason


def test_analyze_deflate_header_reports_invalid_huffman_lengths():
    compressed = bytearray(dynamic_stream())
    compressed[2] ^= 1 << 3

    analysis = deflate_header.analyze_deflate_header(bytes(compressed))

    assert analysis.status == "invalid_huffman_lengths"
    assert "tree" in analysis.reason


def test_analyze_deflate_header_reports_truncated_header():
    analysis = deflate_header.analyze_deflate_header(dynamic_stream()[:4])

    assert analysis.status == "truncated_header"
    assert analysis.context_hex


def test_analyze_deflate_header_accepts_fixed_or_stored_headers():
    fixed = deflate_header.analyze_deflate_header(zlib.compress(b"abc"))
    stored = deflate_header.analyze_deflate_header(zlib.compress(b"abc", 0))

    assert fixed.status == "ok"
    assert fixed.btype == 1
    assert stored.status == "ok"
    assert stored.btype == 0


def test_analyze_deflate_header_reports_bad_zlib_header():
    analysis = deflate_header.analyze_deflate_header(b"\x00\x00abc")

    assert analysis.status == "bad_zlib_header"
    assert analysis.reason == "bad zlib header"


def main():
    checks = [
        ("dynamic header", test_analyze_deflate_header_reports_dynamic_header),
        ("bad code length tree", test_analyze_deflate_header_reports_bad_code_length_tree),
        ("invalid Huffman lengths", test_analyze_deflate_header_reports_invalid_huffman_lengths),
        ("truncated header", test_analyze_deflate_header_reports_truncated_header),
        ("fixed/stored headers", test_analyze_deflate_header_accepts_fixed_or_stored_headers),
        ("bad zlib header", test_analyze_deflate_header_reports_bad_zlib_header),
    ]

    print("Running deflate header tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"Deflate header tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
