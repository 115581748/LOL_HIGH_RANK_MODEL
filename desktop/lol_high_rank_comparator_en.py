"""English desktop entry point for RiftScale."""
from __future__ import annotations

import sys
import os
import traceback
from pathlib import Path

from desktop.english_ui import english, localize_widget_tree, untranslated_widget_text
from desktop.lol_high_rank_comparator import ComparatorApp


class EnglishComparatorApp(ComparatorApp):
    def __init__(self):
        super().__init__()
        self.title("RiftScale · High-rank match review")
        for card in self.dashboard_cards:
            card["label"] = english(card.get("label"))
            card["subtitle"] = english(card.get("subtitle"))
        self._localize_english()

    def _localize_english(self) -> None:
        # Dynamic replay/status content is redrawn frequently, so keep this pass
        # cheap, idempotent, and limited to visible Tk presentation state.
        localize_widget_tree(self)
        for variable_name in ("status_text", "replay_time_text", "replay_layer_caption"):
            variable = getattr(self, variable_name, None)
            if variable is not None:
                try:
                    variable.set(english(variable.get()))
                except Exception:
                    pass

    def _animate_ui(self) -> None:
        super()._animate_ui()
        # The parent redraws Canvas labels on every animation tick. Translate
        # immediately after drawing so Chinese frames never flash on screen.
        self._localize_english()


def main() -> None:
    if "--smoke-check" in sys.argv:
        try:
            app = EnglishComparatorApp()
            app.withdraw()
            app.update()
            app._localize_english()
            remaining = untranslated_widget_text(app)
            app.destroy()
            if remaining:
                raise RuntimeError(f"English UI still contains untranslated text: {remaining[:3]!r}")
        except Exception:
            log_path = os.environ.get("RIFTSCALE_SMOKE_LOG")
            if log_path:
                Path(log_path).write_text(traceback.format_exc(), encoding="utf-8")
            raise SystemExit(1)
        return
    app = EnglishComparatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
