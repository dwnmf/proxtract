"""Textual TUI package for Proxtract."""

from pathlib import Path

STYLES_PATH = Path(__file__).resolve().parent / "styles.tcss"

from .app import ProxtractApp

__all__ = ["ProxtractApp", "STYLES_PATH"]
