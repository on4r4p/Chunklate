from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
import os
from typing import Any

from . import idat
from . import idat_bruteforce


EDITOR_CANVAS_MARGIN = 32
FULL_REGION = (0.0, 0.0, 1.0, 1.0)


@dataclass(frozen=True)
class ReferenceRegionEditorResult:
    saved: bool
    path: str
    warning: str = ""
    region_count: int = 0


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
    tmp_path = path + ".tmp"
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
        from PIL import ImageTk

        tk = tkinter_module or tk
        ImageTk = image_tk_module or ImageTk
        candidate_image, candidate_bytes = _load_image(candidate_path, fallback_data=candidate_data)
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
            outline = "yellow" if side == "candidate" else "cyan"
            for region in pairs:
                if region.match_mode == "search_candidate" and side == "candidate":
                    continue
                if region.match_mode == "search_reference" and side == "reference":
                    continue
                roi = region.candidate_region if side == "candidate" else region.reference_region
                canvas.create_rectangle(*region_to_canvas_bbox(side, roi), outline=outline, width=2, tags=("roi",))
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
            status.config(text="%s saved. Draw another region or press Save." % label)
            redraw_all()
            return True

        def begin(side: str, event) -> None:
            pending[side] = None
            redraw_all()
            start[side] = (float(event.x), float(event.y))
            canvas = canvas_for(side)
            if drag_item[side] is not None:
                canvas.delete(drag_item[side])
            color = "yellow" if side == "candidate" else "cyan"
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
        candidate_canvas.bind("<B1-Motion>", lambda event: drag("candidate", event))
        candidate_canvas.bind("<ButtonRelease-1>", lambda event: end("candidate", event))
        reference_canvas.bind("<ButtonPress-1>", lambda event: begin("reference", event))
        reference_canvas.bind("<B1-Motion>", lambda event: drag("reference", event))
        reference_canvas.bind("<ButtonRelease-1>", lambda event: end("reference", event))
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
                pairs.append(
                    idat_bruteforce.UltimateReferenceRegion(
                        candidate_region=FULL_REGION,
                        reference_region=reference_region,
                        weight=1.0,
                        label=label,
                        match_mode="search_candidate",
                    )
                )
            else:
                pairs.append(
                    idat_bruteforce.UltimateReferenceRegion(
                        candidate_region=candidate_region,
                        reference_region=FULL_REGION,
                        weight=1.0,
                        label=label,
                        match_mode="search_reference",
                    )
                )
            pending["candidate"] = None
            pending["reference"] = None
            redraw_all()
            status.config(text="%s saved as a single-rectangle search ROI." % label)

        def delete_last() -> None:
            if not pairs:
                status.config(text="No saved region to delete.")
                return
            pairs.pop()
            redraw_all()
            status.config(text="Deleted last region.")

        def clear() -> None:
            pairs.clear()
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

        def cancel() -> None:
            result["saved"] = False
            result["warning"] = "reference region editor cancelled"
            root.destroy()

        buttons = tk.Frame(root)
        buttons.pack(fill="x", padx=8, pady=8)
        tk.Button(buttons, text="Save", command=save).pack(side="left", padx=4)
        tk.Button(buttons, text="Delete last", command=delete_last).pack(side="left", padx=4)
        tk.Button(buttons, text="Clear", command=clear).pack(side="left", padx=4)
        tk.Button(buttons, text="Add Single Rectangle", command=add_single_rectangle).pack(side="left", padx=4)
        tk.Button(buttons, text="Draw Same Rectangle", command=same_rectangle).pack(side="left", padx=4)
        tk.Button(buttons, text="Cancel", command=cancel).pack(side="right", padx=4)
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
