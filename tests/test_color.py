"""Unit tests for the TUI terminal color change features in app.py."""

import sys
from pathlib import Path

# Ensure root directory is in path so we can import app.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import build_ui, on_color_change


def test_on_color_change() -> None:
    """Test that the on_color_change function returns the correct color name.

    This function verifies that the backend event handler for the color dropdown
    returns the same color string passed to it.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    for color in ["Green", "Blue", "Red", "Light gray"]:
        assert on_color_change(color) == color


def test_color_dropdown_in_ui() -> None:
    """Test that the color dropdown is present in the built Gradio UI.

    This function builds the Gradio UI and asserts that the dropdown for terminal
    color parameters exists with the expected choice values.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    demo = build_ui()
    dropdown_found = False

    for block in demo.blocks.values():
        label = getattr(block, "label", None)
        if label == "[ PARAM: TERMINAL COLOR ]":
            dropdown_found = True
            choices = getattr(block, "choices", [])
            assert choices == [("Green", "Green"), ("Blue", "Blue"), ("Red", "Red"), ("Light gray", "Light gray")] or choices == ["Green", "Blue", "Red", "Light gray"]
            value = getattr(block, "value", None)
            assert value == "Green"

    assert dropdown_found, "Terminal color dropdown was not found in build_ui()."
