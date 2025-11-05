"""Widget representing an actionable entry within the main menu."""

from __future__ import annotations

from typing import Optional

from rich.text import Text
from textual.widgets import Label, ListItem


class ActionItem(ListItem):
    """Selectable action inside the primary navigation list."""

    DEFAULT_CSS = """
    ActionItem {
        padding: 1 2;
        height: auto;
        margin: 0 0 1 0;
    }

    ActionItem.-selected {
        background: $accent 20%;
        color: $text;
    }
    """

    def __init__(self, label: str, description: str, *, action_id: str, id: Optional[str] = None) -> None:
        label_widget = Label()
        super().__init__(label_widget, id=id or f"action-{action_id}")
        self.action_id = action_id

        text = Text()
        text.append(label, style="bold")
        text.append("\n")
        text.append(description, style="dim")
        label_widget.update(text)
