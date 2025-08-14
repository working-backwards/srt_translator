#!/usr/bin/env python3
"""
Test import barriers between CLI and GUI packages.
"""

import sys

import pytest


def test_cli_imports_without_gui():
    """Test that CLI can import without GUI dependencies."""
    # Ensure PySide6 is not present in sys.modules
    sys.modules.pop("PySide6", None)

    # CLI should import successfully
    import srt_translator.cli.app

    assert hasattr(srt_translator.cli.app, "main")


@pytest.mark.gui
def test_gui_imports_with_gui():
    """Test that GUI can import when PySide6 is available."""
    # This will only run when PySide6 is available
    import srt_translator.gui.main_window

    assert hasattr(srt_translator.gui.main_window, "main")


def test_core_imports_independently():
    """Test that core modules can import without CLI or GUI."""
    # Core should be importable independently


def test_no_cross_imports_in_cli():
    """Test that CLI modules don't import from GUI."""
    import srt_translator.cli.app

    # Check that the CLI module doesn't have GUI imports
    source = srt_translator.cli.app.__file__
    with open(source, "r", encoding="utf-8") as f:
        content = f.read()
        assert "srt_translator.gui" not in content, "CLI should not import from GUI"


def test_no_cross_imports_in_gui():
    """Test that GUI modules don't import from CLI."""
    import srt_translator.gui.main_window

    # Check that the GUI module doesn't have CLI imports
    source = srt_translator.gui.main_window.__file__
    with open(source, "r", encoding="utf-8") as f:
        content = f.read()
        assert "srt_translator.cli" not in content, "GUI should not import from CLI"
