#!/usr/bin/env python3
import sys
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import ultimate_reference_ui
from chunklate.png import PNG_SIGNATURE, build_png_chunk


def _invalid_filter_png():
    ihdr = struct.pack("!IIBBBBB", 1, 2, 8, 2, 0, 0, 0)
    filtered = b"\x00abc" + bytes((217, 0, 0, 0))
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", zlib.compress(filtered))
        + build_png_chunk(b"IEND", b"")
    )


def test_normalize_display_bbox_clamps_and_sorts():
    region = ultimate_reference_ui.normalize_display_bbox(
        (120, -10, -20, 80),
        (100, 100),
    )

    assert region == (0.0, 0.0, 1.0, 0.8)


def test_normalize_canvas_bbox_to_image_clamps_selection_when_image_overlap_is_majority():
    region = ultimate_reference_ui.normalize_canvas_bbox_to_image(
        (0, 0, 100, 100),
        (25, 25, 125, 125),
    )

    assert region == (0.0, 0.0, 0.75, 0.75)


def test_normalize_canvas_bbox_to_image_rejects_selection_mostly_outside_image():
    region = ultimate_reference_ui.normalize_canvas_bbox_to_image(
        (0, 0, 100, 100),
        (80, 80, 180, 180),
    )

    assert region is None


def test_reference_region_editor_reports_unavailable_images(tmp_path):
    result = ultimate_reference_ui.open_ultimate_reference_region_editor(
        str(tmp_path / "missing_source.png"),
        str(tmp_path / "missing_reference.png"),
        str(tmp_path / "_ULF.reference_regions.json"),
    )

    assert result.saved is False
    assert "reference region editor unavailable" in result.warning


def test_load_image_uses_visual_preview_for_invalid_source_snapshot(tmp_path):
    source = _invalid_filter_png()
    source_path = tmp_path / "_ULF.Source.png"
    source_path.write_bytes(source)

    image, identity = ultimate_reference_ui._load_image(
        str(source_path),
        fallback_data=source,
    )

    assert image.size == (1, 2)
    assert identity == source
