"""Interactive REPL loop for the Proxtract CLI."""

from __future__ import annotations

import shlex
from typing import Iterable, Optional, Tuple

from rich.console import Console
from rich.prompt import Prompt

try:  # prompt_toolkit is optional at runtime
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import HTML

    from .completion import CommandCompleter
except Exception:  # pragma: no cover - fallback when dependency is missing
    PromptSession = None  # type: ignore[assignment]
    HTML = None  # type: ignore[assignment]
    CommandCompleter = None  # type: ignore[assignment]

from .commands import COMMANDS, SETTING_ALIASES
from .state import AppState


class CommandParseError(ValueError):
    """Raised when a command line cannot be parsed."""


def parse_command(line: str) -> Tuple[str, Tuple[str, ...]]:
    """Split a line into command and arguments supporting quoted strings."""

    line = line.strip()
    if not line:
        return "", tuple()

    import sys
    if sys.platform == "win32":
        line = line.replace("\\", "/")

    try:
        parts = shlex.split(line)
    except ValueError as exc:
        raise CommandParseError(str(exc)) from exc

    command = parts[0]
    args: Tuple[str, ...] = tuple(parts[1:])
    return command, args


def _build_prompt_session() -> Optional["PromptSession"]:
    if PromptSession is None or CommandCompleter is None:  # pragma: no cover - no dependency
        return None

    message = HTML("<ansicyan><b>proxtract ></b></ansicyan> ") if HTML is not None else "proxtract > "
    completer = CommandCompleter(COMMANDS.keys(), SETTING_ALIASES)
    return PromptSession(message=message, completer=completer)


def start_session(*, console: Optional[Console] = None, state: Optional[AppState] = None) -> None:
    """Run the interactive REPL loop."""

    console = console or Console()
    state = state or AppState()
    session = _build_prompt_session()

    while True:
        try:
            if session is not None:
                user_input = session.prompt()
            else:  # pragma: no cover - fallback path when prompt_toolkit unavailable
                user_input = Prompt.ask("[bold cyan]proxtract >[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold yellow]Session terminated.[/bold yellow]")
            break

        try:
            command, args = parse_command(user_input)
        except CommandParseError as exc:
            console.print(f"[red]Input error:[/red] {exc}")
            continue

        if not command:
            continue

        handler = COMMANDS.get(command)
        if handler is None:
            console.print(f"[red]Unknown command '{command}'. Try /help.[/red]")
            continue

        try:
            should_continue = handler(console, state, args)
        except Exception as exc:  # pragma: no cover - defensive guard for REPL stability
            console.print(f"[red]Unhandled error:[/red] {exc}")
            continue

        if not should_continue:
            break


__all__ = ["start_session", "parse_command", "CommandParseError"]
