"""Unit tests for TUI components."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

import pytest

from proxtract.state import AppState
from proxtract.tui.app import ProxtractApp
from proxtract.tui.screens.extract_screen import ExtractScreen
from proxtract.tui.screens.main_screen import MainScreen
from proxtract.tui.screens.edit_setting_screen import EditSettingScreen


@contextmanager
def mock_textual_app_context():
    """Create a mock Textual app context for testing widgets."""
    mock_app = MagicMock()
    mock_console = MagicMock()
    mock_console.size.width = 80
    mock_console.size.height = 24
    mock_app.console = mock_console
    
    # Mock the ContextVar behavior by patching its get and set methods
    with patch.object(mock_app, 'get', return_value=mock_app):
        with patch('textual._context.active_app', mock_app):
            try:
                yield mock_app
            except Exception:
                yield mock_app


class TestProxtractApp:
    """Test the ProxtractApp class."""

    def test_app_initialization(self, app_state):
        """Test ProxtractApp initialization."""
        app = ProxtractApp(app_state)
        
        assert app.app_state is app_state
        assert app.title == "Proxtract"

    def test_app_initialization_with_custom_title(self, app_state):
        """Test ProxtractApp initialization with custom title."""
        app = ProxtractApp(app_state, title="Custom Title")
        
        assert app.app_state is app_state
        assert app.title == "Custom Title"

    def test_app_bindings(self, app_state):
        """Test that app has correct key bindings."""
        with mock_textual_app_context():
            app = ProxtractApp(app_state)
            
            # Check that key bindings exist (BINDINGS is a list of tuples)
            assert len(app.BINDINGS) == 2
            binding_keys = [binding[0] for binding in app.BINDINGS]
            assert "q" in binding_keys
            assert "ctrl+s" in binding_keys

    def test_on_mount_pushes_main_screen(self, app_state):
        """Test that on_mount pushes the main screen."""
        with mock_textual_app_context():
            app = ProxtractApp(app_state)
            
            with patch.object(app, 'push_screen') as mock_push_screen:
                # Mock the coroutine
                async def mock_on_mount():
                    await app.push_screen(MainScreen(app_state))
                
                # Call on_mount
                import asyncio
                asyncio.run(app.on_mount())
                
                # Verify main screen was pushed
                mock_push_screen.assert_called_once()

    def test_action_quit_saves_config(self, app_state):
        """Test that action_quit saves config and exits."""
        app = ProxtractApp(app_state)
        
        with patch("proxtract.tui.app._save_config") as mock_save_config:
            with patch.object(app, "exit") as mock_exit:
                app.action_quit()
                
                # Should save config
                mock_save_config.assert_called_once_with(app_state)
                # Should exit
                mock_exit.assert_called_once()

    def test_action_quit_save_config_fails(self, app_state):
        """Test that action_quit handles save config failure."""
        app = ProxtractApp(app_state)
        
        with patch("proxtract.tui.app._save_config", side_effect=Exception("Save failed")):
            with patch.object(app, "exit") as mock_exit:
                with patch.object(app, "notify") as mock_notify:
                    app.action_quit()
                    
                    # Should still save config and exit
                    mock_notify.assert_called_once()
                    mock_exit.assert_called_once()

    def test_action_quit_no_save_config(self, app_state):
        """Test that action_quit works when save config is not available."""
        app = ProxtractApp(app_state)
        
        with patch("proxtract.tui.app._save_config", None):
            with patch.object(app, "exit") as mock_exit:
                app.action_quit()
                
                # Should still exit
                mock_exit.assert_called_once()

    def test_action_save_success(self, app_state):
        """Test successful settings save."""
        app = ProxtractApp(app_state)
        
        with patch("proxtract.tui.app._save_config") as mock_save_config:
            with patch.object(app, "notify") as mock_notify:
                app.action_save()
                
                mock_save_config.assert_called_once_with(app_state)
                mock_notify.assert_called_once_with("Settings saved.", severity="information")

    def test_action_save_no_save_config(self, app_state):
        """Test action_save when config persistence is unavailable."""
        app = ProxtractApp(app_state)
        
        with patch("proxtract.tui.app._save_config", None):
            with patch.object(app, "notify") as mock_notify:
                app.action_save()
                
                mock_notify.assert_called_once_with(
                    "Configuration persistence is unavailable.", 
                    severity="warning"
                )

    def test_action_save_failure(self, app_state):
        """Test action_save when save fails."""
        app = ProxtractApp(app_state)
        
        with patch("proxtract.tui.app._save_config", side_effect=Exception("Save failed")):
            with patch.object(app, "notify") as mock_notify:
                app.action_save()
                
                mock_notify.assert_called_once_with(
                    "Failed to save settings: Save failed", 
                    severity="error"
                )


class TestExtractScreen:
    """Test the ExtractScreen class."""

    def test_screen_initialization(self, app_state):
        """Test ExtractScreen initialization."""
        screen = ExtractScreen(app_state)
        
        assert screen.app_state is app_state
        assert screen._progress_bar is None
        assert screen._status_label is None
        assert screen._summary is None
        assert screen._start_button is None
        assert screen._worker is None
        assert screen._cancel_button is None

    def test_compose_yields_correct_widgets(self, app_state):
        """Test that compose yields the expected widgets."""
        screen = ExtractScreen(app_state)
        
        # Note: This is testing the structure, not the actual rendering
        # In a real test environment, we'd need Textual's testing utilities
        widgets = list(screen.compose())
        
        # Should yield a Vertical container
        assert len(widgets) == 1

    def test_on_mount_sets_initial_values(self, app_state):
        """Test that on_mount sets initial values correctly."""
        screen = ExtractScreen(app_state)
        
        # Mock the query_one method to return mock widgets
        mock_root_input = MagicMock()
        mock_output_input = MagicMock()
        mock_progress_bar = MagicMock()
        mock_status_label = MagicMock()
        mock_summary = MagicMock()
        mock_start_button = MagicMock()
        mock_cancel_button = MagicMock()
        
        with patch.object(screen, 'query_one') as mock_query:
            def query_side_effect(selector, widget_type=None):
                if selector == "#extract-root":
                    return mock_root_input
                elif selector == "#extract-output":
                    return mock_output_input
                elif selector == "ProgressBar":
                    return mock_progress_bar
                elif selector == "#extract-status":
                    return mock_status_label
                elif selector == "SummaryDisplay":
                    return mock_summary
                elif selector == "#start":
                    return mock_start_button
                elif selector == "#cancel":
                    return mock_cancel_button
                return MagicMock()
            
            mock_query.side_effect = query_side_effect
            
            # Test on_mount
            screen.on_mount()
            
            # Verify input fields are set
            mock_root_input.value = str(app_state.output_path.parent)
            mock_output_input.value = str(app_state.output_path)
            
            # Verify widgets are stored
            assert screen._progress_bar is mock_progress_bar
            assert screen._status_label is mock_status_label
            assert screen._summary is mock_summary
            assert screen._start_button is mock_start_button
            assert screen._cancel_button is mock_cancel_button

    def test_on_mount_with_last_stats(self, app_state):
        """Test that on_mount shows last stats if available."""
        from proxtract.core import ExtractionStats
        
        app_state.last_stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=[],
            total_bytes=0,
            skipped_paths={},
            errors=[]
        )
        
        screen = ExtractScreen(app_state)
        
        mock_summary = MagicMock()
        
        with patch.object(screen, 'query_one', return_value=mock_summary):
            screen.on_mount()
            
            # Summary should be updated
            mock_summary.update_stats.assert_called_once_with(app_state.last_stats)

    def test_on_button_pressed_cancel(self, app_state):
        """Test cancel button press."""
        screen = ExtractScreen(app_state)
        
        mock_event = MagicMock()
        mock_event.button.id = "cancel"
        
        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.on_button_pressed(mock_event)
            
            mock_dismiss.assert_called_once_with(None)

    def test_on_button_pressed_start(self, app_state):
        """Test start button press."""
        screen = ExtractScreen(app_state)
        
        mock_event = MagicMock()
        mock_event.button.id = "start"
        
        with patch.object(screen, "_begin_extraction") as mock_begin:
            screen.on_button_pressed(mock_event)
            
            mock_begin.assert_called_once()

    def test_on_button_pressed_unknown(self, app_state):
        """Test unknown button press."""
        screen = ExtractScreen(app_state)
        
        mock_event = MagicMock()
        mock_event.button.id = "unknown"
        
        with patch.object(screen, "_begin_extraction") as mock_begin:
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.on_button_pressed(mock_event)
                
                # Should not call any action
                mock_begin.assert_not_called()
                mock_dismiss.assert_not_called()

    def test_begin_extraction_validation(self, app_state):
        """Test that begin_extraction validates inputs."""
        with mock_textual_app_context():
            screen = ExtractScreen(app_state)
            
            mock_root_input = MagicMock()
            mock_root_input.value = ""  # Empty input
            mock_output_input = MagicMock()
            mock_output_input.value = ""  # Empty input
            
            with patch.object(screen, 'query_one') as mock_query:
                mock_query.side_effect = lambda selector, widget_type=None: {
                    "#extract-root": mock_root_input,
                    "#extract-output": mock_output_input
                }[selector]
                
                with patch.object(screen, "notify") as mock_notify:
                    screen._begin_extraction()
                    
                    mock_notify.assert_called_once_with(
                        "Source and output paths are required.",
                        severity="warning"
                    )

    def test_begin_extraction_valid_inputs(self, app_state, temp_dir):
        """Test begin_extraction with valid inputs."""
        with mock_textual_app_context():
            screen = ExtractScreen(app_state)
            
            mock_root_input = MagicMock()
            mock_root_input.value = str(temp_dir)
            mock_output_input = MagicMock()
            mock_output_input.value = str(temp_dir / "output.txt")
            mock_start_button = MagicMock()
            mock_progress_bar = MagicMock()
            
            with patch.object(screen, 'query_one') as mock_query:
                mock_query.side_effect = lambda selector, widget_type=None: {
                    "#extract-root": mock_root_input,
                    "#extract-output": mock_output_input,
                    "#start": mock_start_button,
                    "ProgressBar": mock_progress_bar
                }[selector]
                
                with patch.object(screen, "run_worker") as mock_run_worker:
                    with patch.object(screen, "_update_status") as mock_update_status:
                        screen._begin_extraction()
                        
                        # Verify state was updated
                        assert app_state.output_path == temp_dir / "output.txt"
                        
                        # Verify UI was disabled and progress shown
                        mock_start_button.disabled = True
                        mock_progress_bar.display = True
                        mock_progress_bar.update.assert_called_once_with(0, total=100)
                        
                        # Verify worker was started
                        mock_run_worker.assert_called_once()

    def test_update_status(self, app_state):
        """Test _update_status method."""
        screen = ExtractScreen(app_state)
        
        mock_status_label = MagicMock()
        screen._status_label = mock_status_label
        
        screen._update_status("Test message")
        
        mock_status_label.update.assert_called_once_with("Test message")

    def test_on_extraction_started(self, app_state):
        """Test handling of extraction started message."""
        screen = ExtractScreen(app_state)
        
        mock_progress_bar = MagicMock()
        screen._progress_bar = mock_progress_bar
        
        message = ExtractScreen.ExtractionStarted(total=42)
        
        screen.on_extraction_started(message)
        
        mock_progress_bar.update.assert_called_once_with(0, total=42)
        # Note: We'd also need to test the status update, but that's harder to mock

    def test_on_extraction_progress(self, app_state):
        """Test handling of extraction progress message."""
        screen = ExtractScreen(app_state)
        
        mock_progress_bar = MagicMock()
        screen._progress_bar = mock_progress_bar
        
        message = ExtractScreen.ExtractionProgress(
            processed=10, 
            total=42, 
            description="Processing file.py"
        )
        
        with patch.object(screen, "_update_status") as mock_update_status:
            screen.on_extraction_progress(message)
            
            mock_progress_bar.update.assert_called_once_with(10, total=42)
            mock_update_status.assert_called_once_with("Processing file.py")

    def test_on_extraction_failed(self, app_state):
        """Test handling of extraction failed message."""
        screen = ExtractScreen(app_state)
        
        mock_progress_bar = MagicMock()
        mock_start_button = MagicMock()
        screen._progress_bar = mock_progress_bar
        screen._start_button = mock_start_button
        
        message = ExtractScreen.ExtractionFailed(message="Something went wrong")
        
        with patch.object(screen, "_update_status") as mock_update_status:
            screen.on_extraction_failed(message)
            
            mock_progress_bar.display = False
            mock_start_button.disabled = False
            mock_update_status.assert_called_once_with("Error: Something went wrong")

    def test_on_extraction_completed(self, app_state):
        """Test handling of extraction completed message."""
        from proxtract.core import ExtractionStats
        
        screen = ExtractScreen(app_state)
        
        mock_progress_bar = MagicMock()
        mock_start_button = MagicMock()
        mock_cancel_button = MagicMock()
        mock_summary = MagicMock()
        screen._progress_bar = mock_progress_bar
        screen._start_button = mock_start_button
        screen._cancel_button = mock_cancel_button
        screen._summary = mock_summary
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=[],
            total_bytes=0,
            skipped_paths={},
            errors=[]
        )
        message = ExtractScreen.ExtractionCompleted(stats=stats)
        
        with patch.object(screen, "_update_status") as mock_update_status:
            screen.on_extraction_completed(message)
            
            # Verify UI state changes
            mock_progress_bar.display = False
            mock_start_button.disabled = False
            mock_cancel_button.label = "Close"
            
            # Verify summary update
            mock_summary.update_stats.assert_called_once_with(stats)
            
            mock_update_status.assert_called_once_with("Extraction complete.")

    def test_dismiss(self, app_state):
        """Test dismiss method."""
        from proxtract.core import ExtractionStats
        
        screen = ExtractScreen(app_state)
        
        # Test with no last stats
        app_state.last_stats = None
        
        with patch("builtins.super") as mock_super:
            mock_dismiss = MagicMock()
            mock_super.return_value.dismiss = mock_dismiss
            
            screen.dismiss()
            
            mock_dismiss.assert_called_once_with(None)

    def test_dismiss_with_stats(self, app_state):
        """Test dismiss method with existing stats."""
        from proxtract.core import ExtractionStats
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=[],
            total_bytes=0,
            skipped_paths={},
            errors=[]
        )
        app_state.last_stats = stats
        
        screen = ExtractScreen(app_state)
        
        with patch("builtins.super") as mock_super:
            mock_dismiss = MagicMock()
            mock_super.return_value.dismiss = mock_dismiss
            
            screen.dismiss()
            
            # Should pass the last stats
            mock_dismiss.assert_called_once_with(stats)


class TestMainScreen:
    """Test the MainScreen class."""

    def test_screen_initialization(self, app_state):
        """Test MainScreen initialization."""
        screen = MainScreen(app_state)
        
        assert screen.app_state is app_state
        assert screen._settings_view is None
        assert screen._actions_view is None
        assert screen._summary is None
        assert screen._items == {}

    def test_screen_id(self, app_state):
        """Test that screen has correct ID."""
        screen = MainScreen(app_state)
        
        assert screen.ID == "main"

    def test_compose_yields_correct_widgets(self, app_state):
        """Test that compose yields the expected widgets."""
        screen = MainScreen(app_state)
        
        # Should yield Header, Vertical, and Footer
        widgets = list(screen.compose())
        assert len(widgets) == 3

    def test_setting_specs(self, app_state):
        """Test the _setting_specs property."""
        screen = MainScreen(app_state)
        
        specs = screen._setting_specs
        
        # Should return a sequence of SettingSpec objects
        assert len(specs) == 10  # We have 10 settings
        
        # Check some specific settings
        spec_dict = {spec.attr: spec for spec in specs}
        
        assert "output_path" in spec_dict
        assert "max_size_kb" in spec_dict
        assert "compact_mode" in spec_dict
        assert "include_patterns" in spec_dict
        assert "exclude_patterns" in spec_dict
        
        # Check that formatters exist
        for spec in specs:
            assert callable(spec.formatter)

    def test_on_mount_populates_settings(self, app_state):
        """Test that on_mount populates the settings list."""
        with mock_textual_app_context():
            screen = MainScreen(app_state)
            
            mock_settings_view = MagicMock()
            mock_actions_view = MagicMock()
            mock_summary = MagicMock()
            
            with patch.object(screen, 'query_one') as mock_query:
                def query_side_effect(selector, widget_type=None):
                    if selector == "#settings-list":
                        return mock_settings_view
                    elif selector == "#actions-list":
                        return mock_actions_view
                    elif selector == "SummaryDisplay":
                        return mock_summary
                    return MagicMock()
                
                mock_query.side_effect = query_side_effect
                
                screen.on_mount()
                
                # Should append setting items
                assert mock_settings_view.append.call_count == len(screen._setting_specs)
                # Should append action item
                mock_actions_view.append.assert_called_once()
                # Should set summary
                assert screen._summary is mock_summary

    def test_on_mount_with_last_stats(self, app_state):
        """Test that on_mount shows last stats if available."""
        with mock_textual_app_context():
            from proxtract.core import ExtractionStats
            
            app_state.last_stats = ExtractionStats(
                root=Path("/test"),
                output=Path("/output.txt"),
                processed_paths=[],
                total_bytes=0,
                skipped_paths={},
                errors=[]
            )
            
            screen = MainScreen(app_state)
            
            mock_summary = MagicMock()
            
            with patch.object(screen, 'query_one', return_value=mock_summary):
                screen.on_mount()
                
                # Summary should be updated
                mock_summary.update_stats.assert_called_once_with(app_state.last_stats)

    def test_on_list_view_selected_settings(self, app_state):
        """Test selection of setting items."""
        screen = MainScreen(app_state)
        
        mock_event = MagicMock()
        mock_event.control.id = "settings-list"
        mock_event.item = MagicMock()  # Mock setting item
        
        # Mock the setting processing
        with patch.object(screen, "_handle_setting_selected") as mock_handle:
            import asyncio
            
            # Create a coroutine for the async method
            async def mock_on_list_view_selected():
                await screen.on_list_view_selected(mock_event)
            
            asyncio.run(mock_on_list_view_selected())
            
            mock_handle.assert_called_once_with(mock_event.item)

    def test_on_list_view_selected_actions(self, app_state):
        """Test selection of action items."""
        screen = MainScreen(app_state)
        
        mock_event = MagicMock()
        mock_event.control.id = "actions-list"
        mock_event.item = MagicMock()  # Mock action item
        
        with patch.object(screen, "_handle_action_selected") as mock_handle:
            import asyncio
            
            async def mock_on_list_view_selected():
                await screen.on_list_view_selected(mock_event)
            
            asyncio.run(mock_on_list_view_selected())
            
            mock_handle.assert_called_once_with(mock_event.item)

    def test_handle_setting_selected_bool_toggle(self, app_state):
        """Test that boolean settings are toggled directly."""
        with mock_textual_app_context():
            screen = MainScreen(app_state)
            
            # Create a mock setting item for a boolean setting
            mock_item = MagicMock()
            mock_item.key = "compact_mode"
            
            # Get the actual setting spec
            spec = screen._spec_by_attr("compact_mode")
            
            with patch.object(screen, '_spec_by_attr', return_value=spec):
                import asyncio
                
                async def mock_handle_setting_selected():
                    await screen._handle_setting_selected(mock_item)
                
                # Run the async method
                asyncio.run(mock_handle_setting_selected())
                
                # Boolean should be toggled (True -> False, False -> True)
                assert app_state.compact_mode == False  # Should be False now

    def test_handle_setting_selected_non_bool_opens_edit_screen(self, app_state):
        """Test that non-boolean settings open the edit screen."""
        with mock_textual_app_context():
            screen = MainScreen(app_state)
            
            mock_item = MagicMock()
            mock_item.key = "output_path"
            
            spec = screen._spec_by_attr("output_path")
            
            with patch.object(screen, '_spec_by_attr', return_value=spec):
                with patch.object(screen, 'push_screen_wait') as mock_push_screen:
                    # Mock the return value from edit screen
                    mock_push_screen.return_value = "/new/path.txt"
                    
                    import asyncio
                    
                    async def mock_handle_setting_selected():
                        await screen._handle_setting_selected(mock_item)
                    
                    asyncio.run(mock_handle_setting_selected())
                    
                    # Should open edit screen
                    mock_push_screen.assert_called_once()

    def test_handle_action_selected_extract(self, app_state):
        """Test that extract action opens extract screen."""
        with mock_textual_app_context():
            screen = MainScreen(app_state)
            
            mock_item = MagicMock()
            mock_item.action_id = "extract"
            
            with patch.object(screen, 'push_screen_wait') as mock_push_screen:
                with patch.object(screen, '_summary') as mock_summary:
                    # Mock return value from extract screen
                    from proxtract.core import ExtractionStats
                    mock_stats = MagicMock()
                    mock_push_screen.return_value = mock_stats
                    
                    import asyncio
                    
                    async def mock_handle_action_selected():
                        await screen._handle_action_selected(mock_item)
                    
                    asyncio.run(mock_handle_action_selected())
                    
                    # Should open extract screen
                    mock_push_screen.assert_called_once()
                    # Should update summary
                    mock_summary.update_stats.assert_called_once_with(mock_stats)

    def test_spec_by_attr(self, app_state):
        """Test _spec_by_attr method."""
        screen = MainScreen(app_state)
        
        spec = screen._spec_by_attr("compact_mode")
        
        assert spec.attr == "compact_mode"
        assert spec.label == "Compact Mode"
        assert spec.setting_type == "bool"

    def test_spec_by_attr_not_found(self, app_state):
        """Test _spec_by_attr method with non-existent attribute."""
        screen = MainScreen(app_state)
        
        with pytest.raises(KeyError):
            screen._spec_by_attr("nonexistent")

    def test_format_bool(self, app_state):
        """Test _format_bool static method."""
        screen = MainScreen(app_state)
        
        assert screen._format_bool(True) == "On"
        assert screen._format_bool(False) == "Off"
        assert screen._format_bool(1) == "On"
        assert screen._format_bool(0) == "Off"

    def test_format_list(self, app_state):
        """Test _format_list static method."""
        screen = MainScreen(app_state)
        
        assert screen._format_list([]) == "(none)"
        assert screen._format_list(["a", "b", "c"]) == "a, b, c"

    def test_value_to_string(self, app_state):
        """Test _value_to_string static method."""
        screen = MainScreen(app_state)
        
        # List
        assert screen._value_to_string(["a", "b"], "list") == "a, b"
        assert screen._value_to_string([], "list") == ""
        
        # Other types
        assert screen._value_to_string(42, "int") == "42"
        assert screen._value_to_string("test", "str") == "test"

    def test_parse_value(self, app_state):
        """Test _parse_value static method."""
        screen = MainScreen(app_state)
        
        # Int
        assert screen._parse_value("42", "int") == 42
        
        # List
        assert screen._parse_value("a, b, c", "list") == ["a", "b", "c"]
        assert screen._parse_value("a,b,c", "list") == ["a", "b", "c"]
        assert screen._parse_value("a, , b", "list") == ["a", "b"]  # Empty items filtered
        
        # Bool
        assert screen._parse_value("true", "bool") is True
        assert screen._parse_value("1", "bool") is True
        assert screen._parse_value("yes", "bool") is True
        assert screen._parse_value("false", "bool") is False
        assert screen._parse_value("0", "bool") is False
        
        # Path
        from pathlib import Path
        result = screen._parse_value("/test/path", "path")
        assert isinstance(result, Path)
        assert str(result) == "/test/path"


class TestEditSettingScreen:
    """Test the EditSettingScreen class."""

    def test_screen_initialization(self, app_state):
        """Test EditSettingScreen initialization."""
        # EditSettingScreen doesn't take app_state in constructor
        with mock_textual_app_context():
            screen = EditSettingScreen(
                label="Test Label",
                description="Test Description",
                initial_value="initial"
            )
            
            assert screen._label == "Test Label"
            assert screen._description == "Test Description"
            assert screen._initial_value == "initial"

    def test_compose_yields_correct_widgets(self, app_state):
        """Test that compose yields the expected widgets."""
        with mock_textual_app_context():
            screen = EditSettingScreen(
                label="Label",
                description="Description",
                initial_value="initial"
            )
            
            widgets = list(screen.compose())
            assert len(widgets) == 1  # Vertical container

    def test_on_mount_focuses_input(self, app_state):
        """Test that on_mount focuses the input."""
        with mock_textual_app_context():
            screen = EditSettingScreen(
                label="Label",
                description="Description",
                initial_value="initial"
            )
            
            mock_input = MagicMock()
            
            with patch.object(screen, 'query_one', return_value=mock_input):
                screen.on_mount()
                
                mock_input.focus.assert_called_once()

    def test_on_button_pressed_cancel(self, app_state):
        """Test cancel button press."""
        with mock_textual_app_context():
            screen = EditSettingScreen(
                label="Label",
                description="Description",
                initial_value="initial"
            )
            
            mock_event = MagicMock()
            mock_event.button.id = "cancel"
            
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.on_button_pressed(mock_event)
                
                mock_dismiss.assert_called_once_with(None)

    def test_on_button_pressed_save(self, app_state):
        """Test save button press."""
        with mock_textual_app_context():
            screen = EditSettingScreen(
                label="Label",
                description="Description",
                initial_value="initial"
            )
            
            mock_event = MagicMock()
            mock_event.button.id = "save"
            mock_input = MagicMock()
            mock_input.value = "new value"
            
            with patch.object(screen, 'query_one', return_value=mock_input):
                with patch.object(screen, "dismiss") as mock_dismiss:
                    screen.on_button_pressed(mock_event)
                    
                    mock_dismiss.assert_called_once_with("new value")

    def test_on_input_submitted(self, app_state):
        """Test input submission."""
        with mock_textual_app_context():
            screen = EditSettingScreen(
                label="Label",
                description="Description",
                initial_value="initial"
            )
            
            mock_event = MagicMock()
            mock_event.value = "submitted value"
            
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.on_input_submitted(mock_event)
                
                mock_dismiss.assert_called_once_with("submitted value")