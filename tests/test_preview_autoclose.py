#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Chunklate


class FakePreview:
    def __init__(self):
        self.closed = 0

    def close(self):
        self.closed += 1
        return True


def test_question_closes_active_preview_after_answer():
    preview = FakePreview()
    original_preview = Chunklate.ACTIVE_PREVIEW_IMAGE
    original_ask_question = Chunklate.question_runtime.ask_question

    def fake_ask_question(_runtime, _id, _idhash, *, skipauto=False):
        return True

    try:
        Chunklate.ACTIVE_PREVIEW_IMAGE = preview
        Chunklate.question_runtime.ask_question = fake_ask_question

        assert Chunklate.Question("LineFeed Heavy Probe", "preview-close-test") is True
        assert preview.closed == 1
        assert Chunklate.ACTIVE_PREVIEW_IMAGE is None
    finally:
        Chunklate.ACTIVE_PREVIEW_IMAGE = original_preview
        Chunklate.question_runtime.ask_question = original_ask_question


def test_open_final_image_skips_structurally_invalid_png(tmp_path, monkeypatch):
    invalid = tmp_path / "invalid.png"
    invalid.write_bytes(b"not a png")
    calls = []

    monkeypatch.setattr(Chunklate.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(
        Chunklate.image_viewer,
        "open_image",
        lambda path: calls.append(path),
    )

    assert Chunklate.Open_Final_Image(str(invalid)) is None
    assert calls == []


def test_preview_repair_image_skips_structurally_invalid_png(monkeypatch):
    calls = []

    monkeypatch.setattr(Chunklate.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(
        Chunklate.image_viewer,
        "open_image",
        lambda path: calls.append(path),
    )

    assert Chunklate.Preview_Repair_Image(b"not a png", "invalid-preview") is None
    assert calls == []
