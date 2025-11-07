"""Unit tests for the Rich REPL implementation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from rich.console import Console

from proxtract.core import ExtractionStats
from proxtract.interactive import (
    PROMPT_TOOLKIT_AVAILABLE,
    Document,
    InteractiveShell,
    ProxtractCompleter,
    _tokenize,
)
from proxtract.state import AppState


def _make_shell(tmp_path) -> tuple[InteractiveShell, Console, AppState]:
    console = Console(record=True)
    state = AppState()
    state.set_source_root(tmp_path)
    state.set_output_path(tmp_path / "result.txt")
    shell = InteractiveShell(console=console, state=state)
    return shell, console, state


def test_set_command_updates_state(tmp_path):
    shell, console, state = _make_shell(tmp_path)

    shell.handle_command(f"set source_path {tmp_path}")
    assert state.source_root == tmp_path
    assert "source_path обновлен" in console.export_text()


def test_show_command_renders_table(tmp_path):
    shell, console, _ = _make_shell(tmp_path)

    shell.handle_command("show")
    rendered = console.export_text()
    assert "source_path" in rendered


def test_extract_command_invokes_extractor(monkeypatch, tmp_path):
    shell, console, state = _make_shell(tmp_path)
    output_path = shell.state.output_path

    stats = ExtractionStats(
        root=tmp_path,
        output=output_path,
        processed_paths=["file.py"],
        total_bytes=128,
        skipped_paths={},
        errors=[],
    )

    class FakeExtractor:
        def __init__(self) -> None:
            self.calls: list[tuple[Path, Path]] = []

        def extract(self, root: Path, output: Path, progress_callback=None):
            self.calls.append((Path(root), Path(output)))
            if progress_callback:
                progress_callback(description="file.py")
            return stats

    fake = FakeExtractor()
    monkeypatch.setattr(state, "create_extractor", lambda: fake)

    shell.handle_command("extract")

    assert fake.calls and fake.calls[0][0] == tmp_path
    assert state.last_stats == stats
    assert "Готово" in console.export_text()


def test_extract_with_missing_root(tmp_path):
    tmp_dir = tmp_path / "missing"
    console = Console(record=True)
    state = AppState()
    state.set_source_root(tmp_dir)
    shell = InteractiveShell(console=console, state=state)

    shell.handle_command("extract")
    assert "Укажите корректный source_path" in console.export_text()


def test_save_command_invokes_config(monkeypatch, tmp_path):
    shell, console, state = _make_shell(tmp_path)
    called = {}

    def fake_save(arg):
        called["state"] = arg

    monkeypatch.setattr("proxtract.interactive.save_config", fake_save)
    shell.handle_command("save")
    assert called.get("state") is state
    assert "Настройки сохранены" in console.export_text()


def test_unknown_set_key(tmp_path):
    shell, console, _ = _make_shell(tmp_path)
    shell.handle_command("set not_a_key 1")
    assert "Неизвестный параметр" in console.export_text()


def test_set_boolean_and_validation(tmp_path):
    shell, console, state = _make_shell(tmp_path)
    shell.handle_command("set compact_mode off")
    assert state.compact_mode is False
    shell.handle_command("set compact_mode on")
    assert state.compact_mode is True
    shell.handle_command("set compact_mode maybe")
    assert "Ошибка" in console.export_text()


def test_help_command_lists_entries(tmp_path):
    shell, console, _ = _make_shell(tmp_path)
    shell.handle_command("help")
    text = console.export_text()
    assert "extract" in text
    assert "set <key> <value>" in text


def test_config_alias(tmp_path):
    shell, console, _ = _make_shell(tmp_path)
    shell.handle_command("config")
    assert "Текущие настройки" in console.export_text()


def test_unknown_command(tmp_path):
    shell, console, _ = _make_shell(tmp_path)
    shell.handle_command("foobar")
    assert "Неизвестная команда" in console.export_text()


@pytest.mark.skipif(PROMPT_TOOLKIT_AVAILABLE, reason="Prompt toolkit present")
def test_run_without_prompt_toolkit(tmp_path):
    shell, console, _ = _make_shell(tmp_path)
    shell.run()
    assert "prompt_toolkit is required" in console.export_text()


def test_completer_suggests_commands():
    completer = ProxtractCompleter()
    doc = Document(text="", cursor_position=0)
    suggestions = [c.text for c in completer.get_completions(doc, None)]
    assert "extract" in suggestions

    doc_set = Document(text="set ", cursor_position=4)
    next_suggestions = [c.text for c in completer.get_completions(doc_set, None)]
    assert "source_path" in next_suggestions

    doc_bool = Document(text="set compact_mode o", cursor_position=len("set compact_mode o"))
    bool_suggestions = [c.text for c in completer.get_completions(doc_bool, None)]
    assert "on" in bool_suggestions


def test_tokenize_handles_trailing_space():
    tokens = _tokenize("set foo ")
    assert tokens[-1] == ""


def test_try_copy_reads_file(monkeypatch, tmp_path):
    shell, console, _ = _make_shell(tmp_path)
    output_file = tmp_path / "result.txt"
    output_file.write_text("payload", encoding="utf-8")
    stats = ExtractionStats(
        root=tmp_path,
        output=output_file,
        processed_paths=[],
        total_bytes=0,
        skipped_paths={},
        errors=[],
    )

    class DummyClipboard:
        def __init__(self) -> None:
            self.value = None

        def copy(self, text: str) -> None:
            self.value = text

    clipboard = DummyClipboard()
    monkeypatch.setitem(sys.modules, "pyperclip", clipboard)

    shell._try_copy(stats)
    assert clipboard.value == "payload"
    assert "Результат скопирован" in console.export_text()


def test_build_summary_panel_includes_optional_data(tmp_path):
    shell, console, _ = _make_shell(tmp_path)
    stats = ExtractionStats(
        root=tmp_path,
        output=tmp_path / "out.txt",
        processed_paths=["a.py"],
        total_bytes=42,
        skipped_paths={"binary": ["b.dat"]},
        errors=["warning"],
        token_count=10,
        token_model="gpt-4",
    )
    panel = shell._build_summary_panel(stats)
    console.print(panel)
    text = console.export_text()
    assert "Tokens" in text
    assert "Skipped" in text
    assert "Warnings" in text
