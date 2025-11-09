"""Textual-powered interface for Proxtract."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from rich.console import Console
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.widgets import Button, Checkbox, Footer, Input, Log, Static

from .config import apply_config, load_config, save_config
from .core import ExtractionError, ExtractionStats
from .state import AppState


class InteractiveShell(App[None]):
    """Minimalistic gradient Textual interface for Proxtract."""

    CSS = """
    Screen {
        layout: vertical;
        align: center middle;
        background: linear-gradient(160deg, #1a1f35, #2c3a5b);
        color: #f7f9ff;
    }

    #card {
        width: 90%;
        max-width: 120;
        border: round #7f5af0;
        background: linear-gradient(160deg, rgba(26, 31, 53, 0.95), rgba(16, 19, 33, 0.95));
        padding: 2 4;
        margin: 2;
        height: auto;
        box-sizing: border-box;
    }

    .title {
        content-align: center middle;
        text-style: bold;
        font-size: 2;
    }

    .subtitle {
        content-align: center middle;
        color: #b1b8e6;
        margin-bottom: 1;
    }

    #form {
        grid-size: 2;
        grid-gutter: 1 2;
        margin-top: 1;
    }

    #form > .label {
        align-horizontal: right;
        color: #9da6d4;
    }

    #form Input {
        background: rgba(15, 18, 30, 0.6);
        border: round #3d4469;
    }

    #toggles {
        margin-top: 1;
        padding-top: 1;
        border-top: solid #2f3452;
        layout: vertical;
        gap: 1;
    }

    .toggle {
        layout: horizontal;
        align: center left;
        gap: 1;
    }

    .section-label {
        text-style: bold;
        color: #d3dcff;
        margin-bottom: 1;
    }

    #buttons {
        layout: horizontal;
        gap: 2;
        margin-top: 2;
        content-align: center middle;
        flex-wrap: wrap;
    }

    Button.action {
        border: round #7f5af0;
        background: linear-gradient(160deg, #41348f, #2e1f66);
        color: #fefbff;
        padding: 1 3;
    }

    Button.success {
        background: linear-gradient(160deg, #2ebf91, #1a8c6d);
    }

    Button.warning {
        background: linear-gradient(160deg, #f5a623, #d48806);
    }

    Button.danger {
        background: linear-gradient(160deg, #ff5f6d, #d9344b);
    }

    #log {
        height: 14;
        margin-top: 2;
        border: round #3d4469;
        background: rgba(10, 12, 20, 0.6);
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Выйти"),
        Binding("ctrl+s", "save", "Сохранить"),
        Binding("f5", "refresh", "Обновить"),
    ]

    def __init__(self, *, state: AppState | None = None) -> None:
        super().__init__()
        self.state = apply_config(state or AppState(), load_config())
        self._log_widget: Log | None = None
        self._messages: list[str] = []

    def compose(self) -> ComposeResult:
        with Container(id="card"):
            yield Static("Proxtract", classes="title")
            yield Static("Минималистичный текстовый интерфейс на Textual.", classes="subtitle")
            with Grid(id="form"):
                yield Static("Source path", classes="label")
                yield Input(id="source_path", placeholder="Путь к проекту")
                yield Static("Output file", classes="label")
                yield Input(id="output_path", placeholder="Файл для сохранения")
                yield Static("Max size (KB)", classes="label")
                yield Input(id="max_size_kb", placeholder="500")
                yield Static("Tokenizer model", classes="label")
                yield Input(id="tokenizer_model", placeholder="gpt-4o")
                yield Static("Include patterns", classes="label")
                yield Input(id="include_patterns", placeholder="src/**/*.py, README.md")
                yield Static("Exclude patterns", classes="label")
                yield Input(id="exclude_patterns", placeholder="tests/**")
            with Vertical(id="toggles"):
                yield Static("Флаги", classes="section-label")
                for checkbox in self._build_toggle_section():
                    yield checkbox
            with Horizontal(id="buttons"):
                yield Button("Извлечь", id="run", classes="action success")
                yield Button("Сохранить", id="save", classes="action")
                yield Button("Обновить", id="refresh", classes="action warning")
                yield Button("Выход", id="quit", classes="action danger")
            yield Log(id="log")
        yield Footer()

    def _build_toggle_section(self) -> Iterable[Checkbox]:
        return (
            Checkbox("Компактный режим", id="compact_mode"),
            Checkbox("Пропускать пустые", id="skip_empty"),
            Checkbox("Использовать .gitignore", id="use_gitignore"),
            Checkbox("Принудительно включать", id="force_include"),
            Checkbox("Считать токены", id="count_tokens"),
            Checkbox("Копировать в буфер", id="copy_clipboard"),
        )

    async def on_mount(self) -> None:
        self._log_widget = self.query_one(Log)
        self._populate_form()
        self._append_log("Интерфейс готов. Укажите параметры и нажмите \"Извлечь\".")

    def _populate_form(self) -> None:
        self.query_one("#source_path", Input).value = str(self.state.source_root)
        self.query_one("#output_path", Input).value = str(self.state.output_path)
        self.query_one("#max_size_kb", Input).value = str(self.state.max_size_kb)
        self.query_one("#tokenizer_model", Input).value = self.state.tokenizer_model
        self.query_one("#include_patterns", Input).value = ", ".join(self.state.include_patterns)
        self.query_one("#exclude_patterns", Input).value = ", ".join(self.state.exclude_patterns)
        self.query_one("#compact_mode", Checkbox).value = self.state.compact_mode
        self.query_one("#skip_empty", Checkbox).value = self.state.skip_empty
        self.query_one("#use_gitignore", Checkbox).value = self.state.use_gitignore
        self.query_one("#force_include", Checkbox).value = self.state.force_include
        self.query_one("#count_tokens", Checkbox).value = self.state.enable_token_count
        self.query_one("#copy_clipboard", Checkbox).value = self.state.copy_to_clipboard

    def _append_log(self, message: str) -> None:
        self._messages.append(message)
        if self._log_widget is not None:
            self._log_widget.write_line(message)

    @property
    def messages(self) -> list[str]:
        return list(self._messages)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run":
            await self._handle_run()
        elif event.button.id == "save":
            await self._handle_save()
        elif event.button.id == "refresh":
            await self._handle_refresh()
        elif event.button.id == "quit":
            await self.action_quit()

    async def action_save(self) -> None:
        await self._handle_save()

    async def action_refresh(self) -> None:
        await self._handle_refresh()

    async def _handle_refresh(self) -> None:
        self._populate_form()
        self._append_log("Настройки восстановлены из текущего состояния.")

    async def _handle_save(self) -> None:
        try:
            self._update_state_from_form()
        except ValueError as exc:
            self._append_log(f"[Ошибка] {exc}")
            return
        try:
            save_config(self.state)
        except Exception as exc:  # pragma: no cover - depends on file system
            self._append_log(f"[Ошибка] Не удалось сохранить настройки: {exc}")
            return
        self._append_log("Настройки сохранены.")

    async def _handle_run(self) -> None:
        try:
            self._update_state_from_form()
        except ValueError as exc:
            self._append_log(f"[Ошибка] {exc}")
            return

        root = self.state.source_root
        destination = self.state.output_path

        if not root.exists():
            self._append_log("[Ошибка] Укажите корректный source_path.")
            return

        self._append_log(f"Начинаем извлечение из {root} в {destination}...")

        try:
            stats = await self.call_in_thread(self._perform_extract, root, destination)
        except ExtractionError as exc:
            self._append_log(f"[Ошибка] Извлечение завершилось с ошибкой: {exc}")
            return
        except Exception as exc:  # pragma: no cover - unexpected errors
            self._append_log(f"[Ошибка] Непредвиденная ошибка: {exc}")
            return

        self.state.last_stats = stats
        for line in self._format_summary(stats):
            self._append_log(line)

        if self.state.copy_to_clipboard:
            await self.call_in_thread(self._copy_to_clipboard, stats)

    def _update_state_from_form(self) -> None:
        source = self.query_one("#source_path", Input).value.strip()
        output = self.query_one("#output_path", Input).value.strip()
        max_size = self.query_one("#max_size_kb", Input).value.strip()
        tokenizer = self.query_one("#tokenizer_model", Input).value.strip()
        include_raw = self.query_one("#include_patterns", Input).value
        exclude_raw = self.query_one("#exclude_patterns", Input).value

        if not source:
            raise ValueError("source_path не может быть пустым")
        if not output:
            raise ValueError("output_path не может быть пустым")

        try:
            size_value = int(max_size)
        except ValueError as exc:
            raise ValueError("max_size_kb должно быть числом") from exc
        if size_value <= 0:
            raise ValueError("max_size_kb должно быть больше нуля")

        self.state.set_source_root(source)
        self.state.set_output_path(output)
        self.state.max_size_kb = size_value
        self.state.tokenizer_model = tokenizer or self.state.tokenizer_model
        self.state.include_patterns = self._parse_patterns(include_raw)
        self.state.exclude_patterns = self._parse_patterns(exclude_raw)
        self.state.compact_mode = self.query_one("#compact_mode", Checkbox).value
        self.state.skip_empty = self.query_one("#skip_empty", Checkbox).value
        self.state.use_gitignore = self.query_one("#use_gitignore", Checkbox).value
        self.state.force_include = self.query_one("#force_include", Checkbox).value
        self.state.enable_token_count = self.query_one("#count_tokens", Checkbox).value
        self.state.copy_to_clipboard = self.query_one("#copy_clipboard", Checkbox).value

    def _parse_patterns(self, value: str) -> list[str]:
        if not value.strip():
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def _perform_extract(self, root: Path, destination: Path) -> ExtractionStats:
        extractor = self.state.create_extractor()

        def _callback(advance: int = 1, description: str | None = None) -> None:
            if description:
                self.call_from_thread(self._append_log, f"→ {description}")

        return extractor.extract(root, destination, progress_callback=_callback)

    def _format_summary(self, stats: ExtractionStats) -> Iterable[str]:
        yield "[Готово] Извлечение завершено."
        yield f"Файлов обработано: {stats.processed_files}"
        yield f"Всего байт: {stats.total_bytes}"
        if stats.token_count is not None:
            token_info = f"Токены: {stats.token_count}"
            if stats.token_model:
                token_info += f" ({stats.token_model})"
            yield token_info
        skipped = ", ".join(f"{reason}: {count}" for reason, count in stats.skipped.items() if count)
        if skipped:
            yield f"Пропущено: {skipped}"
        if stats.errors:
            yield "Предупреждения: " + " | ".join(stats.errors)
        yield f"Результат: {stats.output}"

    def _copy_to_clipboard(self, stats: ExtractionStats) -> None:
        try:
            import pyperclip  # type: ignore

            contents = Path(stats.output).read_text(encoding="utf-8")
            pyperclip.copy(contents)
            self.call_from_thread(self._append_log, "Результат скопирован в буфер обмена.")
        except Exception as exc:  # pragma: no cover - platform specific
            self.call_from_thread(self._append_log, f"[Предупреждение] Не удалось скопировать: {exc}")


def run_interactive(console: Console | None = None) -> None:  # noqa: ARG001 - console retained for compatibility
    """Launch the Textual interface."""

    InteractiveShell().run()


__all__ = ["run_interactive", "InteractiveShell"]
