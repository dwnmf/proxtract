"""Modal settings screen that groups advanced options."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Switch

from ...state import AppState
from .. import STYLES_PATH
from ..widgets import CompletionInput


class SettingsScreen(ModalScreen[bool]):
    """Expose the full configuration as a modal with progressive disclosure."""

    CSS_PATH = STYLES_PATH

    def __init__(self, app_state: AppState) -> None:
        super().__init__(id="settings-screen")
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        include_text = ", ".join(self.app_state.include_patterns)
        exclude_text = ", ".join(self.app_state.exclude_patterns)

        yield Vertical(
            Vertical(
                Label("Настройки", id="settings-title"),
                Label("Управляйте расширенными параметрами извлечения.", id="settings-description"),
                id="settings-header",
            ),
            Vertical(
                Label("Основные", classes="group-title"),
                Vertical(
                    Label("Макс. размер файла (КБ)", classes="form-label"),
                    Input(
                        id="max-size",
                        value=str(self.app_state.max_size_kb),
                        placeholder="500",
                    ),
                    classes="form-field",
                ),
                self._switch_row("compact-mode", "Компактный режим", self.app_state.compact_mode),
                self._switch_row("skip-empty", "Пропускать пустые файлы", self.app_state.skip_empty),
                classes="settings-group",
            ),
            Vertical(
                Label("Фильтрация", classes="group-title"),
                self._switch_row("use-gitignore", "Использовать .gitignore", self.app_state.use_gitignore),
                Vertical(
                    Label("Шаблоны для включения", classes="form-label"),
                    CompletionInput(
                        id="include-patterns",
                        mode="list",
                        value=include_text,
                        placeholder="src/**/*.py, *.md",
                    ),
                    classes="form-field",
                ),
                Vertical(
                    Label("Шаблоны для исключения", classes="form-label"),
                    CompletionInput(
                        id="exclude-patterns",
                        mode="list",
                        value=exclude_text,
                        placeholder="*.log, build/**",
                    ),
                    classes="form-field",
                ),
                self._switch_row(
                    "force-include",
                    "Приоритет включения над исключением",
                    self.app_state.force_include,
                ),
                classes="settings-group",
            ),
            Vertical(
                Label("Дополнительно", classes="group-title"),
                self._switch_row(
                    "count-tokens",
                    "Считать токены",
                    self.app_state.enable_token_count,
                ),
                Vertical(
                    Label("Модель токенизатора", classes="form-label"),
                    CompletionInput(
                        id="tokenizer-model",
                        value=self.app_state.tokenizer_model,
                        suggestions=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "o200k_base"],
                    ),
                    classes="form-field",
                ),
                self._switch_row(
                    "copy-to-clipboard",
                    "Копировать результат в буфер",
                    self.app_state.copy_to_clipboard,
                ),
                classes="settings-group",
            ),
            Horizontal(
                Button("Отмена", id="cancel-settings"),
                Button("Сохранить", id="save-settings", variant="primary"),
                id="settings-buttons",
            ),
            id="settings-container",
            classes="modal-card modal-large",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-settings":
            self.dismiss(False)
        elif event.button.id == "save-settings":
            self._apply_changes()

    def _apply_changes(self) -> None:
        max_size_text = self.query_one("#max-size", Input).value.strip()
        max_size = self._parse_int(max_size_text, fallback=self.app_state.max_size_kb)
        if max_size <= 0:
            self.app.notify("Максимальный размер должен быть положительным числом.", severity="warning")
            return

        self.app_state.max_size_kb = max_size
        self.app_state.compact_mode = self._switch_value("compact-mode")
        self.app_state.skip_empty = self._switch_value("skip-empty")
        self.app_state.use_gitignore = self._switch_value("use-gitignore")
        self.app_state.force_include = self._switch_value("force-include")
        self.app_state.enable_token_count = self._switch_value("count-tokens")
        self.app_state.copy_to_clipboard = self._switch_value("copy-to-clipboard")

        include_text = self.query_one("#include-patterns", CompletionInput).value or ""
        exclude_text = self.query_one("#exclude-patterns", CompletionInput).value or ""
        tokenizer_model = self.query_one("#tokenizer-model", CompletionInput).value.strip() or self.app_state.tokenizer_model

        self.app_state.include_patterns = self._split_list(include_text)
        self.app_state.exclude_patterns = self._split_list(exclude_text)
        self.app_state.tokenizer_model = tokenizer_model

        self.app.notify("Настройки обновлены.", severity="information")
        self.dismiss(True)

    def on_switch_changed(self, event: Switch.Changed) -> None:
        state_id = f"#{event.switch.id}-state"
        try:
            state_label = self.query_one(state_id, Label)
        except Exception:  # textual versions <0.60 may emit different exceptions
            return
        state_label.update(self._state_text(event.value))

    def _switch_row(self, switch_id: str, label: str, value: bool) -> Horizontal:
        return Horizontal(
            Switch(value=value, id=switch_id),
            Label(label, classes="switch-label"),
            Label(self._state_text(value), id=f"{switch_id}-state", classes="switch-state"),
            classes="switch-field",
        )

    def _switch_value(self, switch_id: str) -> bool:
        return self.query_one(f"#{switch_id}", Switch).value

    @staticmethod
    def _state_text(value: bool) -> str:
        return "Вкл" if value else "Выкл"

    @staticmethod
    def _split_list(text: str) -> list[str]:
        if not text:
            return []
        return [item.strip() for item in text.split(",") if item.strip()]

    @staticmethod
    def _parse_int(value: str, *, fallback: int) -> int:
        try:
            return int(value)
        except ValueError:
            return fallback


__all__ = ["SettingsScreen"]
