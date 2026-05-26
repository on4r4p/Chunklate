from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import ui


@dataclass
class LegacyDialoguePauseState:
    pending: bool = False
    paused_in_group: bool = False


@dataclass(frozen=True)
class LegacyUiRuntime:
    emit: Callable[[Any], Any]
    random_int: Callable[[int, int], int]
    max_columns: int
    no_dialogue: bool
    use_color: bool
    pause_dialogue_enabled: bool = False
    pause_dialogue: Callable[[], Any] | None = None
    pause_state: LegacyDialoguePauseState | None = None

    def _question_title(self, arg: Any) -> bool:
        return str(arg).strip().upper() == "QUESTION!"

    def _clear_pending_pause(self) -> None:
        if self.pause_state is not None:
            self.pause_state.pending = False

    def _reset_dialogue_pause_group(self) -> None:
        if self.pause_state is not None:
            self.pause_state.pending = False
            self.pause_state.paused_in_group = False

    def _queue_dialogue_pause(self) -> None:
        if not self.pause_dialogue_enabled or self.pause_dialogue is None:
            return
        if self.pause_state is None:
            self.pause_dialogue()
            return
        if self.pause_state.paused_in_group:
            return
        self.pause_state.pending = True

    def _flush_dialogue_pause_before_title(self, arg: Any) -> None:
        if self.pause_state is None or not self.pause_state.pending:
            if self._question_title(arg):
                self._reset_dialogue_pause_group()
            return
        if self._question_title(arg):
            self._reset_dialogue_pause_group()
            return
        if self.pause_dialogue_enabled and self.pause_dialogue is not None:
            self.pause_dialogue()
        self.pause_state.pending = False
        self.pause_state.paused_in_group = True

    def candy(self, mode: str, arg: Any, data: Any = None) -> Any:
        if mode == "Emoj":
            return ui.pick_emoji(arg, self.random_int)

        if mode == "Color":
            return ui.colorize(arg, data, use_color=self.use_color)

        if mode == "Cowsay":
            self.emit(
                ui.render_dialogue(
                    arg,
                    data,
                    max_columns=self.max_columns,
                    emoji_provider=lambda name: self.candy("Emoj", name),
                    use_color=self.use_color,
                )
            )
            self._queue_dialogue_pause()
            return None

        if mode == "Title":
            self._flush_dialogue_pause_before_title(arg)
            if self.no_dialogue:
                return ()
            self.emit(ui.render_title(arg, data, use_color=self.use_color))
            return None

        return None
