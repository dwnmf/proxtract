"""Widget representing an editable application setting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from rich.text import Text
from textual.widgets import Label, ListItem


@dataclass(slots=True)
class SettingMetadata:
    """Metadata describing how a setting should be displayed and edited."""

    key: str
    label: str
    description: str
    value_formatter: Callable[[object], str]
    setting_type: str


class SettingItem(ListItem):
    """Selectable list entry for a single ``AppState`` attribute."""

    DEFAULT_CSS = """
    SettingItem {
        padding: 1 2;
        height: auto;
        margin: 0 0 1 0;
    }

    SettingItem.-selected {
        background: $accent 20%;
        color: $text;
    }
    """

    def __init__(
        self,
        metadata: SettingMetadata,
        value_getter: Callable[[], object],
        *,
        id: Optional[str] = None,
    ) -> None:
        label_widget = Label()
        super().__init__(label_widget, id=id or f"setting-{metadata.key}")
        self.metadata = metadata
        self._value_getter = value_getter
        self._label = label_widget
        self.update_content()

    @property
    def setting_type(self) -> str:
        return self.metadata.setting_type

    @property
    def key(self) -> str:
        return self.metadata.key

    def update_content(self) -> None:
        """Refresh the rendered text based on the latest value."""

        value = self._value_getter()
        formatted_value = self.metadata.value_formatter(value)

        text = Text()
        text.append(self.metadata.label, style="bold")
        text.append("\n")
        text.append(formatted_value, style="cyan")
        text.append("\n")
        text.append(self.metadata.description, style="dim")

        self._label.update(text)
