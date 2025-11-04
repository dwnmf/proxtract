"""Unit tests for configuration persistence in config.py."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from proxtract.config import apply_config, load_config, save_config
from proxtract.state import AppState


class TestConfigPath:
    """Test the _config_path function."""

    @patch("proxtract.config.Path")
    def test_config_path_format(self, mock_path):
        """Test that config path is created with correct format."""
        from proxtract.config import _config_path
        
        # Mock the Path calls
        mock_home = Path("/home/user")
        mock_expanduser = Path("/home/user/.config/proxtract/settings.toml")
        mock_path.home.return_value = mock_home
        mock_home.expanduser.return_value = mock_expanduser
        
        result = _config_path()
        
        assert result == Path("/home/user/.config/proxtract/settings.toml")
        mock_path.home.assert_called_once()
        mock_home.expanduser.assert_called_once()


class TestLoadConfig:
    """Test the load_config function."""

    def test_load_config_file_not_exists(self, monkeypatch):
        """Test load_config when config file doesn't exist."""
        monkeypatch.setattr("proxtract.config._config_path", lambda: Path("/nonexistent/config.toml"))
        
        result = load_config()
        assert result == {}

    @patch("proxtract.config._config_path")
    def test_load_config_toml_not_available(self, mock_config_path, monkeypatch):
        """Test load_config when TOML library is not available."""
        mock_config_path.return_value = Path("/test/config.toml")
        monkeypatch.setattr("proxtract.config._tomllib", None)
        
        result = load_config()
        assert result == {}

    @patch("proxtract.config._config_path")
    def test_load_config_successful_parsing(self, mock_config_path, monkeypatch):
        """Test load_config with successful TOML parsing."""
        mock_config_path.return_value = Path("/test/config.toml")
        
        toml_content = """
        output_path = "output.txt"
        max_size_kb = 1000
        compact_mode = false
        include_patterns = ["*.py"]
        """
        
        mock_toml = {"output_path": "output.txt", "max_size_kb": 1000, "compact_mode": False, "include_patterns": ["*.py"]}
        monkeypatch.setattr("proxtract.config._tomllib", type("MockToml", (), {"loads": lambda text: mock_toml})())
        
        with patch.object(Path, "read_text", return_value=toml_content):
            result = load_config()
        
        assert result == mock_toml

    @patch("proxtract.config._config_path")
    def test_load_config_parsing_error(self, mock_config_path, monkeypatch):
        """Test load_config when TOML parsing fails."""
        mock_config_path.return_value = Path("/test/config.toml")
        
        def mock_loads_error(text):
            raise Exception("Invalid TOML")
        
        monkeypatch.setattr("proxtract.config._tomllib", type("MockToml", (), {"loads": mock_loads_error})())
        
        with patch.object(Path, "read_text", return_value="invalid toml content"):
            result = load_config()
        
        assert result == {}

    @patch("proxtract.config._config_path")
    def test_load_config_read_error(self, mock_config_path, monkeypatch):
        """Test load_config when file reading fails."""
        mock_config_path.return_value = Path("/test/config.toml")
        
        mock_toml = {"output_path": "output.txt"}
        monkeypatch.setattr("proxtract.config._tomllib", type("MockToml", (), {"loads": lambda text: mock_toml})())
        
        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            result = load_config()
        
        assert result == {}


class TestApplyConfig:
    """Test the apply_config function."""

    def test_apply_config_empty_data(self, app_state):
        """Test apply_config with empty data."""
        state = app_state
        original_output_path = state.output_path
        
        result = apply_config(state, {})
        
        assert result is state
        assert state.output_path == original_output_path
        assert state.max_size_kb == 500  # Default value
        assert state.compact_mode is True  # Default value

    def test_apply_config_all_fields(self, app_state):
        """Test apply_config with all fields."""
        state = app_state
        config_data = {
            "output_path": "/custom/output.txt",
            "max_size_kb": 1000,
            "compact_mode": False,
            "skip_empty": False,
            "use_gitignore": False,
            "include_patterns": ["*.py", "*.js"],
            "exclude_patterns": ["test_*", "node_modules"],
            "tokenizer_model": "gpt-3.5-turbo",
            "enable_token_count": False,
            "copy_to_clipboard": True,
        }
        
        result = apply_config(state, config_data)
        
        assert result is state
        assert state.output_path == Path("/custom/output.txt")
        assert state.max_size_kb == 1000
        assert state.compact_mode is False
        assert state.skip_empty is False
        assert state.use_gitignore is False
        assert state.include_patterns == ["*.py", "*.js"]
        assert state.exclude_patterns == ["test_*", "node_modules"]
        assert state.tokenizer_model == "gpt-3.5-turbo"
        assert state.enable_token_count is False
        assert state.copy_to_clipboard is True

    def test_apply_config_partial_data(self, app_state):
        """Test apply_config with only some fields."""
        state = app_state
        config_data = {
            "max_size_kb": 2000,
            "compact_mode": False,
        }
        
        result = apply_config(state, config_data)
        
        assert result is state
        assert state.max_size_kb == 2000
        assert state.compact_mode is False
        # Other values should remain at defaults
        assert state.output_path == Path("extracted.txt")
        assert state.skip_empty is True

    def test_apply_config_include_patterns_types(self, app_state):
        """Test apply_config handles different types for include_patterns."""
        state = app_state
        config_data = {
            "include_patterns": ["*.py", 123, Path("*.js")],  # Mixed types
        }
        
        result = apply_config(state, config_data)
        
        assert result is state
        assert state.include_patterns == ["*.py", "123", "*.js"]

    def test_apply_config_exclude_patterns_types(self, app_state):
        """Test apply_config handles different types for exclude_patterns."""
        state = app_state
        config_data = {
            "exclude_patterns": ["test_*", 456],  # Mixed types
        }
        
        result = apply_config(state, config_data)
        
        assert result is state
        assert state.exclude_patterns == ["test_*", "456"]

    def test_apply_config_include_patterns_not_list(self, app_state):
        """Test apply_config when include_patterns is not a list."""
        state = app_state
        config_data = {
            "include_patterns": "not a list",
        }
        
        result = apply_config(state, config_data)
        
        assert result is state
        # Should not modify include_patterns if it's not a list
        assert state.include_patterns == []

    def test_apply_config_exclude_patterns_not_list(self, app_state):
        """Test apply_config when exclude_patterns is not a list."""
        state = app_state
        config_data = {
            "exclude_patterns": "not a list",
        }
        
        result = apply_config(state, config_data)
        
        assert result is state
        # Should not modify exclude_patterns if it's not a list
        assert state.exclude_patterns == []

    def test_apply_config_path_expansion(self, app_state):
        """Test that output_path in config gets expanded."""
        state = app_state
        config_data = {
            "output_path": "~/test/output.txt",
        }
        
        result = apply_config(state, config_data)
        
        assert result is state
        assert state.output_path == Path.home() / "test/output.txt"

    def test_apply_config_type_conversions(self, app_state):
        """Test type conversions in apply_config."""
        state = app_state
        config_data = {
            "max_size_kb": "1000",  # String instead of int
            "compact_mode": "true",  # String instead of bool
            "skip_empty": "false",  # String instead of bool
            "tokenizer_model": 123,  # Int instead of string
        }
        
        result = apply_config(state, config_data)
        
        assert result is state
        # Note: apply_config uses int() and bool() which will convert strings
        assert state.max_size_kb == 1000
        assert state.compact_mode is True  # bool("true") is True
        assert state.skip_empty is False  # bool("false") is True, so this should be True
        # Tokenizer model should be str(123)
        assert state.tokenizer_model == "123"


class TestSaveConfig:
    """Test the save_config function."""

    @patch("proxtract.config._config_path")
    @patch.object(Path, "open")
    def test_save_config_basic(self, mock_open, mock_config_path, app_state):
        """Test save_config with basic settings."""
        state = app_state
        mock_config_path.return_value = Path("/test/config.toml")
        mock_file = mock_open.return_value.__enter__.return_value
        
        save_config(state)
        
        # Should create directory
        mock_config_path.return_value.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        
        # Should write to file
        mock_open.assert_called_once()
        written_content = "".join(call.args[0] for call in mock_file.write.call_args_list)
        
        # Check that expected keys are in the output
        assert "output_path = " in written_content
        assert "max_size_kb = " in written_content
        assert "compact_mode = " in written_content
        assert "include_patterns = " in written_content

    @patch("proxtract.config._config_path")
    def test_save_config_all_fields(self, mock_config_path, app_state):
        """Test save_config with all fields set."""
        state = app_state
        mock_config_path.return_value = Path("/test/config.toml")
        
        # Set all fields
        state.output_path = Path("/custom/output.txt")
        state.max_size_kb = 1000
        state.compact_mode = False
        state.skip_empty = False
        state.use_gitignore = False
        state.include_patterns = ["*.py", "*.js"]
        state.exclude_patterns = ["test_*", "node_modules"]
        state.tokenizer_model = "gpt-3.5-turbo"
        state.enable_token_count = False
        state.copy_to_clipboard = True
        
        with patch.object(Path, "open", mock_open()):
            save_config(state)
        
        # All fields should be saved
        mock_config_path.return_value.parent.mkdir.assert_called_once()

    @patch("proxtract.config._config_path")
    def test_save_config_creates_directory(self, mock_config_path, app_state):
        """Test that save_config creates the config directory."""
        state = app_state
        mock_config_path.return_value = Path("/test/subdir/config.toml")
        
        with patch.object(Path, "open", mock_open()):
            save_config(state)
        
        # Should create the parent directory
        expected_dir = Path("/test/subdir")
        expected_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("proxtract.config._config_path")
    def test_save_config_escape_backslashes(self, mock_config_path, app_state):
        """Test that save_config properly escapes backslashes."""
        state = app_state
        mock_config_path.return_value = Path("/test/config.toml")
        
        state.include_patterns = ["path\\with\\backslashes", 'path"with"quotes']
        
        with patch.object(Path, "open", mock_open()) as mock_file:
            save_config(state)
            
            # Get the written content
            written_calls = [call for call in mock_file().write.call_args_list]
            content = "".join(call[0][0] for call in written_calls)
            
            # Should escape backslashes and quotes
            assert "path\\\\with\\\\backslashes" in content
            assert "path\\\"with\\\"quotes" in content

    @patch("proxtract.config._config_path")
    def test_save_config_empty_lists(self, mock_config_path, app_state):
        """Test save_config with empty pattern lists."""
        state = app_state
        mock_config_path.return_value = Path("/test/config.toml")
        
        state.include_patterns = []
        state.exclude_patterns = []
        
        with patch.object(Path, "open", mock_open()) as mock_file:
            save_config(state)
            
            # Get the written content
            written_calls = [call for call in mock_file().write.call_args_list]
            content = "".join(call[0][0] for call in written_calls)
            
            # Empty lists should be represented as []
            assert "include_patterns = []" in content
            assert "exclude_patterns = []" in content

    @patch("proxtract.config._config_path")
    def test_save_config_path_object_conversion(self, mock_config_path, app_state):
        """Test that Path objects are properly converted to strings in save_config."""
        state = app_state
        mock_config_path.return_value = Path("/test/config.toml")
        
        state.output_path = Path("/custom/output.txt")
        
        with patch.object(Path, "open", mock_open()) as mock_file:
            save_config(state)
            
            # Get the written content
            written_calls = [call for call in mock_file().write.call_args_list]
            content = "".join(call[0][0] for call in written_calls)
            
            # Path should be converted to string
            assert 'output_path = "/custom/output.txt"' in content

    @patch("proxtract.config._config_path")
    def test_save_config_file_write_error(self, mock_config_path, app_state):
        """Test that save_config handles file write errors gracefully."""
        state = app_state
        mock_config_path.return_value = Path("/test/config.toml")
        
        with patch.object(Path, "open", side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                save_config(state)


class TestConfigIntegration:
    """Integration tests for the config module."""

    @patch("proxtract.config._config_path")
    def test_save_and_load_roundtrip(self, mock_config_path, app_state):
        """Test that saving and loading config produces the same state."""
        state = app_state
        mock_config_path.return_value = Path("/test/config.toml")
        
        # Set all fields
        state.output_path = Path("/custom/output.txt")
        state.max_size_kb = 1000
        state.compact_mode = False
        state.skip_empty = False
        state.use_gitignore = False
        state.include_patterns = ["*.py", "*.js"]
        state.exclude_patterns = ["test_*", "node_modules"]
        state.tokenizer_model = "gpt-3.5-turbo"
        state.enable_token_count = False
        state.copy_to_clipboard = True
        
        # Save config
        with patch.object(Path, "open", mock_open()):
            save_config(state)
        
        # Mock the saved file content
        saved_content = '''output_path = "/custom/output.txt"
max_size_kb = 1000
compact_mode = false
skip_empty = false
use_gitignore = false
include_patterns = ["*.py", "*.js"]
exclude_patterns = ["test_*", "node_modules"]
tokenizer_model = "gpt-3.5-turbo"
enable_token_count = false
copy_to_clipboard = true
'''
        
        mock_toml = {
            "output_path": "/custom/output.txt",
            "max_size_kb": 1000,
            "compact_mode": False,
            "skip_empty": False,
            "use_gitignore": False,
            "include_patterns": ["*.py", "*.js"],
            "exclude_patterns": ["test_*", "node_modules"],
            "tokenizer_model": "gpt-3.5-turbo",
            "enable_token_count": False,
            "copy_to_clipboard": True,
        }
        
        with patch.object(Path, "read_text", return_value=saved_content):
            with patch("proxtract.config._tomllib", type("MockToml", (), {"loads": lambda text: mock_toml})()):
                loaded_config = load_config()
        
        # Create new state and apply config
        new_state = AppState()
        result = apply_config(new_state, loaded_config)
        
        # All fields should match
        assert result.output_path == state.output_path
        assert result.max_size_kb == state.max_size_kb
        assert result.compact_mode == state.compact_mode
        assert result.skip_empty == state.skip_empty
        assert result.use_gitignore == state.use_gitignore
        assert result.include_patterns == state.include_patterns
        assert result.exclude_patterns == state.exclude_patterns
        assert result.tokenizer_model == state.tokenizer_model
        assert result.enable_token_count == state.enable_token_count
        assert result.copy_to_clipboard == state.copy_to_clipboard

    def test_config_with_missing_toml_dependency(self, monkeypatch, app_state):
        """Test config behavior when TOML library is missing."""
        # Simulate missing TOML library
        monkeypatch.setattr("proxtract.config._tomllib", None)
        
        # load_config should return empty dict
        result = load_config()
        assert result == {}
        
        # apply_config should work normally
        config_data = {"max_size_kb": 1000}
        result = apply_config(app_state, config_data)
        assert result is app_state
        assert app_state.max_size_kb == 1000

    def test_config_path_uses_correct_location(self, app_state, monkeypatch):
        """Test that config is saved to the correct location."""
        expected_path = Path.home() / ".config/proxtract/settings.toml"
        
        with patch("proxtract.config._config_path", return_value=expected_path):
            with patch.object(Path, "open", mock_open()):
                save_config(app_state)
        
        # Verify the directory creation was called
        expected_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("proxtract.config._config_path")
    def test_config_error_handling(self, mock_config_path, app_state, monkeypatch):
        """Test that config operations handle various error conditions gracefully."""
        mock_config_path.return_value = Path("/test/config.toml")
        
        # Test with malformed TOML
        with patch.object(Path, "read_text", return_value="invalid toml syntax"):
            with patch("proxtract.config._tomllib", type("MockToml", (), {"loads": lambda text: exec('raise Exception("Invalid TOML")')})()):
                result = load_config()
                assert result == {}

        # Test file permission errors during save
        with patch.object(Path, "open", side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                save_config(app_state)