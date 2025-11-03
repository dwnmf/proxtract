"""Proxtract package exposing the interactive extractor CLI."""

from .core import ExtractionError, ExtractionStats, FileExtractor

__all__ = ["FileExtractor", "ExtractionError", "ExtractionStats"]
