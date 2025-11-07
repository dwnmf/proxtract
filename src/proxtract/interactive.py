"""Rich + prompt_toolkit powered REPL for Proxtract."""

from __future__ import annotations

import shlex
from contextlib import nullcontext
from pathlib import Path
from typing import Iterable, List, Sequence

try:  # pragma: no cover - optional import guarded for minimal envs
    from prompt_toolkit import PromptSession  # type: ignore
    from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter  # type: ignore
    from prompt_toolkit.document import Document  # type: ignore
    from prompt_toolkit.history import FileHistory, InMemoryHistory  # type: ignore
    from prompt_toolkit.patch_stdout import patch_stdout  # type: ignore

    PROMPT_TOOLKIT_AVAILABLE = True
except Exception:  # pragma: no cover - fallback when prompt_toolkit absent
    PromptSession = None  # type: ignore
    PROMPT_TOOLKIT_AVAILABLE = False

    class Completion:  # type: ignore[override]
        def __init__(self, text: str, start_position: int = 0, display=None, display_meta=None) -> None:
            self.text = text
            self.start_position = start_position
            self.display = display
            self.display_meta = display_meta

    class Completer:  # type: ignore[override]
        def get_completions(self, *args, **kwargs):
            return []

    class WordCompleter(Completer):  # type: ignore[override]
        def __init__(self, words, **_):
            self.words = list(words)

    class PathCompleter(Completer):  # type: ignore[override]
        def __init__(self, **_):
            pass

        def get_completions(self, *args, **kwargs):
            return []

    class Document:  # type: ignore[override]
        def __init__(self, text: str = "", cursor_position: int | None = None) -> None:
            self.text = text
            self.cursor_position = len(text) if cursor_position is None else cursor_position

        @property
        def text_before_cursor(self) -> str:
            return self.text[: self.cursor_position]

        def get_word_before_cursor(self) -> str:
            text = self.text_before_cursor.rstrip()
            return text.split()[-1] if text.split() else ""

    class InMemoryHistory:  # type: ignore[override]
        def __init__(self, *_, **__):
            pass

    class FileHistory(InMemoryHistory):  # type: ignore[override]
        def __init__(self, *_, **__):
            raise RuntimeError("prompt_toolkit is required for persistent history support")

    def patch_stdout():  # type: ignore[override]
        return nullcontext()
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from .config import apply_config, load_config, save_config
from .core import ExtractionError, ExtractionStats
from .state import AppState
from .utils import create_console

COMMANDS = ["extract", "set", "show", "config", "save", "help", "exit", "quit"]
SETTING_KEYS = [
    "source_path",
    "output_path",
    "max_size_kb",
    "compact_mode",
    "skip_empty",
    "use_gitignore",
    "force_include",
    "include_patterns",
    "exclude_patterns",
    "count_tokens",
    "tokenizer_model",
    "copy_clipboard",
]
BOOLEAN_KEYS = {
    "compact_mode",
    "skip_empty",
    "use_gitignore",
    "force_include",
    "count_tokens",
    "copy_clipboard",
}
PATH_KEYS = {"source_path", "output_path"}
PATH_ONLY_DIR_KEYS = {"source_path"}


def _history_path() -> Path:
    return Path("~/.config/proxtract/history").expanduser()


def _tokenize(command: str) -> List[str]:
    stripped = command.strip()
    if not stripped:
        return []
    try:
        tokens = shlex.split(command)
    except ValueError:
        # Fallback to simple whitespace split if quoting is incomplete
        tokens = command.split()
    if command.endswith((" ", "\t")):
        tokens.append("")
    return tokens


class ProxtractCompleter(Completer):
    """Context-aware completer for the REPL."""

    def __init__(self) -> None:
        self._command_words = WordCompleter(COMMANDS, ignore_case=True)
        self._setting_words = WordCompleter(SETTING_KEYS, ignore_case=True)
        self._boolean_words = WordCompleter(["on", "off"], ignore_case=True)
        self._path_completer = PathCompleter(expanduser=True)
        self._dir_completer = PathCompleter(expanduser=True, only_directories=True)

    def _complete_from_word_completer(
        self, completer: WordCompleter, word: str
    ) -> Iterable[Completion]:
        prefix = ""
        lookup = word
        if lookup.startswith("/"):
            prefix = "/"
            lookup = lookup[1:]
        start_position = -len(word)
        lowered = lookup.lower()
        for candidate in completer.words:  # type: ignore[attr-defined]
            if lowered and not candidate.lower().startswith(lowered):
                continue
            candidate_text = prefix + candidate
            yield Completion(candidate_text, start_position=start_position)

    def _complete_path(self, word: str, *, directories_only: bool, complete_event) -> Iterable[Completion]:
        completer = self._dir_completer if directories_only else self._path_completer
        fake_document = Document(text=word, cursor_position=len(word))
        for item in completer.get_completions(fake_document, complete_event):
            yield Completion(
                item.text,
                start_position=-len(word),
                display=item.display,
                display_meta=item.display_meta,
            )

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        text = document.text_before_cursor
        tokens = _tokenize(text)
        raw_command = tokens[0] if tokens else document.get_word_before_cursor()
        if not tokens:
            yield from self._complete_from_word_completer(self._command_words, raw_command)
            return

        if tokens[-1] == "":
            current_word = ""
        else:
            current_word = document.get_word_before_cursor()

        command = tokens[0].lower()
        token_count = len(tokens)
        if token_count == 1 and current_word != "":
            yield from self._complete_from_word_completer(self._command_words, raw_command)
            return

        if command in {"exit", "quit", "help", "show", "config", "save"}:
            return

        if command == "set":
            if token_count <= 2 and not text.endswith(" "):
                yield from self._complete_from_word_completer(self._setting_words, current_word)
                return
            if token_count == 2 and text.endswith(" "):
                yield from self._complete_from_word_completer(self._setting_words, "")
                return

            key = tokens[1].lower() if len(tokens) > 1 else ""
            if key in BOOLEAN_KEYS:
                yield from self._complete_from_word_completer(self._boolean_words, current_word)
                return
            if key in PATH_KEYS:
                directories_only = key in PATH_ONLY_DIR_KEYS
                yield from self._complete_path(current_word, directories_only=directories_only, complete_event=complete_event)
                return
            if key:
                return

        if command == "extract":
            if token_count <= 2:
                yield from self._complete_path(current_word, directories_only=True, complete_event=complete_event)
                return
            if token_count == 3:
                yield from self._complete_path(current_word, directories_only=False, complete_event=complete_event)
                return


class InteractiveShell:
    """Interactive REPL for Proxtract commands."""

    PROMPT = "proxtract> "

    def __init__(self, console: Console | None = None, state: AppState | None = None) -> None:
        self.state = state or apply_config(AppState(), load_config())
        self.console = console or create_console()
        color_attr = getattr(self.console, "_proxtract_color_enabled", None)
        if color_attr is None:
            color_attr = bool(getattr(self.console, "color_system", None)) and not getattr(self.console, "no_color", False)
        self._color_enabled = bool(color_attr)
        self._plain_output = not self._color_enabled
        self.completer = ProxtractCompleter()
        self._session: PromptSession | None = None
        self._running = True

    def run(self) -> None:
        self._render_banner()
        try:
            session = self._ensure_session()
        except RuntimeError as exc:
            self.console.print(Panel(f"[red]{exc}[/red]", border_style="red"))
            return
        with patch_stdout():
            while self._running:
                try:
                    text = session.prompt(self.PROMPT)
                except (KeyboardInterrupt, EOFError):
                    self.console.print("[yellow]Type 'exit' or 'quit' to close Proxtract.[/yellow]")
                    continue
                if not text.strip():
                    continue
                if not self.handle_command(text):
                    break

    def handle_command(self, command: str) -> bool:
        tokens = _tokenize(command)
        if not tokens:
            return True
        cmd = tokens[0].lstrip("/").lower()
        args = tokens[1:]

        if cmd in {"exit", "quit"}:
            self.console.print(Panel("[green]До встречи![/green]", border_style="green"))
            return False
        if cmd == "help":
            self._show_help()
            return True
        if cmd in {"show", "config"}:
            self._show_config()
            return True
        if cmd == "save":
            self._save_config_command()
            return True
        if cmd == "set":
            self._set_value(args)
            return True
        if cmd == "extract":
            self._run_extract(args)
            return True

        self.console.print(Panel(f"[red]Неизвестная команда:[/red] {cmd}", border_style="red"))
        return True

    def _render_banner(self) -> None:
        text = Text()
        text.append("Proxtract\n", style="bold green")
        text.append("Интерактивный REPL для извлечения файлов проектов.\n", style="cyan")
        text.append("Команды: extract, set, show, save, help, exit", style="white")
        self.console.print(Panel(text, border_style="cyan"))

    def _ensure_session(self) -> PromptSession:
        if self._session is not None:
            return self._session
        if not PROMPT_TOOLKIT_AVAILABLE or PromptSession is None:
            raise RuntimeError(
                "prompt_toolkit is required for the interactive REPL. "
                "Install it via 'pip install prompt_toolkit' or reinstall Proxtract with the new dependencies."
            )
        history_path = _history_path()
        try:
            history_path.parent.mkdir(parents=True, exist_ok=True)
            history = FileHistory(str(history_path))
        except Exception:
            history = InMemoryHistory()

        self._session = PromptSession(
            history=history,
            completer=self.completer,
            complete_while_typing=True,
        )
        return self._session

    def _show_help(self) -> None:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Команда", style="cyan", no_wrap=True)
        table.add_column("Описание", style="white")
        table.add_row("extract [src] [out]", "Запустить извлечение. Пути опциональны.")
        table.add_row("set <key> <value>", "Изменить настройку (используйте Tab для подсказок).")
        table.add_row("show / config", "Показать текущие настройки.")
        table.add_row("save", "Сохранить настройки в settings.toml.")
        table.add_row("help", "Отобразить эту справку.")
        table.add_row("exit / quit", "Завершить работу.")
        self.console.print(table)

    def _show_config(self) -> None:
        table = Table(title="Текущие настройки", header_style="bold blue")
        table.add_column("Параметр", style="cyan", no_wrap=True)
        table.add_column("Значение", style="white")
        for key, value in self._iter_config():
            table.add_row(key, value)
        self.console.print(table)

    def _iter_config(self) -> Iterable[tuple[str, str]]:
        state = self.state
        yield "source_path", str(state.source_root)
        yield "output_path", str(state.output_path)
        yield "max_size_kb", str(state.max_size_kb)
        yield "compact_mode", "on" if state.compact_mode else "off"
        yield "skip_empty", "on" if state.skip_empty else "off"
        yield "use_gitignore", "on" if state.use_gitignore else "off"
        yield "force_include", "on" if state.force_include else "off"
        yield "include_patterns", ", ".join(state.include_patterns) or "-"
        yield "exclude_patterns", ", ".join(state.exclude_patterns) or "-"
        yield "count_tokens", "on" if state.enable_token_count else "off"
        yield "tokenizer_model", state.tokenizer_model or "-"
        yield "copy_clipboard", "on" if state.copy_to_clipboard else "off"

    def _set_value(self, args: Sequence[str]) -> None:
        if len(args) < 2:
            self.console.print(Panel("[red]Использование: set <key> <value>[/red]", border_style="red"))
            return
        key = args[0].lower()
        value = " ".join(args[1:])
        handler = getattr(self, f"_set_{key}", None)
        if handler is None:
            self.console.print(Panel(f"[red]Неизвестный параметр:[/red] {key}", border_style="red"))
            return
        try:
            handler(value)
        except ValueError as exc:
            self.console.print(Panel(f"[red]Ошибка:[/red] {exc}", border_style="red"))
            return
        self.console.print(Panel(f"[green]{key} обновлен.[/green]", border_style="green"))

    def _parse_bool(self, value: str) -> bool:
        normalized = value.strip().lower()
        if normalized in {"on", "true", "1", "yes"}:
            return True
        if normalized in {"off", "false", "0", "no"}:
            return False
        raise ValueError("Введите 'on' или 'off'")

    def _set_source_path(self, value: str) -> None:
        path = Path(value).expanduser()
        if not path.exists():
            raise ValueError("Путь не существует")
        self.state.set_source_root(path)

    def _set_output_path(self, value: str) -> None:
        path = Path(value).expanduser()
        self.state.set_output_path(path)

    def _set_max_size_kb(self, value: str) -> None:
        size = int(value)
        if size <= 0:
            raise ValueError("Размер должен быть больше нуля")
        self.state.max_size_kb = size

    def _set_compact_mode(self, value: str) -> None:
        self.state.compact_mode = self._parse_bool(value)

    def _set_skip_empty(self, value: str) -> None:
        self.state.skip_empty = self._parse_bool(value)

    def _set_use_gitignore(self, value: str) -> None:
        self.state.use_gitignore = self._parse_bool(value)

    def _set_force_include(self, value: str) -> None:
        self.state.force_include = self._parse_bool(value)

    def _set_include_patterns(self, value: str) -> None:
        self.state.include_patterns = self._parse_patterns(value)

    def _set_exclude_patterns(self, value: str) -> None:
        self.state.exclude_patterns = self._parse_patterns(value)

    def _set_count_tokens(self, value: str) -> None:
        self.state.enable_token_count = self._parse_bool(value)

    def _set_tokenizer_model(self, value: str) -> None:
        self.state.tokenizer_model = value.strip() or self.state.tokenizer_model

    def _set_copy_clipboard(self, value: str) -> None:
        self.state.copy_to_clipboard = self._parse_bool(value)

    def _parse_patterns(self, value: str) -> List[str]:
        if not value.strip():
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def _run_extract(self, args: Sequence[str]) -> None:
        source = args[0] if args else None
        output = args[1] if len(args) > 1 else None
        if source:
            self.state.set_source_root(source)
        if output:
            self.state.set_output_path(output)

        root = self.state.source_root
        destination = self.state.output_path

        if not root.exists():
            self.console.print(Panel("[red]Укажите корректный source_path.[/red]", border_style="red"))
            return

        extractor = self.state.create_extractor()
        use_progress = not self._plain_output and self.console.is_terminal
        try:
            if use_progress:
                progress_columns = [
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TimeElapsedColumn(),
                ]
                with Progress(*progress_columns, refresh_per_second=10, console=self.console) as progress:
                    task_id = progress.add_task("Извлечение...", start=False)

                    def _callback(advance: int = 1, description: str | None = None) -> None:
                        desc = description or "..."
                        if not progress.tasks[task_id].started:
                            progress.start_task(task_id)
                        progress.update(task_id, advance=advance, description=desc)

                    stats = extractor.extract(root, destination, progress_callback=_callback)
            else:
                self.console.print("Извлечение...")
                stats = extractor.extract(root, destination)
        except ExtractionError as exc:
            self.console.print(Panel(f"[red]Ошибка извлечения:[/red] {exc}", border_style="red"))
            return
        except Exception as exc:  # pragma: no cover - defensive
            self.console.print(Panel(f"[red]Непредвиденная ошибка:[/red] {exc}", border_style="red"))
            return

        self.state.last_stats = stats
        self.console.print(self._build_summary_panel(stats))
        if self.state.copy_to_clipboard:
            self._try_copy(stats)

    def _build_summary_panel(self, stats: ExtractionStats) -> Panel:
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="right", style="bold")
        table.add_column()
        table.add_row("Root", str(stats.root))
        table.add_row("Output", str(stats.output))
        table.add_row("Files", str(stats.processed_files))
        table.add_row("Bytes", str(stats.total_bytes))
        if stats.token_count is not None:
            token_info = f"{stats.token_count}"
            if stats.token_model:
                token_info += f" ({stats.token_model})"
            table.add_row("Tokens", token_info)
        skipped_summary = ", ".join(f"{reason}: {count}" for reason, count in stats.skipped.items() if count)
        if skipped_summary:
            table.add_row("Skipped", skipped_summary)
        if stats.errors:
            table.add_row("Warnings", " | ".join(stats.errors))
        return Panel(table, title="[bold green]Готово[/bold green]", border_style="green")

    def _try_copy(self, stats: ExtractionStats) -> None:
        try:
            import pyperclip  # type: ignore

            contents = Path(stats.output).read_text(encoding="utf-8")
            pyperclip.copy(contents)
            self.console.print(Panel("[green]Результат скопирован в буфер обмена.[/green]", border_style="green"))
        except Exception as exc:  # pragma: no cover - platform dependent
            self.console.print(Panel(f"[yellow]Не удалось скопировать:[/yellow] {exc}", border_style="yellow"))

    def _save_config_command(self) -> None:
        try:
            save_config(self.state)
        except Exception as exc:  # pragma: no cover - persistence is best effort
            self.console.print(Panel(f"[red]Не удалось сохранить настройки:[/red] {exc}", border_style="red"))
            return
        self.console.print(Panel("[green]Настройки сохранены.[/green]", border_style="green"))


def run_interactive(console: Console | None = None) -> None:
    """Entry helper used by ``proxtract`` when launched without arguments."""

    InteractiveShell(console=console).run()


__all__ = ["run_interactive", "InteractiveShell", "ProxtractCompleter"]
