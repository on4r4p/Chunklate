from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import io
import inspect

from . import palette, palette_ui


GuessPaletteCount = Callable[[bytes, bytes], int]


@dataclass(frozen=True)
class ManualPaletteSession:
    before: bytes
    after: bytes
    wanabyte: bytes
    palette_count: int
    state: palette_ui.PaletteEditorState


@dataclass(frozen=True)
class ManualPaletteSetup:
    chunk_name: bytes
    session: ManualPaletteSession
    image_array: object
    pil_image: object


@dataclass(frozen=True)
class ManualPaletteSetupRuntime:
    candy: Callable
    emit: Callable
    betterror: Callable
    cv2: object
    numpy: object
    image: object
    guess_palette_count: GuessPaletteCount


@dataclass(frozen=True)
class ManualPaletteSetupContext:
    file: object
    chunk_name: object
    chunk_length: int
    data_offset: int
    data_hex: str
    debug: bool = False


@dataclass(frozen=True)
class ManualPaletteSaveRuntime:
    save_checkpoint: Callable = palette_ui.save_checkpoint


@dataclass(frozen=True)
class ManualPaletteSaveContext:
    window: object
    cancel: bool
    chunk_length: int
    data_offset: int
    from_error: object
    wanabyte: bytes
    palette_state: object
    fallback_values: list
    fallback_sliders: list


@dataclass(frozen=True)
class ManualPaletteActionRuntime:
    web_safe: Callable
    web_random: Callable
    x11: Callable
    x11_random: Callable
    randomize: Callable
    save_palette: Callable
    build_specs: Callable = palette_ui.build_palette_action_button_specs


@dataclass(frozen=True)
class ManualPaletteActionContext:
    before: bytes
    after: bytes
    height: int
    width: int
    window: object
    chunk_length: int
    data_offset: int
    from_error: object
    wanabyte: bytes


@dataclass(frozen=True)
class ManualPaletteEditorRuntime:
    tkinter_module: object
    render_preview: Callable
    create_window: Callable = palette_ui.create_palette_editor_window
    build_layout: Callable = palette_ui.build_editor_layout
    center_window: Callable = palette_ui.center_palette_editor_window
    create_frames: Callable = palette_ui.create_palette_editor_frames
    create_buttons: Callable = palette_ui.create_palette_action_buttons
    build_action_specs: Callable | None = None
    create_slider_canvas: Callable = palette_ui.create_palette_slider_canvas
    create_sliders: Callable = palette_ui.create_palette_sliders
    set_state_sliders: Callable = palette_ui.set_palette_state_sliders
    bind_slider_scrollregion: Callable = palette_ui.bind_palette_slider_scrollregion
    bind_slider_mousewheel: Callable = palette_ui.bind_palette_slider_mousewheel
    refresh_slider_canvas: Callable = palette_ui.refresh_palette_slider_canvas


@dataclass(frozen=True)
class ManualPaletteEditorContext:
    title: str
    session: ManualPaletteSession
    pil_image: object
    chunk_length: int
    data_offset: int
    from_error: object
    scale_factory: Callable
    update_scrollregion: Callable
    action_runtime: ManualPaletteActionRuntime


@dataclass(frozen=True)
class ManualPaletteEditor:
    window: object
    layout: palette_ui.PaletteEditorLayout
    frames: palette_ui.PaletteEditorFrames
    action_buttons: dict
    slider_canvas: palette_ui.PaletteSliderCanvas
    sliders: list


@dataclass(frozen=True)
class PaletteCountGuessRuntime:
    cv2: object
    numpy: object
    image: object
    imagehash: object
    stderr_redirector: Callable
    betterror: Callable
    emit: Callable
    candy: Callable
    end: Callable
    raw_print: Callable
    side_notes: list
    build_palette_png: Callable = palette.build_palette_png


@dataclass(frozen=True)
class PaletteCountGuessContext:
    x11_colors: tuple[str, ...]
    libpng_errors: tuple[str, ...]
    ihdr_depth: str


def manual_palette_after_index(data_offset: int, chunk_length: int) -> int:
    return data_offset + (chunk_length - data_offset)


def manual_palette_slices(data_hex: str, data_offset: int, chunk_length: int) -> tuple[bytes, bytes]:
    before = bytes.fromhex(data_hex[:data_offset])
    after = bytes.fromhex(data_hex[manual_palette_after_index(data_offset, chunk_length) :])
    return before, after


def manual_palette_full_new_data(session: ManualPaletteSession) -> bytes:
    if session.after:
        return session.wanabyte[len(session.before) : len(session.wanabyte) - len(session.after)]
    return session.wanabyte[len(session.before) :]


def manual_palette_debug_lines(
    context: ManualPaletteSetupContext,
    chunk_name: bytes,
    session: ManualPaletteSession,
) -> tuple[str, ...]:
    full_new_data = manual_palette_full_new_data(session)
    return (
        "File:%s" % context.file,
        "ChunkName:%s" % chunk_name,
        "DataOffset:%s" % context.data_offset,
        "ChunkLength:%s" % context.chunk_length,
        "Before_New:%s" % session.before.hex(),
        "After_New:%s" % session.after[:20].hex(),
        "fullnewdatax:%s" % full_new_data.hex(),
        "Palette_nbr:%s" % session.palette_count,
    )


def encode_manual_palette_chunk_name(
    runtime: ManualPaletteSetupRuntime,
    chunk_name: object,
    *,
    debug: bool,
) -> object:
    if isinstance(chunk_name, bytes):
        return chunk_name
    if isinstance(chunk_name, bytearray):
        return bytes(chunk_name)

    try:
        return chunk_name.encode(errors="ignore")
    except Exception as exc:
        runtime.betterror(exc, "Tk_Manual_Plte")
        if debug is True:
            runtime.emit(
                runtime.candy("Color", "red", "Error:%s")
                % runtime.candy("Color", "yellow", exc)
            )
        return chunk_name


def create_manual_palette_session(
    *,
    data_hex: str,
    data_offset: int,
    chunk_length: int,
    chunk_name: bytes,
    guess_palette_count: GuessPaletteCount,
) -> ManualPaletteSession:
    before, after = manual_palette_slices(data_hex, data_offset, chunk_length)
    wanabyte = palette.initial_manual_palette_png(before, chunk_name, after)
    palette_count = guess_palette_count(before, after)
    return ManualPaletteSession(
        before=before,
        after=after,
        wanabyte=wanabyte,
        palette_count=palette_count,
        state=palette_ui.create_palette_editor_state(palette_count, wanabyte),
    )


def create_manual_palette_setup(
    runtime: ManualPaletteSetupRuntime,
    context: ManualPaletteSetupContext,
) -> ManualPaletteSetup:
    runtime.candy("Title", "Manually Bruteforcing Chunk Datas:")
    chunk_name = encode_manual_palette_chunk_name(
        runtime,
        context.chunk_name,
        debug=context.debug,
    )
    session = create_manual_palette_session(
        data_hex=context.data_hex,
        data_offset=context.data_offset,
        chunk_length=context.chunk_length,
        chunk_name=chunk_name,
        guess_palette_count=runtime.guess_palette_count,
    )

    if context.debug is True:
        for line in manual_palette_debug_lines(context, chunk_name, session):
            runtime.emit(line)

    image_array, pil_image = palette_ui.decode_preview_image(
        session.wanabyte,
        cv2_module=runtime.cv2,
        numpy_module=runtime.numpy,
        image_module=runtime.image,
    )
    return ManualPaletteSetup(
        chunk_name=chunk_name,
        session=session,
        image_array=image_array,
        pil_image=pil_image,
    )


def build_manual_palette_setup_runtime_from_namespace(namespace: dict) -> ManualPaletteSetupRuntime:
    return ManualPaletteSetupRuntime(
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        betterror=namespace["Betterror"],
        cv2=namespace["cv2"],
        numpy=namespace["np"],
        image=namespace["Image"],
        guess_palette_count=namespace["Guess_Palettes_Nbr"],
    )


def build_manual_palette_setup_context_from_namespace(
    namespace: dict,
    file: object,
    chunk_name: object,
    chunk_length: int,
    data_offset: int,
    data_hex: str | None = None,
) -> ManualPaletteSetupContext:
    return ManualPaletteSetupContext(
        file=file,
        chunk_name=chunk_name,
        chunk_length=chunk_length,
        data_offset=data_offset,
        data_hex=namespace["DATAX"] if data_hex is None else data_hex,
        debug=namespace["DEBUG"],
    )


def sync_palette_legacy_state(namespace: dict, palette_state) -> None:
    if palette_state is not None:
        namespace["Plte_Blst"] = palette_state.values
        namespace["slider_list"] = palette_state.sliders
        namespace["wanabyte"] = palette_state.wanabyte


def render_palette_preview_from_namespace(
    namespace: dict,
    wanabyte: bytes,
    width: int,
    height: int,
    frame_img: object | None = None,
    *,
    renderer: Callable = palette_ui.render_preview_label,
) -> None:
    if frame_img is not None:
        namespace["frame_img"] = frame_img
    im, pil_image, tk_image = renderer(
        wanabyte,
        namespace["frame_img"],
        width,
        height,
        cv2_module=namespace["cv2"],
        numpy_module=namespace["np"],
        image_module=namespace["Image"],
        image_tk_module=namespace["ImageTk"],
        tkinter_module=namespace["tkinter"],
    )
    namespace["im"] = im
    namespace["pil_image"] = pil_image
    namespace["tk_image"] = tk_image


def render_preview_accepts_frame(render_preview: Callable) -> bool:
    try:
        signature = inspect.signature(render_preview)
    except (TypeError, ValueError):
        return True
    positional_count = 0
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional_count += 1
    return positional_count >= 4


def build_layout_accepts_screen_height(build_layout: Callable) -> bool:
    try:
        signature = inspect.signature(build_layout)
    except (TypeError, ValueError):
        return True
    positional_count = 0
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional_count += 1
    return positional_count >= 3


def build_manual_palette_layout(
    build_layout: Callable,
    window: object,
    image_size: tuple[int, int],
) -> palette_ui.PaletteEditorLayout:
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight() if hasattr(window, "winfo_screenheight") else None
    if screen_height is not None and build_layout_accepts_screen_height(build_layout):
        return build_layout(screen_width, image_size, screen_height)
    return build_layout(screen_width, image_size)


def render_manual_palette_preview(
    render_preview: Callable,
    wanabyte: bytes,
    width: int,
    height: int,
    frame_img: object,
) -> None:
    if render_preview_accepts_frame(render_preview):
        render_preview(wanabyte, width, height, frame_img)
    else:
        render_preview(wanabyte, width, height)


def update_palette_value_from_namespace(
    namespace: dict,
    event: object,
    nbr: object,
    before: bytes,
    after: bytes,
    width: int,
    height: int,
) -> bytes:
    if namespace["palette_state"] is not None:
        wanabyte = palette_ui.update_palette_state_value(
            namespace["palette_state"],
            index=int(nbr),
            raw_value=event,
            before=before,
            after=after,
        )
        namespace["Sync_Palette_Legacy_State"]()
    else:
        palette.set_palette_value(namespace["Plte_Blst"], int(nbr), event)
        wanabyte = palette.build_palette_png(before, namespace["Plte_Blst"], after)
        namespace["wanabyte"] = wanabyte

    namespace["Tk_Render_Plte_Preview"](wanabyte, width, height)
    return wanabyte


def apply_palette_colors_from_namespace(
    namespace: dict,
    colors,
    before: bytes,
    after: bytes,
    width: int,
    height: int,
) -> bytes:
    if namespace["palette_state"] is not None:
        wanabyte = palette_ui.apply_palette_state_colors(
            namespace["palette_state"],
            colors=colors,
            before=before,
            after=after,
        )
        namespace["Sync_Palette_Legacy_State"]()
    else:
        palette_ui.apply_color_table(namespace["Plte_Blst"], namespace["slider_list"], colors)
        wanabyte = palette.build_palette_png(before, namespace["Plte_Blst"], after)
        namespace["wanabyte"] = wanabyte

    namespace["Tk_Render_Plte_Preview"](wanabyte, width, height)
    return wanabyte


def apply_random_palette_colors_from_namespace(
    namespace: dict,
    colors,
    before: bytes,
    after: bytes,
    width: int,
    height: int,
) -> bytes:
    return apply_palette_colors_from_namespace(
        namespace,
        namespace["random"].sample(colors, len(colors)),
        before,
        after,
        width,
        height,
    )


def randomize_palette_from_namespace(
    namespace: dict,
    before: bytes,
    after: bytes,
    width: int,
    height: int,
) -> bytes:
    if namespace["palette_state"] is not None:
        wanabyte = palette_ui.randomize_palette_state(
            namespace["palette_state"],
            random_int=namespace["random"].randint,
            before=before,
            after=after,
        )
        namespace["Sync_Palette_Legacy_State"]()
    else:
        palette_ui.random_palette_values(
            namespace["Plte_Blst"],
            namespace["slider_list"],
            namespace["random"].randint,
        )
        wanabyte = palette.build_palette_png(before, namespace["Plte_Blst"], after)
        namespace["wanabyte"] = wanabyte

    namespace["Tk_Render_Plte_Preview"](wanabyte, width, height)
    return wanabyte


def manual_palette_save_active_state(context: ManualPaletteSaveContext) -> tuple[list, list, bytes]:
    if context.palette_state is not None:
        return (
            context.palette_state.values,
            context.palette_state.sliders,
            context.palette_state.wanabyte,
        )
    return context.fallback_values, context.fallback_sliders, context.wanabyte


def save_manual_palette(
    runtime: ManualPaletteSaveRuntime,
    context: ManualPaletteSaveContext,
) -> palette_ui.PaletteSaveCheckpoint:
    active_values, active_sliders, active_wanabyte = manual_palette_save_active_state(context)

    for slider in active_sliders:
        slider.clean()

    context.window.destroy()
    context.window.quit()

    return runtime.save_checkpoint(
        cancel=context.cancel,
        palette_values=active_values,
        wanabyte=active_wanabyte,
        chunk_length=context.chunk_length,
        data_offset=context.data_offset,
        from_error=context.from_error,
    )


def save_manual_palette_from_namespace(
    namespace: dict,
    window: object,
    cancel: bool,
    chunk_length: int,
    data_offset: int,
    from_error: object,
    wanabyte: bytes,
) -> object:
    checkpoint_call = save_manual_palette(
        ManualPaletteSaveRuntime(),
        ManualPaletteSaveContext(
            window=window,
            cancel=cancel,
            chunk_length=chunk_length,
            data_offset=data_offset,
            from_error=from_error,
            wanabyte=wanabyte,
            palette_state=namespace["palette_state"],
            fallback_values=namespace["Plte_Blst"],
            fallback_sliders=namespace["slider_list"],
        ),
    )
    return namespace["CheckPoint"](
        checkpoint_call.error,
        checkpoint_call.fixed,
        checkpoint_call.function,
        checkpoint_call.chunk,
        list(checkpoint_call.infos),
        *checkpoint_call.toolkit,
    )


def build_manual_palette_action_specs(
    runtime: ManualPaletteActionRuntime,
    context: ManualPaletteActionContext,
) -> tuple[palette_ui.PaletteActionButtonSpec, ...]:
    return runtime.build_specs(
        web_safe=lambda: runtime.web_safe(
            bfn=context.before,
            afn=context.after,
            h=context.height,
            w=context.width,
        ),
        web_random=lambda: runtime.web_random(
            bfn=context.before,
            afn=context.after,
            h=context.height,
            w=context.width,
        ),
        x11=lambda: runtime.x11(
            bfn=context.before,
            afn=context.after,
            h=context.height,
            w=context.width,
        ),
        x11_random=lambda: runtime.x11_random(
            bfn=context.before,
            afn=context.after,
            h=context.height,
            w=context.width,
        ),
        randomize=lambda: runtime.randomize(
            bfn=context.before,
            afn=context.after,
            h=context.height,
            w=context.width,
        ),
        save=lambda: runtime.save_palette(
            context.window,
            False,
            context.chunk_length,
            context.data_offset,
            context.from_error,
            context.wanabyte,
        ),
        cancel=lambda: runtime.save_palette(
            context.window,
            True,
            context.chunk_length,
            context.data_offset,
            context.from_error,
            context.wanabyte,
        ),
    )


def create_manual_palette_editor(
    runtime: ManualPaletteEditorRuntime,
    context: ManualPaletteEditorContext,
) -> ManualPaletteEditor:
    window = runtime.create_window(
        tkinter_module=runtime.tkinter_module,
        title=context.title,
    )
    layout = build_manual_palette_layout(runtime.build_layout, window, context.pil_image.size)
    frames = runtime.create_frames(
        tkinter_module=runtime.tkinter_module,
        window=window,
        layout=layout,
    )

    render_manual_palette_preview(
        runtime.render_preview,
        context.session.wanabyte,
        layout.basewidth,
        layout.hsize,
        frames.img,
    )
    build_action_specs = runtime.build_action_specs or build_manual_palette_action_specs

    action_buttons = runtime.create_buttons(
        tkinter_module=runtime.tkinter_module,
        master=frames.action,
        specs=build_action_specs(
            context.action_runtime,
            ManualPaletteActionContext(
                before=context.session.before,
                after=context.session.after,
                height=layout.hsize,
                width=layout.basewidth,
                window=window,
                chunk_length=context.chunk_length,
                data_offset=context.data_offset,
                from_error=context.from_error,
                wanabyte=context.session.wanabyte,
            ),
        ),
        grid_options={"padx": 10, "pady": 5},
    )

    slider_canvas = runtime.create_slider_canvas(
        tkinter_module=runtime.tkinter_module,
        master=frames.slider,
        height=layout.hsize,
        width=layout.canvas_width,
        canvas_grid_options={"row": 0, "column": 1, "padx": 10, "pady": 5},
        scrollbar_grid_options={"row": 0, "column": 0, "sticky": "ns"},
    )
    sliders = runtime.create_sliders(
        palette_count=context.session.palette_count,
        scale_factory=context.scale_factory,
        master=slider_canvas.frame,
        before=context.session.before,
        after=context.session.after,
        height=layout.hsize,
        width=layout.basewidth,
        slider_length=layout.slider_length,
    )
    runtime.set_state_sliders(context.session.state, sliders)
    runtime.bind_slider_scrollregion(slider_canvas, sliders)
    runtime.bind_slider_mousewheel(slider_canvas, sliders)
    runtime.refresh_slider_canvas(slider_canvas, sliders)
    runtime.center_window(window, layout)

    return ManualPaletteEditor(
        window=window,
        layout=layout,
        frames=frames,
        action_buttons=action_buttons,
        slider_canvas=slider_canvas,
        sliders=sliders,
    )


def build_manual_palette_action_runtime_from_namespace(namespace: dict) -> ManualPaletteActionRuntime:
    return ManualPaletteActionRuntime(
        web_safe=namespace["Tk_Web_Safe_Plte"],
        web_random=namespace["Tk_Web_Safe_Randomize_Plte"],
        x11=namespace["Tk_X11_Plte"],
        x11_random=namespace["Tk_X11_Randomize_Plte"],
        randomize=namespace["Tk_Randomize_Plte"],
        save_palette=namespace["Tk_Save_Plte"],
    )


def build_manual_palette_editor_runtime_from_namespace(namespace: dict) -> ManualPaletteEditorRuntime:
    return ManualPaletteEditorRuntime(
        tkinter_module=namespace["tkinter"],
        render_preview=namespace["Tk_Render_Plte_Preview"],
    )


def build_manual_palette_editor_context_from_namespace(
    namespace: dict,
    setup: ManualPaletteSetup,
    chunk_length: int,
    data_offset: int,
    from_error: object,
) -> ManualPaletteEditorContext:
    return ManualPaletteEditorContext(
        title="PLTE Editor:%s" % namespace["FILE_Origin"],
        session=setup.session,
        pil_image=setup.pil_image,
        chunk_length=chunk_length,
        data_offset=data_offset,
        from_error=from_error,
        scale_factory=namespace["Tk_Gen_Scale_Plte"],
        update_scrollregion=namespace["Tk_update_scrollregion_Plte"],
        action_runtime=build_manual_palette_action_runtime_from_namespace(namespace),
    )


def sync_manual_palette_editor_namespace(
    namespace: dict,
    setup: ManualPaletteSetup,
    editor: ManualPaletteEditor,
) -> None:
    session = setup.session
    namespace["wanabyte"] = session.wanabyte
    namespace["palette_state"] = session.state
    namespace["Plte_Blst"] = session.state.values
    namespace["im"] = setup.image_array
    namespace["pil_image"] = setup.pil_image
    namespace["window"] = editor.window
    namespace["frame_img"] = editor.frames.img
    namespace["canvas_slider"] = editor.slider_canvas.canvas
    namespace["slider_list"] = editor.sliders
    namespace["Sync_Palette_Legacy_State"]()


def create_manual_palette_editor_from_namespace(
    namespace: dict,
    file: object,
    chunk_name: object,
    chunk_length: int,
    data_offset: int,
    from_error: object,
    *,
    data_hex: str | None = None,
    setup_creator: Callable = create_manual_palette_setup,
    editor_creator: Callable = create_manual_palette_editor,
) -> ManualPaletteEditor:
    setup = setup_creator(
        build_manual_palette_setup_runtime_from_namespace(namespace),
        build_manual_palette_setup_context_from_namespace(
            namespace,
            file,
            chunk_name,
            chunk_length,
            data_offset,
            data_hex,
        ),
    )
    namespace["wanabyte"] = setup.session.wanabyte
    namespace["palette_state"] = setup.session.state
    namespace["Plte_Blst"] = setup.session.state.values
    namespace["im"] = setup.image_array
    namespace["pil_image"] = setup.pil_image

    editor = editor_creator(
        build_manual_palette_editor_runtime_from_namespace(namespace),
        build_manual_palette_editor_context_from_namespace(
            namespace,
            setup,
            chunk_length,
            data_offset,
            from_error,
        ),
    )
    sync_manual_palette_editor_namespace(namespace, setup, editor)
    return editor


def guess_palette_count(
    runtime: PaletteCountGuessRuntime,
    context: PaletteCountGuessContext,
    before: bytes,
    after: bytes,
) -> int:
    if (
        runtime.cv2 is None
        or runtime.numpy is None
        or runtime.image is None
        or runtime.imagehash is None
    ):
        return fallback_palette_count(runtime, context)

    hashes = []
    palette_guess_count = None
    palette_values = []

    for index, color in enumerate(context.x11_colors):
        palette_values.append(int(color, 16))
        wanabyte = runtime.build_palette_png(before, palette_values, after)
        stderr = io.BytesIO()
        image_array = None

        with runtime.stderr_redirector(stderr):
            try:
                image_array = runtime.cv2.imdecode(
                    runtime.numpy.frombuffer(wanabyte, runtime.numpy.uint8),
                    -1,
                )
            except Exception as exc:
                runtime.betterror(exc, "Guess_Palettes_Nbr")
                runtime.raw_print("-Error Guess_Palettes_Nbr():", exc)

        result = "{0}".format(stderr.getvalue().decode("utf-8"))
        if any(error in result for error in context.libpng_errors):
            runtime.raw_print("-Error Guess_Palettes_Nbr():", result)
            runtime.end()
            continue

        if image_array is None:
            runtime.betterror(ValueError("Could not decode PLTE candidate"), "Guess_Palettes_Nbr")
            runtime.raw_print("-Error Guess_Palettes_Nbr():", "Could not decode PLTE candidate")
            runtime.end()
            continue

        try:
            pil_image = runtime.image.fromarray(image_array)
        except Exception as exc:
            runtime.betterror(exc, "Guess_Palettes_Nbr")
            runtime.raw_print("-Error Guess_Palettes_Nbr():", exc)
            runtime.end()
            continue

        current_hash = runtime.imagehash.phash(pil_image)
        hashes.append(current_hash)
        if len(hashes) > 1:
            distance_last = hashes[-2] - hashes[-1]
            if distance_last != 0:
                palette_guess_count = index

    if palette_guess_count:
        runtime.emit(
            "-PLTE palettes number estimation: %s"
            % runtime.candy("Color", "green", str(palette_guess_count))
        )
        runtime.side_notes.append("-PLTE palettes number estimation: %s" % str(palette_guess_count))
        return palette_guess_count

    runtime.emit(runtime.candy("Color", "yellow", "Warning:%s") % "Could not estimate palette number.")
    runtime.side_notes.append(
        "Warning:Could not estimate palette number.Returning Max Palettes number according to IHDR Depht"
    )
    return max_palette_count(context)


def max_palette_count(context: PaletteCountGuessContext) -> int:
    try:
        bit_depth = int(context.ihdr_depth)
    except (TypeError, ValueError):
        bit_depth = 8
    return 2 ** bit_depth - 1


def fallback_palette_count(
    runtime: PaletteCountGuessRuntime,
    context: PaletteCountGuessContext,
) -> int:
    runtime.emit(
        runtime.candy("Color", "yellow", "Warning:%s")
        % "Could not estimate palette number; using max palettes from IHDR depth."
    )
    runtime.side_notes.append(
        "Warning:Could not estimate palette number.Returning Max Palettes number according to IHDR Depht"
    )
    return max_palette_count(context)


def build_palette_count_guess_runtime_from_namespace(namespace: dict) -> PaletteCountGuessRuntime:
    return PaletteCountGuessRuntime(
        cv2=namespace["cv2"],
        numpy=namespace["np"],
        image=namespace["Image"],
        imagehash=namespace["imagehash"],
        stderr_redirector=namespace["stderr_redirector"],
        betterror=namespace["Betterror"],
        emit=namespace["PRINT"],
        candy=namespace["Candy"],
        end=namespace["TheEnd"],
        raw_print=namespace.get("print", print),
        side_notes=namespace["SideNotes"],
    )


def build_palette_count_guess_context_from_namespace(namespace: dict) -> PaletteCountGuessContext:
    return PaletteCountGuessContext(
        x11_colors=tuple(namespace["X11_Colors"]),
        libpng_errors=tuple(namespace["LIBPNG_ERR"]),
        ihdr_depth=namespace["IHDR_Depht"],
    )


def guess_palette_count_from_namespace(
    namespace: dict,
    before: bytes,
    after: bytes,
) -> int:
    return guess_palette_count(
        build_palette_count_guess_runtime_from_namespace(namespace),
        build_palette_count_guess_context_from_namespace(namespace),
        before,
        after,
    )
