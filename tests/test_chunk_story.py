#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_story


def test_chunk_bytes_preserves_legacy_encoding():
    assert chunk_story.chunk_bytes(b"IHDR") == b"IHDR"
    assert chunk_story.chunk_bytes("PNG") == b"PNG"
    assert chunk_story.chunk_bytes(123) == b"123"


def test_add_records_legacy_index_and_encoded_chunk():
    history = []
    indexes = []

    assert chunk_story.add(history, indexes, "PNG", 2, 18, 8) is True

    assert history == [b"PNG"]
    assert indexes == ["-1:2:18:8"]


def test_add_skips_duplicate_start_end_length_marker():
    history = [b"PNG"]
    indexes = ["-1:2:18:8"]

    assert chunk_story.add(history, indexes, "IHDR", 2, 18, 8) is False

    assert history == [b"PNG"]
    assert indexes == ["-1:2:18:8"]


def test_delete_legacy_preserves_original_single_match_error():
    history = [b"IHDR"]
    indexes = ["-1:0:10:13"]

    try:
        chunk_story.delete_legacy(history, indexes, b"IHDR")
    except ValueError:
        pass
    else:
        raise AssertionError("single legacy delete should raise after deleting history")

    assert history == []
    assert indexes == ["-1:0:10:13"]


def test_delete_legacy_removes_history_and_matching_index_with_multiple_matches():
    history = [b"IDAT", b"IDAT"]
    indexes = ["-1:0:10:1", "0:10:20:1"]

    chunk_story.delete_legacy(history, indexes, b"IDAT")

    assert history == [b"IDAT"]
    assert indexes == ["0:10:20:1"]


def main():
    checks = [
        ("Chunk bytes", test_chunk_bytes_preserves_legacy_encoding),
        ("Add records index", test_add_records_legacy_index_and_encoded_chunk),
        ("Add skips duplicate marker", test_add_skips_duplicate_start_end_length_marker),
        ("Delete single match", test_delete_legacy_preserves_original_single_match_error),
        ("Delete multiple matches", test_delete_legacy_removes_history_and_matching_index_with_multiple_matches),
    ]

    print("Running chunk story tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk story tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
