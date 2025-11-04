"""Modal screen for configuring and running an extraction."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.worker import Worker, WorkerState
from textual.widgets import Button, Label, ProgressBar

from ...core import ExtractionError, ExtractionStats
from ...state import AppState
from ..widgets import CompletionInput, SummaryDisplay
from .. import STYLES_PATH


class ExtractScreen(ModalScreen[ExtractionStats | None]):
    """Modal workflow for launching a project extraction."""

    CSS_PATH = STYLES_PATH

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
        super().__init__(id="extract-screen")
        self.app_state = app_state
        self._progress_bar: ProgressBar | None = None
        self._status_label: Label | None = None
        self._summary: SummaryDisplay | None = None
        self._start_button: Button | None = None
        self._worker: Worker | None = None
        self._cancel_button: Button | None = None

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Extract Project", id="extract-title"),
            Label(
                "Configure the source directory and output path, then launch extraction.",
                id="extract-description",
            ),
            Label("Source Directory", id="extract-root-label"),
            CompletionInput(id="extract-root", mode="path"),
            Label("Output File", id="extract-output-label"),
            CompletionInput(id="extract-output", mode="path"),
            Horizontal(
                Button("Cancel", id="cancel"),
                Button("Start Extraction", id="start", variant="primary"),
                id="extract-buttons",
            ),
            ProgressBar(id="extract-progress", total=100),
            Label("", id="extract-status"),
            SummaryDisplay(),
            id="extract-container",
        )

    def on_mount(self) -> None:
        root_input = self.query_one("#extract-root", CompletionInput)
        output_input = self.query_one("#extract-output", CompletionInput)
        root_input.value = str(self.app_state.output_path.parent)
        output_input.value = str(self.app_state.output_path)

        self._progress_bar = self.query_one(ProgressBar)
        self._status_label = self.query_one("#extract-status", Label)
        self._summary = self.query_one(SummaryDisplay)
        self._start_button = self.query_one("#start", Button)
        self._cancel_button = self.query_one("#cancel", Button)
        if self._progress_bar is not None:
            self._progress_bar.display = False
        if self._cancel_button is not None:
            self._cancel_button.label = "Cancel"

        if self.app_state.last_stats is not None:
            self._summary.update_stats(self.app_state.last_stats)

        root_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "start":
            self._begin_extraction()

    def _begin_extraction(self) -> None:
        root = self.query_one("#extract-root", CompletionInput).value.strip()
        output = self.query_one("#extract-output", CompletionInput).value.strip()

        if not root or not output:
            self.app.notify("Source and output paths are required.", severity="warning")
            return

        self.app_state.output_path = Path(output).expanduser()

        if self._start_button is not None:
            self._start_button.disabled = True

        if self._cancel_button is not None:
            self._cancel_button.label = "Cancel"

        if self._progress_bar is not None:
            self._progress_bar.display = True
            self._progress_bar.update(progress=0, total=100)

        self._update_status("Preparing...")

        work = partial(self._execute_extraction, root, output)
        self._worker = self.run_worker(
            work,
            name=root,
            group=output,
            exclusive=True,
            thread=True,
            exit_on_error=False,
        )

    def _update_status(self, message: str) -> None:
        if self._status_label is not None:
            self._status_label.update(message)

    def _execute_extraction(self, root: str, output: str) -> None:
        root_path = Path(root).expanduser()
        output_path = Path(output).expanduser()

        self.app.call_from_thread(self._update_status, "Scanning files...")

        try:
            total_files = sum(1 for path in root_path.rglob("*") if path.is_file())
        except Exception as exc:  # pragma: no cover - defensive guard
            self.app.call_from_thread(
                self.post_message, self.ExtractionFailed(str(exc))
            )
            return

        self.app.call_from_thread(
            self.post_message, self.ExtractionStarted(total=max(total_files, 1))
        )

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
            stats = extractor.extract(root_path, output_path, progress_callback=progress_callback)
        except ExtractionError as exc:
            self.app.call_from_thread(
                self.post_message, self.ExtractionFailed(str(exc))
            )
            return

        self.app_state.last_stats = stats
        self.app.call_from_thread(
            self.post_message, self.ExtractionCompleted(stats)
        )

    def on_extract_screen_extraction_started(self, message: ExtractionStarted) -> None:
        if self._progress_bar is not None:
            self._progress_bar.update(progress=0, total=message.total)
        self._update_status("Scanning files...")

    def on_extract_screen_extraction_progress(self, message: ExtractionProgress) -> None:
        if self._progress_bar is not None:
            self._progress_bar.update(progress=message.processed, total=message.total)
        if message.description:
            self._update_status(f"Processing {message.description}")

    def on_extract_screen_extraction_failed(self, message: ExtractionFailed) -> None:
        if self._progress_bar is not None:
            self._progress_bar.display = False
        if self._start_button is not None:
            self._start_button.disabled = False
        self._update_status(f"Error: {message.message}")
        self._worker = None

    def on_extract_screen_extraction_completed(self, message: ExtractionCompleted) -> None:
        if self._progress_bar is not None:
            self._progress_bar.display = False
        if self._start_button is not None:
            self._start_button.disabled = False
        if self._cancel_button is not None:
            self._cancel_button.label = "Close"
        if self._summary is not None:
            self._summary.update_stats(message.stats)
        self._update_status("Extraction complete.")
        self._worker = None
        self.dismiss(message.stats)

        if self.app_state.copy_to_clipboard:
            try:
                import pyperclip  # type: ignore

                try:
                    contents = message.stats.output.read_text(encoding="utf-8")
                    pyperclip.copy(contents)
                    self.app.notify("Copied extraction result to clipboard.", severity="information")
                except Exception as exc:  # pragma: no cover - environment specific
                    self.app.notify(f"Clipboard copy failed: {exc}", severity="warning")
            except Exception:  # pragma: no cover - optional dependency missing
                self.app.notify("pyperclip not installed; cannot copy to clipboard.", severity="warning")

    def dismiss(self, result: ExtractionStats | None = None) -> None:  # type: ignore[override]
        if self._worker is not None and self._worker.is_running:
            self._worker.cancel()
            self._worker = None
        super().dismiss(result if result is not None else self.app_state.last_stats)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if self._worker is None or event.worker is not self._worker:
            return

        if event.state == WorkerState.RUNNING:
            return

        self._worker = None

        if self._progress_bar is not None:
            self._progress_bar.display = False

        if self._start_button is not None:
            self._start_button.disabled = False

        if self._cancel_button is not None:
            self._cancel_button.label = "Close"

        if event.state == WorkerState.CANCELLED:
            self._update_status("Extraction cancelled.")
            event.stop()
            return

        if event.state == WorkerState.ERROR:
            error = event.worker.error
            message = str(error) if error is not None else "Unknown worker error"
            self._update_status(f"Error: {message}")
            self.app.notify(f"Extraction failed: {message}", severity="error")
            event.stop()


__all__ = ["ExtractScreen"]
