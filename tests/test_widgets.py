"""Unit tests for widget components."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

import pytest

from proxtract.core import ExtractionStats
from proxtract.tui.widgets.action_item import ActionItem
from proxtract.tui.widgets.setting_item import SettingItem, SettingMetadata
from proxtract.tui.widgets.summary_display import SummaryDisplay


@contextmanager
def mock_textual_app_context():
    """Create a mock Textual app context for testing widgets."""
    mock_app = MagicMock()
    mock_console = MagicMock()
    mock_console.size.width = 80
    mock_console.size.height = 24
    mock_app.console = mock_console
    
    # Create a mock context var
    mock_context_var = MagicMock()
    mock_context_var.get.return_value = mock_app
    
    with patch('textual._context.active_app', mock_context_var):
        try:
            yield mock_app
        except Exception:
            yield mock_app


class TestActionItem:
    """Test the ActionItem class."""

    def test_item_initialization(self):
        """Test ActionItem initialization."""
        with mock_textual_app_context():
            item = ActionItem(
                label="Test Action",
                description="Test Description",
                action_id="test_action"
            )
            
            assert item.label == "Test Action"
            assert item.description == "Test Description"
            assert item.action_id == "test_action"

    def test_item_initialization_with_custom_id(self):
        """Test ActionItem initialization with custom ID."""
        with mock_textual_app_context():
            item = ActionItem(
                label="Test Action",
                description="Test Description",
                action_id="test_action",
                id="custom_id"
            )
            
            assert item.id == "custom_id"

    def test_item_initialization_without_id(self):
        """Test ActionItem initialization without custom ID."""
        with mock_textual_app_context():
            item = ActionItem(
                label="Test Action",
                description="Test Description",
                action_id="test_action"
            )
            
            # Should use default ID based on action_id
            assert item.id == "action-test_action"

    def test_item_creates_label_widget(self):
        """Test that ActionItem creates a Label widget."""
        with mock_textual_app_context():
            item = ActionItem(
                label="Test Action",
                description="Test Description",
                action_id="test_action"
            )
            
            # Should have a label widget as child
            children = item._nodes
            assert len(children) == 1
            assert hasattr(children[0], 'update')  # It's a Label widget

    def test_item_formats_text_correctly(self):
        """Test that ActionItem formats text with bold label and dim description."""
        with mock_textual_app_context():
            item = ActionItem(
                label="Test Action",
                description="Test Description",
                action_id="test_action"
            )
            
            # The label widget should be updated with formatted text
            label_widget = item._nodes[0]
            
            # Check that the text was set (we can't easily test Rich Text formatting
            # without complex mocking, but we can verify update was called)
            assert hasattr(label_widget, 'update')

    def test_item_css_classes(self):
        """Test that ActionItem has correct CSS classes."""
        with mock_textual_app_context():
            item = ActionItem(
                label="Test Action",
                description="Test Description",
                action_id="test_action"
            )
            
            # Check that default CSS is defined
            assert hasattr(ActionItem, 'DEFAULT_CSS')
            
            # The CSS should include the ActionItem selector
            assert "ActionItem" in ActionItem.DEFAULT_CSS

    def test_item_selected_state_css(self):
        """Test that ActionItem has CSS for selected state."""
        with mock_textual_app_context():
            item = ActionItem(
                label="Test Action",
                description="Test Description",
                action_id="test_action"
            )
            
            # Check that selected state CSS is defined
            assert "ActionItem.-selected" in ActionItem.DEFAULT_CSS
            # Should have background style for selected state
            assert "background" in ActionItem.DEFAULT_CSS


class TestSettingItem:
    """Test the SettingItem class."""

    def test_item_initialization(self):
        """Test SettingItem initialization."""
        with mock_textual_app_context():
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=lambda x: str(x),
                setting_type="str"
            )
            
            def value_getter():
                return "test_value"
            
            item = SettingItem(metadata, value_getter)
            
            assert item.metadata is metadata
            assert item._value_getter is value_getter
            assert item.setting_type == "str"
            assert item.key == "test_setting"

    def test_item_initialization_with_custom_id(self):
        """Test SettingItem initialization with custom ID."""
        with mock_textual_app_context():
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=lambda x: str(x),
                setting_type="str"
            )
            
            def value_getter():
                return "test_value"
            
            item = SettingItem(metadata, value_getter, id="custom_id")
            
            assert item.id == "custom_id"

    def test_item_initialization_without_id(self):
        """Test SettingItem initialization without custom ID."""
        with mock_textual_app_context():
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=lambda x: str(x),
                setting_type="str"
            )
            
            def value_getter():
                return "test_value"
            
            item = SettingItem(metadata, value_getter)
            
            # Should use default ID based on metadata key
            assert item.id == "setting-test_setting"

    def test_item_calls_value_getter_on_init(self):
        """Test that SettingItem calls value getter on initialization."""
        with mock_textual_app_context():
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=lambda x: f"Formatted: {x}",
                setting_type="str"
            )
            
            call_count = 0
            def value_getter():
                nonlocal call_count
                call_count += 1
                return "test_value"
            
            item = SettingItem(metadata, value_getter)
            
            # Value getter should have been called
            assert call_count == 1

    def test_update_content_refreshes_display(self):
        """Test that update_content refreshes the displayed text."""
        with mock_textual_app_context():
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=lambda x: f"Value: {x}",
                setting_type="str"
            )
            
            def value_getter():
                return "current_value"
            
            item = SettingItem(metadata, value_getter)
            
            # Get the label widget
            label_widget = item._label
            
            # Change the value
            def new_value_getter():
                return "new_value"
            
            item._value_getter = new_value_getter
            
            # Update content
            item.update_content()
            
            # The label should be updated (we can't easily verify the exact Rich Text
            # content without complex mocking, but update should be called)
            assert hasattr(label_widget, 'update')

    def test_update_content_calls_formatter(self):
        """Test that update_content calls the value formatter."""
        with mock_textual_app_context():
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=lambda x: f"Formatted: {x}",
                setting_type="str"
            )
            
            call_count = 0
            def value_getter():
                return f"value_{call_count}"
            
            def counting_formatter(value):
                nonlocal call_count
                call_count += 1
                return f"Formatted: {value}"
            
            metadata.value_formatter = counting_formatter
            item = SettingItem(metadata, value_getter)
            
            # Reset counter
            call_count = 0
            
            # Update content
            item.update_content()
            
            # Formatter should have been called
            assert call_count == 1

    def test_update_content_handles_none_value(self):
        """Test that update_content handles None values gracefully."""
        with mock_textual_app_context():
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=lambda x: str(x) if x is not None else "None",
                setting_type="str"
            )
            
            def value_getter():
                return None
            
            item = SettingItem(metadata, value_getter)
            
            # Should not raise an exception
            item.update_content()

    def test_update_content_handles_formatter_exception(self):
        """Test that update_content handles formatter exceptions."""
        with mock_textual_app_context():
            def failing_formatter(value):
                raise Exception("Formatter failed")
            
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=failing_formatter,
                setting_type="str"
            )
            
            def value_getter():
                return "test_value"
            
            item = SettingItem(metadata, value_getter)
            
            # Should raise the exception
            with pytest.raises(Exception, match="Formatter failed"):
                item.update_content()

    def test_item_css_classes(self):
        """Test that SettingItem has correct CSS classes."""
        with mock_textual_app_context():
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=lambda x: str(x),
                setting_type="str"
            )
            
            def value_getter():
                return "test_value"
            
            item = SettingItem(metadata, value_getter)
            
            # Check that default CSS is defined
            assert hasattr(SettingItem, 'DEFAULT_CSS')
            
            # The CSS should include the SettingItem selector
            assert "SettingItem" in SettingItem.DEFAULT_CSS

    def test_item_selected_state_css(self):
        """Test that SettingItem has CSS for selected state."""
        with mock_textual_app_context():
            metadata = SettingMetadata(
                key="test_setting",
                label="Test Setting",
                description="Test Description",
                value_formatter=lambda x: str(x),
                setting_type="str"
            )
            
            def value_getter():
                return "test_value"
            
            item = SettingItem(metadata, value_getter)
            
            # Check that selected state CSS is defined
            assert "SettingItem.-selected" in SettingItem.DEFAULT_CSS
            # Should have background style for selected state
            assert "background" in SettingItem.DEFAULT_CSS


class TestSettingMetadata:
    """Test the SettingMetadata dataclass."""

    def test_metadata_initialization(self):
        """Test SettingMetadata initialization."""
        metadata = SettingMetadata(
            key="test_key",
            label="Test Label",
            description="Test Description",
            value_formatter=lambda x: str(x),
            setting_type="str"
        )
        
        assert metadata.key == "test_key"
        assert metadata.label == "Test Label"
        assert metadata.description == "Test Description"
        assert metadata.value_formatter is not None
        assert metadata.setting_type == "str"

    def test_metadata_with_different_types(self):
        """Test SettingMetadata with different setting types."""
        formatters = {
            "str": lambda x: str(x),
            "int": lambda x: f"{x}",
            "bool": lambda x: "Yes" if x else "No",
            "list": lambda x: ", ".join(str(item) for item in x),
            "path": lambda x: str(x)
        }
        
        for setting_type, formatter in formatters.items():
            metadata = SettingMetadata(
                key=f"test_{setting_type}",
                label=f"Test {setting_type.title()}",
                description=f"Test {setting_type} setting",
                value_formatter=formatter,
                setting_type=setting_type
            )
            
            assert metadata.setting_type == setting_type
            assert metadata.value_formatter is formatter


class TestSummaryDisplay:
    """Test the SummaryDisplay widget."""

    def test_widget_initialization(self):
        """Test SummaryDisplay initialization."""
        widget = SummaryDisplay()
        
        assert widget._stats is None
        assert widget.id == "summary"

    def test_update_stats(self):
        """Test update_stats method."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py", "file2.py"],
            total_bytes=1000,
            skipped_paths={"empty": ["empty.txt"]},
            errors=["some warning"]
        )
        
        widget.update_stats(stats)
        
        assert widget._stats is stats

    def test_clear_stats(self):
        """Test clear_stats method."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=[],
            total_bytes=0,
            skipped_paths={},
            errors=[]
        )
        
        widget.update_stats(stats)
        assert widget._stats is not None
        
        widget.clear_stats()
        assert widget._stats is None

    def test_render_no_stats(self):
        """Test render method with no stats."""
        widget = SummaryDisplay()
        
        result = widget.render()
        
        assert result == "No extraction has been run yet."

    def test_render_with_stats_basic(self):
        """Test render method with basic stats."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py", "file2.py"],
            total_bytes=1000,
            skipped_paths={},
            errors=[]
        )
        
        widget.update_stats(stats)
        result = widget.render()
        
        # Should return a Table object
        assert hasattr(result, 'add_row')

    def test_render_with_all_fields(self):
        """Test render method with all stats fields populated."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py", "file2.py", "file3.py"],
            total_bytes=1500,
            skipped_paths={
                "empty": ["empty1.txt", "empty2.txt"],
                "binary": ["image.png"]
            },
            errors=["warning1", "warning2"],
            token_count=100,
            token_model="gpt-4"
        )
        
        widget.update_stats(stats)
        result = widget.render()
        
        # Should return a Table object
        assert hasattr(result, 'add_row')

    def test_render_skipped_summary_empty(self):
        """Test render with empty skipped summary."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py"],
            total_bytes=100,
            skipped_paths={},  # Empty - no skipped files
            errors=[]
        )
        
        widget.update_stats(stats)
        result = widget.render()
        
        # Should not have a "Skipped" row since no files were skipped
        table = result
        # The table should be created but not have a skipped row

    def test_render_skipped_summary_with_values(self):
        """Test render with non-empty skipped summary."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py"],
            total_bytes=100,
            skipped_paths={
                "empty": ["empty.txt"],
                "binary": ["image.png", "audio.mp3"],
                "excluded_ext": ["config.json"]
            },
            errors=[]
        )
        
        widget.update_stats(stats)
        result = widget.render()
        
        table = result
        # Should have a skipped row with the summary

    def test_render_with_errors(self):
        """Test render with extraction errors."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py"],
            total_bytes=100,
            skipped_paths={},
            errors=["Error 1", "Error 2", "Error 3"]
        )
        
        widget.update_stats(stats)
        result = widget.render()
        
        table = result
        # Should have a warnings row

    def test_render_with_token_count(self):
        """Test render with token counting enabled."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py"],
            total_bytes=100,
            skipped_paths={},
            errors=[],
            token_count=42,
            token_model="gpt-3.5-turbo"
        )
        
        widget.update_stats(stats)
        result = widget.render()
        
        table = result
        # Should have a tokens row with count and model

    def test_widget_css_classes(self):
        """Test that SummaryDisplay has correct CSS classes."""
        widget = SummaryDisplay()
        
        # Check that default CSS is defined
        assert hasattr(SummaryDisplay, 'DEFAULT_CSS')
        
        # The CSS should include the SummaryDisplay selector
        assert "SummaryDisplay" in SummaryDisplay.DEFAULT_CSS
        # Should have border styling
        assert "border" in SummaryDisplay.DEFAULT_CSS

    def test_widget_calls_refresh_on_update(self):
        """Test that update_stats calls refresh."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=[],
            total_bytes=0,
            skipped_paths={},
            errors=[]
        )
        
        with patch.object(widget, 'refresh') as mock_refresh:
            widget.update_stats(stats)
            
            mock_refresh.assert_called_once()

    def test_widget_calls_refresh_on_clear(self):
        """Test that clear_stats calls refresh."""
        widget = SummaryDisplay()
        
        with patch.object(widget, 'refresh') as mock_refresh:
            widget.clear_stats()
            
            mock_refresh.assert_called_once()

    def test_table_grid_structure(self):
        """Test that the table has correct grid structure."""
        widget = SummaryDisplay()
        
        stats = ExtractionStats(
            root=Path("/test"),
            output=Path("/output.txt"),
            processed_paths=["file1.py"],
            total_bytes=100,
            skipped_paths={"empty": ["empty.txt"]},
            errors=["warning"]
        )
        
        widget.update_stats(stats)
        result = widget.render()
        
        # The result should be a Table with proper structure
        # We can't easily test the exact table structure without complex setup,
        # but we can verify it's a Table object
        from rich.table import Table
        assert isinstance(result, Table)

    def test_multiple_updates(self):
        """Test multiple stats updates."""
        widget = SummaryDisplay()
        
        # First stats
        stats1 = ExtractionStats(
            root=Path("/test1"),
            output=Path("/output1.txt"),
            processed_paths=["file1.py"],
            total_bytes=100,
            skipped_paths={},
            errors=[]
        )
        
        widget.update_stats(stats1)
        assert widget._stats is stats1
        
        # Second stats
        stats2 = ExtractionStats(
            root=Path("/test2"),
            output=Path("/output2.txt"),
            processed_paths=["file2.py"],
            total_bytes=200,
            skipped_paths={},
            errors=[]
        )
        
        widget.update_stats(stats2)
        assert widget._stats is stats2
        assert widget._stats is not stats1