"""Tests for TUI main screen parsing helpers."""

from __future__ import annotations

from proxtract.tui.screens.main_screen import MainScreen


def test_parse_value_bool_strings():
    """Boolean parser should treat common falsy strings as False."""
    assert MainScreen._parse_value("false", "bool", default=True) is False
    assert MainScreen._parse_value("no", "bool", default=True) is False
    assert MainScreen._parse_value("0", "bool", default=True) is False
    assert MainScreen._parse_value("yes", "bool", default=False) is True
