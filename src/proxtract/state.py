"""Session state management for the Proxtract TUI and CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from .core import ExtractionStats, FileExtractor


@dataclass
class AppState:
    """Mutable configuration shared across TUI widgets and CLI commands."""

    output_path: Path = field(default_factory=lambda: Path("extracted.txt"))
    max_size_kb: int = 500
    compact_mode: bool = True
    skip_empty: bool = True
    use_gitignore: bool = True
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    tokenizer_model: str = "gpt-4"
    enable_token_count: bool = True
    copy_to_clipboard: bool = False
    last_stats: Optional[ExtractionStats] = None

    def create_extractor(self) -> FileExtractor:
        """Instantiate a ``FileExtractor`` with the current settings."""

        return FileExtractor(
            max_file_size_kb=self.max_size_kb,
            skip_empty=self.skip_empty,
            compact_mode=self.compact_mode,
            use_gitignore=self.use_gitignore,
            include_patterns=self.include_patterns,
            exclude_patterns=self.exclude_patterns,
            tokenizer_model=self.tokenizer_model,
            count_tokens=self.enable_token_count,
        )

    def set_output_path(self, path: str | Path) -> None:
        self.output_path = Path(path).expanduser()

    def set_patterns(
        self,
        *,
        include: Optional[Sequence[str]] = None,
        exclude: Optional[Sequence[str]] = None,
    ) -> None:
        if include is not None:
            self.include_patterns = [str(p) for p in include]
        if exclude is not None:
            self.exclude_patterns = [str(p) for p in exclude]


__all__ = ["AppState"]
