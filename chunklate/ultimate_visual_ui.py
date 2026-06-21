from __future__ import annotations

from dataclasses import dataclass
import json
import os
import shutil
import time
import uuid
from typing import Any

from . import idat_bruteforce


ULTIMATE_FINAL_PREVIEW_FOLDER = ("Bruteforce_Previews", "Final_Previews")
ULTIMATE_FINAL_PREVIEW_RECORD_NAME = "_ULF.final_previews.json"


def _hidden_tmp_path(path: str) -> str:
    directory, filename = os.path.split(path)
    tmp_name = ".%s.%s.%s.tmp" % (
        filename or "chunklate",
        os.getpid(),
        uuid.uuid4().hex,
    )
    return os.path.join(directory, tmp_name) if directory else tmp_name


@dataclass(frozen=True)
class UltimateVisualCandidateEntry:
    index: int
    preview_path: str
    label: str
    visual_score: float | None = None
    coverage: float = 0.0
    tested_candidates: int = 0
    state_id: int = 0
    visual_hash: str = ""
    operation_hash: str = ""


@dataclass(frozen=True)
class UltimateVisualSelectionResult:
    selected_preview_paths: tuple[str, ...] = ()
    final_preview_dir: str = ""
    final_preview_paths: tuple[str, ...] = ()
    defaulted: bool = False
    decision: str = "undecided"
    warning: str = ""


def _coerce_timeout_seconds(value: object) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, timeout)


def _safe_filename_part(value: object) -> str:
    text = str(value or "")
    safe = "".join(char if char.isalnum() or char in ("-", "_", ".") else "_" for char in text)
    return safe.strip("._") or "candidate"


def _json_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _entry_label(index: int, record: dict[str, Any], preview_path: str) -> str:
    score = _json_float(record.get("visual_score"))
    coverage = _json_float(record.get("coverage"))
    score_text = "score ?" if score is None else "score %.3f" % score
    coverage_text = "coverage ?" if coverage is None else "%.1f%%" % (coverage * 100.0)
    tested = _json_int(record.get("tested_candidates"), 0)
    return "%03d  %s  %s  tested %s  %s" % (
        index,
        score_text,
        coverage_text,
        tested,
        os.path.basename(preview_path),
    )


def load_ultimate_visual_candidate_entries(gallery_path: str) -> tuple[UltimateVisualCandidateEntry, ...]:
    if not gallery_path or not os.path.exists(gallery_path):
        return ()
    try:
        with open(gallery_path, "r", encoding="utf-8") as file:
            gallery = json.load(file)
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(gallery, dict):
        return ()

    base_dir = os.path.dirname(os.path.abspath(gallery_path))
    raw_candidates = gallery.get("candidates", ())
    if not isinstance(raw_candidates, list):
        return ()

    entries: list[UltimateVisualCandidateEntry] = []
    for index, item in enumerate(raw_candidates, start=1):
        if not isinstance(item, dict):
            continue
        preview_path = str(item.get("preview_path", "") or "")
        if not preview_path:
            continue
        if not os.path.isabs(preview_path):
            preview_path = os.path.join(base_dir, preview_path)
        preview_path = os.path.abspath(preview_path)
        if not os.path.exists(preview_path):
            continue
        entries.append(
            UltimateVisualCandidateEntry(
                index=index,
                preview_path=preview_path,
                label=_entry_label(index, item, preview_path),
                visual_score=_json_float(item.get("visual_score")),
                coverage=float(_json_float(item.get("coverage")) or 0.0),
                tested_candidates=_json_int(item.get("tested_candidates"), 0),
                state_id=_json_int(item.get("state_id"), 0),
                visual_hash=str(item.get("visual_hash", "") or ""),
                operation_hash=str(item.get("operation_hash", "") or ""),
            )
        )
    return tuple(entries)


def ultimate_final_preview_dir_from_gallery_path(gallery_path: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(gallery_path)) if gallery_path else os.getcwd()
    return os.path.join(base_dir, *ULTIMATE_FINAL_PREVIEW_FOLDER)


def _remove_stale_final_previews(final_dir: str) -> None:
    try:
        names = os.listdir(final_dir)
    except OSError:
        return
    for name in names:
        if not name.startswith("_FinalPreview_") or not name.endswith(".png"):
            continue
        try:
            os.remove(os.path.join(final_dir, name))
        except OSError:
            continue


def write_ultimate_final_previews(
    gallery_path: str,
    entries: tuple[UltimateVisualCandidateEntry, ...],
    *,
    final_dir: str = "",
    decision: str = "undecided",
) -> UltimateVisualSelectionResult:
    if not entries:
        return UltimateVisualSelectionResult(warning="no Ultimate visual candidates selected")
    final_dir = final_dir or ultimate_final_preview_dir_from_gallery_path(gallery_path)
    try:
        os.makedirs(final_dir, exist_ok=True)
        _remove_stale_final_previews(final_dir)
    except OSError as exc:
        return UltimateVisualSelectionResult(
            selected_preview_paths=tuple(entry.preview_path for entry in entries),
            final_preview_dir=final_dir,
            warning="could not prepare Final_Previews folder: %s" % exc,
        )

    written: list[str] = []
    records: list[dict[str, Any]] = []
    for output_index, entry in enumerate(entries, start=1):
        source_name = os.path.basename(entry.preview_path)
        output_name = "_FinalPreview_%03d_from_%s" % (
            output_index,
            _safe_filename_part(source_name),
        )
        if not output_name.endswith(".png"):
            output_name += ".png"
        output_path = os.path.join(final_dir, output_name)
        try:
            shutil.copyfile(entry.preview_path, output_path)
        except OSError:
            continue
        written.append(output_path)
        records.append(
            {
                "index": entry.index,
                "preview_path": os.path.relpath(entry.preview_path, os.path.dirname(os.path.abspath(gallery_path))),
                "final_preview_path": os.path.relpath(output_path, os.path.dirname(os.path.abspath(gallery_path))),
                "visual_score": entry.visual_score,
                "coverage": entry.coverage,
                "tested_candidates": entry.tested_candidates,
                "state_id": entry.state_id,
                "visual_hash": entry.visual_hash,
                "operation_hash": entry.operation_hash,
            }
        )

    record_path = os.path.join(os.path.dirname(os.path.abspath(gallery_path)), ULTIMATE_FINAL_PREVIEW_RECORD_NAME)
    try:
        tmp_path = _hidden_tmp_path(record_path)
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "version": 1,
                    "source_gallery": os.path.basename(gallery_path),
                    "final_preview_dir": os.path.relpath(final_dir, os.path.dirname(os.path.abspath(gallery_path))),
                    "selected_count": len(written),
                    "decision": str(decision or "undecided"),
                    "timestamp": time.time(),
                    "candidates": records,
                },
                file,
                sort_keys=True,
                indent=2,
            )
            file.write("\n")
        os.replace(tmp_path, record_path)
    except OSError:
        pass

    return UltimateVisualSelectionResult(
        selected_preview_paths=tuple(entry.preview_path for entry in entries),
        final_preview_dir=final_dir,
        final_preview_paths=tuple(written),
        decision=str(decision or "undecided"),
        warning="" if written else "could not copy selected Ultimate visual candidates",
    )


def _fit_size(
    size: tuple[int, int],
    *,
    max_width: int,
    max_height: int,
) -> tuple[int, int]:
    width, height = size
    if width <= 0 or height <= 0:
        return (1, 1)
    scale = min(max_width / float(width), max_height / float(height))
    scale = max(0.01, scale)
    return (max(1, int(width * scale)), max(1, int(height * scale)))


def open_ultimate_visual_candidate_selector(
    gallery_path: str,
    *,
    interactive: bool = True,
    default_count: int = 3,
    allow_keep_searching: bool = False,
    timeout_seconds: float | int | None = None,
    instruction: str = "",
    title: str = "Chunklate Ultimate visual candidates",
    tkinter_module: Any | None = None,
    image_tk_module: Any | None = None,
    messagebox_module: Any | None = None,
) -> UltimateVisualSelectionResult:
    entries = load_ultimate_visual_candidate_entries(gallery_path)
    if not entries:
        return UltimateVisualSelectionResult(warning="no Ultimate visual candidates are available")

    default_count = max(1, int(default_count or 3))
    default_entries = entries[: min(default_count, len(entries))]
    timeout_seconds = _coerce_timeout_seconds(timeout_seconds)
    if not interactive:
        result = write_ultimate_final_previews(gallery_path, default_entries)
        return UltimateVisualSelectionResult(
            selected_preview_paths=result.selected_preview_paths,
            final_preview_dir=result.final_preview_dir,
            final_preview_paths=result.final_preview_paths,
            defaulted=True,
            decision=result.decision,
            warning=result.warning,
        )

    try:
        import tkinter as tk
        from tkinter import messagebox
        from PIL import Image, ImageTk

        tk = tkinter_module or tk
        ImageTk = image_tk_module or ImageTk
        messagebox = messagebox_module or messagebox
    except Exception as exc:
        result = write_ultimate_final_previews(gallery_path, default_entries)
        return UltimateVisualSelectionResult(
            selected_preview_paths=result.selected_preview_paths,
            final_preview_dir=result.final_preview_dir,
            final_preview_paths=result.final_preview_paths,
            defaulted=True,
            decision=result.decision,
            warning="Ultimate visual selector unavailable: %s" % exc,
        )

    state: dict[str, Any] = {
        "current": 0,
        "selected": [],
        "photo": None,
        "image": None,
        "done": False,
        "decision": "undecided",
        "last_activity": time.monotonic(),
    }

    try:
        root = tk.Tk()
        root.title(title)
        root.geometry("1100x720+90+90")
        root.minsize(720, 420)

        default_instruction = (
            "Select the preview image(s) that look closest to the original. "
            "Use Finish to save them in Final_Previews for the next repair step."
        )
        if allow_keep_searching:
            default_instruction = (
                "Ultimate is paused so you can inspect the current best previews. "
                "Select a preview if it is good enough, or press Keep searching to continue the same run."
            )
        instruction_text = instruction or default_instruction
        instruction_label = tk.Label(root, text=instruction_text, anchor="w", justify="left", wraplength=1060)
        instruction_label.pack(fill="x", padx=8, pady=(8, 0))

        container = tk.Frame(root)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=3)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(0, weight=1)

        left_frame = tk.Frame(container)
        right_frame = tk.Frame(container)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        tk.Label(left_frame, text="Ultimate visual candidate").grid(row=0, column=0, sticky="w")
        canvas = tk.Canvas(left_frame, bg="#1f1f1f", highlightthickness=0)
        canvas.grid(row=1, column=0, sticky="nsew")

        tk.Label(right_frame, text="Bruteforce_Previews/VisualCandidates").grid(row=0, column=0, sticky="w")
        list_frame = tk.Frame(right_frame)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, exportselection=False)
        scrollbar.config(command=listbox.yview)
        listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        status = tk.Label(root, text="", anchor="w")
        status.pack(fill="x", padx=8, pady=(0, 8))
        timeout_status = tk.Label(root, text="", anchor="w")
        if timeout_seconds > 0:
            timeout_status.pack(fill="x", padx=8, pady=(0, 8))

        def mark_activity(_event=None) -> None:
            state["last_activity"] = time.monotonic()

        def refresh_list() -> None:
            try:
                selected_paths = set(state["selected"])
                active = int(state["current"])
                listbox.delete(0, "end")
                for entry in entries:
                    prefix = "* " if entry.preview_path in selected_paths else "  "
                    listbox.insert("end", prefix + entry.label)
                listbox.selection_set(active)
                listbox.see(active)
                if allow_keep_searching:
                    status.config(
                        text="%s selected. Choose an action below, or Keep searching if these previews are not good enough."
                        % len(selected_paths)
                    )
                else:
                    status.config(text="%s selected. Finish with none selected to keep the top %s." % (len(selected_paths), default_count))
            except Exception:
                pass

        def redraw_image() -> None:
            try:
                entry = entries[int(state["current"])]
                image = Image.open(entry.preview_path).convert("RGBA")
                width = int(canvas.winfo_width()) or 1
                height = int(canvas.winfo_height()) or 1
                display_size = _fit_size(
                    image.size,
                    max_width=max(1, width - 16),
                    max_height=max(1, height - 16),
                )
                display = image.resize(display_size, idat_bruteforce._pil_lanczos_filter())
                photo = ImageTk.PhotoImage(display)
                state["photo"] = photo
                state["image"] = image
                canvas.delete("all")
                left = max(0, (width - display_size[0]) // 2)
                top = max(0, (height - display_size[1]) // 2)
                canvas.create_image(left, top, image=photo, anchor="nw")
                status.config(text=entry.label)
            except Exception as exc:
                status.config(text="Could not display candidate: %s" % exc)

        def list_selected(_event=None) -> None:
            selection = listbox.curselection()
            if not selection:
                return
            state["current"] = int(selection[0])
            redraw_image()

        def add_current() -> None:
            mark_activity()
            entry = entries[int(state["current"])]
            selected = list(state["selected"])
            if entry.preview_path not in selected:
                selected.append(entry.preview_path)
            state["selected"] = selected
            refresh_list()

        def remove_current() -> None:
            mark_activity()
            entry = entries[int(state["current"])]
            state["selected"] = [path for path in state["selected"] if path != entry.preview_path]
            refresh_list()

        def close_with_decision(decision: str) -> None:
            state["decision"] = str(decision or "undecided")
            state["done"] = True
            try:
                root.destroy()
            except Exception:
                pass

        def finish() -> None:
            mark_activity()
            try:
                answer = messagebox.askyesnocancel(
                    "Ultimate final preview",
                    (
                        "Is the best selected preview perfectly correct?\n\n"
                        "Yes: accept it as the final visual repair.\n"
                        "No: keep Final_Previews only.\n"
                        "Cancel: keep Final_Previews only."
                    ),
                    parent=root,
                )
            except Exception:
                answer = None
            if answer is True:
                state["decision"] = "perfect"
            else:
                state["decision"] = "undecided"
            close_with_decision(str(state["decision"]))

        def use_selected_preview() -> None:
            mark_activity()
            close_with_decision("visual_guidance")

        def accept_final_repair() -> None:
            mark_activity()
            close_with_decision("perfect")

        def keep_searching() -> None:
            mark_activity()
            close_with_decision("keep_searching")

        def close_without_decision() -> None:
            close_with_decision("undecided")

        def check_idle_timeout() -> None:
            if timeout_seconds <= 0 or bool(state.get("done")):
                return
            idle = max(0.0, time.monotonic() - float(state.get("last_activity") or 0.0))
            remaining = max(0, int(round(timeout_seconds - idle)))
            try:
                action = "Chunklate will keep searching" if allow_keep_searching else "this window will close"
                timeout_status.config(
                    text="Inactivity timeout: %ss. Move the mouse or use the window; otherwise %s."
                    % (remaining, action)
                )
            except Exception:
                pass
            if idle >= timeout_seconds:
                close_with_decision("keep_searching" if allow_keep_searching else "undecided")
                return
            root.after(1000, check_idle_timeout)

        actions = tk.Frame(root)
        actions.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(actions, text="Add this one to best candidates", command=add_current).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Remove this one from best candidates", command=remove_current).pack(side="left", padx=(0, 8))
        if allow_keep_searching:
            tk.Button(actions, text="Keep searching", command=keep_searching).pack(side="right")
            tk.Button(actions, text="Accept this as final repair", command=accept_final_repair).pack(side="right", padx=(0, 8))
            tk.Button(actions, text="Use selected preview", command=use_selected_preview).pack(side="right", padx=(0, 8))
        else:
            tk.Button(actions, text="Finish", command=finish).pack(side="right")

        listbox.bind("<<ListboxSelect>>", list_selected)
        listbox.bind("<Double-Button-1>", lambda _event: add_current())
        canvas.bind("<Configure>", lambda _event: redraw_image())
        root.bind_all("<Motion>", mark_activity)
        root.bind_all("<Button>", mark_activity)
        root.bind_all("<Key>", mark_activity)
        root.bind_all("<MouseWheel>", mark_activity)
        root.protocol("WM_DELETE_WINDOW", close_without_decision)
        refresh_list()
        redraw_image()
        if timeout_seconds > 0:
            root.after(1000, check_idle_timeout)
        root.mainloop()
    except Exception as exc:
        result = write_ultimate_final_previews(gallery_path, default_entries)
        return UltimateVisualSelectionResult(
            selected_preview_paths=result.selected_preview_paths,
            final_preview_dir=result.final_preview_dir,
            final_preview_paths=result.final_preview_paths,
            defaulted=True,
            decision=result.decision,
            warning="Ultimate visual selector failed: %s" % exc,
        )

    selected_paths = tuple(path for path in state["selected"] if path)
    decision = str(state.get("decision") or "undecided")
    if decision in {"keep_searching", "timeout"}:
        return UltimateVisualSelectionResult(
            selected_preview_paths=(),
            final_preview_dir=ultimate_final_preview_dir_from_gallery_path(gallery_path),
            final_preview_paths=(),
            defaulted=False,
            decision=decision,
        )
    entries_by_path = {entry.preview_path: entry for entry in entries}
    selected_entries = tuple(
        entries_by_path[path] for path in selected_paths if path in entries_by_path
    )
    defaulted = False
    if not selected_entries:
        selected_entries = default_entries
        defaulted = True
    result = write_ultimate_final_previews(
        gallery_path,
        selected_entries,
        decision=decision,
    )
    return UltimateVisualSelectionResult(
        selected_preview_paths=result.selected_preview_paths,
        final_preview_dir=result.final_preview_dir,
        final_preview_paths=result.final_preview_paths,
        defaulted=defaulted,
        decision=result.decision,
        warning=result.warning,
    )
