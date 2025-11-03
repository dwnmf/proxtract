"""Proxtract package exposing the interactive extractor CLI."""

from importlib import metadata as _metadata

from .core import ExtractionError, ExtractionStats, FileExtractor

try:
    __version__ = _metadata.version("proxtract")
except _metadata.PackageNotFoundError:  # pragma: no cover - local editable install
    __version__ = "0.1.0"

__all__ = ["FileExtractor", "ExtractionError", "ExtractionStats", "__version__"]
