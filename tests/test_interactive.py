from __future__ import annotations

import sys
from pathlib import Path

import pytest
from textual.widgets import Checkbox, Input

from proxtract.core import ExtractionStats
from proxtract.interactive import InteractiveShell
from proxtract.state import AppState


@pytest.mark.asyncio
async def test_app_populates_form(tmp_path):
    state = AppState()
    state.set_source_root(tmp_path)
    state.set_output_path(tmp_path / "result.txt")
    state.max_size_kb = 256
    state.include_patterns = ["src/**/*.py"]
    state.exclude_patterns = ["tests/**"]
    state.compact_mode = False

    app = InteractiveShell(state=state)
    async with app.run_test() as _:
        assert app.query_one("#source_path", Input).value == str(tmp_path)
        assert app.query_one("#output_path", Input).value == str(tmp_path / "result.txt")
        assert app.query_one("#max_size_kb", Input).value == "256"
        assert app.query_one("#include_patterns", Input).value == "src/**/*.py"
        assert app.query_one("#exclude_patterns", Input).value == "tests/**"
        assert app.query_one("#compact_mode", Checkbox).value is False


@pytest.mark.asyncio
async def test_update_state_from_form(tmp_path):
    state = AppState()
    state.set_source_root(tmp_path)
    state.set_output_path(tmp_path / "result.txt")

    app = InteractiveShell(state=state)
    async with app.run_test() as _:
        app.query_one("#max_size_kb", Input).value = "128"
        app.query_one("#include_patterns", Input).value = "*.py, *.md"
        app.query_one("#exclude_patterns", Input).value = "tests/**"
        app.query_one("#compact_mode", Checkbox).value = False
        app.query_one("#count_tokens", Checkbox).value = False

        app._update_state_from_form()

    assert state.max_size_kb == 128
    assert state.include_patterns == ["*.py", "*.md"]
    assert state.exclude_patterns == ["tests/**"]
    assert state.compact_mode is False
    assert state.enable_token_count is False


@pytest.mark.asyncio
async def test_run_extraction(monkeypatch, tmp_path):
    state = AppState()
    state.set_source_root(tmp_path)
    output = tmp_path / "result.txt"
    state.set_output_path(output)

    stats = ExtractionStats(
        root=tmp_path,
        output=output,
        processed_paths=["file.py"],
        total_bytes=128,
        skipped_paths={},
        errors=[],
    )

    class FakeExtractor:
        def extract(self, root: Path, destination: Path, progress_callback=None):
            if progress_callback:
                progress_callback(description="file.py")
            destination.write_text("payload", encoding="utf-8")
            return stats

    monkeypatch.setattr(state, "create_extractor", lambda: FakeExtractor())

    app = InteractiveShell(state=state)
    async with app.run_test() as pilot:
        await pilot.click("#run")
        await pilot.pause()

    assert state.last_stats == stats
    assert any("Готово" in message for message in app.messages)
    assert any("file.py" in message for message in app.messages)


@pytest.mark.asyncio
async def test_run_extraction_missing_root(tmp_path):
    state = AppState()
    state.set_source_root(tmp_path / "missing")
    state.set_output_path(tmp_path / "result.txt")

    app = InteractiveShell(state=state)
    async with app.run_test() as pilot:
        await pilot.click("#run")
        await pilot.pause()

    assert any("Укажите корректный" in message for message in app.messages)


@pytest.mark.asyncio
async def test_save_button(monkeypatch, tmp_path):
    state = AppState()
    state.set_source_root(tmp_path)
    state.set_output_path(tmp_path / "result.txt")

    saved: dict[str, AppState] = {}

    def fake_save(arg: AppState) -> None:
        saved["state"] = arg

    monkeypatch.setattr("proxtract.interactive.save_config", fake_save)

    app = InteractiveShell(state=state)
    async with app.run_test() as pilot:
        await pilot.click("#save")
        await pilot.pause()

    assert saved.get("state") is state
    assert any("Настройки сохранены" in message for message in app.messages)


@pytest.mark.asyncio
async def test_invalid_max_size(tmp_path):
    state = AppState()
    state.set_source_root(tmp_path)
    state.set_output_path(tmp_path / "result.txt")

    app = InteractiveShell(state=state)
    async with app.run_test() as pilot:
        app.query_one("#max_size_kb", Input).value = "not-a-number"
        await pilot.click("#run")
        await pilot.pause()

    assert any("max_size_kb должно быть числом" in message for message in app.messages)


@pytest.mark.asyncio
async def test_copy_to_clipboard(monkeypatch, tmp_path):
    state = AppState()
    state.set_source_root(tmp_path)
    output = tmp_path / "result.txt"
    output.write_text("payload", encoding="utf-8")
    state.set_output_path(output)
    state.copy_to_clipboard = True

    stats = ExtractionStats(
        root=tmp_path,
        output=output,
        processed_paths=["file.py"],
        total_bytes=128,
        skipped_paths={},
        errors=[],
    )

    class FakeExtractor:
        def extract(self, root: Path, destination: Path, progress_callback=None):
            return stats

    class DummyClipboard:
        def __init__(self) -> None:
            self.value = None

        def copy(self, value: str) -> None:
            self.value = value

    clipboard = DummyClipboard()
    monkeypatch.setitem(sys.modules, "pyperclip", clipboard)
    monkeypatch.setattr(state, "create_extractor", lambda: FakeExtractor())

    app = InteractiveShell(state=state)
    async with app.run_test() as pilot:
        await pilot.click("#run")
        await pilot.pause()

    assert clipboard.value == "payload"
    assert any("Результат скопирован" in message for message in app.messages)
