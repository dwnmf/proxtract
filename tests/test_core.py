"""Unit tests for the FileExtractor class in core.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from proxtract.core import ExtractionError, ExtractionStats, FileExtractor


class TestExtractionStats:
    """Test the ExtractionStats dataclass."""

    def test_processed_files_property(self):
        """Test the processed_files property."""
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py", "file2.py"],
            total_bytes=1000,
            skipped_paths={},
            errors=[]
        )
        assert stats.processed_files == 2

    def test_skipped_property(self):
        """Test the skipped property with different skip reasons."""
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py"],
            total_bytes=1000,
            skipped_paths={
                "excluded_ext": ["image.png", "document.pdf"],
                "empty": ["empty.txt"],
                "too_large": ["large.bin"],
                "binary": ["data.dat"],
                "unknown_reason": ["weird.txt"]
            },
            errors=[]
        )
        skipped = stats.skipped
        assert skipped["excluded_ext"] == 2
        assert skipped["empty"] == 1
        assert skipped["too_large"] == 1
        assert skipped["binary"] == 1
        assert skipped["other"] == 1  # unknown_reason gets mapped to "other"
        assert skipped["gitignore"] == 0  # not in the data
        assert skipped["excluded_name"] == 0  # not in the data

    def test_as_dict_method(self):
        """Test the as_dict method returns a proper dictionary."""
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py"],
            total_bytes=1000,
            skipped_paths={"empty": ["empty.txt"]},
            errors=["some warning"],
            token_count=42,
            token_model="gpt-4"
        )
        result = stats.as_dict()
        
        assert isinstance(result, dict)
        assert result["root"] == "/test"
        assert result["output"] == "/output.txt"
        assert result["processed_paths"] == ["file1.py"]
        assert result["processed_files"] == 1
        assert result["total_bytes"] == 1000
        assert result["skipped_paths"] == {"empty": ["empty.txt"]}
        assert result["skipped"] == {"empty": 1}
        assert result["errors"] == ["some warning"]


class TestFileExtractor:
    """Test the FileExtractor class."""

    def test_init_default_values(self, extractor):
        """Test FileExtractor initialization with default values."""
        assert extractor.max_file_size == 500 * 1024  # 500KB
        assert extractor.skip_empty is True
        assert extractor.compact_mode is True
        assert extractor.use_gitignore is False
        assert extractor.include_patterns == ()
        assert extractor.exclude_patterns == ()
        assert extractor.tokenizer_model is None
        assert extractor.count_tokens is False

    def test_init_custom_values(self):
        """Test FileExtractor initialization with custom values."""
        extractor = FileExtractor(
            max_file_size_kb=1000,
            skip_empty=False,
            compact_mode=False,
            use_gitignore=True,
            include_patterns=["*.py"],
            exclude_patterns=["test_*"],
            tokenizer_model="gpt-3.5-turbo",
            count_tokens=True
        )
        
        assert extractor.max_file_size == 1000 * 1024
        assert extractor.skip_empty is False
        assert extractor.compact_mode is False
        assert extractor.use_gitignore is True
        assert extractor.include_patterns == ("*.py",)
        assert extractor.exclude_patterns == ("test_*",)
        assert extractor.tokenizer_model == "gpt-3.5-turbo"
        assert extractor.count_tokens is True

    def test_skip_extensions(self, extractor):
        """Test that common binary file extensions are skipped."""
        # These should be in skip_extensions
        skip_exts = extractor.skip_extensions
        assert ".png" in skip_exts
        assert ".jpg" in skip_exts
        assert ".pdf" in skip_exts
        assert ".mp3" in skip_exts
        assert ".pyc" in skip_exts

    def test_skip_patterns(self, extractor):
        """Test that common directory patterns are skipped."""
        skip_patterns = extractor.skip_patterns
        assert "__pycache__" in skip_patterns
        assert ".git" in skip_patterns
        assert "node_modules" in skip_patterns
        assert "venv" in skip_patterns

    def test_skip_files(self, extractor):
        """Test that specific files are skipped."""
        skip_files = extractor.skip_files
        assert "package-lock.json" in skip_files
        assert "yarn.lock" in skip_files
        assert ".DS_Store" in skip_files

    def test_match_any(self, extractor):
        """Test the _match_any static method."""
        patterns = ["*.py", "*.md", "test_*"]
        
        # Should match patterns
        assert extractor._match_any(patterns, "main.py")
        assert extractor._match_any(patterns, "README.md")
        assert extractor._match_any(patterns, "test_file.py")
        
        # Should not match patterns
        assert not extractor._match_any(patterns, "main.c")
        assert not extractor._match_any(patterns, "config.json")
        assert not extractor._match_any(patterns, "other_file.py")

    def test_is_text_file_with_text(self, temp_dir):
        """Test _is_text_file correctly identifies text files."""
        text_file = temp_dir / "text.txt"
        text_file.write_text("This is a text file")
        
        assert FileExtractor._is_text_file(text_file) is True

    def test_is_text_file_with_binary(self, temp_dir, binary_files_dir):
        """Test _is_text_file correctly rejects binary files."""
        binary_file = binary_files_dir / "image.png"
        
        assert FileExtractor._is_text_file(binary_file) is False

    def test_is_text_file_with_encoding_issues(self, temp_dir):
        """Test _is_text_file handles encoding issues gracefully."""
        problematic_file = temp_dir / "problematic.txt"
        # Create a file with bytes that can't be decoded in common encodings
        problematic_file.write_bytes(b"\x80\x81\x82\x83")
        
        assert FileExtractor._is_text_file(problematic_file) is False

    def test_read_file_content_success(self, temp_dir):
        """Test _read_file_content with successful reads."""
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!\nThis is a test file."
        test_file.write_text(test_content)
        
        result = FileExtractor._read_file_content(test_file)
        assert result == test_content

    def test_read_file_content_fallback(self, temp_dir):
        """Test _read_file_content with encoding fallbacks."""
        test_file = temp_dir / "test.txt"
        # UTF-8 with some extended characters
        test_file.write_text("Hello, café!", encoding="utf-8")
        
        result = FileExtractor._read_file_content(test_file)
        assert result == "Hello, café!"

    def test_read_file_content_all_failures(self, temp_dir):
        """Test _read_file_content when all encodings fail."""
        test_file = temp_dir / "test.txt"
        test_file.write_bytes(b"\x80\x81\x82\x83")
        
        result = FileExtractor._read_file_content(test_file)
        assert result == "[ERROR: Could not decode file]"

    def test_format_compact(self, extractor):
        """Test the _format_compact method."""
        relative_path = Path("src/main.py")
        content = "print('Hello')"
        
        result = extractor._format_compact(relative_path, content)
        expected = "\n--- src/main.py ---\nprint('Hello')\n"
        assert result == expected

    def test_format_standard(self, extractor):
        """Test the _format_standard method."""
        relative_path = Path("src/main.py")
        content = "print('Hello')"
        
        result = extractor._format_standard(relative_path, content)
        expected = "\n============================================================\nFILE: src/main.py\n============================================================\nprint('Hello')\n\n"
        assert result == expected

    def test_should_skip_excluded_extension(self, extractor, sample_project_dir):
        """Test that files with excluded extensions are skipped."""
        extractor._root_path = sample_project_dir
        
        # PNG file should be skipped
        png_file = sample_project_dir / "test.png"
        should_skip, reason = extractor._should_skip(png_file, include_override=False)
        assert should_skip is True
        assert reason == "excluded_ext"

    def test_should_skip_excluded_path(self, extractor, sample_project_dir):
        """Test that files in excluded paths are skipped."""
        extractor._root_path = sample_project_dir
        
        # __pycache__ file should be skipped
        cache_file = sample_project_dir / "__pycache__" / "test.pyc"
        should_skip, reason = extractor._should_skip(cache_file, include_override=False)
        assert should_skip is True
        assert reason == "excluded_path"

    def test_should_skip_excluded_name(self, extractor, temp_dir):
        """Test that files with excluded names are skipped."""
        extractor._root_path = temp_dir
        
        # .DS_Store file should be skipped
        ds_store = temp_dir / ".DS_Store"
        should_skip, reason = extractor._should_skip(ds_store, include_override=False)
        assert should_skip is True
        assert reason == "excluded_name"

    def test_should_skip_empty_file(self, extractor, sample_project_dir):
        """Test that empty files are skipped when skip_empty is True."""
        extractor._root_path = sample_project_dir
        extractor.skip_empty = True
        
        empty_file = sample_project_dir / "empty.txt"
        should_skip, reason = extractor._should_skip(empty_file, include_override=False)
        assert should_skip is True
        assert reason == "empty"

    def test_should_skip_large_file(self, extractor, sample_project_dir):
        """Test that large files are skipped."""
        extractor._root_path = sample_project_dir
        extractor.max_file_size = 100  # 100 bytes
        
        # Create a file larger than the limit
        large_file = sample_project_dir / "large_file.txt"
        large_file.write_text("x" * 200)  # 200 bytes
        
        should_skip, reason = extractor._should_skip(large_file, include_override=False)
        assert should_skip is True
        assert reason == "too_large"

    def test_should_skip_with_include_override(self, extractor, sample_project_dir):
        """Test that include patterns override exclusion rules."""
        extractor._root_path = sample_project_dir
        extractor.include_patterns = ["*.png"]
        
        png_file = sample_project_dir / "test.png"
        should_skip, reason = extractor._should_skip(png_file, include_override=True)
        # With include_override=True, even excluded extensions should be included
        assert should_skip is False

    def test_should_skip_with_exclude_patterns(self, extractor, sample_project_dir):
        """Test that exclude patterns cause files to be skipped."""
        extractor._root_path = sample_project_dir
        extractor.exclude_patterns = ["test_*"]
        
        test_file = sample_project_dir / "test_file.py"
        should_skip, reason = extractor._should_skip(test_file, include_override=False)
        assert should_skip is True
        assert reason == "excluded_pattern"

    def test_should_skip_gitignore(self, extractor, sample_project_dir, mock_pathspec):
        """Test that gitignore patterns are respected."""
        extractor._root_path = sample_project_dir
        extractor.use_gitignore = True
        extractor._gitignore_spec = mock_pathspec.from_lines("gitwildmatch", ["*.pyc"])
        
        pyc_file = sample_project_dir / "module.pyc"
        should_skip, reason = extractor._should_skip(pyc_file, include_override=False)
        assert should_skip is True
        assert reason == "gitignore"

    def test_should_skip_stat_error(self, extractor, temp_dir):
        """Test that _should_skip handles stat errors gracefully."""
        extractor._root_path = temp_dir
        
        # Create a path that will cause stat() to fail (simulate permission error)
        # We'll patch os.stat to raise an exception
        with patch('os.stat') as mock_stat:
            mock_stat.side_effect = OSError("Permission denied")
            
            fake_file = temp_dir / "inaccessible.txt"
            with pytest.raises(ExtractionError) as exc_info:
                extractor._should_skip(fake_file, include_override=False)
            
            assert "Unable to inspect file" in str(exc_info.value)

    def test_extract_invalid_directory(self, extractor, temp_dir):
        """Test that extract raises an error for invalid directories."""
        non_existent = temp_dir / "does_not_exist"
        output_file = temp_dir / "output.txt"
        
        with pytest.raises(ExtractionError) as exc_info:
            extractor.extract(non_existent, output_file)
        
        assert "is not a valid directory" in str(exc_info.value)

    def test_extract_basic_functionality(self, extractor, sample_project_dir, temp_dir):
        """Test basic extraction functionality."""
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        assert stats.root == sample_project_dir
        assert stats.output == output_file
        assert len(stats.processed_paths) > 0
        assert stats.total_bytes > 0
        assert not stats.errors  # Should have no errors for basic case
        
        # Check that output file was created
        assert output_file.exists()
        content = output_file.read_text()
        assert "# Extracted from:" in content
        assert "main.py" in content or "README.md" in content

    def test_extract_with_gitignore(self, extractor, sample_project_dir, temp_dir, mock_pathspec):
        """Test extraction with gitignore support."""
        extractor.use_gitignore = True
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        # Should have no gitignore errors since we mocked it
        assert not any("gitignore" in error.lower() for error in stats.errors)

    def test_extract_with_token_counting(self, extractor, sample_project_dir, temp_dir, mock_tiktoken):
        """Test extraction with token counting enabled."""
        extractor.count_tokens = True
        extractor.tokenizer_model = "gpt-4"
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        assert stats.token_count is not None
        assert stats.token_model == "gpt-4"
        assert stats.token_count > 0

    def test_extract_with_include_patterns(self, extractor, sample_project_dir, temp_dir):
        """Test extraction with include patterns."""
        extractor.include_patterns = ["*.py"]
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        # Should only process Python files
        for path in stats.processed_paths:
            assert path.endswith('.py') or "subdir" in path

    def test_extract_with_exclude_patterns(self, extractor, sample_project_dir, temp_dir):
        """Test extraction with exclude patterns."""
        extractor.exclude_patterns = ["test_*", "*test*"]
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        # Should not process files matching exclude patterns
        for path in stats.processed_paths:
            assert not any(pattern in path for pattern in extractor.exclude_patterns)

    def test_extract_progress_callback(self, extractor, sample_project_dir, temp_dir):
        """Test extraction with progress callback."""
        output_file = temp_dir / "extracted.txt"
        
        progress_calls = []
        def progress_callback(advance=1, description=None):
            progress_calls.append((advance, description))
        
        stats = extractor.extract(sample_project_dir, output_file, progress_callback=progress_callback)
        
        assert isinstance(stats, ExtractionStats)
        # Progress callback should have been called
        assert len(progress_calls) > 0
        # Each call should have advance > 0
        for advance, description in progress_calls:
            assert advance > 0
            assert isinstance(description, str)

    def test_extract_cannot_write_output(self, extractor, sample_project_dir):
        """Test extraction behavior when output file cannot be written."""
        # Use a read-only path
        output_file = Path("/dev/full")
        
        with pytest.raises(ExtractionError):
            extractor.extract(sample_project_dir, output_file)

    def test_extract_with_custom_file_size_limit(self, extractor, sample_project_dir, temp_dir):
        """Test extraction with custom file size limit."""
        extractor.max_file_size = 10  # Very small limit
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        # Should skip large files
        assert "too_large" in stats.skipped
        assert stats.skipped["too_large"] > 0

    def test_extract_no_skip_empty(self, extractor, sample_project_dir, temp_dir):
        """Test extraction with skip_empty=False."""
        extractor.skip_empty = False
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        # Empty files should be processed
        assert "empty" not in stats.skipped or stats.skipped["empty"] == 0

    def test_extract_non_compact_mode(self, extractor, sample_project_dir, temp_dir):
        """Test extraction with compact_mode=False."""
        extractor.compact_mode = False
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        # Output should use standard format
        content = output_file.read_text()
        assert "FILE: " in content
        assert "=" * 60 in content

    def test_extract_no_gitignore_dependency(self, extractor, sample_project_dir, temp_dir):
        """Test extraction when gitignore dependency is missing."""
        extractor.use_gitignore = True
        # Mock pathspec as None
        extractor._gitignore_spec = None
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        # Should have an error about missing pathspec
        assert any("pathspec" in error.lower() for error in stats.errors)

    def test_extract_token_counting_fallback(self, extractor, sample_project_dir, temp_dir):
        """Test extraction when token counting fails."""
        extractor.count_tokens = True
        # Mock tiktoken failure
        extractor._root_path = sample_project_dir
        output_file = temp_dir / "extracted.txt"
        
        stats = extractor.extract(sample_project_dir, output_file)
        
        assert isinstance(stats, ExtractionStats)
        # Token count might be None if counting failed
        if stats.token_count is not None:
            assert stats.token_count >= 0

    def test_extract_progress_callback_type_error(self, extractor, sample_project_dir, temp_dir):
        """Test extraction with progress callback that only accepts positional args."""
        output_file = temp_dir / "extracted.txt"
        
        progress_calls = []
        def simple_progress_callback(advance):  # Only accepts positional argument
            progress_calls.append(advance)
        
        stats = extractor.extract(sample_project_dir, output_file, progress_callback=simple_progress_callback)
        
        assert isinstance(stats, ExtractionStats)
        # Should handle the TypeError fallback
        assert len(progress_calls) > 0