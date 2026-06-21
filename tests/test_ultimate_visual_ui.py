#!/usr/bin/env python3
import json
import struct
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import ultimate_visual_ui
from chunklate.png import PNG_SIGNATURE, build_png_chunk, validate_png_structure


class FakeWidget:
    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        self.config_calls = []
        self.bindings = {}

    def pack(self, **kwargs):
        self.pack_call = kwargs

    def grid(self, **kwargs):
        self.grid_call = kwargs

    def config(self, **kwargs):
        self.config_calls.append(kwargs)
        self.kwargs.update(kwargs)

    configure = config

    def columnconfigure(self, *_args, **_kwargs):
        return None

    def rowconfigure(self, *_args, **_kwargs):
        return None

    def bind(self, event, callback):
        self.bindings[event] = callback


class FakeRoot(FakeWidget):
    def __init__(self, tkinter_module):
        super().__init__()
        self.tkinter_module = tkinter_module
        self.destroyed = False
        self.protocols = {}
        self.bind_all_calls = []

    def title(self, value):
        self.title_value = value

    def geometry(self, value):
        self.geometry_value = value

    def minsize(self, width, height):
        self.minsize_value = (width, height)

    def protocol(self, name, callback):
        self.protocols[name] = callback

    def bind_all(self, event, callback):
        self.bind_all_calls.append((event, callback))

    def after(self, _delay, _callback):
        return "after-id"

    def destroy(self):
        self.destroyed = True

    def mainloop(self):
        self.tkinter_module.run_script()


class FakeCanvas(FakeWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.items = []

    def winfo_width(self):
        return int(self.kwargs.get("width", 640) or 640)

    def winfo_height(self):
        return int(self.kwargs.get("height", 480) or 480)

    def delete(self, value):
        self.items.append(("delete", value))

    def create_image(self, *args, **kwargs):
        self.items.append(("image", args, kwargs))
        return len(self.items)


class FakeScrollbar(FakeWidget):
    def set(self, *_args):
        return None


class FakeListbox(FakeWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.items = []
        self.selection = ()

    def delete(self, *_args):
        self.items.clear()

    def insert(self, _index, value):
        self.items.append(value)

    def selection_set(self, index):
        self.selection = (int(index),)

    def see(self, _index):
        return None

    def curselection(self):
        return self.selection

    def yview(self, *_args):
        return None


class FakeButton(FakeWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.text = kwargs.get("text")
        self.command = kwargs.get("command")

    def invoke(self):
        if callable(self.command):
            return self.command()
        return None


class FakeTkinter:
    def __init__(self, script):
        self.script = tuple(script)
        self.buttons = {}
        self.listbox = None

    def Tk(self):
        self.root = FakeRoot(self)
        return self.root

    def Frame(self, parent=None, **kwargs):
        return FakeWidget(parent, **kwargs)

    def Label(self, parent=None, **kwargs):
        return FakeWidget(parent, **kwargs)

    def Canvas(self, parent=None, **kwargs):
        return FakeCanvas(parent, **kwargs)

    def Scrollbar(self, parent=None, **kwargs):
        return FakeScrollbar(parent, **kwargs)

    def Listbox(self, parent=None, **kwargs):
        self.listbox = FakeListbox(parent, **kwargs)
        return self.listbox

    def Button(self, parent=None, **kwargs):
        button = FakeButton(parent, **kwargs)
        self.buttons[button.text] = button
        return button

    def run_script(self):
        for action in self.script:
            if isinstance(action, tuple) and action[0] == "select":
                self.listbox.selection = (int(action[1]),)
                callback = self.listbox.bindings.get("<<ListboxSelect>>")
                if callback is not None:
                    callback(None)
                continue
            self.buttons[action].invoke()


class FakeImageTk:
    class PhotoImage:
        def __init__(self, image=None):
            self.image = image


class FakeMessagebox:
    def __init__(self, answer=None):
        self.answer = answer
        self.calls = []

    def askyesnocancel(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.answer


def tiny_png(color=b"\x80\x20\x20"):
    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    filtered = b"\x00" + color
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", zlib.compress(filtered))
        + build_png_chunk(b"IEND", b"")
    )


def write_gallery(tmp_path, count=4):
    preview_dir = tmp_path / "Bruteforce_Previews" / "VisualCandidates"
    preview_dir.mkdir(parents=True)
    candidates = []
    for index in range(1, count + 1):
        preview = preview_dir / ("_VisualCandidate_%03d.png" % index)
        preview.write_bytes(tiny_png(bytes((index, 20, 30))))
        candidates.append(
            {
                "preview_path": "Bruteforce_Previews/VisualCandidates/%s" % preview.name,
                "visual_score": float(index),
                "coverage": 1.0 - index * 0.01,
                "tested_candidates": index * 10,
                "state_id": index,
                "visual_hash": "vh%s" % index,
                "operation_hash": "oh%s" % index,
            }
        )
    gallery = tmp_path / "_ULF.visual.json"
    gallery.write_text(
        json.dumps(
            {
                "version": 1,
                "preview_directory": "Bruteforce_Previews/VisualCandidates",
                "candidates": candidates,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return gallery


def test_load_ultimate_visual_candidate_entries_resolves_relative_paths(tmp_path):
    gallery = write_gallery(tmp_path, count=2)

    entries = ultimate_visual_ui.load_ultimate_visual_candidate_entries(str(gallery))

    assert len(entries) == 2
    assert Path(entries[0].preview_path).is_absolute()
    assert entries[0].label.startswith("001")
    assert entries[0].visual_score == 1.0
    assert entries[0].tested_candidates == 10


def test_ultimate_visual_selector_noninteractive_writes_top_three_final_previews(tmp_path):
    gallery = write_gallery(tmp_path, count=4)

    result = ultimate_visual_ui.open_ultimate_visual_candidate_selector(
        str(gallery),
        interactive=False,
    )

    assert result.defaulted is True
    assert len(result.selected_preview_paths) == 3
    assert len(result.final_preview_paths) == 3
    assert Path(result.final_preview_dir).name == "Final_Previews"
    for path in result.final_preview_paths:
        assert validate_png_structure(Path(path).read_bytes()).ok
    record = json.loads((tmp_path / "_ULF.final_previews.json").read_text(encoding="utf-8"))
    assert record["selected_count"] == 3
    assert record["candidates"][0]["visual_hash"] == "vh1"


def test_ultimate_visual_selector_noninteractive_does_not_keep_searching(tmp_path):
    gallery = write_gallery(tmp_path, count=4)

    result = ultimate_visual_ui.open_ultimate_visual_candidate_selector(
        str(gallery),
        interactive=False,
        allow_keep_searching=True,
    )

    assert result.defaulted is True
    assert result.decision == "undecided"
    assert len(result.final_preview_paths) == 3


def test_write_ultimate_final_previews_removes_stale_files(tmp_path):
    gallery = write_gallery(tmp_path, count=1)
    entries = ultimate_visual_ui.load_ultimate_visual_candidate_entries(str(gallery))
    final_dir = tmp_path / "Bruteforce_Previews" / "Final_Previews"
    final_dir.mkdir(parents=True)
    stale = final_dir / "_FinalPreview_999_stale.png"
    stale.write_bytes(b"stale")

    result = ultimate_visual_ui.write_ultimate_final_previews(str(gallery), entries)

    assert not stale.exists()
    assert len(result.final_preview_paths) == 1
    assert validate_png_structure(Path(result.final_preview_paths[0]).read_bytes()).ok


def test_write_ultimate_final_previews_records_decision(tmp_path):
    gallery = write_gallery(tmp_path, count=1)
    entries = ultimate_visual_ui.load_ultimate_visual_candidate_entries(str(gallery))

    result = ultimate_visual_ui.write_ultimate_final_previews(
        str(gallery),
        entries,
        decision="perfect",
    )

    record = json.loads((tmp_path / "_ULF.final_previews.json").read_text(encoding="utf-8"))
    assert result.decision == "perfect"
    assert record["decision"] == "perfect"


def test_ultimate_visual_selector_keep_searching_button_writes_no_final_previews(tmp_path):
    gallery = write_gallery(tmp_path, count=4)
    fake_tkinter = FakeTkinter(("Keep searching",))

    result = ultimate_visual_ui.open_ultimate_visual_candidate_selector(
        str(gallery),
        allow_keep_searching=True,
        tkinter_module=fake_tkinter,
        image_tk_module=FakeImageTk,
    )

    assert result.defaulted is False
    assert result.decision == "keep_searching"
    assert result.selected_preview_paths == ()
    assert result.final_preview_paths == ()
    assert "GroundHogDay from selection" not in fake_tkinter.buttons
    assert not (tmp_path / "_ULF.final_previews.json").exists()


def test_ultimate_visual_selector_use_selected_preview_writes_guidance_choice(tmp_path):
    gallery = write_gallery(tmp_path, count=4)
    fake_tkinter = FakeTkinter(("Add this one to best candidates", "Use selected preview"))

    result = ultimate_visual_ui.open_ultimate_visual_candidate_selector(
        str(gallery),
        allow_keep_searching=True,
        tkinter_module=fake_tkinter,
        image_tk_module=FakeImageTk,
    )

    assert result.defaulted is False
    assert result.decision == "visual_guidance"
    assert len(result.selected_preview_paths) == 1
    assert len(result.final_preview_paths) == 1
    assert "GroundHogDay from selection" not in fake_tkinter.buttons
    assert "Accept this as final repair" in fake_tkinter.buttons
    record = json.loads((tmp_path / "_ULF.final_previews.json").read_text(encoding="utf-8"))
    assert record["decision"] == "visual_guidance"
    assert record["selected_count"] == 1


def test_ultimate_visual_selector_accept_final_repair_writes_perfect_choice(tmp_path):
    gallery = write_gallery(tmp_path, count=4)
    fake_tkinter = FakeTkinter(("Add this one to best candidates", "Accept this as final repair"))

    result = ultimate_visual_ui.open_ultimate_visual_candidate_selector(
        str(gallery),
        allow_keep_searching=True,
        tkinter_module=fake_tkinter,
        image_tk_module=FakeImageTk,
    )

    assert result.defaulted is False
    assert result.decision == "perfect"
    assert len(result.selected_preview_paths) == 1
    assert len(result.final_preview_paths) == 1
    record = json.loads((tmp_path / "_ULF.final_previews.json").read_text(encoding="utf-8"))
    assert record["decision"] == "perfect"
    assert record["selected_count"] == 1


def test_ultimate_visual_selector_no_keeps_final_previews_only(tmp_path):
    gallery = write_gallery(tmp_path, count=4)
    fake_tkinter = FakeTkinter(
        (
            "Add this one to best candidates",
            "Remove this one from best candidates",
            "Finish",
        )
    )
    fake_messagebox = FakeMessagebox(answer=False)

    result = ultimate_visual_ui.open_ultimate_visual_candidate_selector(
        str(gallery),
        tkinter_module=fake_tkinter,
        image_tk_module=FakeImageTk,
        messagebox_module=fake_messagebox,
    )

    assert result.defaulted is True
    assert result.decision == "undecided"
    assert len(result.final_preview_paths) == 3
    assert fake_messagebox.calls
    record = json.loads((tmp_path / "_ULF.final_previews.json").read_text(encoding="utf-8"))
    assert record["selected_count"] == 3
    assert record["decision"] == "undecided"
