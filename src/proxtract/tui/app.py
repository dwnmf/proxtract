"""Textual application shell for Proxtract."""

from __future__ import annotations

from typing import Optional

from textual.app import App

from ..state import AppState
from . import STYLES_PATH
from .screens import MainScreen

try:  # Config persistence may be unavailable in minimalist installs
    from ..config import save_config as _save_config
except Exception:  # pragma: no cover - optional dependency missing
    _save_config = None  # type: ignore[assignment]


class ProxtractApp(App[None]):
    """Textual front-end that wraps the Proxtract extraction workflow."""

    CSS_PATH = STYLES_PATH
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+s", "save", "Save"),
    ]

    def __init__(self, app_state: AppState, *, title: Optional[str] = None) -> None:
        super().__init__()
        self.app_state = app_state
        self.title = title or "Proxtract"

    async def on_mount(self) -> None:
        self.push_screen(MainScreen(self.app_state))

    def action_quit(self) -> None:
        """Persist settings (when available) and exit."""

        if _save_config is not None:
            try:
                _save_config(self.app_state)
            except Exception as exc:  # pragma: no cover - defensive best effort
                self.notify(f"Failed to save settings: {exc}", severity="warning")
        self.exit()

    def action_save(self) -> None:
        """Persist the current settings, if the config helper is available."""

        if _save_config is None:
            self.notify("Configuration persistence is unavailable.", severity="warning")
            return

        try:
            _save_config(self.app_state)
        except Exception as exc:  # pragma: no cover - defensive best effort
            self.notify(f"Failed to save settings: {exc}", severity="error")
        else:
            self.notify("Settings saved.", severity="information")


__all__ = ["ProxtractApp"]
