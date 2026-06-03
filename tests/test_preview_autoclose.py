#!/usr/bin/env python3
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Chunklate
from chunklate import messages

VALID_FIXTURE = ROOT / "schaik-javapng-samples" / "basn0g01.png"


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
    original_pause_state = (
        Chunklate.DIALOGUE_PAUSE_STATE.pending,
        Chunklate.DIALOGUE_PAUSE_STATE.paused_in_group,
        Chunklate.DIALOGUE_PAUSE_STATE.rendering_dialogue,
    )

    def fake_ask_question(_runtime, _id, _idhash, *, skipauto=False):
        return True

    try:
        Chunklate.ACTIVE_PREVIEW_IMAGE = preview
        Chunklate.question_runtime.ask_question = fake_ask_question
        Chunklate.DIALOGUE_PAUSE_STATE.pending = True
        Chunklate.DIALOGUE_PAUSE_STATE.paused_in_group = True
        Chunklate.DIALOGUE_PAUSE_STATE.rendering_dialogue = True

        assert Chunklate.Question("SuperMegaLineFeedForceOfDeath", "preview-close-test") is True
        assert preview.closed == 1
        assert Chunklate.ACTIVE_PREVIEW_IMAGE is None
        assert Chunklate.DIALOGUE_PAUSE_STATE.pending is False
        assert Chunklate.DIALOGUE_PAUSE_STATE.paused_in_group is False
        assert Chunklate.DIALOGUE_PAUSE_STATE.rendering_dialogue is False
    finally:
        Chunklate.ACTIVE_PREVIEW_IMAGE = original_preview
        Chunklate.question_runtime.ask_question = original_ask_question
        (
            Chunklate.DIALOGUE_PAUSE_STATE.pending,
            Chunklate.DIALOGUE_PAUSE_STATE.paused_in_group,
            Chunklate.DIALOGUE_PAUSE_STATE.rendering_dialogue,
        ) = original_pause_state


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


def test_preview_repair_image_saves_inside_preview_subfolder(tmp_path, monkeypatch):
    original = tmp_path / "01.png"
    original.write_bytes(VALID_FIXTURE.read_bytes())
    previous = (
        Chunklate.FILE_Origin,
        Chunklate.FILE_DIR,
        Chunklate.ACTIVE_PREVIEW_IMAGE,
    )

    monkeypatch.setattr(Chunklate, "PRINT", lambda message: None)
    monkeypatch.setattr(Chunklate, "Candy", lambda *args: "%s")

    try:
        Chunklate.FILE_Origin = str(original)
        Chunklate.FILE_DIR = str(tmp_path / "out")
        Chunklate.ACTIVE_PREVIEW_IMAGE = None

        result = Chunklate.Preview_Repair_Image(
            VALID_FIXTURE.read_bytes(),
            "preview/subfolder",
            show=False,
        )

        assert result is not None
        preview_path = Path(result.path)
        clone_folder = tmp_path / "out" / "Folder_01"
        assert preview_path.exists()
        assert preview_path.parent == clone_folder / Chunklate.PREVIEW_OUTPUT_FOLDER
        assert preview_path.name == "_Preview_preview_subfolder.png"
        assert not list(clone_folder.glob("_Preview_*.png"))
    finally:
        (
            Chunklate.FILE_Origin,
            Chunklate.FILE_DIR,
            Chunklate.ACTIVE_PREVIEW_IMAGE,
        ) = previous


def test_ultimate_linefeed_candidate_preview_times_out_and_closes(tmp_path, monkeypatch):
    original = tmp_path / "01.png"
    original.write_bytes(VALID_FIXTURE.read_bytes())
    sleeps = []

    class FakeOpenResult:
        success = True
        opener = "feh"
        error = None

        def __init__(self):
            self.closed = 0

        def close(self):
            self.closed += 1
            return True

    opened = []
    previous = (
        Chunklate.FILE_Origin,
        Chunklate.FILE_DIR,
        Chunklate.ULTIMATE_LINEFEED_PREVIEW_TIMEOUT,
        Chunklate.ULTIMATE_LINEFEED_SHOW_PREVIEWS,
        Chunklate.ACTIVE_PREVIEW_IMAGE,
    )

    monkeypatch.setattr(Chunklate.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(Chunklate, "PRINT", lambda message: None)
    monkeypatch.setattr(Chunklate, "Candy", lambda *args: "%s")
    monkeypatch.setattr(Chunklate.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(
        Chunklate.image_viewer,
        "open_image",
        lambda path: opened.append(FakeOpenResult()) or opened[-1],
    )

    try:
        Chunklate.FILE_Origin = str(original)
        Chunklate.FILE_DIR = str(tmp_path / "out")
        Chunklate.ULTIMATE_LINEFEED_PREVIEW_TIMEOUT = 1.5
        Chunklate.ULTIMATE_LINEFEED_SHOW_PREVIEWS = True
        Chunklate.ACTIVE_PREVIEW_IMAGE = None
        candidate = SimpleNamespace(
            data=VALID_FIXTURE.read_bytes(),
            after=SimpleNamespace(
                usable_scanlines=1,
                height=1,
                adler_status="adler_mismatch",
            ),
        )

        result = Chunklate.Ultimate_Linefeed_Candidate_Preview(candidate, 42, 100)

        assert result is opened[0]
        assert sleeps == [1.5]
        assert opened[0].closed == 1
        assert Chunklate.ACTIVE_PREVIEW_IMAGE is None
    finally:
        (
            Chunklate.FILE_Origin,
            Chunklate.FILE_DIR,
            Chunklate.ULTIMATE_LINEFEED_PREVIEW_TIMEOUT,
            Chunklate.ULTIMATE_LINEFEED_SHOW_PREVIEWS,
            Chunklate.ACTIVE_PREVIEW_IMAGE,
        ) = previous


def test_ultimate_linefeed_candidate_preview_saves_without_opening_by_default(tmp_path, monkeypatch):
    calls = []
    original = tmp_path / "01.png"
    original.write_bytes(VALID_FIXTURE.read_bytes())
    previous = (
        Chunklate.FILE_Origin,
        Chunklate.FILE_DIR,
        Chunklate.ULTIMATE_LINEFEED_PREVIEW_TIMEOUT,
        Chunklate.ULTIMATE_LINEFEED_SHOW_PREVIEWS,
        Chunklate.ACTIVE_PREVIEW_IMAGE,
    )

    monkeypatch.setattr(
        Chunklate,
        "print",
        lambda *args, **kwargs: calls.append(("print", args, kwargs)),
        raising=False,
    )
    monkeypatch.setattr(Chunklate, "Candy", lambda *args: "%s")
    monkeypatch.setattr(
        Chunklate.image_viewer,
        "open_image",
        lambda path: calls.append(("open", path)),
    )

    try:
        Chunklate.FILE_Origin = str(original)
        Chunklate.FILE_DIR = str(tmp_path / "out")
        Chunklate.ULTIMATE_LINEFEED_PREVIEW_TIMEOUT = 0
        Chunklate.ULTIMATE_LINEFEED_SHOW_PREVIEWS = False
        Chunklate.ACTIVE_PREVIEW_IMAGE = None
        candidate = SimpleNamespace(
            data=VALID_FIXTURE.read_bytes(),
            after=SimpleNamespace(
                usable_scanlines=1,
                height=1,
                adler_status="adler_mismatch",
            ),
        )

        result = Chunklate.Ultimate_Linefeed_Candidate_Preview(candidate, 42, 100)

        assert result is not None
        assert result.opened is False
        assert Path(result.path).exists()
        assert not any(call[0] == "open" for call in calls)
        assert any(call[0] == "print" for call in calls)
        assert Chunklate.ACTIVE_PREVIEW_IMAGE is None
    finally:
        (
            Chunklate.FILE_Origin,
            Chunklate.FILE_DIR,
            Chunklate.ULTIMATE_LINEFEED_PREVIEW_TIMEOUT,
            Chunklate.ULTIMATE_LINEFEED_SHOW_PREVIEWS,
            Chunklate.ACTIVE_PREVIEW_IMAGE,
        ) = previous


def test_current_display_image_path_uses_original_when_no_clone_exists(tmp_path):
    original = tmp_path / "01.png"
    original.write_bytes(VALID_FIXTURE.read_bytes())
    previous = (
        Chunklate.FILE_Origin,
        Chunklate.FILE_DIR,
        Chunklate.Sample,
        Chunklate.Sample_Name,
        Chunklate.SAVE_COUNT,
    )

    try:
        Chunklate.FILE_Origin = str(original)
        Chunklate.FILE_DIR = str(tmp_path / "out")
        Chunklate.Sample = str(original)
        Chunklate.Sample_Name = original.name
        Chunklate.SAVE_COUNT = 0

        assert Chunklate.Current_Display_Image_Path() == str(original)
    finally:
        (
            Chunklate.FILE_Origin,
            Chunklate.FILE_DIR,
            Chunklate.Sample,
            Chunklate.Sample_Name,
            Chunklate.SAVE_COUNT,
        ) = previous


def test_current_display_image_path_prefers_valid_clone_path(tmp_path):
    original = tmp_path / "01.png"
    original.write_bytes(VALID_FIXTURE.read_bytes())
    output_dir = tmp_path / "out"
    clone_dir = output_dir / "Folder_01"
    clone_dir.mkdir(parents=True)
    clone = clone_dir / original.name
    clone.write_bytes(VALID_FIXTURE.read_bytes())
    previous = (
        Chunklate.FILE_Origin,
        Chunklate.FILE_DIR,
        Chunklate.Sample,
        Chunklate.Sample_Name,
        Chunklate.SAVE_COUNT,
    )

    try:
        Chunklate.FILE_Origin = str(original)
        Chunklate.FILE_DIR = str(output_dir)
        Chunklate.Sample = str(original)
        Chunklate.Sample_Name = original.name
        Chunklate.SAVE_COUNT = 1

        assert Chunklate.Current_Display_Image_Path() == str(clone)
    finally:
        (
            Chunklate.FILE_Origin,
            Chunklate.FILE_DIR,
            Chunklate.Sample,
            Chunklate.Sample_Name,
            Chunklate.SAVE_COUNT,
        ) = previous


def test_current_display_image_path_ignores_stale_clone_without_new_save(tmp_path):
    original = tmp_path / "01.png"
    original.write_bytes(VALID_FIXTURE.read_bytes())
    output_dir = tmp_path / "out"
    clone_dir = output_dir / "Folder_01"
    clone_dir.mkdir(parents=True)
    stale_clone = clone_dir / original.name
    stale_clone.write_bytes(VALID_FIXTURE.read_bytes())
    previous = (
        Chunklate.FILE_Origin,
        Chunklate.FILE_DIR,
        Chunklate.Sample,
        Chunklate.Sample_Name,
        Chunklate.SAVE_COUNT,
    )

    try:
        Chunklate.FILE_Origin = str(original)
        Chunklate.FILE_DIR = str(output_dir)
        Chunklate.Sample = str(original)
        Chunklate.Sample_Name = original.name
        Chunklate.SAVE_COUNT = 0

        assert Chunklate.Current_Display_Image_Path() == str(original)
    finally:
        (
            Chunklate.FILE_Origin,
            Chunklate.FILE_DIR,
            Chunklate.Sample,
            Chunklate.Sample_Name,
            Chunklate.SAVE_COUNT,
        ) = previous


def test_open_current_final_image_opens_valid_original_once(tmp_path, monkeypatch):
    original = tmp_path / "01.png"
    original.write_bytes(VALID_FIXTURE.read_bytes())
    calls = []
    previous = (
        Chunklate.FILE_Origin,
        Chunklate.FILE_DIR,
        Chunklate.Sample,
        Chunklate.Sample_Name,
        Chunklate.SAVE_COUNT,
        Chunklate.FINAL_IMAGE_OPEN_REQUESTED,
        Chunklate.PandoraBox,
    )

    monkeypatch.setattr(Chunklate.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(Chunklate, "PRINT", lambda message: None)
    monkeypatch.setattr(
        Chunklate,
        "Candy",
        lambda *args: calls.append(("candy", args)) or "%s",
    )
    monkeypatch.setattr(
        Chunklate.image_viewer,
        "open_image",
        lambda path: calls.append(path)
        or SimpleNamespace(success=True, opener="feh", error=None),
    )

    try:
        Chunklate.FILE_Origin = str(original)
        Chunklate.FILE_DIR = str(tmp_path / "out")
        Chunklate.Sample = str(original)
        Chunklate.Sample_Name = original.name
        Chunklate.SAVE_COUNT = 0
        Chunklate.FINAL_IMAGE_OPEN_REQUESTED = False
        Chunklate.PandoraBox = {}

        assert Chunklate.Open_Current_Final_Image_If_Valid().success is True
        assert Chunklate.Open_Current_Final_Image_If_Valid() is None
        assert ("candy", ("Cowsay", "Wtf... why did you give that to me? It's perfect!", "good")) in calls
        assert str(original) in calls
    finally:
        (
            Chunklate.FILE_Origin,
            Chunklate.FILE_DIR,
            Chunklate.Sample,
            Chunklate.Sample_Name,
            Chunklate.SAVE_COUNT,
            Chunklate.FINAL_IMAGE_OPEN_REQUESTED,
            Chunklate.PandoraBox,
        ) = previous


def test_the_end_opens_valid_current_image_before_summary(tmp_path, monkeypatch):
    original = tmp_path / "01.png"
    original.write_bytes(VALID_FIXTURE.read_bytes())
    calls = []
    previous = (
        Chunklate.FILE_Origin,
        Chunklate.FILE_DIR,
        Chunklate.Sample,
        Chunklate.Sample_Name,
        Chunklate.SAVE_COUNT,
        Chunklate.FINAL_IMAGE_OPEN_REQUESTED,
        Chunklate.DEBUG,
        Chunklate.PAUSEDEBUG,
        Chunklate.PandoraBox,
        Chunklate.DIALOGUE_PAUSE_STATE.pending,
        Chunklate.DIALOGUE_PAUSE_STATE.paused_in_group,
        Chunklate.DIALOGUE_PAUSE_STATE.rendering_dialogue,
    )

    monkeypatch.setattr(Chunklate.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(Chunklate, "PRINT", lambda message: None)
    monkeypatch.setattr(
        Chunklate,
        "Candy",
        lambda *args: calls.append(("candy", args)) or "%s",
    )
    monkeypatch.setattr(Chunklate, "Summarise", lambda *args: calls.append(("summary", args)))
    monkeypatch.setattr(Chunklate, "Chunklate", lambda sec: calls.append(("banner", sec)))
    monkeypatch.setattr(
        Chunklate.sys,
        "exit",
        lambda code=0: (_ for _ in ()).throw(SystemExit(code)),
    )
    monkeypatch.setattr(
        Chunklate.image_viewer,
        "open_image",
        lambda path: calls.append(("open", path))
        or SimpleNamespace(success=True, opener="feh", error=None),
    )

    try:
        Chunklate.FILE_Origin = str(original)
        Chunklate.FILE_DIR = str(tmp_path / "out")
        Chunklate.Sample = str(original)
        Chunklate.Sample_Name = original.name
        Chunklate.SAVE_COUNT = 0
        Chunklate.FINAL_IMAGE_OPEN_REQUESTED = False
        Chunklate.DEBUG = False
        Chunklate.PAUSEDEBUG = False
        Chunklate.PandoraBox = {}
        Chunklate.DIALOGUE_PAUSE_STATE.pending = True
        Chunklate.DIALOGUE_PAUSE_STATE.paused_in_group = True
        Chunklate.DIALOGUE_PAUSE_STATE.rendering_dialogue = False

        try:
            Chunklate.TheEnd()
        except SystemExit as exc:
            assert exc.code == 0
        else:
            raise AssertionError("TheEnd should exit")

        assert (
            "candy",
            ("Cowsay", "Wtf... why did you give that to me? It's perfect!", "good"),
        ) in calls
        assert calls.index(("open", str(original))) < calls.index(("summary", (None, True)))
        assert ("summary", (None, True)) in calls
        assert calls.index(("summary", (None, True))) < calls.index(("banner", 0))
        assert calls[-1] == ("candy", ("Cowsay", "See you Space Cowboy...", "good"))
        assert Chunklate.DIALOGUE_PAUSE_STATE.pending is False
        assert Chunklate.DIALOGUE_PAUSE_STATE.paused_in_group is False
    finally:
        (
            Chunklate.FILE_Origin,
            Chunklate.FILE_DIR,
            Chunklate.Sample,
            Chunklate.Sample_Name,
            Chunklate.SAVE_COUNT,
            Chunklate.FINAL_IMAGE_OPEN_REQUESTED,
            Chunklate.DEBUG,
            Chunklate.PAUSEDEBUG,
            Chunklate.PandoraBox,
            Chunklate.DIALOGUE_PAUSE_STATE.pending,
            Chunklate.DIALOGUE_PAUSE_STATE.paused_in_group,
            Chunklate.DIALOGUE_PAUSE_STATE.rendering_dialogue,
        ) = previous


def test_the_end_keeps_final_image_closed_when_findings_remain(tmp_path, monkeypatch):
    original = tmp_path / "itxt_compression_flag.png"
    original.write_bytes(VALID_FIXTURE.read_bytes())
    calls = []
    previous = (
        Chunklate.FILE_Origin,
        Chunklate.FILE_DIR,
        Chunklate.Sample,
        Chunklate.Sample_Name,
        Chunklate.SAVE_COUNT,
        Chunklate.FINAL_IMAGE_OPEN_REQUESTED,
        Chunklate.DEBUG,
        Chunklate.PAUSEDEBUG,
        Chunklate.PandoraBox,
    )

    monkeypatch.setattr(Chunklate.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(Chunklate, "PRINT", lambda message: None)
    monkeypatch.setattr(
        Chunklate,
        "Candy",
        lambda *args: calls.append(("candy", args)) or "%s",
    )
    monkeypatch.setattr(Chunklate, "Summarise", lambda *args: calls.append(("summary", args)))
    monkeypatch.setattr(Chunklate, "Chunklate", lambda sec: calls.append(("banner", sec)))
    monkeypatch.setattr(
        Chunklate.sys,
        "exit",
        lambda code=0: (_ for _ in ()).throw(SystemExit(code)),
    )
    monkeypatch.setattr(
        Chunklate.image_viewer,
        "open_image",
        lambda path: calls.append(("open", path))
        or SimpleNamespace(success=True, opener="feh", error=None),
    )

    try:
        Chunklate.FILE_Origin = str(original)
        Chunklate.FILE_DIR = str(tmp_path / "out")
        Chunklate.Sample = str(original)
        Chunklate.Sample_Name = original.name
        Chunklate.SAVE_COUNT = 0
        Chunklate.FINAL_IMAGE_OPEN_REQUESTED = False
        Chunklate.DEBUG = False
        Chunklate.PAUSEDEBUG = False
        Chunklate.PandoraBox = {
            "GetInfo_Error_0:-iTXt Compression Flag must be 0 or 1": {},
        }

        try:
            Chunklate.TheEnd()
        except SystemExit as exc:
            assert exc.code == 0
        else:
            raise AssertionError("TheEnd should exit")

        assert not [call for call in calls if call[0] == "open"]
        assert (
            "candy",
            ("Cowsay", "Wtf... why did you give that to me? It's perfect!", "good"),
        ) not in calls
        assert (
            "candy",
            ("Cowsay", messages.UNIMPLEMENTED_REPAIR_ROUTE_MESSAGE, "bad"),
        ) not in calls
        assert ("summary", (None, True)) in calls
    finally:
        (
            Chunklate.FILE_Origin,
            Chunklate.FILE_DIR,
            Chunklate.Sample,
            Chunklate.Sample_Name,
            Chunklate.SAVE_COUNT,
            Chunklate.FINAL_IMAGE_OPEN_REQUESTED,
            Chunklate.DEBUG,
            Chunklate.PAUSEDEBUG,
            Chunklate.PandoraBox,
        ) = previous
