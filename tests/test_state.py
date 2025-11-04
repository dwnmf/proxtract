"""Unit tests for the AppState class in state.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from proxtract.core import FileExtractor
from proxtract.state import AppState


class TestAppState:
    """Test the AppState class."""

    def test_default_initialization(self, app_state):
        """Test AppState initialization with default values."""
        state = app_state
        
        assert state.output_path == Path("extracted.txt")
        assert state.max_size_kb == 500
        assert state.compact_mode is True
        assert state.skip_empty is True
        assert state.use_gitignore is True
        assert state.include_patterns == []
        assert state.exclude_patterns == []
        assert state.tokenizer_model == "gpt-4"
        assert state.enable_token_count is True
        assert state.copy_to_clipboard is False
        assert state.last_stats is None

    def test_custom_initialization(self):
        """Test AppState initialization with custom values."""
        state = AppState(
            output_path=Path("custom_output.txt"),
            max_size_kb=1000,
            compact_mode=False,
            skip_empty=False,
            use_gitignore=False,
            include_patterns=["*.py"],
            exclude_patterns=["test_*"],
            tokenizer_model="gpt-3.5-turbo",
            enable_token_count=False,
            copy_to_clipboard=True
        )
        
        assert state.output_path == Path("custom_output.txt")
        assert state.max_size_kb == 1000
        assert state.compact_mode is False
        assert state.skip_empty is False
        assert state.use_gitignore is False
        assert state.include_patterns == ["*.py"]
        assert state.exclude_patterns == ["test_*"]
        assert state.tokenizer_model == "gpt-3.5-turbo"
        assert state.enable_token_count is False
        assert state.copy_to_clipboard is True
        assert state.last_stats is None

    def test_create_extractor_default_settings(self, app_state):
        """Test that create_extractor uses current state values."""
        state = app_state
        extractor = state.create_extractor()
        
        assert isinstance(extractor, FileExtractor)
        assert extractor.max_file_size == state.max_size_kb * 1024
        assert extractor.skip_empty == state.skip_empty
        assert extractor.compact_mode == state.compact_mode
        assert extractor.use_gitignore == state.use_gitignore
        assert extractor.include_patterns == tuple(state.include_patterns)
        assert extractor.exclude_patterns == tuple(state.exclude_patterns)
        assert extractor.tokenizer_model == state.tokenizer_model
        assert extractor.count_tokens == state.enable_token_count

    def test_create_extractor_modified_state(self, app_state):
        """Test that create_extractor reflects state changes."""
        state = app_state
        # Modify state
        state.max_size_kb = 1000
        state.compact_mode = False
        state.skip_empty = False
        state.use_gitignore = False
        state.include_patterns = ["*.py", "*.js"]
        state.exclude_patterns = ["node_modules", "*.min.js"]
        state.tokenizer_model = "cl100k_base"
        state.enable_token_count = False
        
        extractor = state.create_extractor()
        
        assert extractor.max_file_size == 1000 * 1024
        assert extractor.compact_mode is False
        assert extractor.skip_empty is False
        assert extractor.use_gitignore is False
        assert extractor.include_patterns == ("*.py", "*.js")
        assert extractor.exclude_patterns == ("node_modules", "*.min.js")
        assert extractor.tokenizer_model == "cl100k_base"
        assert extractor.count_tokens is False

    def test_set_output_path_string(self, app_state):
        """Test setting output path with string."""
        state = app_state
        state.set_output_path("custom/output.txt")
        assert state.output_path == Path("custom/output.txt")

    def test_set_output_path_path_object(self, app_state):
        """Test setting output path with Path object."""
        state = app_state
        path = Path("custom/output.txt")
        state.set_output_path(path)
        assert state.output_path == path

    def test_set_output_path_expands_tilde(self, app_state):
        """Test that set_output_path expands home directory."""
        state = app_state
        state.set_output_path("~/test/output.txt")
        expected = Path.home() / "test/output.txt"
        assert state.output_path == expected

    def test_set_patterns_include_only(self, app_state):
        """Test setting include patterns only."""
        state = app_state
        state.set_patterns(include=["*.py", "*.js"])
        
        assert state.include_patterns == ["*.py", "*.js"]
        assert state.exclude_patterns == []  # Should remain unchanged

    def test_set_patterns_exclude_only(self, app_state):
        """Test setting exclude patterns only."""
        state = app_state
        state.set_patterns(exclude=["test_*", "*.min.js"])
        
        assert state.include_patterns == []  # Should remain unchanged
        assert state.exclude_patterns == ["test_*", "*.min.js"]

    def test_set_patterns_both(self, app_state):
        """Test setting both include and exclude patterns."""
        state = app_state
        state.set_patterns(
            include=["*.py", "*.js"],
            exclude=["test_*", "node_modules"]
        )
        
        assert state.include_patterns == ["*.py", "*.js"]
        assert state.exclude_patterns == ["test_*", "node_modules"]

    def test_set_patterns_with_generators(self, app_state):
        """Test setting patterns with generator expressions."""
        state = app_state
        include_gen = (f"*.{ext}" for ext in ["py", "js", "ts"])
        exclude_gen = (f"test_{i}" for i in range(3))
        
        state.set_patterns(include=include_gen, exclude=exclude_gen)
        
        assert state.include_patterns == ["*.py", "*.js", "*.ts"]
        assert state.exclude_patterns == ["test_0", "test_1", "test_2"]

    def test_set_patterns_converts_to_strings(self, app_state):
        """Test that pattern values are converted to strings."""
        state = app_state
        # Test with non-string objects that have __str__
        state.set_patterns(
            include=[Path("*.py")],  # Path object
            exclude=[123]  # Integer
        )
        
        assert state.include_patterns == ["*.py"]
        assert state.exclude_patterns == ["123"]

    def test_set_patterns_none_values(self, app_state):
        """Test that None values for patterns don't change state."""
        state = app_state
        state.include_patterns = ["*.py"]
        state.exclude_patterns = ["test_*"]
        
        state.set_patterns(include=None, exclude=None)
        
        # Should remain unchanged
        assert state.include_patterns == ["*.py"]
        assert state.exclude_patterns == ["test_*"]

    def test_last_stats_property(self, app_state):
        """Test that last_stats can be set and retrieved."""
        state = app_state
        # Initially None
        assert state.last_stats is None
        
        # Can be set to any value
        from proxtract.core import ExtractionStats
        fake_stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=[],
            total_bytes=0,
            skipped_paths={},
            errors=[]
        )
        
        state.last_stats = fake_stats
        assert state.last_stats == fake_stats

    def test_field_defaults_are_fresh(self):
        """Test that field defaults are fresh instances for each instance."""
        state1 = AppState()
        state2 = AppState()
        
        # Modify one state's list
        state1.include_patterns.append("*.py")
        
        # The other should not be affected
        assert state2.include_patterns == []
        assert state1.include_patterns == ["*.py"]

    def test_output_path_default_factory(self):
        """Test that output_path uses a default factory."""
        state1 = AppState()
        state2 = AppState()
        
        # Modify one instance's output path
        state1.output_path = Path("custom.txt")
        
        # The other should still have the default
        assert state2.output_path == Path("extracted.txt")
        assert state1.output_path == Path("custom.txt")

    @pytest.mark.parametrize("max_size_kb,expected_bytes", [
        (100, 100 * 1024),
        (500, 500 * 1024),
        (1000, 1000 * 1024),
        (1, 1 * 1024),
        (0, 0),  # Edge case
    ])
    def test_create_extractor_respects_max_size(self, max_size_kb, expected_bytes):
        """Test that create_extractor correctly converts max_size_kb to bytes."""
        state = AppState(max_size_kb=max_size_kb)
        extractor = state.create_extractor()
        
        assert extractor.max_file_size == expected_bytes

    def test_create_extractor_multiple_calls(self, app_state):
        """Test that create_extractor can be called multiple times."""
        state = app_state
        # Create first extractor
        extractor1 = state.create_extractor()
        
        # Modify state
        state.max_size_kb = 1000
        state.compact_mode = False
        
        # Create second extractor
        extractor2 = state.create_extractor()
        
        # They should reflect different state values
        assert extractor1.max_file_size == 500 * 1024
        assert extractor2.max_file_size == 1000 * 1024
        assert extractor1.compact_mode is True
        assert extractor2.compact_mode is False

    def test_comprehensive_state_update_workflow(self, app_state):
        """Test a comprehensive workflow of state updates."""
        state = app_state
        # Set various configuration options
        state.set_output_path("~/projects/extracted.txt")
        state.max_size_kb = 2000
        state.compact_mode = False
        state.skip_empty = False
        state.use_gitignore = True
        state.set_patterns(
            include=["*.py", "*.js", "*.ts"],
            exclude=["test_*", "node_modules", "dist/*"]
        )
        state.tokenizer_model = "gpt-3.5-turbo"
        state.enable_token_count = True
        state.copy_to_clipboard = True
        
        # Create extractor and verify all settings
        extractor = state.create_extractor()
        
        assert state.output_path == Path.home() / "projects/extracted.txt"
        assert extractor.max_file_size == 2000 * 1024
        assert extractor.compact_mode is False
        assert extractor.skip_empty is False
        assert extractor.use_gitignore is True
        assert extractor.include_patterns == ("*.py", "*.js", "*.ts")
        assert extractor.exclude_patterns == ("test_*", "node_modules", "dist/*")
        assert extractor.tokenizer_model == "gpt-3.5-turbo"
        assert extractor.count_tokens is True

    def test_path_expansion_consistency(self, app_state):
        """Test that path expansion is consistent."""
        state = app_state
        # Test various path formats
        paths = [
            "output.txt",
            "./output.txt",
            "subdir/output.txt",
            "~/output.txt",
            "../output.txt"
        ]
        
        for path_str in paths:
            state.set_output_path(path_str)
            # Should always be a Path object and expanded
            assert isinstance(state.output_path, Path)
            if path_str.startswith("~/"):
                assert state.output_path.is_absolute()

    def test_list_modification_independence(self, app_state):
        """Test that modifying pattern lists doesn't affect other instances."""
        state1 = AppState()
        state2 = AppState()
        
        # Modify state1's lists
        state1.include_patterns.append("*.py")
        state1.exclude_patterns.append("test_*")
        
        # state2 should be unaffected
        assert state2.include_patterns == []
        assert state2.exclude_patterns == []

    def test_typing_and_serialization_compatibility(self, app_state):
        """Test that state values are compatible with common serialization formats."""
        state = app_state
        # Set all fields to various values
        state.set_output_path("output.txt")
        state.max_size_kb = 1000
        state.compact_mode = True
        state.skip_empty = True
        state.use_gitignore = True
        state.set_patterns(include=["*.py"], exclude=["test_*"])
        state.tokenizer_model = "gpt-4"
        state.enable_token_count = True
        state.copy_to_clipboard = False
        
        # All values should be JSON-serializable
        import json
        try:
            json.dumps({
                "output_path": str(state.output_path),
                "max_size_kb": state.max_size_kb,
                "compact_mode": state.compact_mode,
                "skip_empty": state.skip_empty,
                "use_gitignore": state.use_gitignore,
                "include_patterns": state.include_patterns,
                "exclude_patterns": state.exclude_patterns,
                "tokenizer_model": state.tokenizer_model,
                "enable_token_count": state.enable_token_count,
                "copy_to_clipboard": state.copy_to_clipboard,
            })
        except TypeError as e:
            pytest.fail(f"State contains non-serializable values: {e}")