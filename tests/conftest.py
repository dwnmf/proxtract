import sys
from pathlib import Path
import tempfile
import pytest
from typing import Iterator, Dict, Any, List
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from proxtract.core import FileExtractor
from proxtract.state import AppState


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_text_files(temp_dir: Path) -> Path:
    """Create a directory with sample text files for testing."""
    sample_dir = temp_dir / "samples"
    sample_dir.mkdir()
    
    # Create various text files
    (sample_dir / "python.py").write_text("print('hello world')", encoding="utf-8")
    (sample_dir / "javascript.js").write_text("console.log('hello');", encoding="utf-8")
    (sample_dir / "markdown.md").write_text("# Hello World\n\nThis is a test.", encoding="utf-8")
    (sample_dir / "text.txt").write_text("Just plain text content.", encoding="utf-8")
    (sample_dir / "empty.txt").write_text("", encoding="utf-8")
    (sample_dir / "unicode.txt").write_text("Hello 世界! Café résumé naïve.", encoding="utf-8")
    
    return sample_dir


@pytest.fixture
def binary_files(temp_dir: Path) -> Path:
    """Create a directory with binary files for testing."""
    binary_dir = temp_dir / "binary"
    binary_dir.mkdir()
    
    # Create various binary files using magic bytes
    # PNG file
    png_file = binary_dir / "image.png"
    png_content = b'\x89PNG\r\n\x1a\n' + b'PNG image data' * 10
    png_file.write_bytes(png_content)
    
    # PDF file
    pdf_file = binary_dir / "document.pdf"
    pdf_content = b'%PDF-1.4\n' + b'PDF document content' * 10
    pdf_file.write_bytes(pdf_content)
    
    # ZIP file
    zip_file = binary_dir / "archive.zip"
    zip_content = b'PK\x03\x04' + b'ZIP archive data' * 10
    zip_file.write_bytes(zip_content)
    
    # File with high null byte ratio
    null_file = binary_dir / "nulls.bin"
    null_content = b'\x00' * 50 + b'text' + b'\x00' * 50
    null_file.write_bytes(null_content)
    
    # JPEG file
    jpg_file = binary_dir / "photo.jpg"
    jpg_content = b'\xff\xd8\xff\xe0' + b'JPEG image data' * 10
    jpg_file.write_bytes(jpg_content)
    
    return binary_dir


@pytest.fixture
def mixed_files(temp_dir: Path) -> Path:
    """Create a directory with a mix of text and binary files."""
    mixed_dir = temp_dir / "mixed"
    mixed_dir.mkdir()
    
    # Text files
    (mixed_dir / "readme.md").write_text("# Project README\n\nWelcome!", encoding="utf-8")
    (mixed_dir / "main.py").write_text("def main():\n    print('Hello')\n", encoding="utf-8")
    (mixed_dir / "config.json").write_text('{"key": "value"}', encoding="utf-8")
    
    # Binary files
    (mixed_dir / "logo.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'logo data')
    (mixed_dir / "manual.pdf").write_bytes(b'%PDF-1.4\n' + b'pdf data')
    
    # Files that should be filtered by name/pattern
    (mixed_dir / "package.json").write_text('{"name": "test"}', encoding="utf-8")
    (mixed_dir / "requirements.txt").write_text("requests>=2.0.0", encoding="utf-8")
    (mixed_dir / "__pycache__").mkdir()
    (mixed_dir / "__pycache__" / "module.pyc").write_bytes(b'python bytecode')
    
    return mixed_dir


@pytest.fixture
def large_files(temp_dir: Path) -> Path:
    """Create files of various sizes for testing."""
    large_dir = temp_dir / "large"
    large_dir.mkdir()
    
    # Small file (under 1KB limit)
    small_file = large_dir / "small.txt"
    small_file.write_text("Small content", encoding="utf-8")
    
    # Medium file (under 5KB limit but over 1KB)
    medium_file = large_dir / "medium.txt"
    medium_file.write_text("Medium content. " * 100, encoding="utf-8")  # ~1.7KB
    
    # Large file (over 5KB limit)
    large_file = large_dir / "large.txt"
    large_file.write_text("Large content. " * 1000, encoding="utf-8")  # ~17KB
    
    # Very large file (over 1MB)
    very_large_file = large_dir / "very_large.txt"
    very_large_file.write_text("Very large content. " * 10000, encoding="utf-8")  # ~170KB
    
    return large_dir


@pytest.fixture
def nested_structure(temp_dir: Path) -> Path:
    """Create a nested directory structure for testing."""
    root = temp_dir / "project"
    root.mkdir()
    
    # Create nested structure
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("def main(): pass", encoding="utf-8")
    (root / "src" / "utils.py").write_text("def util(): pass", encoding="utf-8")
    
    (root / "docs").mkdir()
    (root / "docs" / "api.md").write_text("# API Documentation", encoding="utf-8")
    (root / "docs" / "readme.md").write_text("# README", encoding="utf-8")
    
    (root / "tests").mkdir()
    (root / "tests" / "test_main.py").write_text("def test_main(): pass", encoding="utf-8")
    
    (root / "config").mkdir()
    (root / "config" / "settings.toml").write_text('[settings]\ndebug = true', encoding="utf-8")
    
    # Files to be filtered
    (root / "package.json").write_text('{"name": "test"}', encoding="utf-8")
    (root / ".gitignore").write_text("*.log\nnode_modules/", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "cache.pyc").write_bytes(b'bytecode')
    
    return root


@pytest.fixture
def extractor_default() -> FileExtractor:
    """Create a FileExtractor with default settings."""
    return FileExtractor()


@pytest.fixture
def extractor_no_filters() -> FileExtractor:
    """Create a FileExtractor with all filtering disabled."""
    return FileExtractor(
        skip_extensions=set(),
        skip_patterns=set(),
        skip_files=set(),
        skip_empty=False,
        max_file_size_kb=10000,  # Very large limit
    )


@pytest.fixture
def extractor_strict_filters() -> FileExtractor:
    """Create a FileExtractor with strict filtering."""
    return FileExtractor(
        skip_extensions={".txt", ".md", ".json"},
        skip_patterns={"src", "tests"},
        skip_files={"config.json"},
        skip_empty=True,
        max_file_size_kb=1,  # Very small limit
    )


@pytest.fixture
def app_state_default() -> AppState:
    """Create an AppState with default settings."""
    return AppState()


@pytest.fixture
def app_state_custom() -> AppState:
    """Create an AppState with custom settings."""
    state = AppState()
    state.output_path = Path("test_output.txt")
    state.max_size_kb = 1000
    state.compact_mode = False
    state.skip_empty = False
    state.use_gitignore = False
    state.include_patterns = ["*.py", "src/*"]
    state.exclude_patterns = ["*.log", "test_*"]
    state.skip_extensions = {".pdf", ".png"}
    state.skip_patterns = {"__pycache__", ".git"}
    state.skip_files = {"package.json", "requirements.txt"}
    state.tokenizer_model = "gpt-3.5-turbo"
    state.enable_token_count = False
    state.copy_to_clipboard = True
    return state


@pytest.fixture
def mock_config_path(temp_dir: Path) -> Iterator[Path]:
    """Mock the config path to use a temporary location."""
    config_path = temp_dir / "settings.toml"
    with patch('proxtract.config._config_path') as mock_path:
        mock_path.return_value = config_path
        yield config_path


@pytest.fixture
def mock_toml_available():
    """Mock TOML library as available."""
    class MockTomllib:
        @staticmethod
        def loads(text):
            import tomli
            return tomli.loads(text)
    
    class MockTomliW:
        @staticmethod
        def dump(data, handle):
            import tomli_w
            return tomli_w.dump(data, handle)
    
    with patch('proxtract.config._tomllib', MockTomllib):
        with patch('proxtract.config._tomli_w', MockTomliW):
            yield


@pytest.fixture
def mock_toml_unavailable():
    """Mock TOML library as unavailable."""
    with patch('proxtract.config._tomllib', None):
        with patch('proxtract.config._tomli_w', None):
            yield


def create_test_file(directory: Path, filename: str, content: str | bytes, is_binary: bool = False) -> Path:
    """Helper function to create a test file."""
    file_path = directory / filename
    if is_binary or isinstance(content, bytes):
        file_path.write_bytes(content)
    else:
        file_path.write_text(content, encoding="utf-8")
    return file_path


def assert_file_processed(stats: 'ExtractionStats', filename: str) -> None:
    """Assert that a file was processed in extraction stats."""
    assert filename in stats.processed_paths


def assert_file_skipped(stats: 'ExtractionStats', filename: str, reason: str) -> None:
    """Assert that a file was skipped in extraction stats."""
    assert filename in stats.skipped_paths[reason]


def assert_extraction_success(stats: 'ExtractionStats', expected_files: int = None) -> None:
    """Assert that extraction was successful."""
    assert len(stats.errors) == 0, f"Extraction had errors: {stats.errors}"
    if expected_files is not None:
        assert stats.processed_files == expected_files


def create_gitignore_test_setup(temp_dir: Path) -> Path:
    """Create a test setup with .gitignore file."""
    root = temp_dir / "gitignore_test"
    root.mkdir()
    
    # Create .gitignore
    (root / ".gitignore").write_text(
        "*.log\n"
        "__pycache__/\n"
        "node_modules/\n"
        "*.tmp\n",
        encoding="utf-8"
    )
    
    # Create files that should be ignored
    (root / "debug.log").write_text("Log file", encoding="utf-8")
    (root / "temp.tmp").write_text("Temporary file", encoding="utf-8")
    
    # Create pycache directory
    cache_dir = root / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "module.pyc").write_bytes(b'bytecode')
    
    # Create node_modules directory
    node_modules = root / "node_modules"
    node_modules.mkdir()
    (node_modules / "package.json").write_text('{"name": "dep"}', encoding="utf-8")
    
    # Create files that should NOT be ignored
    (root / "main.py").write_text("print('main')", encoding="utf-8")
    (root / "README.md").write_text("# Project", encoding="utf-8")
    
    return root
