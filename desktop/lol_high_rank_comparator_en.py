"""English desktop entry point for RiftScale."""
from __future__ import annotations

import sys
import os
import traceback
from pathlib import Path

from desktop.english_ui import english, localize_widget_tree, untranslated_widget_text
from desktop import lol_high_rank_comparator as native_ui
from desktop.lol_high_rank_comparator import ComparatorApp


def _install_english_messageboxes() -> None:
    """Localize every native modal dialog, including errors raised at runtime."""
    for name in ("showerror", "showwarning", "showinfo"):
        original = getattr(native_ui.messagebox, name)

        def localized(*args, _original=original, **kwargs):
            translated_args = list(args)
            if translated_args:
                translated_args[0] = english(translated_args[0])
            if len(translated_args) > 1:
                translated_args[1] = english(translated_args[1])
            for key in ("title", "message"):
                if key in kwargs:
                    kwargs[key] = english(kwargs[key])
            return _original(*translated_args, **kwargs)

        setattr(native_ui.messagebox, name, localized)


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
            _install_english_messageboxes()
            app = EnglishComparatorApp()
            app.withdraw()
            app.update()
            if app.match_tree.get_children():
                first_match = app.match_tree.get_children()[0]
                app.match_tree.selection_set(first_match)
                app.match_tree.focus(first_match)
                app._on_match_selected()
                app._render_review()
            app._localize_english()
            remaining = untranslated_widget_text(app)
            app.destroy()
            if remaining:
                raise RuntimeError(f"English UI still contains untranslated text: {remaining[:3]!r}")
        except Exception:
            log_path = os.environ.get("RIFTSCALE_SMOKE_LOG")
            if log_path:
                tcl_dir = Path(os.environ.get("TCL_LIBRARY", ""))
                tk_dir = Path(os.environ.get("TK_LIBRARY", ""))
                diagnostics = (
                    f"TCL_LIBRARY={tcl_dir}; init.tcl exists={ (tcl_dir / 'init.tcl').is_file() }\n"
                    f"TK_LIBRARY={tk_dir}; tk.tcl exists={ (tk_dir / 'tk.tcl').is_file() }\n"
                )
                Path(log_path).write_text(diagnostics + traceback.format_exc(), encoding="utf-8")
            raise SystemExit(1)
        return
    _install_english_messageboxes()
    app = EnglishComparatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
