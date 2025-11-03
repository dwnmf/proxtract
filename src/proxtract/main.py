"""Entry point for launching the Proxtract CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from rich.console import Console

try:  # art is optional at runtime; fall back gracefully if missing
    from art import text2art as _text2art
except Exception:  # pragma: no cover - fallback path depends on environment
    _text2art = None

from .repl import start_session
from .state import AppState

try:  # Config helpers are optional if tomllib/tomli missing
    from .config import apply_config, load_config, save_config as _save_config
except Exception:  # pragma: no cover - fallback when persistence unavailable
    apply_config = lambda state, data: state  # type: ignore
    load_config = lambda: {}  # type: ignore
    _save_config = None  # type: ignore


def _render_banner(console: Console) -> None:
    banner: Optional[str] = None
    if _text2art is not None:
        try:
            banner = _text2art("Proxtract", font="small")
        except Exception:  # pragma: no cover - fallback for unexpected art errors
            banner = None

    if banner is None:
        banner = r"""\
  ____                 _                _     
 |  _ \ ___  _____  __| | ___ _ __ __ _| |__  
 | |_) / _ \/ _ \ \/ / _` |/ _ \ '__/ _` | '_ \ 
 |  __/  __/  __/>  < (_| |  __/ | | (_| | |_) |
 |_|   \___|\___/_/\_\__,_|\___|_|  \__,_|_.__/ 
"""

    console.print(f"[bold magenta]{banner}[/bold magenta]")


def _run_cli_extract(args: argparse.Namespace, console: Console) -> int:
    state = apply_config(AppState(), load_config())

    if args.output:
        state.set_output_path(args.output)
    if args.max_size is not None:
        state.max_size_kb = args.max_size
    if args.compact:
        state.compact_mode = True
    elif args.no_compact:
        state.compact_mode = False
    if args.skip_empty:
        state.skip_empty = True
    elif args.no_skip_empty:
        state.skip_empty = False
    if args.use_gitignore:
        state.use_gitignore = True
    elif args.no_gitignore:
        state.use_gitignore = False
    if args.include:
        state.include_patterns = [str(pattern) for pattern in args.include]
    if args.exclude:
        state.exclude_patterns = [str(pattern) for pattern in args.exclude]
    if args.tokenizer_model:
        state.tokenizer_model = args.tokenizer_model
    if args.no_token_count:
        state.enable_token_count = False
    if args.copy:
        state.copy_to_clipboard = True

    extractor = state.create_extractor()
    root = Path(args.path).expanduser()
    output = state.output_path

    console.print(f"[bold]Extracting[/bold] from [cyan]{root}[/cyan] to [green]{output}[/green] ...")
    try:
        stats = extractor.extract(root, output)
    except Exception as exc:
        console.print(f"[red]Extraction failed:[/red] {exc}")
        return 2

    console.print(
        "[bold green]Done.[/bold green] "
        + f"Files: {stats.processed_files}, Size: {stats.total_bytes} bytes"
        + (f", Tokens: {stats.token_count}" if stats.token_count is not None else "")
    )
    if stats.errors:
        console.print(f"[yellow]Warnings ({len(stats.errors)}):[/yellow]")
        for warning in stats.errors:
            console.print(f"  • {warning}")

    if state.copy_to_clipboard or args.copy:
        try:
            import pyperclip  # type: ignore

            try:
                contents = Path(stats.output).read_text(encoding="utf-8")
                pyperclip.copy(contents)
                console.print("[green]Copied extracted content to clipboard.[/green]")
            except Exception as exc:  # pragma: no cover - environment specific
                console.print(f"[yellow]Failed to copy to clipboard:[/yellow] {exc}")
        except Exception:
            console.print("[yellow]pyperclip not installed; cannot copy to clipboard.[/yellow]")

    if args.save_config and _save_config is not None:
        try:
            _save_config(state)
            console.print("[green]Settings saved.[/green]")
        except Exception as exc:  # pragma: no cover - persistence is best-effort
            console.print(f"[yellow]Failed to save settings:[/yellow] {exc}")

    return 0


def main() -> None:
    console = Console()

    parser = argparse.ArgumentParser(prog="proxtract")
    subparsers = parser.add_subparsers(dest="command")

    p_extract = subparsers.add_parser("extract", help="Run a one-off extraction")
    p_extract.add_argument("path", help="Root directory to extract")
    p_extract.add_argument("--output", "-o", help="Output file path")
    p_extract.add_argument("--max-size", type=int, help="Maximum file size in KB")
    group_compact = p_extract.add_mutually_exclusive_group()
    group_compact.add_argument("--compact", action="store_true", help="Enable compact formatting")
    group_compact.add_argument("--no-compact", action="store_true", help="Disable compact formatting")
    group_empty = p_extract.add_mutually_exclusive_group()
    group_empty.add_argument("--skip-empty", action="store_true", help="Skip empty files")
    group_empty.add_argument("--no-skip-empty", action="store_true", help="Do not skip empty files")
    group_gitignore = p_extract.add_mutually_exclusive_group()
    group_gitignore.add_argument("--use-gitignore", dest="use_gitignore", action="store_true", help="Respect .gitignore rules")
    group_gitignore.add_argument("--no-gitignore", dest="no_gitignore", action="store_true", help="Ignore .gitignore rules")
    p_extract.add_argument("--include", action="append", help="Include glob pattern (repeatable)")
    p_extract.add_argument("--exclude", action="append", help="Exclude glob pattern (repeatable)")
    p_extract.add_argument("--tokenizer-model", help="Tokenizer model for token counting")
    p_extract.add_argument("--no-token-count", action="store_true", help="Disable token counting")
    p_extract.add_argument("--copy", action="store_true", help="Copy result to clipboard")
    p_extract.add_argument("--save-config", action="store_true", help="Persist current settings")

    args = parser.parse_args()

    if args.command == "extract":
        raise SystemExit(_run_cli_extract(args, console))

    _render_banner(console)
    console.print("[bold green]Welcome to Proxtract! Type /help to view available commands.[/bold green]")
    state = apply_config(AppState(), load_config())
    start_session(console=console, state=state)


if __name__ == "__main__":  # pragma: no cover
    main()
