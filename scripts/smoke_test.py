"""Quick smoke test for the Proxtract interfaces.

The test validates that the CLI help is accessible, performs a single-file
extraction check using the public API, and verifies the command-line extract
subcommand. This script is intended for manual verification and CI smoke runs.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from proxtract.core import FileExtractor


def _check_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "proxtract", "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(f"CLI help failed: {result.stderr or result.stdout}")

    if "extract" not in result.stdout:
        raise RuntimeError("Expected extract subcommand to appear in help output")


def _check_cli_extract() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "sample.txt").write_text("hello cli", encoding="utf-8")
        output = root / "cli_output.txt"

        process = subprocess.Popen(
            [sys.executable, "-m", "proxtract", "extract", str(root), "--output", str(output)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = process.communicate(timeout=15)

        if process.returncode != 0:
            raise RuntimeError(f"CLI extract failed: {stderr or stdout}")

        if not output.exists():
            raise RuntimeError("CLI extract did not produce the expected output file")


def _check_core_extraction() -> None:
    extractor = FileExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sample_file = root / "sample.txt"
        sample_file.write_text("hello proxtract", encoding="utf-8")
        output = root / "output.txt"

        stats = extractor.extract(root, output)

        if stats.processed_files != 1:
            raise RuntimeError("Expected exactly one file processed")

        merged = output.read_text(encoding="utf-8")
        if "hello proxtract" not in merged:
            raise RuntimeError("Extracted content missing from output")


def _check_file_filtering() -> None:
    """Test file filtering logic including extensions, patterns, and file names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create test files
        (root / "python.py").write_text("print('python')", encoding="utf-8")
        (root / "image.png").write_text("fake png content", encoding="utf-8")  # Binary-like
        (root / "document.pdf").write_text("fake pdf content", encoding="utf-8")
        (root / "test.js").write_text("console.log('test');", encoding="utf-8")
        (root / "package.json").write_text('{"name": "test"}', encoding="utf-8")
        (root / "empty.txt").write_text("", encoding="utf-8")  # Empty file
        (root / "large.txt").write_text("x" * (600 * 1024), encoding="utf-8")  # Large file
        
        # Test with custom filtering rules
        extractor = FileExtractor(
            skip_extensions={".pdf", ".png"},  # Skip PDF and PNG files
            skip_files={"package.json"},       # Skip package.json specifically
            skip_patterns={"test_*"},          # Skip files starting with test_
            max_file_size_kb=500,              # 500KB limit
        )
        
        output = root / "filtered_output.txt"
        stats = extractor.extract(root, output)
        
        # Verify filtering worked
        content = output.read_text(encoding="utf-8")
        
        # Should have processed the .py and .js files
        if "python.py" not in content:
            raise RuntimeError("Expected python.py to be processed")
        if "test.js" not in content:
            raise RuntimeError("Expected test.js to be processed (test_* pattern doesn't match .js files)")
        
        # Should have skipped the filtered files
        if "image.png" in content:
            raise RuntimeError("Expected image.png to be skipped")
        if "document.pdf" in content:
            raise RuntimeError("Expected document.pdf to be skipped")
        if "package.json" in content:
            raise RuntimeError("Expected package.json to be skipped")
        if "empty.txt" in content:
            raise RuntimeError("Expected empty.txt to be skipped (empty files)")
        if "large.txt" in content:
            raise RuntimeError("Expected large.txt to be skipped (too large)")
        
        # Verify stats
        if stats.processed_files != 2:
            raise RuntimeError(f"Expected 2 files processed, got {stats.processed_files}")
        
        if stats.skipped.get("excluded_ext", 0) != 2:
            raise RuntimeError(f"Expected 2 files skipped by extension, got {stats.skipped.get('excluded_ext', 0)}")
        
        if stats.skipped.get("excluded_name", 0) != 1:
            raise RuntimeError(f"Expected 1 file skipped by name, got {stats.skipped.get('excluded_name', 0)}")
        
        if stats.skipped.get("empty", 0) != 1:
            raise RuntimeError(f"Expected 1 file skipped as empty, got {stats.skipped.get('empty', 0)}")
        
        if stats.skipped.get("too_large", 0) != 1:
            raise RuntimeError(f"Expected 1 file skipped as too large, got {stats.skipped.get('too_large', 0)}")


def _check_binary_detection() -> None:
    """Test binary file detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create test files with different content types
        text_file = root / "text.txt"
        text_file.write_text("This is a text file", encoding="utf-8")
        
        binary_like_file = root / "binary.xyz"  # Use extension not in default skip list
        # Write PNG signature + some binary content
        binary_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        binary_like_file.write_bytes(binary_content)
        
        # Create a file with high null byte ratio
        null_file = root / "nulls.abc"  # Use extension not in default skip list
        null_file.write_bytes(b'\x00' * 50 + b'text' + b'\x00' * 50)
        
        extractor = FileExtractor()
        output = root / "binary_output.txt"
        stats = extractor.extract(root, output)
        
        content = output.read_text(encoding="utf-8")
        
        # Text file should be processed
        if "text.txt" not in content:
            raise RuntimeError("Expected text.txt to be processed")
        
        # Binary files should be skipped
        if "binary.xyz" in content:
            raise RuntimeError("Expected binary.xyz to be skipped")
        
        if "nulls.abc" in content:
            raise RuntimeError("Expected nulls.abc to be skipped")
        
        # Verify stats
        if stats.skipped.get("binary", 0) != 2:
            raise RuntimeError(f"Expected 2 files skipped as binary, got {stats.skipped.get('binary', 0)}")


def _check_include_patterns() -> None:
    """Test include pattern filtering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create test files with directories
        (root / "src").mkdir()
        (root / "src" / "file.py").write_text("print('python')", encoding="utf-8")
        (root / "docs").mkdir()
        (root / "docs" / "readme.md").write_text("# README", encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests" / "test.py").write_text("def test(): pass", encoding="utf-8")
        
        extractor = FileExtractor(include_patterns=["src/*", "*.md"])
        output = root / "include_output.txt"
        stats = extractor.extract(root, output)
        
        content = output.read_text(encoding="utf-8")
        
        # Should only process included files
        if "src/file.py" not in content:
            raise RuntimeError("Expected src/file.py to be processed (included pattern)")
        if "docs/readme.md" not in content:
            raise RuntimeError("Expected docs/readme.md to be processed (included pattern)")
        
        # Should skip excluded files
        if "tests/test.py" in content:
            raise RuntimeError("Expected tests/test.py to be skipped (not in include patterns)")


def main() -> None:
    print("Running smoke tests...")
    _check_cli_help()
    print("✓ CLI help check passed")
    
    _check_cli_extract()
    print("✓ CLI extract check passed")
    
    _check_core_extraction()
    print("✓ Core extraction check passed")
    
    _check_file_filtering()
    print("✓ File filtering check passed")
    
    _check_binary_detection()
    print("✓ Binary detection check passed")
    
    _check_include_patterns()
    print("✓ Include patterns check passed")
    
    print("All smoke tests passed! CLI launches and all filtering logic works.")


if __name__ == "__main__":
    main()
