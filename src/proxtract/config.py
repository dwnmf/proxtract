"""Configuration persistence helpers for Proxtract."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .state import AppState
from .utils import normalize_bool

try:  # Python 3.11+
    import tomllib as _tomllib  # type: ignore[assignment]
except Exception:  # pragma: no cover - fallback to tomli if available
    try:
        import tomli as _tomllib  # type: ignore
    except Exception:  # pragma: no cover - optional dependency missing
        _tomllib = None  # type: ignore

try:  # TOML writing library
    import tomli_w as _tomli_w  # type: ignore[assignment]
except Exception:  # pragma: no cover - optional dependency missing
    _tomli_w = None  # type: ignore


def _config_path() -> Path:
    return Path("~/.config/proxtract/settings.toml").expanduser()


def load_config() -> Dict[str, Any]:
    path = _config_path()
    if not path.exists() or _tomllib is None:
        return {}
    try:
        return _tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def apply_config(state: AppState, data: Dict[str, Any]) -> AppState:
    if not data:
        return state

    # Helper function to safely convert to int
    def safe_int(value, default):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    output_path = data.get("output_path", state.output_path)
    state.output_path = Path(output_path).expanduser()
    
    state.max_size_kb = safe_int(data.get("max_size_kb", state.max_size_kb), state.max_size_kb)
    state.compact_mode = normalize_bool(data.get("compact_mode", state.compact_mode), state.compact_mode)
    state.skip_empty = normalize_bool(data.get("skip_empty", state.skip_empty), state.skip_empty)
    state.use_gitignore = normalize_bool(data.get("use_gitignore", state.use_gitignore), state.use_gitignore)
    state.force_include = normalize_bool(data.get("force_include", state.force_include), state.force_include)

    include = data.get("include_patterns")
    if isinstance(include, list):
        state.include_patterns = [str(item) for item in include]

    exclude = data.get("exclude_patterns")
    if isinstance(exclude, list):
        state.exclude_patterns = [str(item) for item in exclude]

    # Filter configuration - allow overriding hardcoded filters
    skip_extensions = data.get("skip_extensions", state.skip_extensions)
    if skip_extensions is None:
        state.skip_extensions = None
    elif isinstance(skip_extensions, list):
        state.skip_extensions = {str(item) for item in skip_extensions}

    skip_patterns = data.get("skip_patterns", state.skip_patterns)
    if skip_patterns is None:
        state.skip_patterns = None
    elif isinstance(skip_patterns, list):
        state.skip_patterns = {str(item) for item in skip_patterns}

    skip_files = data.get("skip_files", state.skip_files)
    if skip_files is None:
        state.skip_files = None
    elif isinstance(skip_files, list):
        state.skip_files = {str(item) for item in skip_files}

    state.tokenizer_model = str(data.get("tokenizer_model", state.tokenizer_model))
    state.enable_token_count = normalize_bool(
        data.get("enable_token_count", state.enable_token_count), state.enable_token_count
    )
    state.copy_to_clipboard = normalize_bool(
        data.get("copy_to_clipboard", state.copy_to_clipboard), state.copy_to_clipboard
    )
    return state


def save_config(state: AppState) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data: Dict[str, Any] = {
        "output_path": str(state.output_path),
        "max_size_kb": int(state.max_size_kb),
        "compact_mode": bool(state.compact_mode),
        "skip_empty": bool(state.skip_empty),
        "use_gitignore": bool(state.use_gitignore),
        "force_include": bool(state.force_include),
        "include_patterns": list(state.include_patterns),
        "exclude_patterns": list(state.exclude_patterns),
        "tokenizer_model": str(state.tokenizer_model),
        "enable_token_count": bool(state.enable_token_count),
        "copy_to_clipboard": bool(state.copy_to_clipboard),
    }

    def _serialize_optional_iterable(key: str, value: Optional[Iterable[str]]) -> None:
        if value is None:
            return
        data[key] = list(value)

    _serialize_optional_iterable("skip_extensions", getattr(state, "skip_extensions", None))
    _serialize_optional_iterable("skip_patterns", getattr(state, "skip_patterns", None))
    _serialize_optional_iterable("skip_files", getattr(state, "skip_files", None))

    # Use proper TOML library if available, otherwise fall back to manual construction
    if _tomli_w is not None:
        try:
            with path.open("wb") as handle:
                _tomli_w.dump(data, handle)
            return
        except Exception:
            # Fall back to manual construction if TOML serialization fails
            pass

    # Fallback to manual construction if TOML library is not available or fails
    def _escape(item: str) -> str:
        return item.replace("\\", "\\\\").replace('"', '\\"')

    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, int):
            rendered = str(value)
        elif isinstance(value, (list, set)):
            rendered = "[" + ", ".join(f'"{_escape(entry)}"' for entry in value) + "]"
        else:
            rendered = f'"{_escape(str(value))}"'
        lines.append(f"{key} = {rendered}")

    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


__all__ = ["load_config", "apply_config", "save_config"]
