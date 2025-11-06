"""Unit tests for configuration loading and saving."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import json

from proxtract.config import load_config, apply_config, save_config, _config_path
from proxtract.state import AppState


class TestConfigPath:
    """Test config path generation."""

    def test_config_path_default(self):
        """Test default config path generation."""
        config_path = _config_path()
        assert config_path.name == "settings.toml"
        assert "proxtract" in str(config_path)
        assert config_path.expanduser().exists() or str(config_path).startswith("~/")


class TestLoadConfig:
    """Test configuration loading."""

    def test_load_config_empty_when_file_not_exists(self):
        """Test loading config when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = Path(tmpdir) / "nonexistent.toml"
                
                config = load_config()
                assert config == {}

    def test_load_config_empty_when_toml_not_available(self):
        """Test loading config when TOML library is not available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "settings.toml"
            config_file.write_text('key = "value"', encoding="utf-8")
            
            with patch('proxtract.config._tomllib', None):
                config = load_config()
                assert config == {}

    def test_load_config_invalid_toml(self):
        """Test loading config with invalid TOML content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "settings.toml"
            config_file.write_text('invalid toml content [}', encoding="utf-8")
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_file
                
                config = load_config()
                assert config == {}

    def test_load_config_valid_toml(self):
        """Test loading config with valid TOML content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "settings.toml"
            toml_content = '''
output_path = "test.txt"
max_size_kb = 1000
compact_mode = false
skip_empty = false
use_gitignore = false
include_patterns = ["*.py", "src/*"]
exclude_patterns = ["*.log", "test_*"]
skip_extensions = [".pdf", ".png"]
skip_patterns = ["__pycache__", ".git"]
skip_files = ["package.json", "requirements.txt"]
tokenizer_model = "gpt-3.5-turbo"
enable_token_count = false
copy_to_clipboard = true
force_include = true
'''
            config_file.write_text(toml_content, encoding="utf-8")
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_file
                
                config = load_config()
                
                assert config["output_path"] == "test.txt"
                assert config["max_size_kb"] == 1000
                assert config["compact_mode"] is False
                assert config["skip_empty"] is False
                assert config["use_gitignore"] is False
                assert config["include_patterns"] == ["*.py", "src/*"]
                assert config["exclude_patterns"] == ["*.log", "test_*"]
                assert config["skip_extensions"] == [".pdf", ".png"]
                assert config["skip_patterns"] == ["__pycache__", ".git"]
                assert config["skip_files"] == ["package.json", "requirements.txt"]
                assert config["tokenizer_model"] == "gpt-3.5-turbo"
                assert config["enable_token_count"] is False
                assert config["copy_to_clipboard"] is True
                assert config["force_include"] is True

    def test_load_config_partial_config(self):
        """Test loading config with only some settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "settings.toml"
            toml_content = '''
output_path = "custom.txt"
max_size_kb = 2000
compact_mode = true
'''
            config_file.write_text(toml_content, encoding="utf-8")
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_file
                
                config = load_config()
                
                assert config["output_path"] == "custom.txt"
                assert config["max_size_kb"] == 2000
                assert config["compact_mode"] is True
                # Other settings should not be present
                assert "skip_empty" not in config


class TestApplyConfig:
    """Test configuration application to AppState."""

    def test_apply_config_empty_data(self):
        """Test applying empty config data."""
        state = AppState()
        original_output = state.output_path
        original_max_size = state.max_size_kb
        
        result = apply_config(state, {})
        
        assert result is state
        assert state.output_path == original_output
        assert state.max_size_kb == original_max_size

    def test_apply_config_basic_settings(self):
        """Test applying basic configuration settings."""
        state = AppState()
        
        config_data = {
            "output_path": "custom_output.txt",
            "max_size_kb": 1500,
            "compact_mode": False,
            "skip_empty": False,
            "use_gitignore": False,
            "force_include": True,
        }
        
        result = apply_config(state, config_data)
        
        assert result is state
        assert state.output_path == Path("custom_output.txt").expanduser()
        assert state.max_size_kb == 1500
        assert state.compact_mode is False
        assert state.skip_empty is False
        assert state.use_gitignore is False
        assert state.force_include is True

    def test_apply_config_boolean_strings(self):
        """Test applying boolean settings from string values."""
        state = AppState()

        config_data = {
            "compact_mode": "false",
            "skip_empty": "no",
            "use_gitignore": "0",
            "enable_token_count": "False",
            "copy_to_clipboard": "yes",
            "force_include": "1",
        }

        apply_config(state, config_data)

        assert state.compact_mode is False
        assert state.skip_empty is False
        assert state.use_gitignore is False
        assert state.enable_token_count is False
        assert state.copy_to_clipboard is True
        assert state.force_include is True

    def test_apply_config_include_patterns(self):
        """Test applying include patterns configuration."""
        state = AppState()
        
        config_data = {
            "include_patterns": ["*.py", "src/*", "docs/*.md"],
            "exclude_patterns": ["*.log", "test_*", "node_modules/*"],
        }
        
        apply_config(state, config_data)
        
        assert state.include_patterns == ["*.py", "src/*", "docs/*.md"]
        assert state.exclude_patterns == ["*.log", "test_*", "node_modules/*"]

    def test_apply_config_filtering_rules(self):
        """Test applying filtering rules configuration."""
        state = AppState()
        
        config_data = {
            "skip_extensions": [".pdf", ".png", ".jpg"],
            "skip_patterns": ["__pycache__", ".git", "test_*"],
            "skip_files": ["package.json", "requirements.txt", "Dockerfile"],
        }
        
        apply_config(state, config_data)
        
        assert state.skip_extensions == {".pdf", ".png", ".jpg"}
        assert state.skip_patterns == {"__pycache__", ".git", "test_*"}
        assert state.skip_files == {"package.json", "requirements.txt", "Dockerfile"}

    def test_apply_config_disable_filters(self):
        """Empty collections should disable custom filters."""
        state = AppState()

        config_data = {
            "skip_extensions": [],
            "skip_patterns": [],
            "skip_files": [],
        }

        apply_config(state, config_data)

        assert state.skip_extensions == set()
        assert state.skip_patterns == set()
        assert state.skip_files == set()

    def test_apply_config_tokenizer_settings(self):
        """Test applying tokenizer configuration."""
        state = AppState()
        
        config_data = {
            "tokenizer_model": "gpt-3.5-turbo",
            "enable_token_count": False,
            "copy_to_clipboard": True,
        }
        
        apply_config(state, config_data)
        
        assert state.tokenizer_model == "gpt-3.5-turbo"
        assert state.enable_token_count is False
        assert state.copy_to_clipboard is True

    def test_apply_config_path_expansion(self):
        """Test that output paths are properly expanded."""
        state = AppState()
        
        config_data = {
            "output_path": "~/documents/output.txt",
        }
        
        apply_config(state, config_data)
        
        # Should expand user home directory
        assert str(state.output_path).startswith(str(Path.home()))

    def test_apply_config_invalid_data_types(self):
        """Test handling of invalid data types in config."""
        state = AppState()
        
        config_data = {
            "max_size_kb": "invalid",  # Should be int
            "compact_mode": "not_bool",  # Should be bool
            "include_patterns": "not_list",  # Should be list
        }
        
        # Should handle gracefully without crashing
        apply_config(state, config_data)
        
        # Invalid values should fall back to defaults
        assert state.max_size_kb == 500  # Default
        assert state.compact_mode is True  # Default
        assert state.include_patterns == []  # Default


class TestSaveConfig:
    """Test configuration saving."""

    def test_save_config_create_directory(self):
        """Test that save_config creates necessary directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested" / "config" / "settings.toml"
            
            state = AppState()
            state.output_path = "test.txt"
            state.max_size_kb = 1000
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_path
                
                save_config(state)
                
                assert config_path.parent.exists()

    def test_save_config_with_tomli_w(self):
        """Test saving config with tomli_w library."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.toml"
            
            state = AppState()
            state.output_path = "test.txt"
            state.max_size_kb = 1000
            state.compact_mode = False
            state.skip_extensions = {".pdf", ".png"}
            state.skip_patterns = {"__pycache__"}
            state.skip_files = {"package.json"}
            state.force_include = True
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_path
                # Mock tomli_w being available
                with patch('proxtract.config._tomli_w') as mock_tomli_w:
                    mock_tomli_w.dump = lambda data, handle: handle.write(b"mocked toml")
                    
                    save_config(state)
                    
                    # Should have created the file
                    assert config_path.exists()

    def test_save_config_fallback_manual(self):
        """Test saving config with manual construction fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.toml"
            
            state = AppState()
            state.output_path = "test.txt"
            state.max_size_kb = 1000
            state.compact_mode = False
            state.skip_empty = True
            state.use_gitignore = True
            state.include_patterns = ["*.py"]
            state.exclude_patterns = ["*.log"]
            state.skip_extensions = {".pdf"}
            state.skip_patterns = {"__pycache__"}
            state.skip_files = {"package.json"}
            state.tokenizer_model = "gpt-4"
            state.enable_token_count = True
            state.copy_to_clipboard = False
            state.force_include = True
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_path
                # Mock tomli_w being unavailable
                with patch('proxtract.config._tomli_w', None):
                    save_config(state)
                    
                    # Should have created the file with manual construction
                    assert config_path.exists()
                    content = config_path.read_text(encoding="utf-8")
                    
                    # Check that all values are present
                    assert 'output_path = "test.txt"' in content
                    assert 'max_size_kb = 1000' in content
                    assert 'compact_mode = false' in content
                    assert 'skip_empty = true' in content
                    assert 'use_gitignore = true' in content
                    assert 'include_patterns = ["*.py"]' in content
                    assert 'exclude_patterns = ["*.log"]' in content
                    assert 'skip_extensions = [".pdf"]' in content
                    assert 'skip_patterns = ["__pycache__"]' in content
                    assert 'skip_files = ["package.json"]' in content
                    assert 'tokenizer_model = "gpt-4"' in content
                    assert 'enable_token_count = true' in content
                    assert 'copy_to_clipboard = false' in content
                    assert 'force_include = true' in content

    def test_save_config_string_escaping(self):
        """Test proper escaping of strings in manual construction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.toml"
            
            state = AppState()
            state.output_path = 'test"with"quotes.txt'
            state.tokenizer_model = 'model\\with\\backslashes'
            state.include_patterns = ['pattern"with"quotes', 'path\\with\\backslashes']
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_path
                with patch('proxtract.config._tomli_w', None):
                    save_config(state)
                    
                    content = config_path.read_text(encoding="utf-8")
                    
                    # Check proper escaping
                    assert 'test\\"with\\"quotes.txt' in content
                    assert 'model\\\\with\\\\backslashes' in content
                    assert 'pattern\\"with\\"quotes' in content
                    assert 'path\\\\with\\\\backslashes' in content

    def test_save_config_missing_attributes(self):
        """Test saving config when state doesn't have all attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.toml"
            
            # Create a minimal state without filtering attributes
            class MinimalState:
                def __init__(self):
                    self.output_path = Path("test.txt")
                    self.max_size_kb = 500
                    self.compact_mode = True
                    self.skip_empty = True
                    self.use_gitignore = True
                    self.force_include = False
                    self.include_patterns = []
                    self.exclude_patterns = []
                    self.tokenizer_model = "gpt-4"
                    self.enable_token_count = True
                    self.copy_to_clipboard = False
            
            state = MinimalState()
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_path
                with patch('proxtract.config._tomli_w', None):
                    # Should not crash on missing attributes
                    save_config(state)
                    
                    assert config_path.exists()

    def test_save_config_with_none_values(self):
        """Test saving config with None values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.toml"
            
            state = AppState()
            # Set some values to None-like states
            state.include_patterns = []
            state.exclude_patterns = []
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_path
                with patch('proxtract.config._tomli_w', None):
                    save_config(state)
                    
                    content = config_path.read_text(encoding="utf-8")
                    
                    # Should handle empty lists properly
                    assert 'include_patterns = []' in content
                    assert 'exclude_patterns = []' in content


class TestConfigRoundTrip:
    """Test complete config load/save round trip."""

    def test_save_and_load_round_trip(self):
        """Test saving config and loading it back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.toml"
            
            # Create initial state
            original_state = AppState()
            original_state.output_path = Path(tmpdir) / "test_output.txt"
            original_state.max_size_kb = 1500
            original_state.compact_mode = False
            original_state.skip_empty = False
            original_state.use_gitignore = False
            original_state.include_patterns = ["*.py", "src/*"]
            original_state.exclude_patterns = ["*.log", "test_*"]
            original_state.skip_extensions = {".pdf", ".png"}
            original_state.skip_patterns = {"__pycache__", ".git"}
            original_state.skip_files = {"package.json", "requirements.txt"}
            original_state.tokenizer_model = "gpt-3.5-turbo"
            original_state.enable_token_count = False
            original_state.copy_to_clipboard = True
            original_state.force_include = True
            original_state.force_include = True
            
            with patch('proxtract.config._config_path') as mock_path:
                mock_path.return_value = config_path
                
                # Save config
                save_config(original_state)
                
                # Load config back
                config_data = load_config()
                
                # Create new state and apply loaded config
                new_state = AppState()
                apply_config(new_state, config_data)
                
                # Verify all values match
                assert new_state.output_path == original_state.output_path
                assert new_state.max_size_kb == original_state.max_size_kb
                assert new_state.compact_mode == original_state.compact_mode
                assert new_state.skip_empty == original_state.skip_empty
                assert new_state.use_gitignore == original_state.use_gitignore
                assert new_state.include_patterns == original_state.include_patterns
                assert new_state.exclude_patterns == original_state.exclude_patterns
                assert new_state.skip_extensions == original_state.skip_extensions
                assert new_state.skip_patterns == original_state.skip_patterns
                assert new_state.skip_files == original_state.skip_files
                assert new_state.tokenizer_model == original_state.tokenizer_model
                assert new_state.enable_token_count == original_state.enable_token_count
                assert new_state.copy_to_clipboard == original_state.copy_to_clipboard
                assert new_state.force_include == original_state.force_include
                assert new_state.force_include == original_state.force_include


if __name__ == "__main__":
    pytest.main([__file__])
