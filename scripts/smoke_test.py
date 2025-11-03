"""Quick smoke test for the Proxtract CLI.

The test launches the REPL, exits immediately, and performs a single-file
extraction check using the public API. This script is intended for manual
verification and CI smoke runs.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from proxtract.core import FileExtractor


def _check_repl_launch() -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "proxtract"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = process.communicate("/exit\n", timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("REPL did not exit within timeout") from None

    if process.returncode not in {0, None}:
        raise RuntimeError(f"REPL exited with code {process.returncode}: {stderr}")

    if "Welcome to Proxtract" not in stdout:
        raise RuntimeError("Welcome banner missing from REPL output")


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


def main() -> None:
    _check_repl_launch()
    _check_cli_extract()
    _check_core_extraction()
    print("Smoke test passed. CLI launches and core extraction works.")


if __name__ == "__main__":
    main()
