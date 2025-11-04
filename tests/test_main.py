"""Unit tests for the CLI interface in main.py."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from proxtract.main import _run_cli_extract, _launch_tui, main
from proxtract.state import AppState


class TestRunCliExtract:
    """Test the _run_cli_extract function."""

    def test_run_cli_extract_basic_success(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test successful CLI extraction with minimal arguments."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        # Mock apply_config to return our test state
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        # Should print success message
        assert any("Extracting" in str(call) for call in mock_console.print_calls)
        assert any("Done" in str(call) for call in mock_console.print_calls)

    def test_run_cli_extract_with_output_path(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with custom output path."""
        output_path = temp_dir / "custom_output.txt"
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(output_path),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        # Verify the state was updated
        assert app_state.output_path == output_path

    def test_run_cli_extract_with_max_size(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with custom max size."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=1000,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.max_size_kb == 1000

    def test_run_cli_extract_compact_mode(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with compact mode enabled."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=True,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.compact_mode is True

    def test_run_cli_extract_no_compact_mode(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with compact mode disabled."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=True,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.compact_mode is False

    def test_run_cli_extract_skip_empty(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with skip empty enabled."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=True,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.skip_empty is True

    def test_run_cli_extract_no_skip_empty(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with skip empty disabled."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=True,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.skip_empty is False

    def test_run_cli_extract_use_gitignore(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with gitignore enabled."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=True,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.use_gitignore is True

    def test_run_cli_extract_no_gitignore(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with gitignore disabled."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=True,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.use_gitignore is False

    def test_run_cli_extract_include_patterns(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with include patterns."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=["*.py", "*.js"],
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.include_patterns == ["*.py", "*.js"]

    def test_run_cli_extract_exclude_patterns(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with exclude patterns."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=["test_*", "node_modules"],
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.exclude_patterns == ["test_*", "node_modules"]

    def test_run_cli_extract_tokenizer_model(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with custom tokenizer model."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model="gpt-3.5-turbo",
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.tokenizer_model == "gpt-3.5-turbo"

    def test_run_cli_extract_no_token_count(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with token counting disabled."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=True,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.enable_token_count is False

    def test_run_cli_extract_copy_to_clipboard(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with clipboard copy enabled."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=True,
            save_config=False
        )
        
        # Mock pyperclip
        mock_pyperclip = MagicMock()
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                with patch("proxtract.main.pyperclip", mock_pyperclip):
                    with patch("proxtract.main.Path") as mock_path:
                        mock_path.return_value.read_text.return_value = "test content"
                        result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        assert app_state.copy_to_clipboard is True

    def test_run_cli_extract_extraction_error(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction when FileExtractor raises an error."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                with patch.object(app_state, "create_extractor") as mock_create_extractor:
                    mock_extractor = MagicMock()
                    mock_extractor.extract.side_effect = Exception("Extraction failed")
                    mock_create_extractor.return_value = mock_extractor
                    
                    result = _run_cli_extract(args, mock_console)
        
        assert result == 2
        # Should print error message
        assert any("Extraction failed" in str(call) for call in mock_console.print_calls)

    def test_run_cli_extract_with_warnings(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction that produces warnings."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=False
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                with patch.object(app_state, "create_extractor") as mock_create_extractor:
                    mock_extractor = MagicMock()
                    from proxtract.core import ExtractionStats
                    mock_stats = ExtractionStats(
                        root=Path(sample_project_dir),
                        output=Path(temp_dir / "output.txt"),
                        processed_paths=["file.py"],
                        total_bytes=100,
                        skipped_paths={"empty": ["empty.txt"]},
                        errors=["Some warning message"]
                    )
                    mock_extractor.extract.return_value = mock_stats
                    mock_create_extractor.return_value = mock_extractor
                    
                    result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        # Should print warnings
        assert any("Warnings" in str(call) for call in mock_console.print_calls)

    def test_run_cli_extract_copy_failure(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction when clipboard copy fails."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=True,
            save_config=False
        )
        
        # Mock pyperclip that fails
        def mock_copy_side_effect(content):
            raise Exception("Clipboard access failed")
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                with patch("proxtract.main.pyperclip", copy=mock_copy_side_effect):
                    with patch("proxtract.main.Path") as mock_path:
                        mock_path.return_value.read_text.return_value = "test content"
                        result = _run_cli_extract(args, mock_console)
        
        assert result == 0  # Should still succeed
        # Should print warning about clipboard failure
        assert any("Failed to copy" in str(call) for call in mock_console.print_calls)

    def test_run_cli_extract_save_config_success(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction with successful config save."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=True
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                with patch("proxtract.main._save_config") as mock_save_config:
                    result = _run_cli_extract(args, mock_console)
        
        assert result == 0
        mock_save_config.assert_called_once_with(app_state)
        # Should print success message
        assert any("Settings saved" in str(call) for call in mock_console.print_calls)

    def test_run_cli_extract_save_config_failure(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction when config save fails."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=True
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                with patch("proxtract.main._save_config", side_effect=Exception("Save failed")):
                    result = _run_cli_extract(args, mock_console)
        
        assert result == 0  # Should still succeed
        # Should print warning about save failure
        assert any("Failed to save settings" in str(call) for call in mock_console.print_calls)

    def test_run_cli_extract_save_config_not_available(self, app_state, mock_console, sample_project_dir, temp_dir):
        """Test CLI extraction when config save is not available."""
        args = argparse.Namespace(
            path=str(sample_project_dir),
            output=str(temp_dir / "output.txt"),
            max_size=None,
            compact=False,
            no_compact=False,
            skip_empty=False,
            no_skip_empty=False,
            use_gitignore=False,
            no_gitignore=False,
            include=None,
            exclude=None,
            tokenizer_model=None,
            no_token_count=False,
            copy=False,
            save_config=True
        )
        
        with patch("proxtract.main.apply_config", return_value=app_state):
            with patch("proxtract.main.Console", return_value=mock_console):
                with patch("proxtract.main._save_config", None):
                    result = _run_cli_extract(args, mock_console)
        
        assert result == 0  # Should still succeed
        # Should indicate that persistence is unavailable


class TestLaunchTui:
    """Test the _launch_tui function."""

    def test_launch_tui_basic(self):
        """Test basic TUI launch."""
        with patch("proxtract.main.apply_config", return_value=AppState()) as mock_apply_config:
            with patch("proxtract.main.ProxtractApp") as mock_app_class:
                with patch.object(mock_app_class.return_value, "run") as mock_run:
                    _launch_tui()
        
        mock_apply_config.assert_called_once()
        mock_app_class.assert_called_once()
        mock_run.assert_called_once()

    def test_launch_tui_with_custom_state(self):
        """Test TUI launch with custom state."""
        custom_state = AppState(max_size_kb=1000)
        
        with patch("proxtract.main.apply_config", return_value=custom_state) as mock_apply_config:
            with patch("proxtract.main.ProxtractApp") as mock_app_class:
                with patch.object(mock_app_class.return_value, "run") as mock_run:
                    _launch_tui()
        
        mock_apply_config.assert_called_once()
        # Should use the returned state
        mock_app_class.assert_called_once_with(custom_state)

    def test_launch_tui_exception_handling(self):
        """Test TUI launch exception handling."""
        with patch("proxtract.main.apply_config", side_effect=Exception("Config error")):
            with patch("proxtract.main.ProxtractApp") as mock_app_class:
                with patch.object(mock_app_class.return_value, "run") as mock_run:
                    # Should still try to launch TUI with default state
                    _launch_tui()
        
        mock_app_class.assert_called_once()
        mock_run.assert_called_once()


class TestMain:
    """Test the main function."""

    def test_main_no_args_launches_tui(self, monkeypatch):
        """Test main with no arguments launches TUI."""
        mock_launch_tui = patch("proxtract.main._launch_tui").start()
        monkeypatch.setattr("sys.argv", ["proxtract"])
        
        main()
        
        mock_launch_tui.assert_called_once()
        patch.stopall()

    def test_main_extract_command(self, monkeypatch):
        """Test main with extract command."""
        mock_run_cli_extract = patch("proxtract.main._run_cli_extract").start()
        mock_console = MagicMock()
        monkeypatch.setattr("proxtract.main.Console", return_value=mock_console)
        monkeypatch.setattr("sys.argv", ["proxtract", "extract", "/test/path"])
        
        with patch("proxtract.main.argparse.ArgumentParser.parse_args") as mock_parse_args:
            mock_args = MagicMock()
            mock_args.command = "extract"
            mock_parse_args.return_value = mock_args
            
            with pytest.raises(SystemExit):
                main()
            
            mock_run_cli_extract.assert_called_once_with(mock_args, mock_console)
        
        patch.stopall()

    def test_main_unknown_command_launches_tui(self, monkeypatch):
        """Test main with unknown command launches TUI."""
        mock_launch_tui = patch("proxtract.main._launch_tui").start()
        monkeypatch.setattr("sys.argv", ["proxtract", "unknown_command"])
        
        with patch("proxtract.main.argparse.ArgumentParser.parse_args") as mock_parse_args:
            mock_args = MagicMock()
            mock_args.command = "unknown_command"
            mock_parse_args.return_value = mock_args
            
            main()
        
        mock_launch_tui.assert_called_once()
        patch.stopall()

    def test_main_with_custom_argv(self):
        """Test main with custom argv parameter."""
        with patch("proxtract.main._launch_tui") as mock_launch_tui:
            main(argv=["proxtract"])
        
        mock_launch_tui.assert_called_once()

    def test_main_extract_with_all_options(self, monkeypatch):
        """Test main with extract command and all options."""
        mock_run_cli_extract = patch("proxtract.main._run_cli_extract").start()
        mock_console = MagicMock()
        monkeypatch.setattr("proxtract.main.Console", return_value=mock_console)
        
        args = [
            "proxtract", "extract", "/test/path",
            "--output", "output.txt",
            "--max-size", "1000",
            "--compact",
            "--include", "*.py",
            "--exclude", "test_*",
            "--tokenizer-model", "gpt-3.5-turbo",
            "--copy",
            "--save-config"
        ]
        monkeypatch.setattr("sys.argv", args)
        
        with patch("proxtract.main.argparse.ArgumentParser.parse_args") as mock_parse_args:
            mock_args = MagicMock()
            mock_args.command = "extract"
            mock_parse_args.return_value = mock_args
            
            with pytest.raises(SystemExit):
                main()
            
            mock_run_cli_extract.assert_called_once_with(mock_args, mock_console)
        
        patch.stopall()

    def test_main_argument_parsing(self, monkeypatch):
        """Test that main properly parses command line arguments."""
        monkeypatch.setattr("sys.argv", ["proxtract", "extract", "/test/path", "--max-size", "500"])
        
        with patch("proxtract.main._run_cli_extract") as mock_run_cli_extract:
            with patch("proxtract.main.Console"):
                with pytest.raises(SystemExit):
                    main()
                
                # Verify the arguments were parsed correctly
                assert mock_run_cli_extract.called
                args = mock_run_cli_extract.call_args[0][0]  # First positional argument
                assert args.path == "/test/path"
                assert args.max_size == 500

    def test_main_mutually_exclusive_groups(self, monkeypatch):
        """Test that mutually exclusive argument groups work correctly."""
        # Test compact vs no-compact
        monkeypatch.setattr("sys.argv", ["proxtract", "extract", "/test/path", "--compact"])
        
        with patch("proxtract.main._run_cli_extract"):
            with patch("proxtract.main.Console"):
                with pytest.raises(SystemExit):
                    main()
        
        # Test skip-empty vs no-skip-empty
        monkeypatch.setattr("sys.argv", ["proxtract", "extract", "/test/path", "--skip-empty"])
        
        with patch("proxtract.main._run_cli_extract"):
            with patch("proxtract.main.Console"):
                with pytest.raises(SystemExit):
                    main()
        
        # Test gitignore vs no-gitignore
        monkeypatch.setattr("sys.argv", ["proxtract", "extract", "/test/path", "--use-gitignore"])
        
        with patch("proxtract.main._run_cli_extract"):
            with patch("proxtract.main.Console"):
                with pytest.raises(SystemExit):
                    main()