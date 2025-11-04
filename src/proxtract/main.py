"""Entry point for launching the Proxtract CLI and TUI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from rich.console import Console

from .state import AppState
from .tui.app import ProxtractApp

try:  # Shell auto-completion support
    import argcomplete  # type: ignore
    from argcomplete.completers import FilesCompleter  # type: ignore
except Exception:  # pragma: no cover - degrade gracefully if unavailable
    argcomplete = None  # type: ignore[assignment]
    FilesCompleter = None  # type: ignore[assignment]

try:  # Config helpers are optional if tomllib/tomli missing
    from .config import apply_config, load_config, save_config as _save_config
except Exception:  # pragma: no cover - fallback when persistence unavailable
    apply_config = lambda state, data: state  # type: ignore
    load_config = lambda: {}  # type: ignore
    _save_config = None  # type: ignore
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


def _launch_tui() -> None:
    state = apply_config(AppState(), load_config())
    ProxtractApp(state).run()


def main(argv: Optional[Sequence[str]] = None) -> None:
    program_name = Path(sys.argv[0]).name or "proxtract"
    parser = argparse.ArgumentParser(prog=program_name, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command")

    p_extract = subparsers.add_parser("extract", help="Run a one-off extraction", aliases=["e"])
    path_argument = p_extract.add_argument("path", help="Root directory to extract")
    output_argument = p_extract.add_argument("--output", "-o", help="Output file path")
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
    tokenizer_argument = p_extract.add_argument("--tokenizer-model", help="Tokenizer model for token counting")
    p_extract.add_argument("--no-token-count", action="store_true", help="Disable token counting")
    p_extract.add_argument("--copy", action="store_true", help="Copy result to clipboard")
    p_extract.add_argument("--save-config", action="store_true", help="Persist current settings")

    args_list = list(sys.argv[1:] if argv is None else argv)

    if FilesCompleter is not None:  # pragma: no cover - requires argcomplete at runtime
        try:
            path_argument.completer = FilesCompleter(directories=True)  # type: ignore[attr-defined]
            output_argument.completer = FilesCompleter()  # type: ignore[attr-defined]
        except Exception:
            pass

    if argv is None and argcomplete is not None:  # pragma: no cover - requires argcomplete at runtime
        try:
            from argcomplete.completers import ChoicesCompleter  # type: ignore
        except Exception:
            ChoicesCompleter = None  # type: ignore[assignment]
        else:
            token_models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "o200k_base"]
            tokenizer_argument.completer = ChoicesCompleter(token_models)  # type: ignore[attr-defined]

        argcomplete.autocomplete(parser)  # type: ignore[call-arg]

    if not args_list:
        _launch_tui()
        return

    args = parser.parse_args(args_list)

    if args.command == "extract":
        raise SystemExit(_run_cli_extract(args, Console()))

    _launch_tui()


if __name__ == "__main__":  # pragma: no cover
    main()
