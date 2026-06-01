from __future__ import annotations

from dataclasses import dataclass
import io
from typing import Any
from typing import Iterable

from chunklate import palette


@dataclass(frozen=True)
class PaletteSaveCheckpoint:
    error: bool
    fixed: bool
    function: str
    chunk: bytes
    infos: tuple[str, ...]
    toolkit: tuple[Any, ...]


@dataclass(frozen=True)
class PaletteEditorLayout:
    basewidth: int
    hsize: int
    action_width: int
    action_height: int
    canvas_width: int
    slider_length: int


@dataclass(frozen=True)
class PaletteScaleWidget:
    var: Any
    scale: Any
    swatch: Any
    container: Any


@dataclass(frozen=True)
class PaletteSliderCanvas:
    canvas: Any
    frame: Any
    scrollbar: Any
    window_id: Any = None


@dataclass(frozen=True)
class PaletteActionButtonSpec:
    name: str
    text: str
    command: Any
    row: int
    column: int


@dataclass(frozen=True)
class PaletteEditorFrames:
    img: Any
    slider: Any
    action: Any


@dataclass
class PaletteEditorState:
    values: list[Any]
    sliders: list[Any]
    wanabyte: bytes


def create_palette_editor_state(palette_count: int, wanabyte: bytes) -> PaletteEditorState:
    return PaletteEditorState(
        values=[palette.EMPTY_PALETTE_ENTRY for _ in range(palette_count)],
        sliders=[],
        wanabyte=wanabyte,
    )


def set_palette_state_sliders(state: PaletteEditorState, sliders: list[Any]) -> None:
    state.sliders = sliders


def update_palette_state_value(
    state: PaletteEditorState,
    *,
    index: int,
    raw_value: Any,
    before: bytes,
    after: bytes,
) -> bytes:
    palette.set_palette_value(state.values, index, raw_value)
    state.wanabyte = palette.build_palette_png(before, state.values, after)
    return state.wanabyte


def apply_palette_state_colors(
    state: PaletteEditorState,
    *,
    colors: Iterable[str],
    before: bytes,
    after: bytes,
) -> bytes:
    apply_color_table(state.values, state.sliders, colors)
    state.wanabyte = palette.build_palette_png(before, state.values, after)
    return state.wanabyte


def randomize_palette_state(
    state: PaletteEditorState,
    *,
    random_int: Any,
    before: bytes,
    after: bytes,
) -> bytes:
    random_palette_values(state.values, state.sliders, random_int)
    state.wanabyte = palette.build_palette_png(before, state.values, after)
    return state.wanabyte


def palette_value_to_hex(value: Any) -> str:
    try:
        color_value = int(value)
    except (TypeError, ValueError):
        return "#ffffff"
    if color_value < 0:
        return "#ffffff"
    return "#%06x" % min(color_value, 0xFFFFFF)


def update_palette_swatch(swatch: Any, value: Any) -> None:
    if swatch is None or not hasattr(swatch, "config"):
        return
    swatch.config(bg=palette_value_to_hex(value))


def update_slider_swatch(slider: Any, value: Any) -> None:
    update_palette_swatch(getattr(slider, "swatch", None), value)


def preview_dimensions(width: int, height: int) -> tuple[int, int]:
    return width - 10, height - 10


def slider_length_for_canvas_width(width: int) -> int:
    return max(120, int(width) - 140)


def build_editor_layout(
    screen_width: int,
    image_size: tuple[int, int],
    screen_height: int | None = None,
) -> PaletteEditorLayout:
    basewidth = int(screen_width / 2.10)
    wpercent = basewidth / float(image_size[0])
    hsize = int(float(image_size[1]) * float(wpercent))
    if screen_height is not None:
        max_hsize = max(100, int((screen_height * 0.90 - 20) / 1.10))
        if hsize > max_hsize:
            hsize = max_hsize
            basewidth = int(hsize * float(image_size[0]) / float(image_size[1]))
    return PaletteEditorLayout(
        basewidth=basewidth,
        hsize=hsize,
        action_width=basewidth * 2,
        action_height=int(hsize / 10),
        canvas_width=basewidth - 15,
        slider_length=basewidth - 30,
    )


def palette_editor_window_size(layout: PaletteEditorLayout) -> tuple[int, int]:
    return (
        max(layout.basewidth * 2 + 40, layout.action_width + 20),
        layout.hsize + layout.action_height + 20,
    )


def center_palette_editor_window(
    window: Any,
    layout: PaletteEditorLayout,
    *,
    margin: int = 20,
) -> str | None:
    required = ("geometry", "winfo_screenwidth", "winfo_screenheight")
    if not all(hasattr(window, name) for name in required):
        return None
    if hasattr(window, "update_idletasks"):
        window.update_idletasks()

    screen_width = int(window.winfo_screenwidth())
    screen_height = int(window.winfo_screenheight())
    width, height = palette_editor_window_size(layout)
    width = min(width, max(1, screen_width - margin * 2))
    height = min(height, max(1, screen_height - margin * 2))
    x = max(0, int((screen_width - width) / 2))
    y = max(0, int((screen_height - height) / 2))
    geometry = f"{width}x{height}+{x}+{y}"
    window.geometry(geometry)
    return geometry


def create_palette_editor_window(
    *,
    tkinter_module: Any,
    title: str,
    bg: str = "skyblue",
    resizable: tuple[bool, bool] = (False, False),
) -> Any:
    window = tkinter_module.Tk()
    window.title(title)
    window.config(bg=bg)
    window.resizable(*resizable)
    return window


def create_palette_editor_frames(
    *,
    tkinter_module: Any,
    window: Any,
    layout: PaletteEditorLayout,
) -> PaletteEditorFrames:
    frame_img = tkinter_module.Frame(window, width=layout.basewidth, height=layout.hsize)
    frame_img.grid(row=0, column=0, padx=10, pady=5)
    frame_img.columnconfigure(0, weight=1)
    frame_img.rowconfigure(0, weight=1)

    frame_slider = tkinter_module.Frame(window, width=layout.basewidth, height=layout.hsize, bg="green")
    frame_slider.columnconfigure(0, weight=1)
    frame_slider.rowconfigure(0, weight=1)
    frame_slider.grid(row=0, column=1, padx=10, pady=5)

    frame_action = tkinter_module.Frame(
        window,
        width=layout.action_width,
        height=layout.action_height,
        bg="orange",
    )
    frame_action.columnconfigure(0, weight=1)
    frame_action.rowconfigure(0, weight=1)
    frame_action.grid(row=1, column=0, padx=10, pady=5)

    return PaletteEditorFrames(img=frame_img, slider=frame_slider, action=frame_action)


def decode_preview_image(
    wanabyte: bytes,
    *,
    cv2_module: Any,
    numpy_module: Any,
    image_module: Any,
) -> tuple[Any, Any]:
    if cv2_module is not None and numpy_module is not None:
        im = cv2_module.imdecode(numpy_module.frombuffer(wanabyte, numpy_module.uint8), -1)
        if im is not None:
            return im, image_module.fromarray(im)

    if image_module is None:
        raise RuntimeError("PIL is required to render the PLTE editor preview without OpenCV.")

    pil_image = image_module.open(io.BytesIO(wanabyte))
    pil_image.load()
    return None, pil_image


def render_preview_label(
    wanabyte: bytes,
    frame_img: Any,
    width: int,
    height: int,
    *,
    cv2_module: Any,
    numpy_module: Any,
    image_module: Any,
    image_tk_module: Any,
    tkinter_module: Any,
) -> tuple[Any, Any, Any]:
    im, pil_image = decode_preview_image(
        wanabyte,
        cv2_module=cv2_module,
        numpy_module=numpy_module,
        image_module=image_module,
    )
    new_pil_image = pil_image.resize(
        preview_dimensions(width, height),
        image_module.Resampling.LANCZOS,
    )
    tk_image = image_tk_module.PhotoImage(image=new_pil_image)
    tkinter_module.Label(frame_img, image=tk_image).grid(row=1, column=0, padx=5, pady=5)
    return im, pil_image, tk_image


def create_palette_scale(
    *,
    tkinter_module: Any,
    master: Any,
    label: str,
    value: int,
    from_: int,
    to: int,
    length: int,
    command: Any,
    orient: str = "horizontal",
    grid_options: dict[str, Any] | None = None,
) -> PaletteScaleWidget:
    container = tkinter_module.Frame(master)
    container.grid(**(grid_options or {}))
    container.columnconfigure(1, weight=1)
    var = tkinter_module.IntVar()
    swatch = tkinter_module.Label(
        container,
        bg=palette_value_to_hex(value),
        width=4,
        height=2,
        relief="solid",
        borderwidth=1,
    )
    swatch.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="ns")

    def update_and_call(event):
        update_palette_swatch(swatch, event)
        if callable(command):
            return command(event)
        return None

    scale = tkinter_module.Scale(
        container,
        label=label,
        variable=var,
        from_=from_,
        to=to,
        length=length,
        command=update_and_call,
        orient=orient,
    )
    var.set(value)
    scale.grid(row=0, column=1, sticky="ew")
    return PaletteScaleWidget(var=var, scale=scale, swatch=swatch, container=container)


def slider_scale_widget(slider: Any) -> Any:
    return getattr(slider, "s", None) or getattr(slider, "scale", None) or slider


def set_slider_widget_length(slider: Any, length: int) -> None:
    widget = slider_scale_widget(slider)
    configure = getattr(widget, "configure", None) or getattr(widget, "config", None)
    if callable(configure):
        configure(length=length)


def set_palette_slider_lengths(sliders: Iterable[Any], length: int) -> None:
    for slider in sliders:
        set_slider_widget_length(slider, length)


def widget_width(widget: Any, fallback: int | None = None) -> int | None:
    if hasattr(widget, "winfo_width"):
        try:
            width = int(widget.winfo_width())
        except (TypeError, ValueError):
            width = 0
        if width > 1:
            return width

    if hasattr(widget, "cget"):
        try:
            width = int(widget.cget("width"))
        except (TypeError, ValueError):
            width = 0
        if width > 1:
            return width

    kwargs = getattr(widget, "kwargs", None)
    if isinstance(kwargs, dict):
        try:
            width = int(kwargs.get("width", 0))
        except (TypeError, ValueError):
            width = 0
        if width > 1:
            return width

    return fallback


def create_palette_slider_canvas(
    *,
    tkinter_module: Any,
    master: Any,
    height: int,
    width: int,
    frame_bg: str = "#EBEBEB",
    canvas_grid_options: dict[str, Any] | None = None,
    scrollbar_grid_options: dict[str, Any] | None = None,
) -> PaletteSliderCanvas:
    canvas = tkinter_module.Canvas(master, height=height, width=width)
    canvas.grid(**(canvas_grid_options or {}))
    frame = tkinter_module.Frame(canvas, bg=frame_bg)
    window_id = canvas.create_window(0, 0, window=frame, anchor="nw", width=width)

    scrollbar = tkinter_module.Scrollbar(master, orient="vertical")
    scrollbar.config(command=canvas.yview)
    canvas.config(yscrollcommand=scrollbar.set)
    scrollbar.grid(**(scrollbar_grid_options or {}))
    return PaletteSliderCanvas(canvas=canvas, frame=frame, scrollbar=scrollbar, window_id=window_id)


def resize_palette_slider_canvas(
    slider_canvas: PaletteSliderCanvas,
    sliders: Iterable[Any] = (),
) -> None:
    width = widget_width(slider_canvas.canvas)
    if width is None:
        return

    if slider_canvas.window_id is not None and hasattr(slider_canvas.canvas, "itemconfigure"):
        slider_canvas.canvas.itemconfigure(slider_canvas.window_id, width=width)
    set_palette_slider_lengths(sliders, slider_length_for_canvas_width(width))


def refresh_palette_slider_canvas(
    slider_canvas: PaletteSliderCanvas,
    sliders: Iterable[Any] = (),
) -> None:
    canvas = slider_canvas.canvas
    if hasattr(canvas, "update_idletasks"):
        canvas.update_idletasks()

    resize_palette_slider_canvas(slider_canvas, sliders)
    if hasattr(canvas, "update_idletasks"):
        canvas.update_idletasks()

    bbox = canvas.bbox("all") if hasattr(canvas, "bbox") else None
    if bbox is None:
        return

    configure = getattr(canvas, "configure", None) or getattr(canvas, "config", None)
    if callable(configure):
        configure(scrollregion=bbox)


def bind_palette_slider_scrollregion(
    slider_canvas: PaletteSliderCanvas,
    sliders: Iterable[Any] = (),
) -> Any:
    def refresh(_event: Any = None) -> None:
        refresh_palette_slider_canvas(slider_canvas, sliders)

    if hasattr(slider_canvas.frame, "bind"):
        slider_canvas.frame.bind("<Configure>", refresh)
    if hasattr(slider_canvas.canvas, "bind"):
        slider_canvas.canvas.bind("<Configure>", refresh)
    return refresh


def palette_mousewheel_units(event: Any) -> int:
    delta = getattr(event, "delta", 0)
    if delta:
        if abs(delta) >= 120:
            return max(-10, min(10, int(-delta / 120)))
        return -1 if delta > 0 else 1

    button = getattr(event, "num", None)
    if button == 4:
        return -1
    if button == 5:
        return 1
    return 0


def palette_slider_mousewheel_widgets(
    slider_canvas: PaletteSliderCanvas,
    sliders: Iterable[Any] = (),
) -> tuple[Any, ...]:
    widgets = [slider_canvas.canvas, slider_canvas.frame]
    for slider in sliders:
        for candidate in (
            getattr(slider, "container", None),
            getattr(slider, "swatch", None),
            slider_scale_widget(slider),
        ):
            if candidate is not None:
                widgets.append(candidate)

    unique_widgets = []
    seen = set()
    for widget in widgets:
        identity = id(widget)
        if identity not in seen:
            seen.add(identity)
            unique_widgets.append(widget)
    return tuple(unique_widgets)


def bind_palette_slider_mousewheel(
    slider_canvas: PaletteSliderCanvas,
    sliders: Iterable[Any] = (),
) -> Any:
    canvas = slider_canvas.canvas

    def focus_canvas(_event: Any = None) -> None:
        if hasattr(canvas, "focus_set"):
            canvas.focus_set()

    def scroll(event: Any = None) -> str | None:
        units = palette_mousewheel_units(event)
        if units and hasattr(canvas, "yview_scroll"):
            canvas.yview_scroll(units, "units")
            return "break"
        return None

    for widget in palette_slider_mousewheel_widgets(slider_canvas, sliders):
        if not hasattr(widget, "bind"):
            continue
        widget.bind("<Enter>", focus_canvas)
        widget.bind("<MouseWheel>", scroll)
        widget.bind("<Button-4>", scroll)
        widget.bind("<Button-5>", scroll)
    return scroll


def create_palette_action_buttons(
    *,
    tkinter_module: Any,
    master: Any,
    specs: Iterable[PaletteActionButtonSpec],
    grid_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    buttons = {}
    for spec in specs:
        button = tkinter_module.Button(master, text=spec.text, command=spec.command)
        button.grid(row=spec.row, column=spec.column, **(grid_options or {}))
        buttons[spec.name] = button
    return buttons


def build_palette_action_button_specs(
    *,
    web_safe: Any,
    web_random: Any,
    x11: Any,
    x11_random: Any,
    randomize: Any,
    save: Any,
    cancel: Any,
) -> tuple[PaletteActionButtonSpec, ...]:
    return (
        PaletteActionButtonSpec("x216_btn", "Web Safe Color", web_safe, 0, 0),
        PaletteActionButtonSpec("random_web_btn", "Web Random", web_random, 0, 1),
        PaletteActionButtonSpec("x11_btn", "X11 Colors", x11, 0, 2),
        PaletteActionButtonSpec("random_classic_btn", "X11 Random", x11_random, 0, 3),
        PaletteActionButtonSpec("random_btn", "Randomize", randomize, 1, 0),
        PaletteActionButtonSpec("save_btn", "Save", save, 1, 2),
        PaletteActionButtonSpec("cancel_btn", "Cancel", cancel, 1, 3),
    )


def create_palette_sliders(
    *,
    palette_count: int,
    scale_factory: Any,
    master: Any,
    before: bytes,
    after: bytes,
    height: int,
    width: int,
    slider_length: int,
) -> list[Any]:
    return [
        scale_factory(
            master=master,
            from_=-1,
            to=16777215,
            ln=slider_length,
            label="Palette %d" % (index + 1),
            nbr=index,
            bfn=before,
            afn=after,
            h=height,
            w=width,
        )
        for index in range(palette_count)
    ]


def apply_color_table(values: list[Any], sliders: Iterable[Any], colors: Iterable[str]) -> None:
    for index, (slider, color) in enumerate(zip(sliders, colors)):
        color_value = int(color, 16)
        values[index] = color_value
        slider.var.set(color_value)
        update_slider_swatch(slider, color_value)


def random_palette_values(values: list[Any], sliders: Iterable[Any], random_int) -> None:
    for index, slider in enumerate(sliders):
        color_value = random_int(0, 16777215)
        values[index] = color_value
        slider.var.set(color_value)
        update_slider_swatch(slider, color_value)


def save_checkpoint(
    *,
    cancel: bool,
    palette_values: Iterable[Any],
    wanabyte: bytes,
    chunk_length: int,
    data_offset: int,
    from_error: Any,
) -> PaletteSaveCheckpoint:
    if cancel:
        return PaletteSaveCheckpoint(
            error=True,
            fixed=False,
            function="Tk_Save_Plte",
            chunk=b"PLTE",
            infos=("-Manually modify PLTE datas has been canceled by user.",),
            toolkit=(
                wanabyte.hex(),
                data_offset,
                data_offset + chunk_length,
                "-Manually modify PLTE datas has been canceled by user.",
                b"PLTE",
                from_error,
            ),
        )

    return PaletteSaveCheckpoint(
        error=True,
        fixed=True,
        function="Tk_Save_Plte",
        chunk=b"PLTE",
        infos=("-PLTE Data has been replaced manually.",),
        toolkit=(
            wanabyte.hex(),
            data_offset,
            data_offset + chunk_length,
            "-PLTE Data has been modified with %s new palettes."
            % palette.legacy_palette_count(palette_values),
            b"PLTE",
            from_error,
        ),
    )
