import os
from pathlib import Path

import pytest

from proxtract.tui.widgets import CompletionInput


@pytest.mark.tui
class TestCompletionInput:
    def test_list_mode_completion_preserves_prefix(self):
        widget = CompletionInput(mode="list", suggestions=["alpha", "beta", "gamma"])
        prefix, fragment = widget._split_list_seed("foo, be")
        assert prefix == "foo, "
        assert fragment == "be"

        matches = widget._gather_completions("foo, be")
        assert matches == ["foo, beta"]

    def test_list_mode_completion_handles_leading_whitespace(self):
        widget = CompletionInput(mode="list", suggestions=["alpha", "beta"])
        prefix, fragment = widget._split_list_seed("  be")
        assert prefix == "  "
        assert fragment == "be"

        matches = widget._gather_completions("  be")
        assert matches == ["  beta"]

    def test_path_mode_completion(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        nested = tmp_path / "nested"
        nested.mkdir()
        file_path = tmp_path / "demo.txt"
        file_path.write_text("data", encoding="utf-8")

        widget = CompletionInput(mode="path")

        # Ensure deterministic ordering across platforms
        monkeypatch.chdir(tmp_path)
        completions = widget._gather_completions("")
        assert [Path(c).name for c in completions] == ["nested", "demo.txt"]

        completions = widget._gather_completions(str(tmp_path) + os.sep)
        assert completions[0].endswith("nested" + os.sep)
        assert completions[1].endswith("demo.txt")
