"""Tests for proxtract.main CLI helpers."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console

from proxtract import main as prox_main


def _make_args(**overrides) -> argparse.Namespace:
    defaults = {
        "path": ".",
        "output": None,
        "max_size": None,
        "compact": False,
        "no_compact": False,
        "skip_empty": False,
        "no_skip_empty": False,
        "use_gitignore": False,
        "no_gitignore": False,
        "include": None,
        "exclude": None,
        "force_include": False,
        "no_force_include": False,
        "tokenizer_model": None,
        "no_token_count": False,
        "copy": False,
        "save_config": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class DummyExtractor:
    def __init__(self, result):
        self._result = result
        self.calls: list[tuple[Path, Path]] = []

    def extract(self, root: Path, output: Path):
        self.calls.append((root, output))
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def test_run_cli_extract_success(tmp_path, monkeypatch):
    """_run_cli_extract should configure state and run extractor."""

    stats = SimpleNamespace(
        processed_files=3,
        total_bytes=4096,
        token_count=500,
        errors=["token warning"],
        output=tmp_path / "bundle.txt",
    )
    extractor = DummyExtractor(stats)
    monkeypatch.setattr(prox_main.AppState, "create_extractor", lambda self: extractor)

    args = _make_args(
        path=str(tmp_path),
        output=str(tmp_path / "result.txt"),
        max_size=256,
        compact=True,
        skip_empty=False,
        no_skip_empty=True,
        use_gitignore=True,
        include=["*.py"],
        exclude=["*.log"],
        force_include=True,
        tokenizer_model="gpt-4o-mini",
    )
    console = Console(record=True)

    exit_code = prox_main._run_cli_extract(args, console)

    assert exit_code == 0
    assert extractor.calls and extractor.calls[0][0] == tmp_path
    output_text = console.export_text()
    assert "Done." in output_text
    assert "token warning" in output_text


def test_run_cli_extract_failure(tmp_path, monkeypatch):
    """Errors from extractor should be reported and return code 2."""

    extractor = DummyExtractor(RuntimeError("boom"))
    monkeypatch.setattr(prox_main.AppState, "create_extractor", lambda self: extractor)

    args = _make_args(path=str(tmp_path))
    console = Console(record=True)

    exit_code = prox_main._run_cli_extract(args, console)

    assert exit_code == 2
    assert "Extraction failed" in console.export_text()


def test_main_launches_tui_when_no_args(monkeypatch):
    """main() should launch the TUI when no arguments are provided."""

    called = {}

    def fake_launch():
        called["ran"] = True

    monkeypatch.setattr(prox_main, "_launch_tui", fake_launch)
    prox_main.main([])
    assert called.get("ran") is True


def test_main_dispatches_extract(monkeypatch):
    """main() should dispatch extract subcommand and exit with its return code."""

    calls: dict[str, argparse.Namespace] = {}

    def fake_run(args, _console):
        calls["args"] = args
        return 0

    monkeypatch.setattr(prox_main, "_run_cli_extract", fake_run)

    with pytest.raises(SystemExit) as exc:
        prox_main.main(["extract", "."])

    assert exc.value.code == 0
    assert isinstance(calls["args"], argparse.Namespace)
