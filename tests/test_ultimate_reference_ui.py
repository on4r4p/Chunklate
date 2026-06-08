#!/usr/bin/env python3
import sys
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import ultimate_reference_ui
from chunklate import idat_bruteforce
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


def test_describe_reference_region_explains_same_position_pair():
    region = idat_bruteforce.UltimateReferenceRegion(
        candidate_region=(0.1, 0.2, 0.3, 0.4),
        reference_region=(0.1, 0.2, 0.3, 0.4),
        label="ROI 4",
        match_mode="paired",
    )

    message = ultimate_reference_ui.describe_reference_region(region, "candidate")

    assert "ROI 4" in message
    assert "paired ROI" in message
    assert "Same normalized position" in message


def test_describe_reference_region_explains_search_reference_pattern():
    region = idat_bruteforce.UltimateReferenceRegion(
        candidate_region=ultimate_reference_ui.FULL_REGION,
        reference_region=(0.1, 0.2, 0.3, 0.4),
        label="ROI 5",
        match_mode="search",
    )

    message = ultimate_reference_ui.describe_reference_region(region, "reference")

    assert "ROI 5" in message
    assert "search ROI" in message
    assert "reference pattern" in message
    assert "candidate" in message


def test_negative_roi_has_dedicated_outline_color():
    assert ultimate_reference_ui.ROI_NEGATIVE_OUTLINE != ultimate_reference_ui.ROI_CANDIDATE_OUTLINE
    assert ultimate_reference_ui.ROI_NEGATIVE_OUTLINE != ultimate_reference_ui.ROI_REFERENCE_OUTLINE


def test_point_in_bbox_detects_inside_area_not_only_border():
    bbox = (10.0, 20.0, 80.0, 90.0)

    assert ultimate_reference_ui.point_in_bbox((40.0, 50.0), bbox)
    assert ultimate_reference_ui.point_in_bbox((10.0, 20.0), bbox)
    assert not ultimate_reference_ui.point_in_bbox((9.0, 50.0), bbox)
    assert not ultimate_reference_ui.point_in_bbox((40.0, 91.0), bbox)


def test_has_unsaved_region_state_tracks_saved_regions_and_pending_rectangles():
    assert not ultimate_reference_ui.has_unsaved_region_state(0, None, None)
    assert ultimate_reference_ui.has_unsaved_region_state(1, None, None)
    assert ultimate_reference_ui.has_unsaved_region_state(0, (0.1, 0.1, 0.2, 0.2), None)
    assert ultimate_reference_ui.has_unsaved_region_state(0, None, (0.1, 0.1, 0.2, 0.2))


def test_reference_region_editor_reports_unavailable_images(tmp_path):
    result = ultimate_reference_ui.open_ultimate_reference_region_editor(
        str(tmp_path / "missing_source.png"),
        str(tmp_path / "missing_reference.png"),
        str(tmp_path / "_ULF.reference_regions.json"),
    )

    assert result.saved is False
    assert "reference region editor unavailable" in result.warning


def test_select_reference_png_path_uses_png_filter(tmp_path):
    calls = []

    class FakeFileDialog:
        @staticmethod
        def askopenfilename(**kwargs):
            calls.append(kwargs)
            return str(tmp_path / "reference.png")

    selected = ultimate_reference_ui._select_reference_png_path(
        FakeFileDialog,
        initial_path=str(tmp_path / "old.png"),
    )

    assert selected.endswith("reference.png")
    assert calls[0]["title"] == "Select reference PNG"
    assert ("PNG files", "*.png") in calls[0]["filetypes"]


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
