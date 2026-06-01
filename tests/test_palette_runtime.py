#!/usr/bin/env python3
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import palette, palette_runtime, palette_ui


class EndReached(Exception):
    pass


class FakeNumpy:
    uint8 = object()

    def frombuffer(self, value, dtype):
        return value


class FakeCv2:
    def imdecode(self, value, flags):
        return ("decoded", value, flags)


class FakeImage:
    def fromarray(self, value):
        return ("image", value)

    def open(self, payload):
        return FakePilImage(payload.read())


class FailingImage:
    def fromarray(self, value):
        raise ValueError("bad image")


class FakeImageHash:
    def __init__(self, values):
        self.values = iter(values)

    def phash(self, image):
        return next(self.values)


class FakeSlider:
    def __init__(self, name):
        self.name = name
        self.cleaned = False

    def clean(self):
        self.cleaned = True


class FakeVar:
    def __init__(self):
        self.values = []

    def set(self, value):
        self.values.append(value)


class FakeScaleSlider:
    def __init__(self):
        self.var = FakeVar()


class FakeWindow:
    def __init__(self):
        self.calls = []

    def winfo_screenwidth(self):
        return 2100

    def destroy(self):
        self.calls.append("destroy")

    def quit(self):
        self.calls.append("quit")


class FakeWindowWithHeight(FakeWindow):
    def winfo_screenheight(self):
        return 1080


class FakeCanvas:
    def __init__(self):
        self.binds = []

    def bind(self, event, callback):
        self.binds.append((event, callback))


class FakePilImage:
    size = (100, 50)

    def __init__(self, source=None):
        self.source = source

    def load(self):
        return None


@contextmanager
def clean_stderr(stream):
    yield stream


def libpng_stderr(message):
    @contextmanager
    def redirector(stream):
        stream.write(message.encode())
        yield stream

    return redirector


def build_guess_runtime(calls, side_notes=None, *, hashes=(10, 10, 15), stderr_redirector=clean_stderr, image=None):
    if side_notes is None:
        side_notes = []
    if image is None:
        image = FakeImage()

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    return palette_runtime.PaletteCountGuessRuntime(
        cv2=FakeCv2(),
        numpy=FakeNumpy(),
        image=image,
        imagehash=FakeImageHash(hashes),
        stderr_redirector=stderr_redirector,
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        emit=lambda message: calls.append(("emit", message)),
        candy=candy,
        end=lambda: calls.append(("end",)),
        raw_print=lambda *args: calls.append(("raw_print", args)),
        side_notes=side_notes,
        build_palette_png=lambda before, values, after: calls.append(
            ("build_palette_png", before, tuple(values), after)
        ) or b"png",
    )


def build_manual_setup_runtime(calls):
    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    return palette_runtime.ManualPaletteSetupRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        cv2=FakeCv2(),
        numpy=FakeNumpy(),
        image=FakeImage(),
        guess_palette_count=lambda before, after: calls.append(("guess", before, after)) or 3,
    )


def guess_context(**updates):
    values = {
        "x11_colors": ("000000", "111111", "222222"),
        "libpng_errors": ("libpng error:",),
        "ihdr_depth": "2",
    }
    values.update(updates)
    return palette_runtime.PaletteCountGuessContext(**values)


def test_manual_palette_after_index_preserves_legacy_expression():
    assert palette_runtime.manual_palette_after_index(8, 20) == 20
    assert palette_runtime.manual_palette_after_index(0, 20) == 20


def test_manual_palette_slices_preserve_legacy_before_after_cut():
    before, after = palette_runtime.manual_palette_slices("0011223344556677", 4, 10)

    assert before == bytes.fromhex("0011")
    assert after == bytes.fromhex("556677")


def test_create_manual_palette_session_builds_initial_png_and_state():
    calls = []

    def guess_palette_count(before, after):
        calls.append((before, after))
        return 3

    session = palette_runtime.create_manual_palette_session(
        data_hex="0011223344556677",
        data_offset=4,
        chunk_length=10,
        chunk_name=b"PLTE",
        guess_palette_count=guess_palette_count,
    )

    assert calls == [(bytes.fromhex("0011"), bytes.fromhex("556677"))]
    assert session.before == bytes.fromhex("0011")
    assert session.after == bytes.fromhex("556677")
    assert session.wanabyte == palette.initial_manual_palette_png(session.before, b"PLTE", session.after)
    assert session.palette_count == 3
    assert session.state.values == ["empty", "empty", "empty"]
    assert session.state.wanabyte == session.wanabyte


def test_create_manual_palette_setup_builds_session_image_and_debug_report():
    calls = []

    setup = palette_runtime.create_manual_palette_setup(
        build_manual_setup_runtime(calls),
        palette_runtime.ManualPaletteSetupContext(
            file="sample.png",
            chunk_name="PLTE",
            chunk_length=10,
            data_offset=4,
            data_hex="0011223344556677",
            debug=True,
        ),
    )

    assert setup.chunk_name == b"PLTE"
    assert setup.session.before == bytes.fromhex("0011")
    assert setup.session.after == bytes.fromhex("556677")
    assert setup.session.palette_count == 3
    assert setup.image_array == ("decoded", setup.session.wanabyte, -1)
    assert setup.pil_image == ("image", setup.image_array)
    assert ("candy", ("Title", "Manually Bruteforcing Chunk Datas:")) in calls
    assert ("guess", bytes.fromhex("0011"), bytes.fromhex("556677")) in calls
    assert ("emit", "File:sample.png") in calls
    assert ("emit", "ChunkName:b'PLTE'") in calls
    assert ("emit", "Palette_nbr:3") in calls


def test_create_manual_palette_setup_accepts_bytes_chunk_name_without_error():
    calls = []

    setup = palette_runtime.create_manual_palette_setup(
        build_manual_setup_runtime(calls),
        palette_runtime.ManualPaletteSetupContext(
            file="sample.png",
            chunk_name=b"PLTE",
            chunk_length=10,
            data_offset=4,
            data_hex="0011223344556677",
            debug=True,
        ),
    )

    assert setup.chunk_name == b"PLTE"
    assert not any(call[0] == "betterror" for call in calls)
    assert not any(call[0] == "emit" and "<red:Error:" in call[1] for call in calls)


def test_create_manual_palette_setup_uses_pillow_preview_without_cv2():
    calls = []
    runtime = build_manual_setup_runtime(calls)
    runtime = palette_runtime.ManualPaletteSetupRuntime(
        **{**runtime.__dict__, "cv2": None, "numpy": None}
    )

    setup = palette_runtime.create_manual_palette_setup(
        runtime,
        palette_runtime.ManualPaletteSetupContext(
            file="sample.png",
            chunk_name=b"PLTE",
            chunk_length=10,
            data_offset=4,
            data_hex="0011223344556677",
            debug=False,
        ),
    )

    assert setup.image_array is None
    assert setup.pil_image.size == (100, 50)
    assert ("guess", bytes.fromhex("0011"), bytes.fromhex("556677")) in calls


def test_manual_palette_full_new_data_returns_chunk_bytes_between_slices():
    session = palette_runtime.ManualPaletteSession(
        before=b"aa",
        after=b"zz",
        wanabyte=b"aaPLTEzz",
        palette_count=1,
        state=None,
    )
    no_after = palette_runtime.ManualPaletteSession(
        before=b"aa",
        after=b"",
        wanabyte=b"aaPLTE",
        palette_count=1,
        state=None,
    )

    assert palette_runtime.manual_palette_full_new_data(session) == b"PLTE"
    assert palette_runtime.manual_palette_full_new_data(no_after) == b"PLTE"


def test_sync_palette_legacy_state_updates_namespace_when_state_exists():
    state = palette_ui.PaletteEditorState(
        values=["00"],
        wanabyte=b"png",
        sliders=["slider"],
    )
    namespace = {"Plte_Blst": [], "slider_list": [], "wanabyte": b""}

    palette_runtime.sync_palette_legacy_state(namespace, state)

    assert namespace == {
        "Plte_Blst": ["00"],
        "slider_list": ["slider"],
        "wanabyte": b"png",
    }


def test_sync_palette_legacy_state_ignores_none_state():
    namespace = {"Plte_Blst": ["old"], "slider_list": ["old"], "wanabyte": b"old"}

    palette_runtime.sync_palette_legacy_state(namespace, None)

    assert namespace == {"Plte_Blst": ["old"], "slider_list": ["old"], "wanabyte": b"old"}


def test_render_palette_preview_from_namespace_updates_image_globals():
    calls = []
    namespace = {
        "frame_img": "frame",
        "cv2": "cv2",
        "np": "np",
        "Image": "Image",
        "ImageTk": "ImageTk",
        "tkinter": "tkinter",
    }

    def renderer(*args, **kwargs):
        calls.append((args, kwargs))
        return "im", "pil", "tk"

    palette_runtime.render_palette_preview_from_namespace(
        namespace,
        b"png",
        100,
        50,
        renderer=renderer,
    )

    assert namespace["im"] == "im"
    assert namespace["pil_image"] == "pil"
    assert namespace["tk_image"] == "tk"
    assert calls == [
        (
            (b"png", "frame", 100, 50),
            {
                "cv2_module": "cv2",
                "numpy_module": "np",
                "image_module": "Image",
                "image_tk_module": "ImageTk",
                "tkinter_module": "tkinter",
            },
        )
    ]


def test_render_palette_preview_from_namespace_accepts_frame_argument():
    calls = []
    namespace = {
        "cv2": "cv2",
        "np": "np",
        "Image": "Image",
        "ImageTk": "ImageTk",
        "tkinter": "tkinter",
    }

    def renderer(*args, **kwargs):
        calls.append((args, kwargs))
        return "im", "pil", "tk"

    palette_runtime.render_palette_preview_from_namespace(
        namespace,
        b"png",
        100,
        50,
        "new-frame",
        renderer=renderer,
    )

    assert namespace["frame_img"] == "new-frame"
    assert calls[0][0] == (b"png", "new-frame", 100, 50)


def test_update_palette_value_from_namespace_updates_state_sync_and_preview():
    calls = []
    state = palette_ui.PaletteEditorState(values=["empty"], sliders=[], wanabyte=b"old")
    namespace = {
        "palette_state": state,
        "Sync_Palette_Legacy_State": lambda: calls.append(("sync",)),
        "Tk_Render_Plte_Preview": lambda data, width, height: calls.append(
            ("preview", data, width, height)
        ),
    }

    result = palette_runtime.update_palette_value_from_namespace(
        namespace,
        "7",
        "0",
        b"before",
        b"after",
        100,
        50,
    )

    assert state.values == ["7"]
    assert result == state.wanabyte
    assert calls == [("sync",), ("preview", state.wanabyte, 100, 50)]


def test_apply_palette_colors_from_namespace_updates_fallback_palette_and_preview():
    calls = []
    sliders = [FakeScaleSlider(), FakeScaleSlider()]
    namespace = {
        "palette_state": None,
        "Plte_Blst": ["empty", "empty"],
        "slider_list": sliders,
        "Tk_Render_Plte_Preview": lambda data, width, height: calls.append(
            ("preview", data, width, height)
        ),
    }

    result = palette_runtime.apply_palette_colors_from_namespace(
        namespace,
        ("000001", "000002"),
        b"before",
        b"after",
        100,
        50,
    )

    assert namespace["Plte_Blst"] == [1, 2]
    assert sliders[0].var.values == [1]
    assert sliders[1].var.values == [2]
    assert result == palette.build_palette_png(b"before", [1, 2], b"after")
    assert namespace["wanabyte"] == result
    assert calls == [("preview", result, 100, 50)]


def test_random_palette_helpers_use_namespace_random_sources():
    calls = []
    sliders = [FakeScaleSlider(), FakeScaleSlider()]

    class FakeRandom:
        def __init__(self):
            self.randint_values = iter((5, 6))

        def sample(self, colors, count):
            calls.append(("sample", tuple(colors), count))
            return ("000002", "000001")

        def randint(self, start, stop):
            calls.append(("randint", start, stop))
            return next(self.randint_values)

    namespace = {
        "palette_state": None,
        "Plte_Blst": ["empty", "empty"],
        "slider_list": sliders,
        "random": FakeRandom(),
        "Tk_Render_Plte_Preview": lambda data, width, height: calls.append(
            ("preview", data, width, height)
        ),
    }

    sampled = palette_runtime.apply_random_palette_colors_from_namespace(
        namespace,
        ("000001", "000002"),
        b"before",
        b"after",
        100,
        50,
    )
    randomized = palette_runtime.randomize_palette_from_namespace(
        namespace,
        b"before",
        b"after",
        100,
        50,
    )

    assert namespace["Plte_Blst"] == [5, 6]
    assert sliders[0].var.values == [2, 5]
    assert sliders[1].var.values == [1, 6]
    assert sampled == palette.build_palette_png(b"before", [2, 1], b"after")
    assert randomized == palette.build_palette_png(b"before", [5, 6], b"after")
    assert calls == [
        ("sample", ("000001", "000002"), 2),
        ("preview", sampled, 100, 50),
        ("randint", 0, 16777215),
        ("randint", 0, 16777215),
        ("preview", randomized, 100, 50),
    ]


def test_save_manual_palette_from_namespace_calls_checkpoint():
    calls = []
    slider = FakeSlider("fallback")
    window = FakeWindow()
    namespace = {
        "palette_state": None,
        "Plte_Blst": [1],
        "slider_list": [slider],
        "CheckPoint": lambda *args: calls.append(("checkpoint", args)) or "result",
    }

    result = palette_runtime.save_manual_palette_from_namespace(
        namespace,
        window,
        False,
        12,
        4,
        "source",
        b"png",
    )

    assert result == "result"
    assert slider.cleaned is True
    assert window.calls == ["destroy", "quit"]
    assert calls == [
        (
            "checkpoint",
            (
                True,
                True,
                "Tk_Save_Plte",
                b"PLTE",
                ["-PLTE Data has been replaced manually."],
                "706e67",
                4,
                16,
                "-PLTE Data has been modified with 256 new palettes.",
                b"PLTE",
                "source",
            ),
        )
    ]


def test_save_manual_palette_uses_palette_state_cleans_sliders_and_closes_window():
    calls = []
    sliders = [FakeSlider("a"), FakeSlider("b")]
    window = FakeWindow()
    state = palette_ui.PaletteEditorState(
        values=["empty", 0],
        sliders=sliders,
        wanabyte=b"state-png",
    )

    checkpoint = palette_runtime.save_manual_palette(
        palette_runtime.ManualPaletteSaveRuntime(
            save_checkpoint=lambda **kwargs: calls.append(("save_checkpoint", kwargs)) or "checkpoint"
        ),
        palette_runtime.ManualPaletteSaveContext(
            window=window,
            cancel=False,
            chunk_length=12,
            data_offset=4,
            from_error="source",
            wanabyte=b"fallback-png",
            palette_state=state,
            fallback_values=["fallback"],
            fallback_sliders=[FakeSlider("fallback")],
        ),
    )

    assert checkpoint == "checkpoint"
    assert [slider.cleaned for slider in sliders] == [True, True]
    assert window.calls == ["destroy", "quit"]
    assert calls == [
        (
            "save_checkpoint",
            {
                "cancel": False,
                "palette_values": ["empty", 0],
                "wanabyte": b"state-png",
                "chunk_length": 12,
                "data_offset": 4,
                "from_error": "source",
            },
        )
    ]


def test_save_manual_palette_falls_back_to_legacy_values_without_palette_state():
    fallback_slider = FakeSlider("fallback")
    window = FakeWindow()

    checkpoint = palette_runtime.save_manual_palette(
        palette_runtime.ManualPaletteSaveRuntime(),
        palette_runtime.ManualPaletteSaveContext(
            window=window,
            cancel=True,
            chunk_length=12,
            data_offset=4,
            from_error="source",
            wanabyte=b"png",
            palette_state=None,
            fallback_values=["empty", 0, 1],
            fallback_sliders=[fallback_slider],
        ),
    )

    assert fallback_slider.cleaned is True
    assert window.calls == ["destroy", "quit"]
    assert checkpoint.error is True
    assert checkpoint.fixed is False
    assert checkpoint.function == "Tk_Save_Plte"
    assert checkpoint.toolkit == (
        "706e67",
        4,
        16,
        "-Manually modify PLTE datas has been canceled by user.",
        b"PLTE",
        "source",
    )


def test_build_manual_palette_action_specs_preserves_legacy_callbacks():
    calls = []

    def record(name):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))

        return callback

    specs = palette_runtime.build_manual_palette_action_specs(
        palette_runtime.ManualPaletteActionRuntime(
            web_safe=record("web_safe"),
            web_random=record("web_random"),
            x11=record("x11"),
            x11_random=record("x11_random"),
            randomize=record("randomize"),
            save_palette=record("save_palette"),
        ),
        palette_runtime.ManualPaletteActionContext(
            before=b"before",
            after=b"after",
            height=50,
            width=100,
            window="window",
            chunk_length=12,
            data_offset=4,
            from_error="source",
            wanabyte=b"png",
        ),
    )

    assert [spec.name for spec in specs] == [
        "x216_btn",
        "random_web_btn",
        "x11_btn",
        "random_classic_btn",
        "random_btn",
        "save_btn",
        "cancel_btn",
    ]

    for spec in specs:
        spec.command()

    palette_kwargs = {"bfn": b"before", "afn": b"after", "h": 50, "w": 100}
    assert calls == [
        ("web_safe", (), palette_kwargs),
        ("web_random", (), palette_kwargs),
        ("x11", (), palette_kwargs),
        ("x11_random", (), palette_kwargs),
        ("randomize", (), palette_kwargs),
        ("save_palette", ("window", False, 12, 4, "source", b"png"), {}),
        ("save_palette", ("window", True, 12, 4, "source", b"png"), {}),
    ]


def test_create_manual_palette_editor_wires_window_frames_actions_and_sliders():
    calls = []
    window = FakeWindow()
    layout = palette_ui.PaletteEditorLayout(
        basewidth=1000,
        hsize=500,
        action_width=2000,
        action_height=50,
        canvas_width=985,
        slider_length=970,
    )
    frames = palette_ui.PaletteEditorFrames(
        img="frame-img",
        slider="frame-slider",
        action="frame-action",
    )
    canvas = FakeCanvas()
    slider_canvas = palette_ui.PaletteSliderCanvas(
        canvas=canvas,
        frame="frame-canvas",
        scrollbar="scrollbar",
    )
    state = palette_ui.PaletteEditorState(values=["empty", "empty"], sliders=[], wanabyte=b"png")
    session = palette_runtime.ManualPaletteSession(
        before=b"before",
        after=b"after",
        wanabyte=b"png",
        palette_count=2,
        state=state,
    )

    def action_runtime_callback(*args, **kwargs):
        calls.append(("action_runtime", args, kwargs))

    action_runtime = palette_runtime.ManualPaletteActionRuntime(
        web_safe=action_runtime_callback,
        web_random=action_runtime_callback,
        x11=action_runtime_callback,
        x11_random=action_runtime_callback,
        randomize=action_runtime_callback,
        save_palette=action_runtime_callback,
    )
    update_scrollregion = object()
    scale_factory = object()

    editor = palette_runtime.create_manual_palette_editor(
        palette_runtime.ManualPaletteEditorRuntime(
            tkinter_module="tk",
            render_preview=lambda data, width, height: calls.append(("render_preview", data, width, height)),
            create_window=lambda **kwargs: calls.append(("create_window", kwargs)) or window,
            build_layout=lambda screen_width, image_size: calls.append(
                ("build_layout", screen_width, image_size)
            ) or layout,
            center_window=lambda target, target_layout: calls.append(
                ("center_window", target, target_layout)
            ),
            create_frames=lambda **kwargs: calls.append(("create_frames", kwargs)) or frames,
            build_action_specs=lambda runtime, context: calls.append(
                ("build_action_specs", runtime, context)
            ) or ("spec",),
            create_buttons=lambda **kwargs: calls.append(("create_buttons", kwargs)) or {"save_btn": "save"},
            create_slider_canvas=lambda **kwargs: calls.append(("create_slider_canvas", kwargs)) or slider_canvas,
            create_sliders=lambda **kwargs: calls.append(("create_sliders", kwargs)) or ["slider-a", "slider-b"],
            set_state_sliders=lambda target, sliders: calls.append(("set_state_sliders", target, sliders)),
            bind_slider_scrollregion=lambda target, sliders: calls.append(
                ("bind_slider_scrollregion", target, sliders)
            ),
            bind_slider_mousewheel=lambda target, sliders: calls.append(
                ("bind_slider_mousewheel", target, sliders)
            ),
            refresh_slider_canvas=lambda target, sliders: calls.append(("refresh_slider_canvas", target, sliders)),
        ),
        palette_runtime.ManualPaletteEditorContext(
            title="PLTE Editor:file.png",
            session=session,
            pil_image=FakePilImage(),
            chunk_length=12,
            data_offset=4,
            from_error="source",
            scale_factory=scale_factory,
            update_scrollregion=update_scrollregion,
            action_runtime=action_runtime,
        ),
    )

    assert editor.window is window
    assert editor.layout is layout
    assert editor.frames is frames
    assert editor.action_buttons == {"save_btn": "save"}
    assert editor.slider_canvas is slider_canvas
    assert editor.sliders == ["slider-a", "slider-b"]
    assert ("bind_slider_scrollregion", slider_canvas, ["slider-a", "slider-b"]) in calls
    assert ("bind_slider_mousewheel", slider_canvas, ["slider-a", "slider-b"]) in calls
    assert ("refresh_slider_canvas", slider_canvas, ["slider-a", "slider-b"]) in calls
    assert ("render_preview", b"png", 1000, 500) in calls
    assert calls[0] == ("create_window", {"tkinter_module": "tk", "title": "PLTE Editor:file.png"})
    assert ("build_layout", 2100, (100, 50)) in calls
    assert ("center_window", window, layout) in calls
    assert ("set_state_sliders", state, ["slider-a", "slider-b"]) in calls

    action_call = next(call for call in calls if call[0] == "build_action_specs")
    assert action_call[1] is action_runtime
    assert action_call[2].before == b"before"
    assert action_call[2].after == b"after"
    assert action_call[2].height == 500
    assert action_call[2].width == 1000
    assert action_call[2].window is window
    assert action_call[2].chunk_length == 12
    assert action_call[2].data_offset == 4
    assert action_call[2].from_error == "source"
    assert action_call[2].wanabyte == b"png"

    create_buttons_call = next(call for call in calls if call[0] == "create_buttons")
    assert create_buttons_call[1]["tkinter_module"] == "tk"
    assert create_buttons_call[1]["master"] == "frame-action"
    assert create_buttons_call[1]["specs"] == ("spec",)
    assert create_buttons_call[1]["grid_options"] == {"padx": 10, "pady": 5}

    create_sliders_call = next(call for call in calls if call[0] == "create_sliders")
    assert create_sliders_call[1]["palette_count"] == 2
    assert create_sliders_call[1]["scale_factory"] is scale_factory
    assert create_sliders_call[1]["master"] == "frame-canvas"
    assert create_sliders_call[1]["before"] == b"before"
    assert create_sliders_call[1]["after"] == b"after"
    assert create_sliders_call[1]["height"] == 500
    assert create_sliders_call[1]["width"] == 1000
    assert create_sliders_call[1]["slider_length"] == 970


def test_build_manual_palette_layout_passes_screen_height_when_supported():
    calls = []
    window = FakeWindowWithHeight()

    layout = palette_runtime.build_manual_palette_layout(
        lambda screen_width, image_size, screen_height: calls.append(
            ("layout", screen_width, image_size, screen_height)
        )
        or "layout",
        window,
        (32, 32),
    )

    assert layout == "layout"
    assert calls == [("layout", 2100, (32, 32), 1080)]


def test_build_manual_palette_layout_keeps_two_argument_builders():
    calls = []
    window = FakeWindowWithHeight()

    layout = palette_runtime.build_manual_palette_layout(
        lambda screen_width, image_size: calls.append(
            ("layout", screen_width, image_size)
        )
        or "layout",
        window,
        (32, 32),
    )

    assert layout == "layout"
    assert calls == [("layout", 2100, (32, 32))]


def test_create_manual_palette_editor_passes_frame_to_preview_when_supported():
    calls = []
    window = FakeWindow()
    frames = palette_ui.PaletteEditorFrames(
        img="frame-img",
        slider="frame-slider",
        action="frame-action",
    )
    slider_canvas = palette_ui.PaletteSliderCanvas(
        canvas=FakeCanvas(),
        frame="frame-canvas",
        scrollbar="scrollbar",
    )
    session = palette_runtime.ManualPaletteSession(
        before=b"before",
        after=b"after",
        wanabyte=b"png",
        palette_count=1,
        state=palette_ui.PaletteEditorState(values=["empty"], sliders=[], wanabyte=b"png"),
    )
    action_runtime = palette_runtime.ManualPaletteActionRuntime(
        web_safe=lambda *args, **kwargs: None,
        web_random=lambda *args, **kwargs: None,
        x11=lambda *args, **kwargs: None,
        x11_random=lambda *args, **kwargs: None,
        randomize=lambda *args, **kwargs: None,
        save_palette=lambda *args, **kwargs: None,
    )

    palette_runtime.create_manual_palette_editor(
        palette_runtime.ManualPaletteEditorRuntime(
            tkinter_module="tk",
            render_preview=lambda data, width, height, frame: calls.append(
                ("render_preview", data, width, height, frame)
            ),
            create_window=lambda **kwargs: window,
            build_layout=lambda screen_width, image_size: palette_ui.PaletteEditorLayout(
                basewidth=1000,
                hsize=500,
                action_width=2000,
                action_height=50,
                canvas_width=985,
                slider_length=970,
            ),
            create_frames=lambda **kwargs: frames,
            build_action_specs=lambda runtime, context: (),
            create_buttons=lambda **kwargs: {},
            create_slider_canvas=lambda **kwargs: slider_canvas,
            create_sliders=lambda **kwargs: [],
            set_state_sliders=lambda state, sliders: None,
        ),
        palette_runtime.ManualPaletteEditorContext(
            title="PLTE Editor:file.png",
            session=session,
            pil_image=FakePilImage(),
            chunk_length=12,
            data_offset=4,
            from_error="source",
            scale_factory=object(),
            update_scrollregion=object(),
            action_runtime=action_runtime,
        ),
    )

    assert calls == [("render_preview", b"png", 1000, 500, "frame-img")]


def test_create_manual_palette_editor_from_namespace_wires_legacy_globals():
    calls = []
    state = palette_ui.PaletteEditorState(values=["empty", "empty"], sliders=[], wanabyte=b"png")
    session = palette_runtime.ManualPaletteSession(
        before=b"before",
        after=b"after",
        wanabyte=b"png",
        palette_count=2,
        state=state,
    )
    setup = palette_runtime.ManualPaletteSetup(
        chunk_name=b"PLTE",
        session=session,
        image_array="image-array",
        pil_image=FakePilImage(),
    )
    editor = palette_runtime.ManualPaletteEditor(
        window=FakeWindow(),
        layout=palette_ui.PaletteEditorLayout(
            basewidth=1000,
            hsize=500,
            action_width=2000,
            action_height=50,
            canvas_width=985,
            slider_length=970,
        ),
        frames=palette_ui.PaletteEditorFrames(
            img="frame-img",
            slider="frame-slider",
            action="frame-action",
        ),
        action_buttons={"save_btn": "save"},
        slider_canvas=palette_ui.PaletteSliderCanvas(
            canvas=FakeCanvas(),
            frame="frame-canvas",
            scrollbar="scrollbar",
        ),
        sliders=["slider-a", "slider-b"],
    )

    def callback(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return name

        return inner

    scale_factory = object()
    update_scrollregion = object()
    namespace = {
        "Candy": callback("Candy"),
        "PRINT": callback("PRINT"),
        "Betterror": callback("Betterror"),
        "cv2": "cv2",
        "np": "np",
        "Image": "Image",
        "Guess_Palettes_Nbr": callback("Guess_Palettes_Nbr"),
        "DATAX": "001122",
        "DEBUG": True,
        "tkinter": "tk",
        "Tk_Render_Plte_Preview": callback("Tk_Render_Plte_Preview"),
        "FILE_Origin": "origin.png",
        "Tk_Gen_Scale_Plte": scale_factory,
        "Tk_update_scrollregion_Plte": update_scrollregion,
        "Tk_Web_Safe_Plte": callback("Tk_Web_Safe_Plte"),
        "Tk_Web_Safe_Randomize_Plte": callback("Tk_Web_Safe_Randomize_Plte"),
        "Tk_X11_Plte": callback("Tk_X11_Plte"),
        "Tk_X11_Randomize_Plte": callback("Tk_X11_Randomize_Plte"),
        "Tk_Randomize_Plte": callback("Tk_Randomize_Plte"),
        "Tk_Save_Plte": callback("Tk_Save_Plte"),
        "Sync_Palette_Legacy_State": callback("Sync_Palette_Legacy_State"),
    }

    def setup_creator(runtime, context):
        assert runtime.candy is namespace["Candy"]
        assert runtime.emit is namespace["PRINT"]
        assert runtime.betterror is namespace["Betterror"]
        assert runtime.cv2 == "cv2"
        assert runtime.numpy == "np"
        assert runtime.image == "Image"
        assert runtime.guess_palette_count is namespace["Guess_Palettes_Nbr"]
        assert context == palette_runtime.ManualPaletteSetupContext(
            file="sample.png",
            chunk_name="PLTE",
            chunk_length=12,
            data_offset=4,
            data_hex="001122",
            debug=True,
        )
        return setup

    def editor_creator(runtime, context):
        assert runtime.tkinter_module == "tk"
        assert runtime.render_preview is namespace["Tk_Render_Plte_Preview"]
        assert context.title == "PLTE Editor:origin.png"
        assert context.session is session
        assert context.pil_image is setup.pil_image
        assert context.chunk_length == 12
        assert context.data_offset == 4
        assert context.from_error == "source"
        assert context.scale_factory is scale_factory
        assert context.update_scrollregion is update_scrollregion
        assert context.action_runtime.web_safe is namespace["Tk_Web_Safe_Plte"]
        assert context.action_runtime.web_random is namespace["Tk_Web_Safe_Randomize_Plte"]
        assert context.action_runtime.x11 is namespace["Tk_X11_Plte"]
        assert context.action_runtime.x11_random is namespace["Tk_X11_Randomize_Plte"]
        assert context.action_runtime.randomize is namespace["Tk_Randomize_Plte"]
        assert context.action_runtime.save_palette is namespace["Tk_Save_Plte"]
        return editor

    result = palette_runtime.create_manual_palette_editor_from_namespace(
        namespace,
        "sample.png",
        "PLTE",
        12,
        4,
        "source",
        setup_creator=setup_creator,
        editor_creator=editor_creator,
    )

    assert result is editor
    assert namespace["wanabyte"] == b"png"
    assert namespace["palette_state"] is state
    assert namespace["Plte_Blst"] == ["empty", "empty"]
    assert namespace["im"] == "image-array"
    assert namespace["pil_image"] is setup.pil_image
    assert namespace["window"] is editor.window
    assert namespace["frame_img"] == "frame-img"
    assert namespace["canvas_slider"] is editor.slider_canvas.canvas
    assert namespace["slider_list"] == ["slider-a", "slider-b"]
    assert calls == [("Sync_Palette_Legacy_State", (), {})]


def test_guess_palette_count_uses_phash_distance_and_records_side_note():
    calls = []
    side_notes = []

    result = palette_runtime.guess_palette_count(
        build_guess_runtime(calls, side_notes),
        guess_context(),
        b"before",
        b"after",
    )

    assert result == 2
    assert (
        "build_palette_png",
        b"before",
        (0, 1118481, 2236962),
        b"after",
    ) in calls
    assert ("emit", "-PLTE palettes number estimation: <green:2>") in calls
    assert side_notes == ["-PLTE palettes number estimation: 2"]


def test_guess_palette_count_preserves_ihdr_depth_fallback():
    calls = []
    side_notes = []

    result = palette_runtime.guess_palette_count(
        build_guess_runtime(calls, side_notes, hashes=(10, 10, 10)),
        guess_context(ihdr_depth="3"),
        b"before",
        b"after",
    )

    assert result == 7
    assert ("emit", "<yellow:Warning:%s>" % "Could not estimate palette number.") in calls
    assert side_notes == [
        "Warning:Could not estimate palette number.Returning Max Palettes number according to IHDR Depht"
    ]


def test_guess_palette_count_routes_libpng_error_to_end():
    calls = []

    palette_runtime.guess_palette_count(
        build_guess_runtime(
            calls,
            hashes=(10, 11, 12),
            stderr_redirector=libpng_stderr("libpng error: broken"),
        ),
        guess_context(),
        b"before",
        b"after",
    )

    assert ("raw_print", ("-Error Guess_Palettes_Nbr():", "libpng error: broken")) in calls
    assert ("end",) in calls


def test_guess_palette_count_routes_image_error_to_betterror_and_end():
    calls = []

    def end():
        calls.append(("end",))
        raise EndReached()

    runtime = build_guess_runtime(calls, image=FailingImage())
    runtime = palette_runtime.PaletteCountGuessRuntime(
        **{**runtime.__dict__, "end": end}
    )

    try:
        palette_runtime.guess_palette_count(
            runtime,
            guess_context(),
            b"before",
            b"after",
        )
    except EndReached:
        pass
    else:
        raise AssertionError("TheEnd should stop image error path")

    assert ("betterror", "bad image", "Guess_Palettes_Nbr") in calls
    assert any(
        call[0] == "raw_print"
        and call[1][0] == "-Error Guess_Palettes_Nbr():"
        and str(call[1][1]) == "bad image"
        for call in calls
    )
    assert ("end",) in calls


def test_guess_palette_count_falls_back_when_decode_candidate_fails():
    calls = []
    side_notes = []

    class FailingCv2:
        def imdecode(self, value, flags):
            raise ValueError("decode failed")

    runtime = build_guess_runtime(calls, side_notes, hashes=(10, 11, 12))
    runtime = palette_runtime.PaletteCountGuessRuntime(
        **{**runtime.__dict__, "cv2": FailingCv2()}
    )

    result = palette_runtime.guess_palette_count(
        runtime,
        guess_context(ihdr_depth="3"),
        b"before",
        b"after",
    )

    assert result == 7
    assert ("betterror", "decode failed", "Guess_Palettes_Nbr") in calls
    assert ("end",) in calls
    assert side_notes == [
        "Warning:Could not estimate palette number.Returning Max Palettes number according to IHDR Depht"
    ]


def test_guess_palette_count_falls_back_without_cv2_dependencies():
    calls = []
    side_notes = []
    runtime = build_guess_runtime(calls, side_notes, hashes=(10, 11, 12))
    runtime = palette_runtime.PaletteCountGuessRuntime(
        **{**runtime.__dict__, "cv2": None, "numpy": None}
    )

    result = palette_runtime.guess_palette_count(
        runtime,
        guess_context(ihdr_depth="4"),
        b"before",
        b"after",
    )

    assert result == 15
    assert ("emit", "<yellow:Warning:%s>" % "Could not estimate palette number; using max palettes from IHDR depth.") in calls
    assert ("end",) not in calls
    assert not any(call[0] == "build_palette_png" for call in calls)
    assert side_notes == [
        "Warning:Could not estimate palette number.Returning Max Palettes number according to IHDR Depht"
    ]


def test_guess_palette_count_from_namespace_uses_globals_and_builtin_print_fallback():
    calls = []
    side_notes = []
    namespace = {
        "cv2": FakeCv2(),
        "np": FakeNumpy(),
        "Image": FakeImage(),
        "imagehash": FakeImageHash((10, 10, 15)),
        "stderr_redirector": clean_stderr,
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "Candy": lambda kind, *args: "<%s:%s>" % (args[0], args[1])
        if kind == "Color"
        else "candy:%s" % kind,
        "TheEnd": lambda: calls.append(("end",)),
        "SideNotes": side_notes,
        "X11_Colors": ("000000", "111111", "222222"),
        "LIBPNG_ERR": ("libpng error:",),
        "IHDR_Depht": "2",
    }

    result = palette_runtime.guess_palette_count_from_namespace(namespace, b"before", b"after")

    assert result == 2
    assert ("emit", "-PLTE palettes number estimation: <green:2>") in calls
    assert side_notes == ["-PLTE palettes number estimation: 2"]


def main():
    checks = [
        ("After index", test_manual_palette_after_index_preserves_legacy_expression),
        ("Before/after slices", test_manual_palette_slices_preserve_legacy_before_after_cut),
        ("Manual palette session", test_create_manual_palette_session_builds_initial_png_and_state),
        ("Manual palette setup", test_create_manual_palette_setup_builds_session_image_and_debug_report),
        ("Manual palette bytes chunk", test_create_manual_palette_setup_accepts_bytes_chunk_name_without_error),
        ("Manual palette setup no cv2", test_create_manual_palette_setup_uses_pillow_preview_without_cv2),
        ("Full new data", test_manual_palette_full_new_data_returns_chunk_bytes_between_slices),
        ("Sync palette legacy state", test_sync_palette_legacy_state_updates_namespace_when_state_exists),
        ("Sync palette none state", test_sync_palette_legacy_state_ignores_none_state),
        ("Render palette namespace preview", test_render_palette_preview_from_namespace_updates_image_globals),
        (
            "Render palette namespace preview frame",
            test_render_palette_preview_from_namespace_accepts_frame_argument,
        ),
        (
            "Update palette namespace state",
            test_update_palette_value_from_namespace_updates_state_sync_and_preview,
        ),
        (
            "Apply palette namespace fallback",
            test_apply_palette_colors_from_namespace_updates_fallback_palette_and_preview,
        ),
        ("Random palette namespace helpers", test_random_palette_helpers_use_namespace_random_sources),
        ("Manual palette namespace save", test_save_manual_palette_from_namespace_calls_checkpoint),
        ("Manual palette save state", test_save_manual_palette_uses_palette_state_cleans_sliders_and_closes_window),
        ("Manual palette save fallback", test_save_manual_palette_falls_back_to_legacy_values_without_palette_state),
        ("Manual palette action specs", test_build_manual_palette_action_specs_preserves_legacy_callbacks),
        ("Manual palette editor", test_create_manual_palette_editor_wires_window_frames_actions_and_sliders),
        (
            "Manual palette layout screen height",
            test_build_manual_palette_layout_passes_screen_height_when_supported,
        ),
        (
            "Manual palette layout two-arg compatibility",
            test_build_manual_palette_layout_keeps_two_argument_builders,
        ),
        ("Manual palette editor preview frame", test_create_manual_palette_editor_passes_frame_to_preview_when_supported),
        (
            "Manual palette namespace editor",
            test_create_manual_palette_editor_from_namespace_wires_legacy_globals,
        ),
        ("Guess palette count", test_guess_palette_count_uses_phash_distance_and_records_side_note),
        ("Guess palette fallback", test_guess_palette_count_preserves_ihdr_depth_fallback),
        ("Guess palette libpng error", test_guess_palette_count_routes_libpng_error_to_end),
        ("Guess palette image error", test_guess_palette_count_routes_image_error_to_betterror_and_end),
        ("Guess palette decode fallback", test_guess_palette_count_falls_back_when_decode_candidate_fails),
        ("Guess palette no cv2 fallback", test_guess_palette_count_falls_back_without_cv2_dependencies),
        (
            "Guess palette namespace bridge",
            test_guess_palette_count_from_namespace_uses_globals_and_builtin_print_fallback,
        ),
    ]

    print("Running palette runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"palette runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
