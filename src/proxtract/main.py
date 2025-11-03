"""Entry point for launching the Proxtract CLI."""

from __future__ import annotations

from typing import Optional

from rich.console import Console

try:  # art is optional at runtime; fall back gracefully if missing
    from art import text2art as _text2art
except Exception:  # pragma: no cover - fallback path depends on environment
    _text2art = None

from .repl import start_session
from .state import AppState


def _render_banner(console: Console) -> None:
    banner: Optional[str] = None
    if _text2art is not None:
        try:
            banner = _text2art("Proxtract", font="small")
        except Exception:  # pragma: no cover - fallback for unexpected art errors
            banner = None

    if banner is None:
        banner = """\
  ____                 _                _     
 |  _ \ ___  _____  __| | ___ _ __ __ _| |__  
 | |_) / _ \/ _ \ \/ / _` |/ _ \ '__/ _` | '_ \ 
 |  __/  __/  __/>  < (_| |  __/ | | (_| | |_) |
 |_|   \___|\___/_/\_\__,_|\___|_|  \__,_|_.__/ 
"""

    console.print(f"[bold magenta]{banner}[/bold magenta]")


def main() -> None:
    console = Console()
    _render_banner(console)
    console.print("[bold green]Welcome to Proxtract! Type /help to view available commands.[/bold green]")
    start_session(console=console, state=AppState())


if __name__ == "__main__":  # pragma: no cover
    main()
