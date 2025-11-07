"""Shared utility helpers for Proxtract."""

from __future__ import annotations

import os
import sys
from typing import Any, IO, Iterable

from rich.console import Console

_TRUE_WORDS = {"1", "true", "yes", "on", "y", "t"}
_FALSE_WORDS = {"0", "false", "no", "off", "n", "f"}

_ENV_TRUE = {"1", "true", "yes", "on", "enable"}
_ENV_FALSE = {"0", "false", "no", "off", ""}


def normalize_bool(value: Any, default: bool) -> bool:
    """Return a normalized boolean value from arbitrary input.

    Args:
        value: Incoming configuration value (string, number, bool, etc.).
        default: Fallback value when ``value`` cannot be interpreted.

    Returns:
        ``True`` or ``False`` based on ``value`` or ``default`` if parsing fails.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        if value == 0:
            return False
        if value == 1:
            return True
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_WORDS:
            return True
        if normalized in _FALSE_WORDS:
            return False

    return default


def _env_flag(name: str, truthy: Iterable[str] | None = None) -> bool:
    """Return True when env var ``name`` is set to a truthy value."""

    value = os.environ.get(name)
    if value is None:
        return False
    normalized = value.strip().lower()
    truthy_values = _ENV_TRUE if truthy is None else set(truthy)
    falsy_values = _ENV_FALSE
    if normalized in truthy_values:
        return True
    if normalized in falsy_values:
        return False
    return True


def supports_color(stream: IO[str] | None = None) -> bool:
    """Best-effort check for ANSI color support."""

    if _env_flag("PROXTRACT_FORCE_COLOR"):
        return True

    if _env_flag("PROXTRACT_NO_COLOR") or _env_flag("NO_COLOR"):
        return False

    if _env_flag("PYCHARM_HOSTED"):
        return False

    if stream is None:
        stream = sys.stdout

    isatty = getattr(stream, "isatty", None)
    try:
        if isatty is None or not isatty():
            return False
    except Exception:
        return False

    term = os.environ.get("TERM", "")
    if not term or term.lower() == "dumb":
        return False

    if sys.platform == "win32":
        return bool(
            os.environ.get("WT_SESSION")
            or os.environ.get("ANSICON")
            or os.environ.get("ConEmuANSI") == "ON"
            or os.environ.get("TERM_PROGRAM") == "vscode"
        )

    return True


def create_console(*, plain: bool | None = None, **kwargs) -> Console:
    """Return a Rich console tuned for the current environment."""

    stream = kwargs.get("file")
    options = dict(kwargs)

    explicit_no_color = options.get("no_color")
    if explicit_no_color is not None:
        color_enabled = not explicit_no_color
    elif plain is True:
        color_enabled = False
    elif plain is False:
        color_enabled = True
    else:
        color_enabled = supports_color(stream if stream is not None else None)

    options.setdefault("force_terminal", color_enabled)
    if not color_enabled:
        options["no_color"] = True

    console = Console(**options)
    setattr(console, "_proxtract_color_enabled", color_enabled)
    return console


__all__ = ["normalize_bool", "supports_color", "create_console"]
