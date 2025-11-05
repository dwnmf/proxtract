"""Core extraction logic for the Proxtract CLI."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, DefaultDict, Dict, Iterable, Optional, Protocol
import fnmatch

try:  # Optional dependency for .gitignore support
    import pathspec as _pathspec  # type: ignore
except Exception:  # pragma: no cover - dependency optional
    _pathspec = None  # type: ignore

try:  # Optional dependency for token counting
    import tiktoken as _tiktoken  # type: ignore
except Exception:  # pragma: no cover - dependency optional
    _tiktoken = None  # type: ignore


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
    token_count: Optional[int] = None
    token_model: Optional[str] = None

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

    def __init__(
        self,
        *,
        max_file_size_kb: int = 500,
        skip_empty: bool = True,
        compact_mode: bool = True,
        use_gitignore: bool = False,
        include_patterns: Optional[Iterable[str]] = None,
        exclude_patterns: Optional[Iterable[str]] = None,
        tokenizer_model: Optional[str] = None,
        count_tokens: bool = False,
    ) -> None:
        self.max_file_size = max_file_size_kb * 1024
        self.skip_empty = skip_empty
        self.compact_mode = compact_mode
        self.use_gitignore = use_gitignore
        self.include_patterns = tuple(include_patterns or ())
        self.exclude_patterns = tuple(exclude_patterns or ())
        self.tokenizer_model = tokenizer_model
        self.count_tokens = count_tokens

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

        self._root_path: Optional[Path] = None
        self._gitignore_spec = None

    def _rel(self, file_path: Path) -> str:
        assert self._root_path is not None
        return str(file_path.relative_to(self._root_path))

    @staticmethod
    def _match_any(patterns: Iterable[str], rel: str) -> bool:
        for pattern in patterns:
            if fnmatch.fnmatch(rel, pattern):
                return True
        return False

    def _should_skip(self, file_path: Path, *, include_override: bool) -> tuple[bool, str]:
        rel = self._rel(file_path)

        if self._match_any(self.exclude_patterns, rel):
            return True, "excluded_pattern"

        if self._gitignore_spec is not None and self._gitignore_spec.match_file(rel):  # type: ignore[union-attr]
            return True, "gitignore"

        if self.include_patterns and not include_override:
            return True, "not_included"

        if not include_override:
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

        self._root_path = root_path
        self._gitignore_spec = None
        gitignore_error: Optional[str] = None
        if self.use_gitignore:
            if _pathspec is None:
                gitignore_error = "use_gitignore enabled but 'pathspec' is not installed"
            else:
                gitignore_path = root_path / ".gitignore"
                try:
                    lines: Iterable[str] = ()
                    if gitignore_path.exists():
                        lines = gitignore_path.read_text(encoding="utf-8").splitlines()
                    self._gitignore_spec = _pathspec.PathSpec.from_lines("gitwildmatch", lines)
                except Exception as exc:  # pragma: no cover - defensive guard
                    gitignore_error = f"Failed to load .gitignore: {exc}"

        skipped_paths: DefaultDict[str, list[str]] = defaultdict(list)
        processed_paths: list[str] = []
        total_bytes = 0
        errors: list[str] = []
        if gitignore_error is not None:
            errors.append(gitignore_error)

        token_count: Optional[int] = None
        token_model: Optional[str] = None
        encoder = None

        try:
            with open(output_path, "w", encoding="utf-8") as destination:
                destination.write(f"# Extracted from: {root_path}\n")
                destination.write(f"# Max file size: {self.max_file_size // 1024}KB\n")
                destination.write(f"# Mode: {'compact' if self.compact_mode else 'standard'}\n")
                destination.write("=" * 60 + "\n")
                if self.use_gitignore:
                    destination.write(f"# Gitignore: {'on' if self._gitignore_spec is not None else 'off'}\n")
                if self.include_patterns:
                    destination.write(f"# Include patterns: {', '.join(self.include_patterns)}\n")
                if self.exclude_patterns:
                    destination.write(f"# Exclude patterns: {', '.join(self.exclude_patterns)}\n")

                encoder = None
                token_count = None
                token_model = None
                if self.count_tokens:
                    if _tiktoken is None:
                        errors.append("Token counting enabled but 'tiktoken' is not installed")
                    else:
                        try:
                            token_model = self.tokenizer_model or "gpt-4"
                            try:
                                encoder = _tiktoken.encoding_for_model(token_model)
                            except Exception:
                                encoder = _tiktoken.get_encoding("cl100k_base")
                            token_count = 0
                        except Exception as exc:  # pragma: no cover - defensive
                            errors.append(f"Failed to initialize tokenizer: {exc}")
                            encoder = None

                for file_path in sorted(root_path.rglob("*")):
                    if not file_path.is_file() or file_path.resolve() == output_path:
                        continue

                    relative_path = file_path.relative_to(root_path)
                    relative_str = str(relative_path)

                    include_override = False
                    if self.include_patterns:
                        include_override = self._match_any(self.include_patterns, relative_str)

                    try:
                        skip, reason = self._should_skip(file_path, include_override=include_override)
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

                    if encoder is not None and token_count is not None:
                        try:
                            token_count += len(encoder.encode(content))
                        except Exception:  # pragma: no cover - tokenizer fallback
                            pass

                    if progress_callback is not None:
                        try:
                            progress_callback(advance=1, description=relative_str)
                        except TypeError:
                            # Fallback for simpler callbacks accepting a single positional argument.
                            progress_callback(1)  # type: ignore[misc]

                destination.write(f"\n{'=' * 60}\n")
                destination.write(f"# Total files processed: {len(processed_paths)}\n")
                destination.write(f"# Total size: {total_bytes // 1024}KB\n")
                if token_count is not None:
                    destination.write(f"# Total tokens: {token_count}\n")

        except OSError as exc:
            raise ExtractionError(str(exc)) from exc

        stats = ExtractionStats(
            root=root_path,
            output=output_path,
            processed_paths=list(processed_paths),
            total_bytes=total_bytes,
            skipped_paths={reason: list(paths) for reason, paths in skipped_paths.items()},
            errors=errors,
        )

        if token_count is not None:
            stats.token_count = token_count
            stats.token_model = token_model

        self._root_path = None
        self._gitignore_spec = None

        return stats


__all__ = ["FileExtractor", "ExtractionError", "ExtractionStats"]
