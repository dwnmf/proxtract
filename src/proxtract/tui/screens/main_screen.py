"""Primary dashboard screen for the Proxtract TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListView

from ...core import ExtractionStats
from ...state import AppState
from ..widgets import ActionItem, SettingItem, SettingMetadata, SummaryDisplay
from .edit_setting_screen import EditSettingScreen
from .extract_screen import ExtractScreen


@dataclass(frozen=True)
class SettingSpec:
    """Definition describing how to render and edit a setting."""

    attr: str
    label: str
    description: str
    setting_type: str
    formatter: Callable[[Any], str]


class MainScreen(Screen):
    """Top-level screen that exposes settings and key actions."""

    ID = "main"

    def __init__(self, app_state: AppState) -> None:
        super().__init__(id=self.ID)
        self.app_state = app_state
        self._settings_view: ListView | None = None
        self._actions_view: ListView | None = None
        self._summary: SummaryDisplay | None = None
        self._items: dict[str, SettingItem] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Proxtract Settings", id="title"),
            Horizontal(
                Vertical(
                    Label("Settings", id="settings-header"),
                    ListView(id="settings-list"),
                ),
                Vertical(
                    Label("Actions", id="actions-header"),
                    ListView(id="actions-list"),
                ),
                id="content",
            ),
            Label("Extraction Summary", id="summary-header"),
            SummaryDisplay(),
        )
        yield Footer()

    def on_mount(self) -> None:
        self._settings_view = self.query_one("#settings-list", ListView)
        self._actions_view = self.query_one("#actions-list", ListView)
        self._summary = self.query_one(SummaryDisplay)

        for spec in self._setting_specs:
            metadata = SettingMetadata(
                key=spec.attr,
                label=spec.label,
                description=spec.description,
                value_formatter=spec.formatter,
                setting_type=spec.setting_type,
            )
            item = SettingItem(metadata, lambda attr=spec.attr: getattr(self.app_state, attr))
            self._items[spec.attr] = item
            self._settings_view.append(item)

        self._actions_view.append(
            ActionItem(
                "Extract Project",
                "Launch the extraction workflow with the current settings.",
                action_id="extract",
            )
        )

        if self.app_state.last_stats is not None:
            self._summary.update_stats(self.app_state.last_stats)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.control.id == "settings-list":
            self._handle_setting_selected(event.item)
        elif event.control.id == "actions-list":
            self._handle_action_selected(event.item)

    def _handle_setting_selected(self, item) -> None:
        if not isinstance(item, SettingItem):
            return

        attr = item.key
        spec = self._spec_by_attr(attr)
        current_value = getattr(self.app_state, attr)

        if spec.setting_type == "bool":
            setattr(self.app_state, attr, not bool(current_value))
            item.update_content()
            return

        self.app.push_screen(
            EditSettingScreen(
                key=spec.attr,
                label=spec.label,
                description=spec.description,
                setting_type=spec.setting_type,
                initial_value=self._value_to_string(current_value, spec.setting_type),
            ),
            callback=lambda value, attr=attr: self._apply_setting_update(attr, value),
        )

    def _handle_action_selected(self, item) -> None:
        if not isinstance(item, ActionItem):
            return

        if item.action_id == "extract":
            self.app.push_screen(
                ExtractScreen(self.app_state),
                callback=self._handle_extract_result,
            )

    def _handle_extract_result(self, stats: ExtractionStats | None) -> None:
        if stats is None:
            stats = self.app_state.last_stats

        if stats is not None and self._summary is not None:
            self._summary.update_stats(stats)

        output_item = self._items.get("output_path")
        if output_item is not None:
            output_item.update_content()

    def _apply_setting_update(self, attr: str, raw_value: str | None) -> None:
        if raw_value is None:
            return

        spec = self._spec_by_attr(attr)
        parsed = self._parse_value(raw_value, spec.setting_type)
        setattr(self.app_state, attr, parsed)

        item = self._items.get(attr)
        if item is not None:
            item.update_content()

    @property
    def _setting_specs(self) -> Sequence[SettingSpec]:
        return (
            SettingSpec(
                attr="output_path",
                label="Output Path",
                description="Destination file for extracted content.",
                setting_type="path",
                formatter=lambda value: str(value),
            ),
            SettingSpec(
                attr="max_size_kb",
                label="Max File Size (KB)",
                description="Files larger than this size are skipped.",
                setting_type="int",
                formatter=lambda value: f"{value} KB",
            ),
            SettingSpec(
                attr="compact_mode",
                label="Compact Mode",
                description="Use minimal separators between files in the bundle.",
                setting_type="bool",
                formatter=self._format_bool,
            ),
            SettingSpec(
                attr="skip_empty",
                label="Skip Empty Files",
                description="Do not include files without content.",
                setting_type="bool",
                formatter=self._format_bool,
            ),
            SettingSpec(
                attr="use_gitignore",
                label="Respect .gitignore",
                description="Honor .gitignore patterns when scanning directories.",
                setting_type="bool",
                formatter=self._format_bool,
            ),
            SettingSpec(
                attr="include_patterns",
                label="Include Patterns",
                description="Glob patterns that force inclusion (comma separated).",
                setting_type="list",
                formatter=self._format_list,
            ),
            SettingSpec(
                attr="exclude_patterns",
                label="Exclude Patterns",
                description="Glob patterns that exclude matches (comma separated).",
                setting_type="list",
                formatter=self._format_list,
            ),
            SettingSpec(
                attr="tokenizer_model",
                label="Tokenizer Model",
                description="Model name passed to the token counter.",
                setting_type="str",
                formatter=str,
            ),
            SettingSpec(
                attr="enable_token_count",
                label="Count Tokens",
                description="Estimate token usage for the extracted bundle.",
                setting_type="bool",
                formatter=self._format_bool,
            ),
            SettingSpec(
                attr="copy_to_clipboard",
                label="Copy to Clipboard",
                description="Copy extraction result to clipboard when supported.",
                setting_type="bool",
                formatter=self._format_bool,
            ),
        )

    def _spec_by_attr(self, attr: str) -> SettingSpec:
        for spec in self._setting_specs:
            if spec.attr == attr:
                return spec
        raise KeyError(attr)

    @staticmethod
    def _format_bool(value: Any) -> str:
        return "On" if bool(value) else "Off"

    @staticmethod
    def _format_list(value: Any) -> str:
        if not value:
            return "(none)"
        return ", ".join(str(item) for item in value)

    @staticmethod
    def _value_to_string(value: Any, setting_type: str) -> str:
        if setting_type == "list":
            return ", ".join(str(item) for item in value) if value else ""
        return str(value)

    @staticmethod
    def _parse_value(value: str, setting_type: str) -> Any:
        if setting_type == "int":
            return int(value)
        if setting_type == "list":
            parts = [part.strip() for part in value.split(",")]
            return [part for part in parts if part]
        if setting_type == "bool":
            lowered = value.strip().lower()
            return lowered in {"1", "true", "yes", "on"}
        if setting_type == "path":
            from pathlib import Path

            return Path(value).expanduser()
        return value


__all__ = ["MainScreen"]
