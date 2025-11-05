"""Unit tests for core filtering and extraction logic."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from proxtract.core import FileExtractor, ExtractionStats, ExtractionError


class TestFileFiltering:
    """Test file filtering logic."""

    def test_default_extension_filtering(self):
        """Test that default extensions are properly filtered."""
        extractor = FileExtractor()
        
        # Test with default extensions
        assert ".pdf" in extractor.skip_extensions
        assert ".png" in extractor.skip_extensions
        assert ".jpg" in extractor.skip_extensions
        assert ".txt" not in extractor.skip_extensions
        assert ".py" not in extractor.skip_extensions

    def test_custom_skip_extensions(self):
        """Test custom extension filtering rules."""
        extractor = FileExtractor(skip_extensions={".py", ".js"})
        
        assert ".py" in extractor.skip_extensions
        assert ".js" in extractor.skip_extensions
        assert ".pdf" not in extractor.skip_extensions
        assert ".png" not in extractor.skip_extensions

    def test_custom_skip_patterns(self):
        """Test custom pattern filtering rules."""
        extractor = FileExtractor(skip_patterns={"__pycache__", "test_*"})
        
        assert "__pycache__" in extractor.skip_patterns
        assert "test_*" in extractor.skip_patterns
        # Default patterns should still be present
        assert ".git" in extractor.skip_patterns

    def test_custom_skip_files(self):
        """Test custom file name filtering rules."""
        extractor = FileExtractor(skip_files={"package.json", "requirements.txt"})
        
        assert "package.json" in extractor.skip_files
        assert "requirements.txt" in extractor.skip_files

    def test_match_any_function(self):
        """Test the _match_any function."""
        patterns = ["*.py", "test_*", "config.*"]
        
        # Test matching patterns
        assert FileExtractor._match_any(patterns, "main.py")
        assert FileExtractor._match_any(patterns, "test_module.py")
        assert FileExtractor._match_any(patterns, "config.json")
        
        # Test non-matching patterns
        assert not FileExtractor._match_any(patterns, "app.js")
        assert not FileExtractor._match_any(patterns, "README.md")

    def test_should_skip_extension_filter(self):
        """Test file skipping due to extension filtering."""
        extractor = FileExtractor(skip_extensions={".pdf", ".png"})
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            extractor._root_path = root
            
            pdf_file = root / "document.pdf"
            pdf_file.write_text("PDF content", encoding="utf-8")
            
            should_skip, reason = extractor._should_skip(pdf_file, include_override=False)
            assert should_skip
            assert reason == "excluded_ext"

    def test_should_skip_file_name_filter(self):
        """Test file skipping due to file name filtering."""
        extractor = FileExtractor(skip_files={"package.json", "requirements.txt"})
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            extractor._root_path = root
            
            pkg_file = root / "package.json"
            pkg_file.write_text('{"name": "test"}', encoding="utf-8")
            
            should_skip, reason = extractor._should_skip(pkg_file, include_override=False)
            assert should_skip
            assert reason == "excluded_name"

    def test_should_skip_pattern_filter(self):
        """Test file skipping due to pattern filtering."""
        extractor = FileExtractor(skip_patterns={"__pycache__", "test_*"})
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            extractor._root_path = root
            
            # Test __pycache__ directory
            cache_dir = root / "__pycache__"
            cache_dir.mkdir()
            test_file = cache_dir / "module.pyc"
            test_file.write_text("bytecode", encoding="utf-8")
            
            should_skip, reason = extractor._should_skip(test_file, include_override=False)
            assert should_skip
            assert reason == "excluded_path"

    def test_should_skip_empty_files(self):
        """Test empty file handling."""
        extractor = FileExtractor(skip_empty=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            extractor._root_path = root
            
            empty_file = root / "empty.txt"
            empty_file.write_text("", encoding="utf-8")
            
            should_skip, reason = extractor._should_skip(empty_file, include_override=False)
            assert should_skip
            assert reason == "empty"

    def test_should_skip_large_files(self):
        """Test large file handling."""
        extractor = FileExtractor(max_file_size_kb=1)  # 1KB limit
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            extractor._root_path = root
            
            large_file = root / "large.txt"
            large_file.write_text("x" * (2 * 1024), encoding="utf-8")  # 2KB
            
            should_skip, reason = extractor._should_skip(large_file, include_override=False)
            assert should_skip
            assert reason == "too_large"

    def test_include_pattern_override(self):
        """Test include pattern override functionality."""
        extractor = FileExtractor(include_patterns=["src/*"])
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            extractor._root_path = root
            
            # Create files
            src_file = root / "src" / "main.py"
            src_file.write_text("print('src')", encoding="utf-8")
            src_file.parent.mkdir(parents=True)
            
            other_file = root / "other.py"
            other_file.write_text("print('other')", encoding="utf-8")
            
            # With include override, included files should not be filtered
            should_skip, reason = extractor._should_skip(src_file, include_override=True)
            assert not should_skip
            
            # Without include override, non-included files should be filtered
            should_skip, reason = extractor._should_skip(other_file, include_override=False)
            assert should_skip
            assert reason == "not_included"


class TestBinaryDetection:
    """Test binary file detection logic."""

    def test_is_text_file_utf8(self):
        """Test text file detection with UTF-8 content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            text_file = root / "text.txt"
            text_file.write_text("Hello, world! This is a UTF-8 text file.", encoding="utf-8")
            
            assert FileExtractor._is_text_file(text_file)

    def test_is_text_file_empty(self):
        """Test that empty files are considered text files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            empty_file = root / "empty.txt"
            empty_file.write_text("", encoding="utf-8")
            
            assert FileExtractor._is_text_file(empty_file)

    def test_is_text_file_binary_signature(self):
        """Test binary file detection with magic bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Test PNG file
            png_file = root / "image.png"
            png_content = b'\x89PNG\r\n\x1a\n' + b'text content'
            png_file.write_bytes(png_content)
            assert not FileExtractor._is_text_file(png_file)
            
            # Test PDF file
            pdf_file = root / "document.pdf"
            pdf_content = b'%PDF-1.4\n' + b'pdf content'
            pdf_file.write_bytes(pdf_content)
            assert not FileExtractor._is_text_file(pdf_file)
            
            # Test ZIP file
            zip_file = root / "archive.zip"
            zip_content = b'PK\x03\x04' + b'zip content'
            zip_file.write_bytes(zip_content)
            assert not FileExtractor._is_text_file(zip_file)

    def test_is_text_file_null_bytes(self):
        """Test binary file detection with null bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # File with high null byte ratio
            null_file = root / "binary.bin"
            null_content = b'\x00' * 20 + b'text' + b'\x00' * 20  # > 50% null bytes
            null_file.write_bytes(null_content)
            assert not FileExtractor._is_text_file(null_file)
            
            # File with low null byte ratio (should be treated as text)
            text_with_nulls = root / "text_with_nulls.txt"
            text_content = b'text content\x00with some nulls'
            text_with_nulls.write_bytes(text_content)
            assert FileExtractor._is_text_file(text_with_nulls)

    def test_is_text_file_encoding_detection(self):
        """Test text file detection with different encodings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Test Latin-1 encoded file
            latin1_file = root / "latin1.txt"
            latin1_content = "Café résumé naïve".encode('latin-1')
            latin1_file.write_bytes(latin1_content)
            assert FileExtractor._is_text_file(latin1_file)
            
            # Test UTF-8 BOM file
            bom_file = root / "bom.txt"
            bom_content = b'\xef\xbb\xbf' + b'UTF-8 with BOM'
            bom_file.write_bytes(bom_content)
            assert FileExtractor._is_text_file(bom_file)

    def test_is_text_file_control_characters(self):
        """Test text file detection with high control character ratio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # File with too many control characters
            control_file = root / "control.txt"
            control_content = b'text\x01\x02\x03\x04\x05' * 10  # Many control chars
            control_file.write_bytes(control_content)
            assert not FileExtractor._is_text_file(control_file)


class TestExtractionStats:
    """Test ExtractionStats class."""

    def test_processed_files_property(self):
        """Test processed_files property."""
        stats = ExtractionStats(
            root=Path("/tmp"),
            output=Path("/tmp/output.txt"),
            processed_paths=["file1.txt", "file2.py", "file3.js"],
            total_bytes=1024,
            skipped_paths={},
            errors=[],
        )
        
        assert stats.processed_files == 3

    def test_skipped_property(self):
        """Test skipped property aggregation."""
        stats = ExtractionStats(
            root=Path("/tmp"),
            output=Path("/tmp/output.txt"),
            processed_paths=[],
            total_bytes=0,
            skipped_paths={
                "excluded_ext": ["file1.pdf", "file2.png"],
                "empty": ["file3.txt"],
                "too_large": ["file4.bin"],
                "custom_reason": ["file5.custom"],
            },
            errors=[],
        )
        
        skipped = stats.skipped
        assert skipped["excluded_ext"] == 2
        assert skipped["empty"] == 1
        assert skipped["too_large"] == 1
        assert skipped["other"] == 1  # custom_reason should be aggregated to "other"

    def test_as_dict_method(self):
        """Test as_dict method."""
        stats = ExtractionStats(
            root=Path("/tmp"),
            output=Path("/tmp/output.txt"),
            processed_paths=["file1.txt"],
            total_bytes=512,
            skipped_paths={"excluded_ext": ["file.pdf"]},
            errors=[],
            token_count=100,
            token_model="gpt-4",
        )
        
        result = stats.as_dict()
        assert isinstance(result, dict)
        assert result["processed_files"] == 1
        assert result["total_bytes"] == 512
        assert result["skipped"]["excluded_ext"] == 1
        assert result["token_count"] == 100


class TestExtractionWorkflow:
    """Test complete extraction workflow."""

    def test_extract_basic_workflow(self):
        """Test basic extraction workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create test files
            (root / "file1.txt").write_text("Content 1", encoding="utf-8")
            (root / "file2.py").write_text("print('hello')", encoding="utf-8")
            
            output_file = root / "extracted.txt"
            extractor = FileExtractor()
            
            stats = extractor.extract(root, output_file)
            
            # Check stats
            assert stats.processed_files == 2
            assert stats.total_bytes > 0
            assert len(stats.skipped) == 0
            
            # Check output file
            content = output_file.read_text(encoding="utf-8")
            assert "Content 1" in content
            assert "print('hello')" in content

    def test_extract_with_filtering(self):
        """Test extraction with various filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create test files with different types
            (root / "src.py").write_text("print('python')", encoding="utf-8")
            (root / "image.png").write_text("fake png", encoding="utf-8")
            (root / "empty.txt").write_text("", encoding="utf-8")
            
            output_file = root / "extracted.txt"
            extractor = FileExtractor(skip_extensions={".png"})
            
            stats = extractor.extract(root, output_file)
            
            assert stats.processed_files == 1  # Only .py file
            assert stats.skipped["excluded_ext"] == 1  # .png file
            assert stats.skipped["empty"] == 1  # empty file
            
            content = output_file.read_text(encoding="utf-8")
            assert "src.py" in content
            assert "image.png" not in content

    def test_extract_binary_files(self):
        """Test that binary files are properly detected and skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create text file
            text_file = root / "text.txt"
            text_file.write_text("This is text", encoding="utf-8")
            
            # Create binary file
            binary_file = root / "image.png"
            binary_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'binary data')
            
            output_file = root / "extracted.txt"
            extractor = FileExtractor()
            
            stats = extractor.extract(root, output_file)
            
            assert stats.processed_files == 1  # Only text file
            assert stats.skipped["binary"] == 1  # Binary file skipped
            
            content = output_file.read_text(encoding="utf-8")
            assert "text.txt" in content
            assert "image.png" not in content

    def test_extract_gitignore_support(self):
        """Test .gitignore support (if pathspec is available)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create .gitignore file
            (root / ".gitignore").write_text("*.log\n", encoding="utf-8")
            
            # Create test files
            (root / "main.py").write_text("print('main')", encoding="utf-8")
            (root / "debug.log").write_text("debug output", encoding="utf-8")
            
            output_file = root / "extracted.txt"
            extractor = FileExtractor(use_gitignore=True)
            
            stats = extractor.extract(root, output_file)
            
            # Should skip .log file due to gitignore
            assert stats.processed_files == 1
            content = output_file.read_text(encoding="utf-8")
            assert "main.py" in content
            assert "debug.log" not in content

    def test_extract_include_patterns(self):
        """Test extraction with include patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create nested files
            (root / "src" / "main.py").write_text("print('main')", encoding="utf-8")
            (root / "docs" / "readme.md").write_text("# README", encoding="utf-8")
            (root / "tests" / "test.py").write_text("def test(): pass", encoding="utf-8")
            
            output_file = root / "extracted.txt"
            extractor = FileExtractor(include_patterns=["src/*", "*.md"])
            
            stats = extractor.extract(root, output_file)
            
            assert stats.processed_files == 2  # src/main.py and docs/readme.md
            
            content = output_file.read_text(encoding="utf-8")
            assert "src/main.py" in content
            assert "docs/readme.md" in content
            assert "tests/test.py" not in content

    def test_extract_nonexistent_directory_raises_error(self):
        """Test that extraction fails on nonexistent directory."""
        extractor = FileExtractor()
        
        with pytest.raises(ExtractionError):
            extractor.extract("/nonexistent", "/tmp/output.txt")

    def test_extract_file_reading_fallback(self):
        """Test file reading with encoding fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create a file with mixed encoding that will fail UTF-8 but succeed with cp1251
            mixed_file = root / "mixed.txt"
            mixed_content = "Café résumé naïve".encode('cp1251') + b'\xe9'  # Test fallback
            mixed_file.write_bytes(mixed_content)
            
            output_file = root / "extracted.txt"
            extractor = FileExtractor()
            
            # Should not raise an error due to fallback encoding
            stats = extractor.extract(root, output_file)
            assert stats.processed_files == 1

    def test_extract_progress_callback(self):
        """Test progress callback functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            (root / "file1.txt").write_text("Content 1", encoding="utf-8")
            (root / "file2.txt").write_text("Content 2", encoding="utf-8")
            
            output_file = root / "extracted.txt"
            extractor = FileExtractor()
            
            # Mock progress callback
            progress_calls = []
            def progress_callback(*, advance, description):
                progress_calls.append((advance, description))
            
            stats = extractor.extract(root, output_file, progress_callback=progress_callback)
            
            assert len(progress_calls) == 2
            assert all(call[0] == 1 for call in progress_calls)  # Each call advances by 1


if __name__ == "__main__":
    pytest.main([__file__])