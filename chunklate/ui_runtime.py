from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import ui


@dataclass(frozen=True)
class LegacyUiRuntime:
    emit: Callable[[Any], Any]
    random_int: Callable[[int, int], int]
    max_columns: int
    no_dialogue: bool
    use_color: bool
    pause_dialogue_enabled: bool = False
    pause_dialogue: Callable[[], Any] | None = None

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
            if self.pause_dialogue_enabled and self.pause_dialogue is not None:
                self.pause_dialogue()
            return None

        if mode == "Title":
            if self.no_dialogue:
                return ()
            self.emit(ui.render_title(arg, data, use_color=self.use_color))
            return None

        return None
