"""Focused extractor-first screen for the Proxtract TUI."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Optional

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar
from textual.worker import Worker, WorkerState

from ...core import ExtractionError, ExtractionStats
from ...state import AppState
from ..widgets import CompletionInput, SummaryDisplay
from .settings_screen import SettingsScreen
from .summary_screen import SummaryScreen


class MainScreen(Screen):
    """Single-screen extractor workflow with progressive disclosure controls."""

    ID = "main"
    TINY_WIDTH = 45
    NARROW_WIDTH = 80
    COMPACT_WIDTH = 60

    @dataclass
    class ExtractionProgress(Message):
        processed: int
        total: int
        description: str

    @dataclass
    class ExtractionStarted(Message):
        total: int

    @dataclass
    class ExtractionFailed(Message):
        message: str

    @dataclass
    class ExtractionCompleted(Message):
        stats: ExtractionStats

    def __init__(self, app_state: AppState) -> None:
        super().__init__(id=self.ID)
        self.app_state = app_state
        self._source_input: CompletionInput | None = None
        self._output_input: CompletionInput | None = None
        self._extract_button: Button | None = None
        self._settings_button: Button | None = None
        self._progress_bar: ProgressBar | None = None
        self._status_label: Label | None = None
        self._summary_widget: SummaryDisplay | None = None
        self._summary_container: Vertical | None = None
        self._worker: Worker | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Vertical(
            Label("Proxtract", id="title"),
            Label("Укажите проект и получите все его файлы в одном пакете.", id="subtitle"),
            Vertical(
                Vertical(
                    Label("Директория проекта", classes="form-label"),
                    CompletionInput(id="source-input", mode="path", classes="form-input"),
                    classes="form-field",
                ),
                Vertical(
                    Label("Выходной файл", classes="form-label"),
                    CompletionInput(id="output-input", mode="path", classes="form-input"),
                    classes="form-field",
                ),
                Horizontal(
                    Button("Извлечь", id="extract", variant="primary"),
                    Button("Настройки", id="settings", variant="primary"),
                    id="form-actions",
                ),
                ProgressBar(id="extract-progress", total=100),
                Label("Готово к запуску.", id="extract-status"),
                Vertical(
                    Label("Сводка последнего запуска", id="summary-header"),
                    SummaryDisplay(),
                    id="summary-section",
                ),
                id="extractor-form",
                classes="panel-card",
            ),
            id="main-body",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._source_input = self.query_one("#source-input", CompletionInput)
        self._output_input = self.query_one("#output-input", CompletionInput)
        self._extract_button = self.query_one("#extract", Button)
        self._settings_button = self.query_one("#settings", Button)
        self._progress_bar = self.query_one(ProgressBar)
        self._status_label = self.query_one("#extract-status", Label)
        self._summary_widget = self.query_one(SummaryDisplay)
        self._summary_container = self.query_one("#summary-section", Vertical)

        self._source_input.value = str(self.app_state.source_root)
        self._output_input.value = str(self.app_state.output_path)
        self._source_input.focus()

        if self._progress_bar is not None:
            self._progress_bar.display = False

        if self.app_state.last_stats is not None and self._summary_widget is not None:
            self._summary_widget.update_stats(self.app_state.last_stats)
        self._update_summary_visibility(self.app_state.last_stats is not None)
        self._update_breakpoints(self.size.width if self.size is not None else None)

    def on_resize(self, event: events.Resize) -> None:
        self._update_breakpoints(event.size.width)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "extract":
            if self._worker is not None and self._worker.is_running:
                self._cancel_extraction()
            else:
                self._begin_extraction()
        elif event.button.id == "settings":
            self.app.push_screen(
                SettingsScreen(self.app_state),
                callback=lambda _: self._handle_settings_closed(),
            )

    def _handle_settings_closed(self) -> None:
        if self._output_input is not None:
            self._output_input.value = str(self.app_state.output_path)

    def _begin_extraction(self) -> None:
        if self._source_input is None or self._output_input is None:
            return

        root_text = (self._source_input.value or "").strip()
        output_text = (self._output_input.value or "").strip()

        if not root_text or not output_text:
            self.app.notify("Укажите исходную директорию и выходной файл.", severity="warning")
            return

        root = Path(root_text).expanduser()
        if not root.exists() or not root.is_dir():
            self.app.notify("Указанная директория недоступна.", severity="error")
            return

        self.app_state.set_source_root(root)
        self.app_state.set_output_path(output_text)

        if self._progress_bar is not None:
            self._progress_bar.display = True
            self._progress_bar.update(progress=0, total=100)
        self._update_status("Подготовка к извлечению…")
        self._set_busy(True)

        work = partial(self._execute_extraction, root, self.app_state.output_path)
        self._worker = self.run_worker(
            work,
            name=str(root),
            group=str(self.app_state.output_path),
            exclusive=True,
            thread=True,
            exit_on_error=False,
        )

    def _cancel_extraction(self) -> None:
        if self._worker is None:
            return
        if self._worker.is_running:
            self._worker.cancel()
        self._update_status("Отмена…")

    def _execute_extraction(self, root: Path, output: Path) -> None:
        self.app.call_from_thread(self._update_status, "Сканирование файлов…")

        try:
            total_files = sum(1 for path in root.rglob("*") if path.is_file())
        except Exception as exc:  # pragma: no cover
            self.app.call_from_thread(self.post_message, self.ExtractionFailed(str(exc)))
            return

        self.app.call_from_thread(self.post_message, self.ExtractionStarted(total=max(total_files, 1)))

        processed = 0

        def progress_callback(*, advance: int, description: Optional[str] = None) -> None:
            nonlocal processed
            processed += advance
            self.app.call_from_thread(
                self.post_message,
                self.ExtractionProgress(
                    processed=processed,
                    total=max(total_files, 1),
                    description=description or "",
                ),
            )

        extractor = self.app_state.create_extractor()

        try:
            stats = extractor.extract(root, output, progress_callback=progress_callback)
        except ExtractionError as exc:
            self.app.call_from_thread(self.post_message, self.ExtractionFailed(str(exc)))
            return

        if total_files == 0 and processed == 0:
            processed = 1
            self.app.call_from_thread(
                self.post_message,
                self.ExtractionProgress(processed=processed, total=1, description=""),
            )

        self.app_state.last_stats = stats
        self.app.call_from_thread(self.post_message, self.ExtractionCompleted(stats))

    def on_main_screen_extraction_started(self, message: ExtractionStarted) -> None:
        if self._progress_bar is not None:
            self._progress_bar.update(progress=0, total=message.total)
        self._update_status("Сканирование файлов…")

    def on_main_screen_extraction_progress(self, message: ExtractionProgress) -> None:
        if self._progress_bar is not None:
            self._progress_bar.update(progress=message.processed, total=message.total)
        if message.description:
            self._update_status(f"Обработка: {message.description}")

    def on_main_screen_extraction_failed(self, message: ExtractionFailed) -> None:
        self._reset_busy_state()
        self._update_status(f"Ошибка: {message.message}")
        self.app.notify(f"Извлечение не удалось: {message.message}", severity="error")

    def on_main_screen_extraction_completed(self, message: ExtractionCompleted) -> None:
        self._reset_busy_state()
        if self._summary_widget is not None:
            self._summary_widget.update_stats(message.stats)
        self._update_summary_visibility(True)
        self._update_status("Извлечение завершено.")
        self.app.push_screen(SummaryScreen(message.stats))

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if self._worker is None or event.worker is not self._worker:
            return

        if event.state == WorkerState.RUNNING:
            return

        self._worker = None
        if event.state == WorkerState.CANCELLED:
            self._reset_busy_state()
            self._update_status("Извлечение отменено.")
            event.stop()
            return

        if event.state == WorkerState.ERROR:
            self._reset_busy_state()
            error = event.worker.error
            message = str(error) if error is not None else "Неизвестная ошибка."
            self._update_status(f"Ошибка: {message}")
            self.app.notify(f"Извлечение не удалось: {message}", severity="error")
            event.stop()

    def _reset_busy_state(self) -> None:
        self._set_busy(False)
        if self._progress_bar is not None:
            self._progress_bar.display = False

    def _set_busy(self, busy: bool) -> None:
        if self._source_input is not None:
            self._source_input.disabled = busy
        if self._output_input is not None:
            self._output_input.disabled = busy
        if self._settings_button is not None:
            self._settings_button.disabled = busy
        if self._extract_button is not None:
            self._extract_button.label = "Отмена" if busy else "Извлечь"
            self._extract_button.variant = "error" if busy else "primary"
        if busy and self._progress_bar is not None:
            self._progress_bar.display = True

    def _update_status(self, message: str) -> None:
        if self._status_label is not None:
            self._status_label.update(message)

    def _update_summary_visibility(self, show: bool) -> None:
        if self._summary_container is None:
            return
        self._summary_container.display = show

    def _update_breakpoints(self, width: int | None) -> None:
        self.set_class(False, "bp-tiny")
        self.set_class(False, "bp-narrow")
        self.set_class(False, "bp-compact")

        if width is None:
            return
        if width <= self.TINY_WIDTH:
            self.set_class(True, "bp-tiny")
        elif width <= self.COMPACT_WIDTH:
            self.set_class(True, "bp-compact")
        elif width <= self.NARROW_WIDTH:
            self.set_class(True, "bp-narrow")


__all__ = ["MainScreen"]
