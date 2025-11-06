"""Core extraction logic for the Proxtract CLI."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, DefaultDict, Dict, Iterable, Optional, Protocol
import fnmatch
import os
import tempfile

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

        counts: DefaultDict[str, int] = defaultdict(int)
        canonical_reasons = {
            "excluded_ext",
            "empty",
            "too_large",
            "binary",
            "excluded_name",
            "excluded_path",
            "excluded_pattern",
            "gitignore",
            "not_included",
            "other",
        }
        for reason, paths in self.skipped_paths.items():
            key = reason if reason in canonical_reasons else "other"
            count = len(paths)
            if count:
                counts[key] = counts.get(key, 0) + count
        return counts

    def as_dict(self) -> Dict[str, object]:
        """Return stats in plain dict form for serialization/logging."""

        result = {
            "root": str(self.root),
            "output": str(self.output),
            "processed_paths": list(self.processed_paths),
            "processed_files": self.processed_files,
            "total_bytes": self.total_bytes,
            "skipped_paths": {reason: list(paths) for reason, paths in self.skipped_paths.items()},
            "skipped": dict(self.skipped),
            "errors": list(self.errors),
        }
        if self.token_count is not None:
            result["token_count"] = self.token_count
        if self.token_model is not None:
            result["token_model"] = self.token_model
        return result


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
        force_include: bool = False,
        tokenizer_model: Optional[str] = None,
        count_tokens: bool = False,
        # Configurable filtering rules
        skip_extensions: Optional[Iterable[str]] = None,
        skip_patterns: Optional[Iterable[str]] = None,
        skip_files: Optional[Iterable[str]] = None,
    ) -> None:
        self.max_file_size = max_file_size_kb * 1024
        self.skip_empty = skip_empty
        self.compact_mode = compact_mode
        self.use_gitignore = use_gitignore
        self.include_patterns = tuple(include_patterns or ())
        self.exclude_patterns = tuple(exclude_patterns or ())
        self.force_include = force_include
        self.tokenizer_model = tokenizer_model
        self.count_tokens = count_tokens

        # Default filtering rules
        default_extensions = {
            ".csv", ".jpeg", ".jpg", ".png", ".gif", ".bmp", ".gitignore", ".env",
            ".mp4", ".lgb", ".sqlite3-wal", ".sqlite3-shm", ".sqlite3", ".mkv",
            ".webm", ".mp3", ".wav", ".flac", ".aac", ".html", ".wma", ".ico",
            ".svg", ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".lock",
            ".exe", ".dll", ".so", ".dylib", ".pdf", ".doc", ".docx", ".xls",
            ".xlsx", ".ppt", ".pptx", ".pyc", ".pyo", ".pyd", ".pkl", ".parquet",
            ".orc", ".avro", ".feather", ".h5", ".hdf5", ".db", ".sqlite", ".bin",
            ".dat", ".idx", ".model", ".pt", ".ckpt", ".npy", ".npz", ".woff",
            ".woff2", ".ttf", ".eot"
        }

        default_patterns = {
            "__pycache__", ".git", ".svn", ".hg", "node_modules", ".vscode",
            ".idea", ".pytest_cache", ".mypy_cache", "venv", "env", "virtualenv",
            "dist", "build", ".next", "coverage", ".nyc_output", "vendor"
        }

        default_files = {
            "package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock",
            ".DS_Store", "Thumbs.db", "desktop.ini"
        }

        def _coerce_set(values: Iterable[str]) -> set[str]:
            return {str(entry) for entry in values}

        def _coerce_extensions(values: Iterable[str]) -> set[str]:
            return {str(entry).lower() for entry in values}

        # Use provided rules or fall back to defaults
        self.skip_extensions = (
            _coerce_extensions(default_extensions) if skip_extensions is None else _coerce_extensions(skip_extensions)
        )
        self.skip_patterns = _coerce_set(default_patterns) if skip_patterns is None else _coerce_set(skip_patterns)
        self.skip_files = _coerce_set(default_files) if skip_files is None else _coerce_set(skip_files)

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
        include_forced = include_override and self.force_include

        if not include_forced and self._match_any(self.exclude_patterns, rel):
            return True, "excluded_pattern"

        if (
            not include_forced
            and self._gitignore_spec is not None
            and self._gitignore_spec.match_file(rel)  # type: ignore[union-attr]
        ):
            return True, "gitignore"

        if self.include_patterns and not include_override:
            return True, "not_included"

        if not include_override:
            if file_path.name in self.skip_files:
                return True, "excluded_name"

            if file_path.suffix.lower() in self.skip_extensions:
                return True, "excluded_ext"

            # Check if filename matches any skip patterns
            rel = self._rel(file_path)
            if self._match_any(self.skip_patterns, rel):
                return True, "excluded_path"

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
        """Enhanced text file detection with binary detection."""
        # Check file size first - very small files are often text
        try:
            size = file_path.stat().st_size
        except OSError:
            return False
            
        if size == 0:
            return True
            
        # Read a reasonable chunk for analysis (limit to 8192 bytes)
        max_bytes = min(size, 8192)
        
        try:
            with open(file_path, "rb") as handle:
                data = handle.read(max_bytes)
        except (PermissionError, OSError):
            return False
            
        # Check for common binary file signatures (magic bytes)
        binary_signatures = {
            # Images
            b'\x89PNG': '.png',
            b'\xff\xd8\xff': '.jpg',
            b'GIF8': '.gif',
            b'RIFF': '.webp',  # may be webp or other RIFF-based format
            # Archives
            b'PK\x03\x04': '.zip',
            b'PK\x05\x06': '.zip',  # empty zip
            b'PK\x07\x08': '.zip',  # spanned zip
            b'RARF': '.rar',
            b'7z\xbc\xaf\x27\x1c': '.7z',
            b'\x1f\x8b': '.gz',
            b'BZh': '.bz2',
            # Documents
            b'%PDF': '.pdf',
            b'\xd0\xcf\x11\xe0': '.doc',  # MS Office
            b'PK\x03\x04': '.docx',  # OOXML
            # Audio/Video
            b'fLaC': '.flac',
            b'ID3': '.mp3',  # MP3 with ID3
            b'OggS': '.ogg',
            # Executables
            b'MZ': '.exe',
            b'\x7fELF': '.elf',
            # Database files
            b'SQLite': '.sqlite',
            b'\x00\x00\x00\x20ftyp': '.mp4',  # MP4/M4A
        }
        
        # Check for magic bytes
        for signature in binary_signatures:
            if data.startswith(signature):
                return False
                
        # Check for null bytes (strong indicator of binary content)
        # But allow null bytes in specific file types that might contain them
        if b'\x00' in data:
            # Additional check: if file is mostly null bytes, it's definitely binary
            null_ratio = data.count(b'\x00') / len(data)
            if null_ratio > 0.1:  # More than 10% null bytes
                return False
                
        # Try to decode as text with different encodings
        encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1", "cp1251"]
        for encoding in encodings:
            try:
                decoded = data.decode(encoding)
                # Additional check: if decoded content contains too many control
                # characters (except common ones like \n, \r, \t), it might be binary
                control_chars = sum(1 for c in decoded if (not c.isprintable()) and c not in '\n\r\t')
                control_ratio = control_chars / len(decoded) if decoded else 0
                if control_ratio > 0.1:  # More than 10% control characters
                    continue
                return True
            except UnicodeDecodeError:
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
        output_path.parent.mkdir(parents=True, exist_ok=True)

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

        temp_path: Optional[Path] = None
        temp_path_resolved: Optional[Path] = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=str(output_path.parent),
                prefix=f"{output_path.name}.",
                suffix=".tmp",
            ) as destination:
                temp_path = Path(destination.name)
                temp_path_resolved = temp_path.resolve()
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

                def report(description: str) -> None:
                    if progress_callback is None:
                        return
                    try:
                        progress_callback(advance=1, description=description)
                    except TypeError:
                        progress_callback(1)  # type: ignore[misc]

                for file_path in sorted(root_path.rglob("*")):
                    if not file_path.is_file():
                        continue

                    relative_path = file_path.relative_to(root_path)
                    relative_str = str(relative_path)

                    if temp_path_resolved is not None and file_path.resolve() == temp_path_resolved:
                        continue
                    if file_path.resolve() == output_path:
                        report(f"Skipping {relative_str}")
                        continue

                    include_override = False
                    if self.include_patterns:
                        include_override = self._match_any(self.include_patterns, relative_str)

                    try:
                        skip, reason = self._should_skip(file_path, include_override=include_override)
                    except ExtractionError as exc:
                        errors.append(str(exc))
                        skipped_paths["other"].append(relative_str)
                        report(f"Skipping {relative_str}")
                        continue

                    if skip:
                        skipped_key = reason or "other"
                        skipped_paths[skipped_key].append(relative_str)
                        report(f"Skipping {relative_str}")
                        continue

                    if not self._is_text_file(file_path):
                        skipped_paths["binary"].append(relative_str)
                        report(f"Skipping {relative_str}")

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

                    report(relative_str)

                destination.write(f"\n{'=' * 60}\n")
                destination.write(f"# Total files processed: {len(processed_paths)}\n")
                destination.write(f"# Total size: {total_bytes // 1024}KB\n")
                if token_count is not None:
                    destination.write(f"# Total tokens: {token_count}\n")
                destination.flush()
                os.fsync(destination.fileno())

            if temp_path is None:
                raise ExtractionError("Failed to create temporary output file")

            os.replace(temp_path, output_path)

        except ExtractionError:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        except OSError as exc:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise ExtractionError(str(exc)) from exc
        except Exception:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        finally:
            self._root_path = None
            self._gitignore_spec = None

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

        return stats


__all__ = ["FileExtractor", "ExtractionError", "ExtractionStats"]
