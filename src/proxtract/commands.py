"""Command handlers for the Proxtract REPL."""

from __future__ import annotations

import argparse
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .core import ExtractionError
from .state import AppState

try:  # Config persistence is optional (tomllib/tomli may be absent)
    from .config import save_config
except Exception:  # pragma: no cover - optional dependency missing
    save_config = None  # type: ignore[assignment]


CommandHandler = Callable[[Console, AppState, Tuple[str, ...]], bool]


SETTING_ALIASES: Dict[str, set[str]] = {
    "max_size": {"max_size", "max", "size"},
    "output": {"output", "out", "file", "path", "output_path"},
    "compact": {"compact", "compact_mode", "mode"},
    "skip_empty": {"skip_empty", "skip-empty", "empty"},
    "use_gitignore": {"use_gitignore", "gitignore", "use-gitignore"},
    "tokenizer_model": {"tokenizer_model", "tokenizer", "model"},
    "token_count": {"token_count", "count_tokens", "tokens"},
    "copy_clipboard": {"copy", "clipboard", "copy_to_clipboard"},
}


def _render_settings_table(state: AppState) -> Table:
    table = Table(title="Current Settings", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    table.add_row("output_path", str(state.output_path))
    table.add_row("max_size_kb", str(state.max_size_kb))
    table.add_row("compact_mode", "yes" if state.compact_mode else "no")
    table.add_row("skip_empty", "yes" if state.skip_empty else "no")
    table.add_row("use_gitignore", "yes" if state.use_gitignore else "no")
    table.add_row("include_patterns", ", ".join(state.include_patterns) or "—")
    table.add_row("exclude_patterns", ", ".join(state.exclude_patterns) or "—")
    table.add_row("tokenizer_model", state.tokenizer_model)
    table.add_row("enable_token_count", "yes" if state.enable_token_count else "no")
    table.add_row("copy_to_clipboard", "yes" if state.copy_to_clipboard else "no")
    return table


def cmd_help(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:  # noqa: ARG001
    table = Table(title="Available Commands", show_header=True, header_style="bold green")
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    for command, description in COMMAND_HELP:
        table.add_row(command, description)
    console.print(table)
    return True


def cmd_exit(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:  # noqa: ARG001
    if save_config is not None:
        try:
            save_config(state)
        except Exception as exc:  # pragma: no cover - persistence is best-effort
            console.print(f"[yellow]Warning: Failed to save settings: {exc}[/yellow]")
    console.print("[bold yellow]Goodbye![/bold yellow]")
    return False


def cmd_clear(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:  # noqa: ARG001
    console.clear()
    return True


def _parse_bool(value: str) -> bool:
    return value.lower() in {"on", "true", "1", "yes", "y"}


def cmd_settings(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:
    if not args:
        console.print(_render_settings_table(state))
        return True

    raw_key = args[0]
    raw_value = args[1] if len(args) > 1 else None

    if "=" in raw_key and raw_value is None:
        raw_key, raw_value = raw_key.split("=", 1)

    key = raw_key.lower()
    canonical = None
    for target, aliases in SETTING_ALIASES.items():
        if key in aliases:
            canonical = target
            break

    if canonical is None:
        console.print(f"[red]Unknown setting '{raw_key}'.[/red]")
        return True

    value = raw_value

    if canonical == "max_size":
        if value is None:
            console.print("[red]Provide a numeric value for max_size.[/red]")
            return True
        try:
            state.max_size_kb = int(value)
        except ValueError:
            console.print("[red]max_size must be an integer (KB).[/red]")
            return True
    elif canonical == "output":
        if value is None:
            console.print("[red]Provide a path for output file.[/red]")
            return True
        state.set_output_path(value)
    elif canonical == "compact":
        if value is None:
            console.print("[red]Provide 'on' or 'off' for compact mode.[/red]")
            return True
        state.compact_mode = _parse_bool(value)
    elif canonical == "skip_empty":
        if value is None:
            console.print("[red]Provide 'on' or 'off' for skip_empty.[/red]")
            return True
        state.skip_empty = _parse_bool(value)
    elif canonical == "use_gitignore":
        if value is None:
            console.print("[red]Provide 'on' or 'off' for use_gitignore.[/red]")
            return True
        state.use_gitignore = _parse_bool(value)
    elif canonical == "tokenizer_model":
        if value is None:
            console.print("[red]Provide a tokenizer model name.[/red]")
            return True
        state.tokenizer_model = value
    elif canonical == "token_count":
        if value is None:
            console.print("[red]Provide 'on' or 'off' for token counting.[/red]")
            return True
        state.enable_token_count = _parse_bool(value)
    elif canonical == "copy_clipboard":
        if value is None:
            console.print("[red]Provide 'on' or 'off' for copy to clipboard.[/red]")
            return True
        state.copy_to_clipboard = _parse_bool(value)

    console.print("[green]Setting updated.[/green]")
    console.print(_render_settings_table(state))
    return True


def cmd_rules(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:  # noqa: ARG001
    table = Table(title="Active Rules", show_header=True, header_style="bold cyan")
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    table.add_row("use_gitignore", "yes" if state.use_gitignore else "no")
    table.add_row("include_patterns", ", ".join(state.include_patterns) or "—")
    table.add_row("exclude_patterns", ", ".join(state.exclude_patterns) or "—")
    console.print(table)
    return True


def _cmd_list_patterns(console: Console, label: str, values: list[str]) -> None:
    table = Table(title=f"{label} Patterns", show_header=True, header_style="bold blue")
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Pattern", style="white")
    if not values:
        table.add_row("—", "None")
    else:
        for index, pattern in enumerate(values, 1):
            table.add_row(str(index), pattern)
    console.print(table)


def _mutate_patterns(values: list[str], op: str, pattern: str | None) -> str:
    if op == "add":
        if pattern is None:
            return "Provide a pattern to add."
        if pattern in values:
            return "Pattern already present."
        values.append(pattern)
        return "Pattern added."
    if op == "remove":
        if pattern is None:
            return "Provide a pattern to remove."
        try:
            values.remove(pattern)
            return "Pattern removed."
        except ValueError:
            return "Pattern not found."
    if op == "clear":
        values.clear()
        return "All patterns cleared."
    if op == "list":
        return ""
    return "Unknown operation. Use add|remove|clear|list."


def cmd_include(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:
    op = args[0] if args else "list"
    pattern = args[1] if len(args) > 1 else None
    message = _mutate_patterns(state.include_patterns, op, pattern)
    if op == "list" or not message:
        _cmd_list_patterns(console, "Include", state.include_patterns)
    else:
        success_messages = {
            "Pattern added.",
            "Pattern removed.",
            "All patterns cleared.",
        }
        warning_messages = {
            "Pattern already present.",
            "Pattern not found.",
        }
        if message in success_messages:
            colour = "green"
        elif message in warning_messages:
            colour = "yellow"
        else:
            colour = "red"
        console.print(f"[{colour}]{message}[/]")
    return True


def cmd_exclude(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:
    op = args[0] if args else "list"
    pattern = args[1] if len(args) > 1 else None
    message = _mutate_patterns(state.exclude_patterns, op, pattern)
    if op == "list" or not message:
        _cmd_list_patterns(console, "Exclude", state.exclude_patterns)
    else:
        success_messages = {
            "Pattern added.",
            "Pattern removed.",
            "All patterns cleared.",
        }
        warning_messages = {
            "Pattern already present.",
            "Pattern not found.",
        }
        if message in success_messages:
            colour = "green"
        elif message in warning_messages:
            colour = "yellow"
        else:
            colour = "red"
        console.print(f"[{colour}]{message}[/]")
    return True


def cmd_save(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:  # noqa: ARG001
    if save_config is None:
        console.print("[yellow]Config persistence is not available in this environment.[/yellow]")
        return True
    try:
        save_config(state)
    except Exception as exc:  # pragma: no cover - persistence is best-effort
        console.print(f"[red]Failed to save settings:[/red] {exc}")
    else:
        console.print("[green]Settings saved.[/green]")
    return True


def cmd_extract(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:
    parser = argparse.ArgumentParser(prog="/extract", add_help=False)
    parser.add_argument("path", nargs="?", help="Root directory to extract")
    parser.add_argument("--output", "-o")
    parser.add_argument("--max-size", type=int)
    group_compact = parser.add_mutually_exclusive_group()
    group_compact.add_argument("--compact", action="store_true")
    group_compact.add_argument("--no-compact", action="store_true")
    group_empty = parser.add_mutually_exclusive_group()
    group_empty.add_argument("--skip-empty", action="store_true")
    group_empty.add_argument("--no-skip-empty", action="store_true")
    parser.add_argument("--copy", action="store_true")

    try:
        ns = parser.parse_args(list(args))
    except SystemExit:
        console.print("[red]Invalid arguments for /extract.[/red]")
        return True

    if not ns.path:
        console.print("[red]/extract requires at least a target directory.[/red]")
        return True

    source = Path(ns.path).expanduser()
    if ns.output:
        state.set_output_path(ns.output)
    if ns.max_size is not None:
        state.max_size_kb = ns.max_size
    if ns.compact:
        state.compact_mode = True
    elif ns.no_compact:
        state.compact_mode = False
    if ns.skip_empty:
        state.skip_empty = True
    elif ns.no_skip_empty:
        state.skip_empty = False

    extractor = state.create_extractor()
    output = state.output_path

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Starting extraction...", total=None)
        callback = partial(progress.update, task_id)

        try:
            stats = extractor.extract(source, output, progress_callback=callback)
        except ExtractionError as exc:
            console.print(f"[red]Extraction failed:[/red] {exc}")
            return True

        progress.update(task_id, description="Extraction complete", advance=0)

    state.last_stats = stats

    table = Table(title="Extraction Summary", show_header=True, header_style="bold blue")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    table.add_row("Root", str(stats.root))
    table.add_row("Output", str(stats.output))
    table.add_row("Processed files", str(stats.processed_files))
    table.add_row("Total size (bytes)", str(stats.total_bytes))
    if stats.token_count is not None:
        table.add_row("Total tokens", str(stats.token_count))
        if stats.token_model:
            table.add_row("Tokenizer model", stats.token_model)
    table.add_row("Skipped - excluded_ext", str(stats.skipped["excluded_ext"]))
    table.add_row("Skipped - empty", str(stats.skipped["empty"]))
    table.add_row("Skipped - too_large", str(stats.skipped["too_large"]))
    table.add_row("Skipped - binary", str(stats.skipped["binary"]))
    table.add_row("Skipped - other", str(stats.skipped["other"]))
    console.print(table)

    if stats.processed_paths:
        included_table = Table(title="Included Files", show_header=True, header_style="bold green")
        included_table.add_column("Path", style="white")
        for path in stats.processed_paths:
            included_table.add_row(path)
        console.print(included_table)

    if any(stats.skipped_paths.values()):
        skipped_table = Table(title="Skipped Files", show_header=True, header_style="bold red")
        skipped_table.add_column("Reason", style="cyan", no_wrap=True)
        skipped_table.add_column("Path", style="white")
        for reason in sorted(stats.skipped_paths):
            paths = stats.skipped_paths[reason]
            if not paths:
                continue
            first = True
            for path in paths:
                skipped_table.add_row(reason if first else "", path)
                first = False
        console.print(skipped_table)

    if stats.errors:
        console.print("[yellow]Warnings during extraction:[/yellow]")
        for message in stats.errors:
            console.print(f"  • {message}")

    if ns.copy or state.copy_to_clipboard:
        try:
            import pyperclip  # type: ignore

            try:
                text = Path(stats.output).read_text(encoding="utf-8")
                pyperclip.copy(text)
                console.print("[green]Copied extracted content to clipboard.[/green]")
            except Exception as exc:  # pragma: no cover - environment dependent
                console.print(f"[yellow]Failed to copy to clipboard:[/yellow] {exc}")
        except Exception:
            console.print("[yellow]pyperclip not installed; cannot copy to clipboard.[/yellow]")

    return True


COMMAND_HELP: Iterable[Tuple[str, str]] = (
    ("/help", "Show this help table"),
    ("/extract <path> [--output file] [--max-size KB] [--compact|--no-compact] [--skip-empty|--no-skip-empty] [--copy]", "Extract project files"),
    ("/settings [key value]", "View or update session settings"),
    ("/include [list|add|remove|clear] [pattern]", "Manage include glob patterns"),
    ("/exclude [list|add|remove|clear] [pattern]", "Manage exclude glob patterns"),
    ("/rules", "Show active include/exclude and gitignore settings"),
    ("/save", "Persist current settings to config"),
    ("/clear", "Clear the terminal output"),
    ("/exit", "Exit the application"),
)


COMMANDS: Dict[str, CommandHandler] = {
    "/help": cmd_help,
    "/extract": cmd_extract,
    "/settings": cmd_settings,
    "/include": cmd_include,
    "/exclude": cmd_exclude,
    "/rules": cmd_rules,
    "/save": cmd_save,
    "/clear": cmd_clear,
    "/exit": cmd_exit,
}


__all__ = ["COMMANDS", "COMMAND_HELP"]
