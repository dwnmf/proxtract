"""Configuration persistence helpers for Proxtract."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .state import AppState

try:  # Python 3.11+
    import tomllib as _tomllib  # type: ignore[assignment]
except Exception:  # pragma: no cover - fallback to tomli if available
    try:
        import tomli as _tomllib  # type: ignore
    except Exception:  # pragma: no cover - optional dependency missing
        _tomllib = None  # type: ignore


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

    state.output_path = Path(data.get("output_path", state.output_path)).expanduser()
    state.max_size_kb = int(data.get("max_size_kb", state.max_size_kb))
    state.compact_mode = bool(data.get("compact_mode", state.compact_mode))
    state.skip_empty = bool(data.get("skip_empty", state.skip_empty))
    state.use_gitignore = bool(data.get("use_gitignore", state.use_gitignore))

    include = data.get("include_patterns")
    if isinstance(include, list):
        state.include_patterns = [str(item) for item in include]

    exclude = data.get("exclude_patterns")
    if isinstance(exclude, list):
        state.exclude_patterns = [str(item) for item in exclude]

    state.tokenizer_model = str(data.get("tokenizer_model", state.tokenizer_model))
    state.enable_token_count = bool(data.get("enable_token_count", state.enable_token_count))
    state.copy_to_clipboard = bool(data.get("copy_to_clipboard", state.copy_to_clipboard))
    return state


def save_config(state: AppState) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "output_path": str(state.output_path),
        "max_size_kb": int(state.max_size_kb),
        "compact_mode": bool(state.compact_mode),
        "skip_empty": bool(state.skip_empty),
        "use_gitignore": bool(state.use_gitignore),
        "include_patterns": list(state.include_patterns),
        "exclude_patterns": list(state.exclude_patterns),
        "tokenizer_model": str(state.tokenizer_model),
        "enable_token_count": bool(state.enable_token_count),
        "copy_to_clipboard": bool(state.copy_to_clipboard),
    }

    def _escape(item: str) -> str:
        return item.replace("\\", "\\\\").replace('"', '\\"')

    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, int):
            rendered = str(value)
        elif isinstance(value, list):
            rendered = "[" + ", ".join(f'"{_escape(entry)}"' for entry in value) + "]"
        else:
            rendered = f'"{_escape(str(value))}"'
        lines.append(f"{key} = {rendered}")

    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


__all__ = ["load_config", "apply_config", "save_config"]
