from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
import os
import time
from typing import Any

from . import idat
from . import idat_bruteforce


EDITOR_CANVAS_MARGIN = 32
FULL_REGION = (0.0, 0.0, 1.0, 1.0)
ROI_CANDIDATE_OUTLINE = "yellow"
ROI_REFERENCE_OUTLINE = "cyan"
ROI_NEGATIVE_OUTLINE = "#ff4d4d"
ROI_HOVER_DELAY_MS = 500


def _hidden_tmp_path(path: str) -> str:
    directory, filename = os.path.split(path)
    tmp_name = ".%s.%s.%s.tmp" % (
        filename or "chunklate",
        os.getpid(),
        time.monotonic_ns(),
    )
    return os.path.join(directory, tmp_name) if directory else tmp_name


@dataclass(frozen=True)
class ReferenceRegionEditorResult:
    saved: bool
    path: str
    warning: str = ""
    region_count: int = 0


def describe_reference_region(
    region: idat_bruteforce.UltimateReferenceRegion,
    side: str,
) -> str:
    label = region.label or "ROI"
    mode = idat_bruteforce._coerce_ultimate_roi_match_mode(region.match_mode)
    if mode == "negative":
        return "%s: negative ROI. Candidate noise and artifacts should stay low here." % label
    if mode == "single":
        return "%s: single ROI. Candidate area is compared to the pre-Ultimate snapshot." % label
    if mode == "search":
        if region.candidate_region == FULL_REGION:
            return "%s: search ROI. This reference pattern is searched anywhere in the candidate." % label
        if region.reference_region == FULL_REGION:
            return "%s: search ROI. This source pattern is searched anywhere in the reference." % label
        return "%s: search ROI. Best matching area is searched on the other image." % label
    if region.candidate_region == region.reference_region:
        return "%s: paired ROI. Same normalized position, with a tiny candidate shift allowed." % label
    return "%s: paired ROI. Source and reference rectangles are compared, with a tiny candidate shift allowed." % label


def point_in_bbox(
    point: tuple[float, float],
    bbox: tuple[float, float, float, float],
) -> bool:
    x, y = point
    left, top, right, bottom = bbox
    return left <= x <= right and top <= y <= bottom


def has_unsaved_region_state(
    region_count: int,
    candidate_pending: object | None,
    reference_pending: object | None,
) -> bool:
    return region_count > 0 or candidate_pending is not None or reference_pending is not None


def normalize_display_bbox(
    bbox: tuple[float, float, float, float],
    size: tuple[int, int],
) -> tuple[float, float, float, float] | None:
    width, height = size
    if width <= 0 or height <= 0:
        return None
    x0, y0, x1, y1 = bbox
    left = min(x0, x1) / width
    right = max(x0, x1) / width
    top = min(y0, y1) / height
    bottom = max(y0, y1) / height
    return idat_bruteforce._coerce_ultimate_region((left, top, right, bottom))


def normalize_canvas_bbox_to_image(
    bbox: tuple[float, float, float, float],
    image_box: tuple[float, float, float, float],
    *,
    min_image_overlap: float = 0.5,
) -> tuple[float, float, float, float] | None:
    x0, y0, x1, y1 = bbox
    left = min(x0, x1)
    right = max(x0, x1)
    top = min(y0, y1)
    bottom = max(y0, y1)
    selection_area = max(0.0, right - left) * max(0.0, bottom - top)
    if selection_area <= 0:
        return None

    image_left, image_top, image_right, image_bottom = image_box
    image_width = image_right - image_left
    image_height = image_bottom - image_top
    if image_width <= 0 or image_height <= 0:
        return None

    clipped_left = max(left, image_left)
    clipped_top = max(top, image_top)
    clipped_right = min(right, image_right)
    clipped_bottom = min(bottom, image_bottom)
    clipped_area = max(0.0, clipped_right - clipped_left) * max(0.0, clipped_bottom - clipped_top)
    if clipped_area / selection_area < min_image_overlap:
        return None

    return idat_bruteforce._coerce_ultimate_region(
        (
            (clipped_left - image_left) / image_width,
            (clipped_top - image_top) / image_height,
            (clipped_right - image_left) / image_width,
            (clipped_bottom - image_top) / image_height,
        )
    )


def _fit_size(
    size: tuple[int, int],
    *,
    max_width: int = 620,
    max_height: int = 520,
    allow_upscale: bool = False,
) -> tuple[int, int]:
    width, height = size
    if width <= 0 or height <= 0:
        return (1, 1)
    scale = min(1.0, max_width / float(width), max_height / float(height))
    if allow_upscale:
        scale = min(max_width / float(width), max_height / float(height))
    return (max(1, int(round(width * scale))), max(1, int(round(height * scale))))


def _source_preview_data(data: bytes) -> bytes | None:
    for repairer in (
        idat.rebuild_visual_idat_preview,
        idat.rebuild_tolerant_idat_salvage,
        idat.rebuild_partial_idat_blackfill,
    ):
        try:
            repair = repairer(data)
        except Exception:
            repair = None
        if repair is not None:
            return repair.data
    return None


def _decode_rgba_bytes(data: bytes):
    from PIL import Image

    image = Image.open(BytesIO(data)).convert("RGBA")
    image.load()
    return image


def _load_image(path: str, *, fallback_data: bytes = b""):
    original_data = b""
    if path and os.path.exists(path):
        with open(path, "rb") as file:
            original_data = file.read()
        try:
            return _decode_rgba_bytes(original_data), original_data
        except Exception:
            if not fallback_data:
                raise
    if fallback_data:
        try:
            return _decode_rgba_bytes(fallback_data), fallback_data
        except Exception:
            preview_data = _source_preview_data(fallback_data)
            if preview_data is not None:
                return _decode_rgba_bytes(preview_data), fallback_data
    raise FileNotFoundError(path)


def _write_region_mapping(
    path: str,
    *,
    candidate_image,
    candidate_data: bytes,
    reference_image,
    regions: tuple[idat_bruteforce.UltimateReferenceRegion, ...],
) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    record = idat_bruteforce.build_ultimate_reference_regions_record(
        candidate_size=tuple(int(value) for value in candidate_image.size),
        reference_size=tuple(int(value) for value in reference_image.size),
        candidate_hash=idat_bruteforce._ultimate_image_hash_from_bytes(candidate_data),
        reference_hash=idat_bruteforce._ultimate_image_hash_from_image(reference_image),
        regions=regions,
    )
    tmp_path = _hidden_tmp_path(path)
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(record, file, sort_keys=True, indent=2)
        file.write("\n")
    os.replace(tmp_path, path)


def open_ultimate_reference_region_editor(
    candidate_path: str,
    reference_path: str,
    output_path: str,
    *,
    candidate_data: bytes = b"",
    tkinter_module: Any | None = None,
    image_tk_module: Any | None = None,
) -> ReferenceRegionEditorResult:
    try:
        import tkinter as tk
        from tkinter import messagebox
        from PIL import ImageTk

        tk = tkinter_module or tk
        ImageTk = image_tk_module or ImageTk
        candidate_image, candidate_bytes = _load_image(candidate_path, fallback_data=candidate_data)
        if candidate_data:
            candidate_bytes = candidate_data
        reference_image, _reference_bytes = _load_image(reference_path)
    except Exception as exc:
        return ReferenceRegionEditorResult(False, output_path, "reference region editor unavailable: %s" % exc)

    try:
        root = tk.Tk()
        root.title("Chunklate Ultimate reference regions")
        root.geometry("+80+80")

        candidate_display_size = _fit_size(candidate_image.size)
        reference_display_size = _fit_size(reference_image.size)

        result = {"saved": False, "warning": "", "region_count": 0}
        pending: dict[str, tuple[float, float, float, float] | None] = {
            "candidate": None,
            "reference": None,
        }
        start: dict[str, tuple[float, float] | None] = {"candidate": None, "reference": None}
        drag_item: dict[str, Any] = {"candidate": None, "reference": None}
        pairs: list[idat_bruteforce.UltimateReferenceRegion] = []
        redo_stack: list[idat_bruteforce.UltimateReferenceRegion] = []
        roi_hover_regions: dict[str, list[tuple[tuple[float, float, float, float], str]]] = {
            "candidate": [],
            "reference": [],
        }
        roi_hover: dict[str, Any] = {"after": None, "message": ""}
        side_state: dict[str, dict[str, Any]] = {
            "candidate": {
                "image": candidate_image,
                "display_size": candidate_display_size,
                "image_box": (0.0, 0.0, float(candidate_display_size[0]), float(candidate_display_size[1])),
                "photo": None,
                "image_item": None,
            },
            "reference": {
                "image": reference_image,
                "display_size": reference_display_size,
                "image_box": (0.0, 0.0, float(reference_display_size[0]), float(reference_display_size[1])),
                "photo": None,
                "image_item": None,
            },
        }

        container = tk.Frame(root)
        container.pack(fill="both", expand=True)
        left_frame = tk.Frame(container)
        right_frame = tk.Frame(container)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        tk.Label(left_frame, text="Ultimate source snapshot").grid(row=0, column=0, sticky="w")
        tk.Label(right_frame, text="Reference").grid(row=0, column=0, sticky="w")
        candidate_canvas = tk.Canvas(
            left_frame,
            width=candidate_display_size[0] + EDITOR_CANVAS_MARGIN * 2,
            height=candidate_display_size[1] + EDITOR_CANVAS_MARGIN * 2,
            cursor="crosshair",
            bg="#d7d7d7",
            highlightthickness=0,
        )
        reference_canvas = tk.Canvas(
            right_frame,
            width=reference_display_size[0] + EDITOR_CANVAS_MARGIN * 2,
            height=reference_display_size[1] + EDITOR_CANVAS_MARGIN * 2,
            cursor="crosshair",
            bg="#d7d7d7",
            highlightthickness=0,
        )
        candidate_canvas.grid(row=1, column=0, sticky="nsew")
        reference_canvas.grid(row=1, column=0, sticky="nsew")
        status = tk.Label(
            root,
            text="Draw on either image, then draw its match on the other one. Same rectangle can complete the pair.",
        )
        status.pack(anchor="w", padx=8)

        def canvas_for(side: str):
            return candidate_canvas if side == "candidate" else reference_canvas

        def add_tooltip(widget, text: str) -> None:
            tip = {"window": None}

            def show(_event=None) -> None:
                if tip["window"] is not None:
                    return
                try:
                    x = widget.winfo_rootx() + 12
                    y = widget.winfo_rooty() + widget.winfo_height() + 8
                    window = tk.Toplevel(widget)
                    window.wm_overrideredirect(True)
                    window.wm_geometry("+%d+%d" % (x, y))
                    label = tk.Label(
                        window,
                        text=text,
                        justify="left",
                        background="#ffffe0",
                        relief="solid",
                        borderwidth=1,
                        padx=6,
                        pady=3,
                    )
                    label.pack()
                    tip["window"] = window
                except Exception:
                    tip["window"] = None

            def hide(_event=None) -> None:
                window = tip.get("window")
                tip["window"] = None
                if window is not None:
                    try:
                        window.destroy()
                    except Exception:
                        pass

            widget.bind("<Enter>", show)
            widget.bind("<Leave>", hide)

        def cancel_roi_hover() -> None:
            after_id = roi_hover.get("after")
            roi_hover["after"] = None
            roi_hover["message"] = ""
            if after_id is not None:
                try:
                    root.after_cancel(after_id)
                except Exception:
                    pass

        def schedule_roi_hover(message: str) -> None:
            cancel_roi_hover()
            roi_hover["message"] = message

            def show_message() -> None:
                roi_hover["after"] = None
                if roi_hover.get("message") == message:
                    status.config(text=message)

            try:
                roi_hover["after"] = root.after(ROI_HOVER_DELAY_MS, show_message)
            except Exception:
                status.config(text=message)

        def clear_redo_stack() -> None:
            redo_stack.clear()

        def canvas_motion(side: str, event) -> None:
            point = (float(event.x), float(event.y))
            for bbox, message in reversed(roi_hover_regions[side]):
                if point_in_bbox(point, bbox):
                    if roi_hover.get("message") != message:
                        schedule_roi_hover(message)
                    return
            cancel_roi_hover()

        def region_to_canvas_bbox(
            side: str,
            region: tuple[float, float, float, float],
        ) -> tuple[float, float, float, float]:
            image_left, image_top, image_right, image_bottom = side_state[side]["image_box"]
            image_width = image_right - image_left
            image_height = image_bottom - image_top
            return (
                image_left + region[0] * image_width,
                image_top + region[1] * image_height,
                image_left + region[2] * image_width,
                image_top + region[3] * image_height,
            )

        def redraw_side(side: str) -> None:
            canvas = canvas_for(side)
            state = side_state[side]
            cancel_roi_hover()
            width = int(canvas.winfo_width())
            height = int(canvas.winfo_height())
            if width <= 1:
                width = int(canvas.cget("width"))
            if height <= 1:
                height = int(canvas.cget("height"))
            width = max(1, width)
            height = max(1, height)
            display_size = _fit_size(
                state["image"].size,
                max_width=max(1, width - EDITOR_CANVAS_MARGIN * 2),
                max_height=max(1, height - EDITOR_CANVAS_MARGIN * 2),
                allow_upscale=True,
            )
            left = max(0, (width - display_size[0]) // 2)
            top = max(0, (height - display_size[1]) // 2)
            state["display_size"] = display_size
            state["image_box"] = (
                float(left),
                float(top),
                float(left + display_size[0]),
                float(top + display_size[1]),
            )
            display = state["image"].resize(display_size, idat_bruteforce._pil_lanczos_filter())
            photo = ImageTk.PhotoImage(display)
            state["photo"] = photo
            if state["image_item"] is None:
                state["image_item"] = canvas.create_image(left, top, image=photo, anchor="nw", tags=("image",))
            else:
                canvas.coords(state["image_item"], left, top)
                canvas.itemconfigure(state["image_item"], image=photo)
            canvas.tag_lower(state["image_item"])
            canvas.delete("roi")
            roi_hover_regions[side].clear()
            outline = ROI_CANDIDATE_OUTLINE if side == "candidate" else ROI_REFERENCE_OUTLINE
            for region in pairs:
                mode = idat_bruteforce._coerce_ultimate_roi_match_mode(region.match_mode)
                if mode == "search" and side == "candidate" and region.candidate_region == FULL_REGION:
                    continue
                if mode in {"search", "single", "negative"} and side == "reference" and region.reference_region == FULL_REGION:
                    continue
                if mode in {"single", "negative"} and side == "reference":
                    continue
                roi = region.candidate_region if side == "candidate" else region.reference_region
                item_outline = ROI_NEGATIVE_OUTLINE if mode == "negative" else outline
                bbox = region_to_canvas_bbox(side, roi)
                canvas.create_rectangle(
                    *bbox,
                    outline=item_outline,
                    width=2,
                    tags=("roi",),
                )
                message = describe_reference_region(region, side)
                roi_hover_regions[side].append((bbox, message))
            if pending.get(side) is not None:
                canvas.create_rectangle(
                    *region_to_canvas_bbox(side, pending[side]),
                    outline=outline,
                    width=2,
                    dash=(4, 3),
                    tags=("roi",),
                )

        def redraw_all() -> None:
            redraw_side("candidate")
            redraw_side("reference")

        def complete_pending_pair() -> bool:
            candidate_region = pending.get("candidate")
            reference_region = pending.get("reference")
            if candidate_region is None or reference_region is None:
                waiting_for = "reference" if candidate_region is not None else "source"
                status.config(text="Now draw the matching rectangle on the %s, or use Same rectangle." % waiting_for)
                return False
            label = "ROI %s" % (len(pairs) + 1)
            clear_redo_stack()
            pairs.append(
                idat_bruteforce.UltimateReferenceRegion(
                    candidate_region=candidate_region,
                    reference_region=reference_region,
                    weight=1.0,
                    label=label,
                    match_mode="paired",
                )
            )
            pending["candidate"] = None
            pending["reference"] = None
            status.config(text="%s saved as paired ROI." % label)
            redraw_all()
            return True

        def ask_single_rectangle_mode(side: str) -> str | None:
            try:
                if side == "reference":
                    answer = messagebox.askyesnocancel(
                        "Single reference rectangle",
                        "Keep the same normalized position in the candidate?\n\n"
                        "Yes: compare the same area.\n"
                        "No: search this reference pattern in the whole candidate.",
                        parent=root,
                    )
                else:
                    answer = messagebox.askyesnocancel(
                        "Single source rectangle",
                        "Compare this source area to the pre-Ultimate snapshot?\n\n"
                        "Yes: compare the same source area.\n"
                        "No: search this source pattern in the whole reference.",
                        parent=root,
                    )
            except Exception:
                answer = True
            if answer is None:
                return None
            if side == "reference":
                return "paired" if answer else "search"
            return "single" if answer else "search"

        def begin(side: str, event) -> None:
            pending[side] = None
            redraw_all()
            start[side] = (float(event.x), float(event.y))
            canvas = canvas_for(side)
            if drag_item[side] is not None:
                canvas.delete(drag_item[side])
            color = ROI_CANDIDATE_OUTLINE if side == "candidate" else ROI_REFERENCE_OUTLINE
            drag_item[side] = canvas.create_rectangle(
                event.x,
                event.y,
                event.x,
                event.y,
                outline=color,
                width=2,
                tags=("drag",),
            )

        def drag(side: str, event) -> None:
            origin = start[side]
            item = drag_item[side]
            if origin is None or item is None:
                return
            canvas_for(side).coords(item, origin[0], origin[1], event.x, event.y)

        def end(side: str, event) -> None:
            origin = start[side]
            item = drag_item[side]
            start[side] = None
            drag_item[side] = None
            if origin is None or item is None:
                return
            region = normalize_canvas_bbox_to_image(
                (origin[0], origin[1], float(event.x), float(event.y)),
                side_state[side]["image_box"],
            )
            canvas_for(side).delete(item)
            if region is None:
                status.config(text="Selection is mostly outside the image. Try again.")
                redraw_all()
                return
            pending[side] = region
            complete_pending_pair()
            redraw_all()

        candidate_canvas.bind("<ButtonPress-1>", lambda event: begin("candidate", event))
        candidate_canvas.bind("<Motion>", lambda event: canvas_motion("candidate", event))
        candidate_canvas.bind("<B1-Motion>", lambda event: drag("candidate", event))
        candidate_canvas.bind("<ButtonRelease-1>", lambda event: end("candidate", event))
        candidate_canvas.bind("<Leave>", lambda _event: cancel_roi_hover())
        reference_canvas.bind("<ButtonPress-1>", lambda event: begin("reference", event))
        reference_canvas.bind("<Motion>", lambda event: canvas_motion("reference", event))
        reference_canvas.bind("<B1-Motion>", lambda event: drag("reference", event))
        reference_canvas.bind("<ButtonRelease-1>", lambda event: end("reference", event))
        reference_canvas.bind("<Leave>", lambda _event: cancel_roi_hover())
        candidate_canvas.bind("<Configure>", lambda _event: redraw_all())
        reference_canvas.bind("<Configure>", lambda _event: redraw_all())

        def same_rectangle() -> None:
            if pending.get("candidate") is None and pending.get("reference") is None:
                status.config(text="Draw one rectangle first, then press Draw Same Rectangle.")
                return
            if pending.get("candidate") is None:
                pending["candidate"] = pending["reference"]
            if pending.get("reference") is None:
                pending["reference"] = pending["candidate"]
            complete_pending_pair()

        def add_single_rectangle() -> None:
            candidate_region = pending.get("candidate")
            reference_region = pending.get("reference")
            if candidate_region is None and reference_region is None:
                status.config(text="Draw one rectangle first, then press Add Single Rectangle.")
                return
            label = "ROI %s" % (len(pairs) + 1)
            if reference_region is not None:
                mode = ask_single_rectangle_mode("reference")
                if mode is None:
                    status.config(text="Single rectangle kept pending.")
                    redraw_all()
                    return
                if mode == "paired":
                    clear_redo_stack()
                    pairs.append(
                        idat_bruteforce.UltimateReferenceRegion(
                            candidate_region=reference_region,
                            reference_region=reference_region,
                            weight=1.0,
                            label=label,
                            match_mode="paired",
                        )
                    )
                    message = "%s saved as same-position paired ROI." % label
                else:
                    clear_redo_stack()
                    pairs.append(
                        idat_bruteforce.UltimateReferenceRegion(
                            candidate_region=FULL_REGION,
                            reference_region=reference_region,
                            weight=1.0,
                            label=label,
                            match_mode="search",
                        )
                    )
                    message = "%s saved as whole-image search ROI." % label
            else:
                mode = ask_single_rectangle_mode("candidate")
                if mode is None:
                    status.config(text="Single rectangle kept pending.")
                    redraw_all()
                    return
                if mode == "search":
                    clear_redo_stack()
                    pairs.append(
                        idat_bruteforce.UltimateReferenceRegion(
                            candidate_region=candidate_region,
                            reference_region=FULL_REGION,
                            weight=1.0,
                            label=label,
                            match_mode="search",
                        )
                    )
                    message = "%s saved as whole-reference search ROI." % label
                else:
                    clear_redo_stack()
                    pairs.append(
                        idat_bruteforce.UltimateReferenceRegion(
                            candidate_region=candidate_region,
                            reference_region=FULL_REGION,
                            weight=1.0,
                            label=label,
                            match_mode="single",
                        )
                    )
                    message = "%s saved as single ROI." % label
            pending["candidate"] = None
            pending["reference"] = None
            redraw_all()
            status.config(text=message)

        def add_negative_rectangle() -> None:
            candidate_region = pending.get("candidate")
            if candidate_region is None:
                status.config(text="Draw one rectangle on the source first, then press Add Negative Rectangle.")
                return
            label = "ROI %s" % (len(pairs) + 1)
            clear_redo_stack()
            pairs.append(
                idat_bruteforce.UltimateReferenceRegion(
                    candidate_region=candidate_region,
                    reference_region=FULL_REGION,
                    weight=1.0,
                    label=label,
                    match_mode="negative",
                )
            )
            pending["candidate"] = None
            pending["reference"] = None
            redraw_all()
            status.config(text="%s saved as negative ROI." % label)

        def delete_last() -> None:
            if not pairs:
                status.config(text="No saved region to delete.")
                return
            redo_stack.append(pairs.pop())
            redraw_all()
            status.config(text="Deleted last region.")

        def redo_last() -> None:
            if not redo_stack:
                status.config(text="No deleted region to redo.")
                return
            pending["candidate"] = None
            pending["reference"] = None
            pairs.append(redo_stack.pop())
            redraw_all()
            status.config(text="Redid last deleted region.")

        def clear() -> None:
            pairs.clear()
            redo_stack.clear()
            pending["candidate"] = None
            pending["reference"] = None
            candidate_canvas.delete("drag")
            reference_canvas.delete("drag")
            redraw_all()
            status.config(text="Cleared regions.")

        def save() -> None:
            regions = tuple(pairs)
            if not regions:
                status.config(text="No complete region pair selected.")
                return
            try:
                _write_region_mapping(
                    output_path,
                    candidate_image=candidate_image,
                    candidate_data=candidate_bytes,
                    reference_image=reference_image,
                    regions=regions,
                )
            except Exception as exc:
                result["warning"] = "could not save reference regions: %s" % exc
                status.config(text=result["warning"])
                return
            result["saved"] = True
            result["region_count"] = len(regions)
            root.destroy()

        def confirm_discard_unsaved() -> bool:
            if not has_unsaved_region_state(
                len(pairs),
                pending.get("candidate"),
                pending.get("reference"),
            ):
                return True
            try:
                answer = messagebox.askyesno(
                    "Discard ROI mapping?",
                    "Close without saving the current ROI mapping?",
                    parent=root,
                )
                return bool(answer)
            except Exception:
                return True

        def cancel() -> None:
            if not confirm_discard_unsaved():
                status.config(text="Close cancelled. Save the ROI mapping or keep editing.")
                return
            result["saved"] = False
            result["warning"] = "reference region editor cancelled"
            root.destroy()

        buttons = tk.Frame(root)
        buttons.pack(fill="x", padx=8, pady=8)
        save_button = tk.Button(buttons, text="Save", command=save)
        delete_button = tk.Button(buttons, text="Delete last", command=delete_last)
        redo_button = tk.Button(buttons, text="Redo", command=redo_last)
        clear_button = tk.Button(buttons, text="Clear", command=clear)
        single_button = tk.Button(buttons, text="Add Single Rectangle", command=add_single_rectangle)
        same_button = tk.Button(buttons, text="Draw Same Rectangle", command=same_rectangle)
        negative_button = tk.Button(buttons, text="Add Negative Rectangle", command=add_negative_rectangle)
        cancel_button = tk.Button(buttons, text="Cancel", command=cancel)
        save_button.pack(side="left", padx=4)
        delete_button.pack(side="left", padx=4)
        redo_button.pack(side="left", padx=4)
        clear_button.pack(side="left", padx=4)
        single_button.pack(side="left", padx=4)
        same_button.pack(side="left", padx=4)
        negative_button.pack(side="left", padx=4)
        cancel_button.pack(side="right", padx=4)
        add_tooltip(save_button, "Save the ROI mapping and close the editor.")
        add_tooltip(delete_button, "Remove the last saved ROI.")
        add_tooltip(redo_button, "Restore the last ROI removed with Delete last.")
        add_tooltip(clear_button, "Remove every saved ROI and pending selection.")
        add_tooltip(single_button, "Save one rectangle; choose same-position or whole-image search.")
        add_tooltip(same_button, "Copy the pending rectangle to the same normalized position on the other image.")
        add_tooltip(negative_button, "Save a source-side rectangle where candidate noise should stay low.")
        add_tooltip(cancel_button, "Close without saving a new ROI mapping.")
        root.protocol("WM_DELETE_WINDOW", cancel)
        redraw_all()
        root.mainloop()
        return ReferenceRegionEditorResult(
            bool(result["saved"]),
            output_path,
            str(result["warning"] or ""),
            int(result["region_count"] or 0),
        )
    except Exception as exc:
        return ReferenceRegionEditorResult(False, output_path, "reference region editor failed: %s" % exc)
