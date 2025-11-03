"""Command handlers for the Proxtract REPL."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .core import ExtractionError
from .state import AppState


CommandHandler = Callable[[Console, AppState, Tuple[str, ...]], bool]


SETTING_ALIASES: Dict[str, set[str]] = {
    "max_size": {"max_size", "max", "size"},
    "output": {"output", "out", "file", "path", "output_path"},
    "compact": {"compact", "compact_mode", "mode"},
    "skip_empty": {"skip_empty", "skip-empty", "empty"},
}


def _render_settings_table(state: AppState) -> Table:
    table = Table(title="Current Settings", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    table.add_row("output_path", str(state.output_path))
    table.add_row("max_size_kb", str(state.max_size_kb))
    table.add_row("compact_mode", "yes" if state.compact_mode else "no")
    table.add_row("skip_empty", "yes" if state.skip_empty else "no")
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
    console.print("[bold yellow]Goodbye![/bold yellow]")
    return False


def cmd_clear(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:  # noqa: ARG001
    console.clear()
    return True


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
        state.compact_mode = value.lower() in {"on", "true", "1", "yes"}
    elif canonical == "skip_empty":
        if value is None:
            console.print("[red]Provide 'on' or 'off' for skip_empty.[/red]")
            return True
        state.skip_empty = value.lower() in {"on", "true", "1", "yes"}

    console.print("[green]Setting updated.[/green]")
    console.print(_render_settings_table(state))
    return True


def cmd_extract(console: Console, state: AppState, args: Tuple[str, ...]) -> bool:
    if not args:
        console.print("[red]/extract requires at least a target directory.[/red]")
        return True

    source = Path(args[0]).expanduser()
    output = Path(args[1]).expanduser() if len(args) > 1 else state.output_path

    extractor = state.create_extractor()

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

    return True


COMMAND_HELP: Iterable[Tuple[str, str]] = (
    ("/help", "Show this help table"),
    ("/extract <path> [output]", "Extract project files into one document"),
    ("/settings [key value]", "View or update session settings"),
    ("/clear", "Clear the terminal output"),
    ("/exit", "Exit the application"),
)


COMMANDS: Dict[str, CommandHandler] = {
    "/help": cmd_help,
    "/extract": cmd_extract,
    "/settings": cmd_settings,
    "/clear": cmd_clear,
    "/exit": cmd_exit,
    "/quit": cmd_exit,
}


__all__ = ["COMMANDS"]
