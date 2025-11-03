"""Core extraction logic for the Proxtract CLI."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, DefaultDict, Dict, Optional, Protocol


class ProgressCallback(Protocol):
    """Callable invoked to report extraction progress."""

    def __call__(self, *, advance: int, description: Optional[str] = None) -> None:  # pragma: no cover - Protocol definition
        ...


@dataclass
class ExtractionStats:
    """Structured information returned after a successful extraction."""

    root: Path
    output: Path
    processed_paths: list[str]
    total_bytes: int
    skipped_paths: Dict[str, list[str]]
    errors: list[str]

    @property
    def processed_files(self) -> int:
        """Backward compatible count of processed files."""

        return len(self.processed_paths)

    @property
    def skipped(self) -> Dict[str, int]:
        """Backward compatible summary of skipped files by reason."""

        counts: Dict[str, int] = {}
        canonical_reasons = {"excluded_ext", "empty", "too_large", "binary", "other"}
        for reason, paths in self.skipped_paths.items():
            key = reason if reason in canonical_reasons else "other"
            counts[key] = counts.get(key, 0) + len(paths)
        for key in ("excluded_ext", "empty", "too_large", "binary", "other"):
            counts.setdefault(key, 0)
        return counts

    def as_dict(self) -> Dict[str, object]:
        """Return stats in plain dict form for serialization/logging."""

        return {
            "root": str(self.root),
            "output": str(self.output),
            "processed_paths": list(self.processed_paths),
            "processed_files": self.processed_files,
            "total_bytes": self.total_bytes,
            "skipped_paths": {reason: list(paths) for reason, paths in self.skipped_paths.items()},
            "skipped": dict(self.skipped),
            "errors": list(self.errors),
        }


class ExtractionError(RuntimeError):
    """Raised when extraction cannot be performed."""


class FileExtractor:
    """Extract text-friendly files from a project tree into a single document."""

    def __init__(self, *, max_file_size_kb: int = 500, skip_empty: bool = True, compact_mode: bool = True) -> None:
        self.max_file_size = max_file_size_kb * 1024
        self.skip_empty = skip_empty
        self.compact_mode = compact_mode

        self.skip_extensions = {
            ".csv",
            ".jpeg",
            ".jpg",
            ".png",
            ".gif",
            ".bmp",
            ".gitignore",
            ".env",
            ".mp4",
            ".lgb",
            ".sqlite3-wal",
            ".sqlite3-shm",
            ".sqlite3",
            ".mkv",
            ".webm",
            ".mp3",
            ".wav",
            ".flac",
            ".aac",
            ".html",
            ".wma",
            ".ico",
            ".svg",
            ".zip",
            ".rar",
            ".7z",
            ".tar",
            ".gz",
            ".bz2",
            ".lock",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".pyc",
            ".pyo",
            ".pyd",
            ".pkl",
            ".parquet",
            ".orc",
            ".avro",
            ".feather",
            ".h5",
            ".hdf5",
            ".db",
            ".sqlite",
            ".bin",
            ".dat",
            ".idx",
            ".model",
            ".pt",
            ".ckpt",
            ".npy",
            ".npz",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
        }

        self.skip_patterns = {
            "__pycache__",
            ".git",
            ".svn",
            ".hg",
            "node_modules",
            ".vscode",
            ".idea",
            ".pytest_cache",
            ".mypy_cache",
            "venv",
            "env",
            "virtualenv",
            "dist",
            "build",
            ".next",
            "coverage",
            ".nyc_output",
            "vendor",
        }

        self.skip_files = {
            "package-lock.json",
            "yarn.lock",
            "poetry.lock",
            "Pipfile.lock",
            ".DS_Store",
            "Thumbs.db",
            "desktop.ini",
        }

    def _should_skip(self, file_path: Path) -> tuple[bool, str]:
        if file_path.name in self.skip_files:
            return True, "excluded_name"

        if file_path.suffix.lower() in self.skip_extensions:
            return True, "excluded_ext"

        for part in file_path.parts:
            if part in self.skip_patterns or part.startswith("."):
                return True, "excluded_path"

        try:
            size = file_path.stat().st_size
        except OSError as exc:  # Permission denied, etc.
            raise ExtractionError(f"Unable to inspect file '{file_path}': {exc}") from exc

        if self.skip_empty and size == 0:
            return True, "empty"

        if size > self.max_file_size:
            return True, "too_large"

        return False, ""

    @staticmethod
    def _is_text_file(file_path: Path) -> bool:
        encodings = ["utf-8", "cp1251", "latin-1"]
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as handle:
                    handle.read(2048)
                return True
            except (UnicodeDecodeError, PermissionError):
                continue
        return False

    @staticmethod
    def _read_file_content(file_path: Path) -> str:
        encodings = ["utf-8", "cp1251", "latin-1"]
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as handle:
                    return handle.read()
            except (UnicodeDecodeError, PermissionError):
                continue
        return "[ERROR: Could not decode file]"

    def _format_compact(self, relative_path: Path, content: str) -> str:
        return f"\n--- {relative_path} ---\n{content}\n"

    def _format_standard(self, relative_path: Path, content: str) -> str:
        separator = "=" * 60
        return f"\n{separator}\nFILE: {relative_path}\n{separator}\n{content}\n\n"

    def extract(
        self,
        root_dir: str | Path,
        output_file: str | Path,
        *,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ExtractionStats:
        """Extract text files into a single document.

        Args:
            root_dir: Directory to scan.
            output_file: Destination file path.
            progress_callback: Optional callable compatible with
                ``rich.progress.Progress.update``. It receives keyword arguments
                ``advance`` (int) and ``description`` (str) describing the current file.

        Returns:
            ``ExtractionStats`` describing the operation.

        Raises:
            ExtractionError: If the root directory is invalid or I/O fails.
        """

        root_path = Path(root_dir).expanduser().resolve()
        if not root_path.exists() or not root_path.is_dir():
            raise ExtractionError(f"'{root_dir}' is not a valid directory")

        output_path = Path(output_file).expanduser().resolve()

        skipped_paths: DefaultDict[str, list[str]] = defaultdict(list)
        processed_paths: list[str] = []
        total_bytes = 0
        errors: list[str] = []

        try:
            with open(output_path, "w", encoding="utf-8") as destination:
                destination.write(f"# Extracted from: {root_path}\n")
                destination.write(f"# Max file size: {self.max_file_size // 1024}KB\n")
                destination.write(f"# Mode: {'compact' if self.compact_mode else 'standard'}\n")
                destination.write("=" * 60 + "\n")

                for file_path in sorted(root_path.rglob("*")):
                    if not file_path.is_file() or file_path.resolve() == output_path:
                        continue

                    relative_path = file_path.relative_to(root_path)
                    relative_str = str(relative_path)

                    try:
                        skip, reason = self._should_skip(file_path)
                    except ExtractionError as exc:
                        errors.append(str(exc))
                        skipped_paths["other"].append(relative_str)
                        continue

                    if skip:
                        skipped_key = reason or "other"
                        skipped_paths[skipped_key].append(relative_str)
                        continue

                    if not self._is_text_file(file_path):
                        skipped_paths["binary"].append(relative_str)
                        continue

                    content = self._read_file_content(file_path)

                    formatter = self._format_compact if self.compact_mode else self._format_standard
                    destination.write(formatter(relative_path, content))

                    processed_paths.append(relative_str)
                    total_bytes += len(content)

                    if progress_callback is not None:
                        try:
                            progress_callback(advance=1, description=relative_str)
                        except TypeError:
                            # Fallback for simpler callbacks accepting a single positional argument.
                            progress_callback(1)  # type: ignore[misc]

                destination.write(f"\n{'=' * 60}\n")
                destination.write(f"# Total files processed: {len(processed_paths)}\n")
                destination.write(f"# Total size: {total_bytes // 1024}KB\n")

        except OSError as exc:
            raise ExtractionError(str(exc)) from exc

        return ExtractionStats(
            root=root_path,
            output=output_path,
            processed_paths=list(processed_paths),
            total_bytes=total_bytes,
            skipped_paths={reason: list(paths) for reason, paths in skipped_paths.items()},
            errors=errors,
        )


__all__ = ["FileExtractor", "ExtractionError", "ExtractionStats"]
