"""Tests for TUI responsive design to small terminals."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from proxtract.state import AppState
from proxtract.tui.screens.main_screen import MainScreen
from proxtract.tui.screens.extract_screen import ExtractScreen


class TestResponsiveDesign:
    """Test responsive breakpoint detection and layout adaptation."""

    def test_main_screen_breakpoint_detection(self):
        """Test that MainScreen correctly detects and applies responsive breakpoints."""
        app_state = Mock(spec=AppState)
        screen = MainScreen(app_state)
        
        # Test tiny width (very small terminals)
        screen._update_breakpoints(40)
        assert screen.has_class("bp-tiny")
        assert not screen.has_class("bp-narrow")
        assert not screen.has_class("bp-compact")
        
        # Test narrow width (small-medium terminals)  
        screen.set_class(False, "bp-tiny")  # Reset tiny class
        screen._update_breakpoints(70)
        assert not screen.has_class("bp-tiny")
        assert screen.has_class("bp-narrow")
        assert not screen.has_class("bp-compact")
        
        # Test compact width (compact view threshold)
        screen.set_class(False, "bp-narrow")  # Reset narrow class
        screen._update_breakpoints(50)
        assert not screen.has_class("bp-tiny")
        assert not screen.has_class("bp-narrow")
        assert screen.has_class("bp-compact")
        
        # Test normal width (large terminals)
        screen.set_class(False, "bp-compact")  # Reset compact class
        screen._update_breakpoints(120)
        assert not screen.has_class("bp-tiny")
        assert not screen.has_class("bp-narrow")
        assert not screen.has_class("bp-compact")

    def test_extract_screen_breakpoint_detection(self):
        """Test that ExtractScreen correctly detects and applies responsive breakpoints."""
        app_state = Mock(spec=AppState)
        screen = ExtractScreen(app_state)
        
        # Test tiny width detection
        screen._update_breakpoints(40)
        assert screen.has_class("bp-tiny")
        assert not screen.has_class("bp-narrow")
        assert not screen.has_class("bp-compact")
        
        # Test narrow width detection
        screen.set_class(False, "bp-tiny")
        screen._update_breakpoints(70)
        assert not screen.has_class("bp-tiny")
        assert screen.has_class("bp-narrow")
        assert not screen.has_class("bp-compact")

    def test_breakpoint_width_constants(self):
        """Test that breakpoint width constants are reasonable for small terminals."""
        # Tiny screens should work with very small widths
        assert MainScreen.TINY_WIDTH == 45
        assert ExtractScreen.TINY_WIDTH == 45
        
        # Narrow should be reasonable for small terminals
        assert MainScreen.NARROW_WIDTH == 80
        assert ExtractScreen.NARROW_WIDTH == 80
        
        # Compact should be the most restrictive
        assert MainScreen.COMPACT_WIDTH == 60
        assert ExtractScreen.COMPACT_WIDTH == 60

    @pytest.mark.parametrize("width,expected_classes", [
        (30, {"bp-tiny"}),
        (40, {"bp-tiny"}),
        (45, {"bp-tiny"}),  # Exactly at tiny threshold
        (50, {"bp-compact"}),  # Should be compact, not tiny
        (60, {"bp-compact"}),  # Exactly at compact threshold
        (70, {"bp-narrow"}),  # Should be narrow, not compact
        (80, {"bp-narrow"}),  # Exactly at narrow threshold
        (120, set()),  # Normal view
    ])
    def test_main_screen_breakpoint_combinations(self, width: int, expected_classes: set):
        """Test various width combinations to ensure correct breakpoint application."""
        app_state = Mock(spec=AppState)
        screen = MainScreen(app_state)
        
        screen._update_breakpoints(width)
        
        for class_name in ["bp-tiny", "bp-narrow", "bp-compact"]:
            expected = class_name in expected_classes
            actual = screen.has_class(class_name)
            assert actual == expected, f"Width {width}: expected {class_name}={expected}, got {actual}"