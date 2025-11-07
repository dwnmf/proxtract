"""Modal screen that captures a new value for a setting."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from .. import STYLES_PATH
from ..widgets import CompletionInput


class EditSettingScreen(ModalScreen[str | None]):
    """Prompt the user for a new string value."""

    CSS_PATH = STYLES_PATH

    def __init__(
        self,
        *,
        key: str,
        label: str,
        description: str,
        setting_type: str,
        initial_value: str,
    ) -> None:
        super().__init__(id="edit-setting")
        self._key = key
        self._label = label
        self._description = description
        self._setting_type = setting_type
        self._initial_value = initial_value

    def compose(self) -> ComposeResult:
        mode = "path"
        if self._setting_type == "list":
            mode = "list"
        elif self._setting_type != "path":
            mode = "text"

        input_widget = CompletionInput(
            value=self._initial_value,
            id="edit-input",
            mode=mode,
            suggestions=self._initial_suggestions(),
        )

        yield Vertical(
            Vertical(
                Label(self._label, id="edit-title"),
                Label(self._description, id="edit-description"),
                id="edit-header",
            ),
            Vertical(
                Label("Новое значение", id="edit-input-label", classes="form-label"),
                input_widget,
                classes="form-field",
            ),
            Horizontal(
                Button("Cancel", id="cancel"),
                Button("Save", id="save", variant="primary"),
                id="edit-buttons",
            ),
            id="edit-container",
            classes="modal-card",
        )

    def on_mount(self) -> None:
        self.query_one("#edit-input", CompletionInput).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "save":
            self.dismiss(self.query_one("#edit-input", CompletionInput).value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def _initial_suggestions(self) -> list[str]:
        if self._setting_type == "bool":
            return ["on", "off", "true", "false", "yes", "no"]
        if self._setting_type == "list":
            return [item.strip() for item in self._initial_value.split(",") if item.strip()]
        if self._key == "tokenizer_model":
            return ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "o200k_base"]
        return []


__all__ = ["EditSettingScreen"]
