"""Input widget that supports basic tab completion for paths and known values."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Sequence

from textual import events
from textual.widgets import Input


class CompletionInput(Input):
    """Input widget with lightweight tab-completion support."""

    def __init__(
        self,
        value: str | None = None,
        *,
        mode: str = "text",
        suggestions: Iterable[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(value=value, **kwargs)
        self.mode = mode
        self._static_suggestions: List[str] = list(suggestions or [])
        self._cycle_values: List[str] = []
        self._cycle_index: int = -1
        self._cycle_seed: str = ""

    def set_suggestions(self, suggestions: Sequence[str]) -> None:
        """Update the static suggestion list used for completions."""

        self._static_suggestions = list(suggestions)
        self._reset_cycle()

    def on_event(self, event: events.Event):
        if isinstance(event, events.Key):
            key = event.key
            if key in {"tab", "shift+tab"}:
                event.prevent_default()
                event.stop()
                self._handle_completion(forward=(key == "tab"))
                return super().on_event(event)

            self._reset_cycle()

        return super().on_event(event)

    def _handle_completion(self, *, forward: bool) -> None:
        seed = self.value or ""

        if self._cycle_values and seed.startswith(self._cycle_seed):
            self._cycle_index = (self._cycle_index + (1 if forward else -1)) % len(self._cycle_values)
            self._apply_completion(self._cycle_values[self._cycle_index])
            return

        matches = self._gather_completions(seed)
        if not matches:
            self.app.bell()
            self._reset_cycle()
            return

        self._cycle_seed = seed
        self._cycle_values = matches
        self._cycle_index = 0 if forward else len(matches) - 1
        self._apply_completion(self._cycle_values[self._cycle_index])

        if len(matches) > 1:
            preview = ", ".join(matches[:5])
            try:
                self.app.notify(f"Suggestions: {preview}", severity="information")
            except Exception:
                pass

    def _gather_completions(self, seed: str) -> List[str]:
        if self.mode == "path":
            return self._path_completions(seed)

        if not self._static_suggestions:
            return []

        lowered = seed.lower()
        candidates = [item for item in self._static_suggestions if item.lower().startswith(lowered)]
        if not candidates and lowered:
            candidates = [item for item in self._static_suggestions if lowered in item.lower()]
        return sorted(dict.fromkeys(candidates))

    def _path_completions(self, seed: str) -> List[str]:
        seed = seed or ""
        expanded = os.path.expanduser(seed)

        if seed.endswith(os.sep):
            base_dir = Path(expanded or ".")
            prefix = ""
        else:
            candidate = Path(expanded or ".")
            if candidate.is_dir():
                base_dir = candidate
                prefix = ""
            else:
                base_dir = candidate.parent
                prefix = candidate.name

        if not str(base_dir):
            base_dir = Path(".")

        if not base_dir.exists():
            return []

        try:
            entries = sorted(base_dir.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower()))
        except Exception:
            return []

        if prefix:
            root_text = seed[: len(seed) - len(prefix)]
        else:
            root_text = seed
            if root_text and not root_text.endswith(os.sep):
                root_text = f"{root_text}{os.sep}"

        completions: List[str] = []
        for entry in entries:
            name = entry.name
            if prefix and not name.startswith(prefix):
                continue
            suggestion = f"{root_text}{name}"
            if entry.is_dir():
                suggestion = f"{suggestion}{os.sep}"
            completions.append(suggestion)
        return completions

    def _apply_completion(self, value: str) -> None:
        self.value = value
        self.action_end()

    def _reset_cycle(self) -> None:
        self._cycle_seed = ""
        self._cycle_values = []
        self._cycle_index = -1


__all__ = ["CompletionInput"]
