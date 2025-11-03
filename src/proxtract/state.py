"""Session state management for the Proxtract REPL."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .core import ExtractionStats, FileExtractor


@dataclass
class AppState:
    """Mutable configuration shared across REPL commands."""

    output_path: Path = field(default_factory=lambda: Path("extracted.txt"))
    max_size_kb: int = 500
    compact_mode: bool = True
    skip_empty: bool = True
    last_stats: Optional[ExtractionStats] = None

    def create_extractor(self) -> FileExtractor:
        """Instantiate a ``FileExtractor`` with the current settings."""

        return FileExtractor(
            max_file_size_kb=self.max_size_kb,
            skip_empty=self.skip_empty,
            compact_mode=self.compact_mode,
        )

    def set_output_path(self, path: str | Path) -> None:
        self.output_path = Path(path).expanduser()


__all__ = ["AppState"]
