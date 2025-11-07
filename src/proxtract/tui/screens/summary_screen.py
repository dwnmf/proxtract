"""Modal summary screen shown after the extraction flow completes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from ...core import ExtractionStats
from .. import STYLES_PATH


class SummaryScreen(ModalScreen[None]):
    """Present extraction results with actionable follow-up controls."""

    CSS_PATH = STYLES_PATH

    def __init__(self, stats: ExtractionStats) -> None:
        super().__init__(id="summary-screen")
        self._stats = stats

    def compose(self) -> ComposeResult:
        processed = self._stats.processed_files
        total_size = self._format_size(self._stats.total_bytes)
        token_label = (
            f"{self._stats.token_count:,} ({self._stats.token_model})"
            if self._stats.token_count is not None
            else "н/д"
        )

        skipped_total = sum(self._stats.skipped.values())
        skipped_body = self._build_skipped_summary()
        warnings_body = self._build_warnings()

        yield Vertical(
            Vertical(
                Label("Извлечение завершено", id="summary-title"),
                Label(f"Результат сохранён в {self._stats.output}", id="summary-path"),
                id="summary-modal-header",
            ),
            Horizontal(
                self._metric("Обработано файлов", f"{processed}"),
                self._metric("Общий размер", total_size),
                self._metric("Токены", token_label),
                id="summary-metrics",
            ),
            Vertical(
                Label(f"Пропущено файлов ({skipped_total})", classes="group-title"),
                skipped_body,
                classes="summary-block",
            ),
            Vertical(
                Label("Предупреждения", classes="group-title"),
                warnings_body,
                classes="summary-block",
            ),
            Horizontal(
                Button("Копировать в буфер", id="copy-output", variant="primary"),
                Button("Открыть файл", id="open-output"),
                Button("Закрыть", id="close-summary"),
                id="summary-buttons",
            ),
            classes="modal-card modal-large summary-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-output":
            self._copy_output()
        elif event.button.id == "open-output":
            self._open_output()
        elif event.button.id == "close-summary":
            self.dismiss(None)

    def _copy_output(self) -> None:
        try:
            import pyperclip  # type: ignore
        except Exception:
            self.app.notify("pyperclip не установлен.", severity="warning")
            return

        try:
            contents = Path(self._stats.output).read_text(encoding="utf-8")
        except Exception as exc:
            self.app.notify(f"Не удалось прочитать файл: {exc}", severity="error")
            return

        try:
            pyperclip.copy(contents)
        except Exception as exc:  # pragma: no cover - environment specific
            self.app.notify(f"Буфер обмена недоступен: {exc}", severity="warning")
        else:
            self.app.notify("Содержимое скопировано в буфер обмена.", severity="information")

    def _open_output(self) -> None:
        path = Path(self._stats.output)
        if not path.exists():
            self.app.notify("Файл ещё не создан.", severity="warning")
            return

        try:
            if sys.platform.startswith("darwin"):
                subprocess.Popen(["open", str(path)])
            elif sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:  # pragma: no cover - environment dependent
            self.app.notify(f"Не удалось открыть файл: {exc}", severity="warning")
        else:
            self.app.notify("Открытие файла запущено.", severity="information")

    def _metric(self, label: str, value: str) -> Vertical:
        return Vertical(
            Label(label, classes="metric-label"),
            Label(value, classes="metric-value"),
            classes="metric-card",
        )

    def _build_skipped_summary(self) -> Vertical:
        if not self._stats.skipped:
            return Vertical(Static("Все файлы обработаны.", classes="summary-empty"))

        rows = [
            Label(f"{reason}: {count}", classes="summary-row")
            for reason, count in sorted(self._stats.skipped.items(), key=lambda item: item[0])
        ]
        return Vertical(*rows, classes="summary-list")

    def _build_warnings(self) -> Vertical:
        if not self._stats.errors:
            return Vertical(Static("Предупреждений нет.", classes="summary-empty"))

        rows = [Label(f"• {message}", classes="summary-row") for message in self._stats.errors]
        return Vertical(*rows, classes="summary-list")

    @staticmethod
    def _format_size(total_bytes: int) -> str:
        if total_bytes <= 0:
            return "0 КБ"
        kb = total_bytes / 1024
        if kb < 1024:
            return f"{kb:.1f} КБ"
        mb = kb / 1024
        return f"{mb:.2f} МБ"


__all__ = ["SummaryScreen"]
