"""Pytest configuration and shared fixtures for Proxtract tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from proxtract.core import FileExtractor
from proxtract.state import AppState


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_project_dir(temp_dir: Path) -> Path:
    """Create a sample project structure for testing."""
    project_dir = temp_dir / "sample_project"
    project_dir.mkdir()
    
    # Create some test files
    (project_dir / "main.py").write_text("# This is main.py\nprint('Hello, World!')")
    (project_dir / "README.md").write_text("# Sample Project\nThis is a test project.")
    (project_dir / "config.json").write_text('{"name": "test", "version": "1.0"}')
    (project_dir / "empty.txt").write_text("")
    (project_dir / "large_file.txt").write_text("x" * 1000)  # 1KB file
    (project_dir / "subdir").mkdir()
    (project_dir / "subdir" / "nested.py").write_text("# Nested file\ndef func(): pass")
    (project_dir / ".gitignore").write_text("*.pyc\n__pycache__/")
    
    return project_dir


@pytest.fixture
def binary_files_dir(temp_dir: Path) -> Path:
    """Create directory with binary files for testing."""
    binary_dir = temp_dir / "binary_files"
    binary_dir.mkdir()
    
    # Create some binary files
    (binary_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG header
    (binary_dir / "audio.mp3").write_bytes(b"ID3\x03\x00\x00\x00\x00\x00")  # MP3 header
    
    return binary_dir


@pytest.fixture
def extractor() -> FileExtractor:
    """Create a FileExtractor instance for testing."""
    return FileExtractor()


@pytest.fixture
def app_state() -> AppState:
    """Create an AppState instance for testing."""
    return AppState()


@pytest.fixture
def mock_pathspec(monkeypatch):
    """Mock pathspec module for testing gitignore functionality."""
    class MockPathspec:
        def __init__(self, lines):
            self.lines = lines
        
        def match_file(self, path):
            return "*.pyc" in path or "__pycache__" in path
    
    class MockPathSpec:
        @staticmethod
        def from_lines(format, lines):
            return MockPathspec(lines)
    
    monkeypatch.setattr("proxtract.core._pathspec", MockPathSpec)
    return MockPathSpec


@pytest.fixture
def mock_tiktoken(monkeypatch):
    """Mock tiktoken module for testing token counting."""
    class MockEncoder:
        def encode(self, text):
            # Simple mock: return number of words as "tokens"
            return text.split()
    
    class MockTiktoken:
        @staticmethod
        def encoding_for_model(model):
            return MockEncoder()
        
        @staticmethod
        def get_encoding(name):
            return MockEncoder()
    
    monkeypatch.setattr("proxtract.core._tiktoken", MockTiktoken)
    return MockTiktoken


@pytest.fixture
def mock_console(monkeypatch):
    """Mock Rich Console for testing CLI output."""
    class MockConsole:
        def __init__(self):
            self.print_calls = []
        
        def print(self, *args, **kwargs):
            self.print_calls.append((args, kwargs))
    
    mock = MockConsole()
    monkeypatch.setattr("rich.console.Console", lambda: mock)
    return mock