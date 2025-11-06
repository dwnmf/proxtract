"""Shared utility helpers for Proxtract."""

from __future__ import annotations

from typing import Any

_TRUE_WORDS = {"1", "true", "yes", "on", "y", "t"}
_FALSE_WORDS = {"0", "false", "no", "off", "n", "f"}


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


__all__ = ["normalize_bool"]
