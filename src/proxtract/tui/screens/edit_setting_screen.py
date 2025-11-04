"""Modal screen that captures a new value for a setting."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from .. import STYLES_PATH


class EditSettingScreen(ModalScreen[str | None]):
    """Prompt the user for a new string value."""

    CSS_PATH = STYLES_PATH

    def __init__(self, *, label: str, description: str, initial_value: str) -> None:
        super().__init__(id="edit-setting")
        self._label = label
        self._description = description
        self._initial_value = initial_value

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self._label, id="edit-title"),
            Label(self._description, id="edit-description"),
            Input(value=self._initial_value, id="edit-input"),
            Horizontal(
                Button("Cancel", id="cancel"),
                Button("Save", id="save", variant="primary"),
                id="edit-buttons",
            ),
            id="edit-container",
        )

    def on_mount(self) -> None:
        self.query_one("#edit-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "save":
            self.dismiss(self.query_one("#edit-input", Input).value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


__all__ = ["EditSettingScreen"]
