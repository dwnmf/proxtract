"""Widget for presenting ``ExtractionStats`` summaries."""

from __future__ import annotations

from typing import Optional

from rich.table import Table
from textual.widgets import Static

from ...core import ExtractionStats


class SummaryDisplay(Static):
    """Render extraction statistics in a compact table."""

    DEFAULT_CSS = """
    SummaryDisplay {
        border: heavy $accent;
        padding: 1 2;
        height: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__(id="summary")
        self._stats: Optional[ExtractionStats] = None

    def update_stats(self, stats: ExtractionStats) -> None:
        """Store and render a new ``ExtractionStats`` payload."""

        self._stats = stats
        self.refresh()

    def clear_stats(self) -> None:
        """Remove any previously rendered stats."""

        self._stats = None
        self.refresh()

    def render(self) -> Table | str:
        if self._stats is None:
            return "No extraction has been run yet."

        stats = self._stats
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="right", style="bold")
        table.add_column()
        table.add_row("Root", str(stats.root))
        table.add_row("Output", str(stats.output))
        table.add_row("Files", str(stats.processed_files))
        table.add_row("Bytes", str(stats.total_bytes))
        if stats.token_count is not None:
            table.add_row("Tokens", f"{stats.token_count} ({stats.token_model})")
        skipped_summary = ", ".join(f"{reason}: {count}" for reason, count in stats.skipped.items() if count)
        if skipped_summary:
            table.add_row("Skipped", skipped_summary)
        if stats.errors:
            table.add_row("Warnings", " | ".join(stats.errors))
        return table
