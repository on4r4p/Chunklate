#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import palette
from chunklate import palette_ui


class FakeSlider:
    def __init__(self):
        self.var = self
        self.value = None
        self.swatch = FakeSwatch()

    def set(self, value):
        self.value = value


class FakeSwatch:
    def __init__(self):
        self.config_calls = []

    def config(self, **kwargs):
        self.config_calls.append(kwargs)


class FakeNumpy:
    uint8 = "uint8"

    def __init__(self):
        self.frombuffer_call = None

    def frombuffer(self, payload, dtype):
        self.frombuffer_call = (payload, dtype)
        return "numpy-buffer"


class FakeCv2:
    def __init__(self):
        self.imdecode_call = None

    def imdecode(self, payload, flags):
        self.imdecode_call = (payload, flags)
        return "decoded-image"


class FakePillowImage:
    def __init__(self, source):
        self.source = source
        self.resize_call = None

    def resize(self, dimensions, resampling):
        self.resize_call = (dimensions, resampling)
        return "resized-preview"

    def load(self):
        return None


class FakeImageModule:
    class Resampling:
        LANCZOS = "lanczos"

    def __init__(self):
        self.last_image = None

    def fromarray(self, payload):
        self.last_image = FakePillowImage(payload)
        return self.last_image

    def open(self, payload):
        self.last_image = FakePillowImage(payload.read())
        return self.last_image


class FakeImageTk:
    class PhotoImage:
        def __init__(self, image):
            self.image = image


class FakeLabel:
    def __init__(self, parent, image=None, **kwargs):
        self.parent = parent
        self.image = image
        self.kwargs = kwargs
        self.grid_call = None
        self.config_calls = []

    def grid(self, **kwargs):
        self.grid_call = kwargs

    def config(self, **kwargs):
        self.config_calls.append(kwargs)


class FakeIntVar:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


class FakeScale:
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        self.grid_call = None
        self.configure_calls = []

    def grid(self, **kwargs):
        self.grid_call = kwargs

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)


class FakeFrame:
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        self.grid_call = None
        self.columnconfigure_calls = []
        self.rowconfigure_calls = []
        self.bind_calls = []
        self.destroy_called = False

    def grid(self, **kwargs):
        self.grid_call = kwargs

    def bind(self, *args):
        self.bind_calls.append(args)

    def columnconfigure(self, *args, **kwargs):
        self.columnconfigure_calls.append((args, kwargs))

    def rowconfigure(self, *args, **kwargs):
        self.rowconfigure_calls.append((args, kwargs))

    def destroy(self):
        self.destroy_called = True


class FakeCanvas:
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        self.grid_call = None
        self.create_window_call = None
        self.create_window_result = "window-id"
        self.config_call = None
        self.configure_call = None
        self.itemconfigure_call = None
        self.bind_calls = []
        self.bbox_call = None
        self.bbox_result = (0, 0, 10, 20)
        self.width = kwargs.get("width", 0)
        self.update_idletasks_called = False
        self.focus_set_called = False
        self.yview_scroll_calls = []

    def grid(self, **kwargs):
        self.grid_call = kwargs

    def create_window(self, *args, **kwargs):
        self.create_window_call = (args, kwargs)
        return self.create_window_result

    def config(self, **kwargs):
        self.config_call = kwargs

    def configure(self, **kwargs):
        self.configure_call = kwargs

    def itemconfigure(self, *args, **kwargs):
        self.itemconfigure_call = (args, kwargs)

    def bind(self, *args):
        self.bind_calls.append(args)

    def bbox(self, *args):
        self.bbox_call = args
        return self.bbox_result

    def winfo_width(self):
        return self.width

    def update_idletasks(self):
        self.update_idletasks_called = True

    def focus_set(self):
        self.focus_set_called = True

    def yview(self, *args):
        return args

    def yview_scroll(self, *args):
        self.yview_scroll_calls.append(args)


class FakeScrollbar:
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        self.config_call = None
        self.grid_call = None

    def config(self, **kwargs):
        self.config_call = kwargs

    def grid(self, **kwargs):
        self.grid_call = kwargs

    def set(self, *args):
        return args


class FakeButton:
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        self.grid_call = None

    def grid(self, **kwargs):
        self.grid_call = kwargs


class FakeWindow:
    def __init__(self):
        self.title_call = None
        self.config_call = None
        self.resizable_call = None
        self.geometry_call = None
        self.update_idletasks_called = False

    def title(self, value):
        self.title_call = value

    def config(self, **kwargs):
        self.config_call = kwargs

    def resizable(self, *args):
        self.resizable_call = args

    def winfo_screenwidth(self):
        return 1920

    def winfo_screenheight(self):
        return 1080

    def update_idletasks(self):
        self.update_idletasks_called = True

    def geometry(self, value):
        self.geometry_call = value


class FakeTkinter:
    def __init__(self):
        self.last_window = None
        self.last_label = None
        self.last_int_var = None
        self.last_scale = None
        self.last_frame = None
        self.last_canvas = None
        self.last_scrollbar = None
        self.buttons = []
        self.frames = []

    def Tk(self):
        self.last_window = FakeWindow()
        return self.last_window

    def Label(self, parent, image=None, **kwargs):
        self.last_label = FakeLabel(parent, image, **kwargs)
        return self.last_label

    def IntVar(self):
        self.last_int_var = FakeIntVar()
        return self.last_int_var

    def Scale(self, parent, **kwargs):
        self.last_scale = FakeScale(parent, **kwargs)
        return self.last_scale

    def Frame(self, parent, **kwargs):
        self.last_frame = FakeFrame(parent, **kwargs)
        self.frames.append(self.last_frame)
        return self.last_frame

    def Canvas(self, parent, **kwargs):
        self.last_canvas = FakeCanvas(parent, **kwargs)
        return self.last_canvas

    def Scrollbar(self, parent, **kwargs):
        self.last_scrollbar = FakeScrollbar(parent, **kwargs)
        return self.last_scrollbar

    def Button(self, parent, **kwargs):
        button = FakeButton(parent, **kwargs)
        self.buttons.append(button)
        return button


def test_preview_dimensions_preserve_legacy_padding():
    assert palette_ui.preview_dimensions(120, 90) == (110, 80)


def test_create_palette_editor_state_initializes_values_and_wanabyte():
    state = palette_ui.create_palette_editor_state(3, b"png")

    assert state.values == ["empty", "empty", "empty"]
    assert state.sliders == []
    assert state.wanabyte == b"png"


def test_update_palette_state_value_rebuilds_wanabyte():
    state = palette_ui.create_palette_editor_state(2, b"old")

    wanabyte = palette_ui.update_palette_state_value(
        state,
        index=0,
        raw_value="1",
        before=b"before",
        after=b"after",
    )

    assert state.values == ["1", "empty"]
    assert wanabyte == palette.build_palette_png(b"before", state.values, b"after")
    assert state.wanabyte == wanabyte


def test_apply_palette_state_colors_updates_sliders_and_wanabyte():
    state = palette_ui.create_palette_editor_state(2, b"old")
    state.sliders = [FakeSlider(), FakeSlider()]

    wanabyte = palette_ui.apply_palette_state_colors(
        state,
        colors=["000001", "0000ff"],
        before=b"before",
        after=b"after",
    )

    assert state.values == [1, 255]
    assert [slider.value for slider in state.sliders] == [1, 255]
    assert [slider.swatch.config_calls for slider in state.sliders] == [
        [{"bg": "#000001"}],
        [{"bg": "#0000ff"}],
    ]
    assert wanabyte == palette.build_palette_png(b"before", state.values, b"after")
    assert state.wanabyte == wanabyte


def test_randomize_palette_state_uses_injected_random_source():
    state = palette_ui.create_palette_editor_state(2, b"old")
    state.sliders = [FakeSlider(), FakeSlider()]
    generated = iter([7, 9])

    wanabyte = palette_ui.randomize_palette_state(
        state,
        random_int=lambda start, end: next(generated),
        before=b"before",
        after=b"after",
    )

    assert state.values == [7, 9]
    assert [slider.value for slider in state.sliders] == [7, 9]
    assert [slider.swatch.config_calls for slider in state.sliders] == [
        [{"bg": "#000007"}],
        [{"bg": "#000009"}],
    ]
    assert wanabyte == palette.build_palette_png(b"before", state.values, b"after")
    assert state.wanabyte == wanabyte


def test_set_palette_state_sliders_preserves_slider_list_reference():
    state = palette_ui.create_palette_editor_state(2, b"png")
    sliders = [FakeSlider(), FakeSlider()]

    palette_ui.set_palette_state_sliders(state, sliders)

    assert state.sliders is sliders


def test_build_editor_layout_preserves_legacy_geometry():
    layout = palette_ui.build_editor_layout(2100, (100, 50))

    assert layout.basewidth == 1000
    assert layout.hsize == 500
    assert layout.action_width == 2000
    assert layout.action_height == 50
    assert layout.canvas_width == 985
    assert layout.slider_length == 970


def test_build_editor_layout_caps_square_preview_to_screen_height():
    layout = palette_ui.build_editor_layout(1920, (32, 32), 1080)

    assert layout.basewidth == 865
    assert layout.hsize == 865
    assert layout.action_width == 1730
    assert layout.action_height == 86
    assert layout.canvas_width == 850
    assert layout.slider_length == 835


def test_center_palette_editor_window_uses_screen_center():
    window = FakeWindow()
    layout = palette_ui.PaletteEditorLayout(
        basewidth=865,
        hsize=865,
        action_width=1730,
        action_height=86,
        canvas_width=850,
        slider_length=835,
    )

    geometry = palette_ui.center_palette_editor_window(window, layout)

    assert geometry == "1770x971+75+54"
    assert window.geometry_call == "1770x971+75+54"
    assert window.update_idletasks_called is True


def test_create_palette_editor_window_preserves_legacy_window_setup():
    fake_tkinter = FakeTkinter()

    window = palette_ui.create_palette_editor_window(
        tkinter_module=fake_tkinter,
        title="PLTE Editor:sample.png",
    )

    assert window is fake_tkinter.last_window
    assert window.title_call == "PLTE Editor:sample.png"
    assert window.config_call == {"bg": "skyblue"}
    assert window.resizable_call == (False, False)


def test_create_palette_editor_frames_preserves_legacy_frame_wiring():
    fake_tkinter = FakeTkinter()
    layout = palette_ui.PaletteEditorLayout(
        basewidth=1000,
        hsize=500,
        action_width=2000,
        action_height=50,
        canvas_width=985,
        slider_length=970,
    )

    frames = palette_ui.create_palette_editor_frames(
        tkinter_module=fake_tkinter,
        window="window",
        layout=layout,
    )

    assert frames.img is fake_tkinter.frames[0]
    assert frames.slider is fake_tkinter.frames[1]
    assert frames.action is fake_tkinter.frames[2]

    assert frames.img.parent == "window"
    assert frames.img.kwargs == {"width": 1000, "height": 500}
    assert frames.img.grid_call == {"row": 0, "column": 0, "padx": 10, "pady": 5}
    assert frames.img.columnconfigure_calls == [((0,), {"weight": 1})]
    assert frames.img.rowconfigure_calls == [((0,), {"weight": 1})]

    assert frames.slider.parent == "window"
    assert frames.slider.kwargs == {"width": 1000, "height": 500, "bg": "green"}
    assert frames.slider.grid_call == {"row": 0, "column": 1, "padx": 10, "pady": 5}
    assert frames.slider.columnconfigure_calls == [((0,), {"weight": 1})]
    assert frames.slider.rowconfigure_calls == [((0,), {"weight": 1})]

    assert frames.action.parent == "window"
    assert frames.action.kwargs == {"width": 2000, "height": 50, "bg": "orange"}
    assert frames.action.grid_call == {
        "row": 1,
        "column": 0,
        "columnspan": 2,
        "padx": 10,
        "pady": 5,
        "sticky": "ew",
    }
    assert frames.action.columnconfigure_calls == [((0,), {"weight": 1})]
    assert frames.action.rowconfigure_calls == [((0,), {"weight": 1})]


def test_render_preview_label_uses_injected_ui_modules():
    fake_numpy = FakeNumpy()
    fake_cv2 = FakeCv2()
    fake_image = FakeImageModule()
    fake_tkinter = FakeTkinter()

    im, pil_image, tk_image = palette_ui.render_preview_label(
        b"png-bytes",
        "frame",
        120,
        90,
        cv2_module=fake_cv2,
        numpy_module=fake_numpy,
        image_module=fake_image,
        image_tk_module=FakeImageTk,
        tkinter_module=fake_tkinter,
    )

    assert fake_numpy.frombuffer_call == (b"png-bytes", "uint8")
    assert fake_cv2.imdecode_call == ("numpy-buffer", -1)
    assert im == "decoded-image"
    assert pil_image.source == "decoded-image"
    assert pil_image.resize_call == ((110, 80), "lanczos")
    assert tk_image.image == "resized-preview"
    assert fake_tkinter.last_label.parent == "frame"
    assert fake_tkinter.last_label.image is tk_image
    assert fake_tkinter.last_label.grid_call == {"row": 1, "column": 0, "padx": 5, "pady": 5}


def test_render_preview_label_falls_back_to_pillow_without_cv2():
    fake_image = FakeImageModule()
    fake_tkinter = FakeTkinter()

    im, pil_image, tk_image = palette_ui.render_preview_label(
        b"png-bytes",
        "frame",
        120,
        90,
        cv2_module=None,
        numpy_module=None,
        image_module=fake_image,
        image_tk_module=FakeImageTk,
        tkinter_module=fake_tkinter,
    )

    assert im is None
    assert pil_image.source == b"png-bytes"
    assert pil_image.resize_call == ((110, 80), "lanczos")
    assert tk_image.image == "resized-preview"
    assert fake_tkinter.last_label.parent == "frame"
    assert fake_tkinter.last_label.image is tk_image


def test_create_palette_scale_uses_injected_tkinter_module():
    fake_tkinter = FakeTkinter()
    callback_calls = []

    widget = palette_ui.create_palette_scale(
        tkinter_module=fake_tkinter,
        master="frame",
        label="Palette 1",
        value=42,
        from_=-1,
        to=16777215,
        length=970,
        command=lambda value: callback_calls.append(value),
        grid_options={"padx": 10, "pady": 5},
    )

    assert widget.var is fake_tkinter.last_int_var
    assert widget.scale is fake_tkinter.last_scale
    assert widget.swatch is fake_tkinter.last_label
    assert widget.container is fake_tkinter.frames[-1]
    assert widget.var.value == 42
    assert widget.container.parent == "frame"
    assert widget.container.kwargs == {}
    assert widget.container.grid_call == {"padx": 10, "pady": 5}
    assert widget.container.columnconfigure_calls == [((1,), {"weight": 1})]
    assert widget.swatch.parent is widget.container
    assert widget.swatch.kwargs == {
        "bg": "#00002a",
        "width": 4,
        "height": 2,
        "relief": "solid",
        "borderwidth": 1,
    }
    assert widget.swatch.grid_call == {
        "row": 0,
        "column": 0,
        "padx": (0, 8),
        "pady": 0,
        "sticky": "ns",
    }
    assert widget.scale.parent is widget.container
    assert widget.scale.kwargs == {
        "label": "Palette 1",
        "variable": widget.var,
        "from_": -1,
        "to": 16777215,
        "length": 970,
        "command": widget.scale.kwargs["command"],
        "orient": "horizontal",
    }
    widget.scale.kwargs["command"](255)
    assert widget.swatch.config_calls == [{"bg": "#0000ff"}]
    assert callback_calls == [255]
    assert widget.scale.grid_call == {"row": 0, "column": 1, "sticky": "ew"}


def test_create_palette_slider_canvas_wires_canvas_frame_and_scrollbar():
    fake_tkinter = FakeTkinter()

    widgets = palette_ui.create_palette_slider_canvas(
        tkinter_module=fake_tkinter,
        master="slider-frame",
        height=500,
        width=985,
        canvas_grid_options={"row": 0, "column": 1, "padx": 10, "pady": 5},
        scrollbar_grid_options={"row": 0, "column": 0, "sticky": "ns"},
    )

    assert widgets.canvas is fake_tkinter.last_canvas
    assert widgets.frame is fake_tkinter.last_frame
    assert widgets.scrollbar is fake_tkinter.last_scrollbar
    assert widgets.canvas.parent == "slider-frame"
    assert widgets.canvas.kwargs == {"height": 500, "width": 985}
    assert widgets.canvas.grid_call == {"row": 0, "column": 1, "padx": 10, "pady": 5}
    assert widgets.frame.parent is widgets.canvas
    assert widgets.frame.kwargs == {"bg": "#EBEBEB"}
    assert widgets.window_id == "window-id"
    assert widgets.canvas.create_window_call == (
        (0, 0),
        {"window": widgets.frame, "anchor": "nw", "width": 985},
    )
    assert widgets.scrollbar.parent == "slider-frame"
    assert widgets.scrollbar.kwargs == {"orient": "vertical"}
    assert widgets.scrollbar.config_call["command"].__self__ is widgets.canvas
    assert widgets.canvas.config_call == {"yscrollcommand": widgets.scrollbar.set}
    assert widgets.scrollbar.grid_call == {"row": 0, "column": 0, "sticky": "ns"}


def test_bind_palette_slider_scrollregion_refreshes_canvas_on_layout_changes():
    fake_tkinter = FakeTkinter()
    widgets = palette_ui.create_palette_slider_canvas(
        tkinter_module=fake_tkinter,
        master="slider-frame",
        height=500,
        width=985,
    )
    slider = FakeSlider()
    slider.s = FakeScale("scale-parent")

    callback = palette_ui.bind_palette_slider_scrollregion(widgets, [slider])
    callback()

    assert widgets.frame.bind_calls == [("<Configure>", callback)]
    assert widgets.canvas.bind_calls == [("<Configure>", callback)]
    assert widgets.canvas.update_idletasks_called is True
    assert widgets.canvas.itemconfigure_call == (("window-id",), {"width": 985})
    assert slider.s.configure_calls == [{"length": 845}]
    assert widgets.canvas.bbox_call == ("all",)
    assert widgets.canvas.configure_call == {"scrollregion": (0, 0, 10, 20)}


def test_bind_palette_slider_mousewheel_scrolls_when_pointer_is_over_controls():
    fake_tkinter = FakeTkinter()
    widgets = palette_ui.create_palette_slider_canvas(
        tkinter_module=fake_tkinter,
        master="slider-frame",
        height=500,
        width=985,
    )
    slider = FakeSlider()
    slider.container = FakeFrame("frame")
    slider.s = FakeScale("scale-parent")
    slider.s.bind_calls = []
    slider.s.bind = lambda *args: slider.s.bind_calls.append(args)

    scroll_callback = palette_ui.bind_palette_slider_mousewheel(widgets, [slider])

    enter_callback = next(call[1] for call in widgets.canvas.bind_calls if call[0] == "<Enter>")
    enter_callback(None)
    assert widgets.canvas.focus_set_called is True

    class WheelEvent:
        delta = -120
        num = None

    assert scroll_callback(WheelEvent()) == "break"
    assert widgets.canvas.yview_scroll_calls == [(1, "units")]

    class ButtonEvent:
        delta = 0
        num = 4

    scroll_callback(ButtonEvent())
    assert widgets.canvas.yview_scroll_calls[-1] == (-1, "units")
    assert any(call[0] == "<MouseWheel>" for call in slider.container.bind_calls)
    assert any(call[0] == "<Button-5>" for call in slider.s.bind_calls)


def test_create_palette_action_buttons_uses_specs_and_grid_options():
    fake_tkinter = FakeTkinter()
    callbacks = {"web": object(), "save": object()}

    buttons = palette_ui.create_palette_action_buttons(
        tkinter_module=fake_tkinter,
        master="action-frame",
        specs=(
            palette_ui.PaletteActionButtonSpec("web", "Web Safe Color", callbacks["web"], 0, 0),
            palette_ui.PaletteActionButtonSpec("save", "Save", callbacks["save"], 1, 2),
        ),
        grid_options={"padx": 10, "pady": 5},
    )

    assert buttons == {"web": fake_tkinter.buttons[0], "save": fake_tkinter.buttons[1]}
    assert fake_tkinter.buttons[0].parent == "action-frame"
    assert fake_tkinter.buttons[0].kwargs == {"text": "Web Safe Color", "command": callbacks["web"]}
    assert fake_tkinter.buttons[0].grid_call == {"row": 0, "column": 0, "padx": 10, "pady": 5}
    assert fake_tkinter.buttons[1].parent == "action-frame"
    assert fake_tkinter.buttons[1].kwargs == {"text": "Save", "command": callbacks["save"]}
    assert fake_tkinter.buttons[1].grid_call == {"row": 1, "column": 2, "padx": 10, "pady": 5}


def test_build_palette_action_button_specs_preserves_legacy_actions():
    callbacks = {
        "web_safe": object(),
        "web_random": object(),
        "x11": object(),
        "x11_random": object(),
        "randomize": object(),
        "save": object(),
        "cancel": object(),
    }

    specs = palette_ui.build_palette_action_button_specs(**callbacks)

    assert specs == (
        palette_ui.PaletteActionButtonSpec("x216_btn", "Web Safe Color", callbacks["web_safe"], 0, 1),
        palette_ui.PaletteActionButtonSpec("random_web_btn", "Web Random", callbacks["web_random"], 0, 2),
        palette_ui.PaletteActionButtonSpec("x11_btn", "X11 Colors", callbacks["x11"], 0, 3),
        palette_ui.PaletteActionButtonSpec(
            "random_classic_btn",
            "X11 Random",
            callbacks["x11_random"],
            0,
            4,
        ),
        palette_ui.PaletteActionButtonSpec("random_btn", "Randomize", callbacks["randomize"], 0, 5),
        palette_ui.PaletteActionButtonSpec("save_btn", "Save", callbacks["save"], 0, 6),
        palette_ui.PaletteActionButtonSpec("cancel_btn", "Cancel", callbacks["cancel"], 0, 7),
    )


def test_create_palette_sliders_uses_legacy_factory_arguments():
    calls = []

    def scale_factory(**kwargs):
        calls.append(kwargs)
        return "slider-%d" % kwargs["nbr"]

    sliders = palette_ui.create_palette_sliders(
        palette_count=2,
        scale_factory=scale_factory,
        master="frame-canvas",
        before=b"before",
        after=b"after",
        height=500,
        width=1000,
        slider_length=970,
    )

    assert sliders == ["slider-0", "slider-1"]
    assert calls == [
        {
            "master": "frame-canvas",
            "from_": -1,
            "to": 16777215,
            "ln": 970,
            "label": "Palette 1",
            "nbr": 0,
            "bfn": b"before",
            "afn": b"after",
            "h": 500,
            "w": 1000,
        },
        {
            "master": "frame-canvas",
            "from_": -1,
            "to": 16777215,
            "ln": 970,
            "label": "Palette 2",
            "nbr": 1,
            "bfn": b"before",
            "afn": b"after",
            "h": 500,
            "w": 1000,
        },
    ]


def test_apply_color_table_updates_values_and_sliders():
    values = ["empty", "empty"]
    sliders = [FakeSlider(), FakeSlider()]

    palette_ui.apply_color_table(values, sliders, ["000001", "0000ff"])

    assert values == [1, 255]
    assert [slider.value for slider in sliders] == [1, 255]


def test_random_palette_values_uses_injected_random_source():
    values = ["empty", "empty"]
    sliders = [FakeSlider(), FakeSlider()]
    generated = iter([7, 9])

    palette_ui.random_palette_values(values, sliders, lambda start, end: next(generated))

    assert values == [7, 9]
    assert [slider.value for slider in sliders] == [7, 9]


def test_save_checkpoint_preserves_legacy_cancel_and_save_payloads():
    cancel = palette_ui.save_checkpoint(
        cancel=True,
        palette_values=["empty"],
        wanabyte=b"png",
        chunk_length=12,
        data_offset=4,
        from_error="source",
    )
    saved = palette_ui.save_checkpoint(
        cancel=False,
        palette_values=["empty", 0, 1],
        wanabyte=b"png",
        chunk_length=12,
        data_offset=4,
        from_error="source",
    )

    assert cancel.error is True
    assert cancel.fixed is False
    assert cancel.function == "Tk_Save_Plte"
    assert cancel.chunk == b"PLTE"
    assert cancel.infos == ("-Manually modify PLTE datas has been canceled by user.",)
    assert cancel.toolkit == (
        "706e67",
        4,
        16,
        "-Manually modify PLTE datas has been canceled by user.",
        b"PLTE",
        "source",
    )

    assert saved.error is True
    assert saved.fixed is True
    assert saved.infos == ("-PLTE Data has been replaced manually.",)
    assert saved.toolkit == (
        "706e67",
        4,
        16,
        "-PLTE Data has been modified with 255 new palettes.",
        b"PLTE",
        "source",
    )


def main():
    checks = [
        ("Preview dimensions", test_preview_dimensions_preserve_legacy_padding),
        ("Editor state", test_create_palette_editor_state_initializes_values_and_wanabyte),
        ("Editor state value update", test_update_palette_state_value_rebuilds_wanabyte),
        ("Editor state colors", test_apply_palette_state_colors_updates_sliders_and_wanabyte),
        ("Editor state randomize", test_randomize_palette_state_uses_injected_random_source),
        ("Editor state sliders", test_set_palette_state_sliders_preserves_slider_list_reference),
        ("Editor layout", test_build_editor_layout_preserves_legacy_geometry),
        ("Editor layout height cap", test_build_editor_layout_caps_square_preview_to_screen_height),
        ("Editor window center", test_center_palette_editor_window_uses_screen_center),
        ("Editor window", test_create_palette_editor_window_preserves_legacy_window_setup),
        ("Editor frames", test_create_palette_editor_frames_preserves_legacy_frame_wiring),
        ("Preview renderer", test_render_preview_label_uses_injected_ui_modules),
        ("Preview renderer no cv2", test_render_preview_label_falls_back_to_pillow_without_cv2),
        ("Palette scale widget", test_create_palette_scale_uses_injected_tkinter_module),
        ("Palette slider canvas", test_create_palette_slider_canvas_wires_canvas_frame_and_scrollbar),
        ("Palette slider scrollregion", test_bind_palette_slider_scrollregion_refreshes_canvas_on_layout_changes),
        ("Palette slider mousewheel", test_bind_palette_slider_mousewheel_scrolls_when_pointer_is_over_controls),
        ("Palette action buttons", test_create_palette_action_buttons_uses_specs_and_grid_options),
        ("Palette action specs", test_build_palette_action_button_specs_preserves_legacy_actions),
        ("Palette sliders", test_create_palette_sliders_uses_legacy_factory_arguments),
        ("Apply color table", test_apply_color_table_updates_values_and_sliders),
        ("Random palette values", test_random_palette_values_uses_injected_random_source),
        ("Save CheckPoint payload", test_save_checkpoint_preserves_legacy_cancel_and_save_payloads),
    ]

    print("Running palette UI helper tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"palette UI helper tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
