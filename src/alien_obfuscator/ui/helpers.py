"""Shared UI helpers and backend bootstrap for the Alien Obfuscator.

This module initialises the LLM backend and RiddleGenerator singleton, and
provides shared formatting and event-handler utilities used across the
Gradio tabs.
"""

import os

from dotenv import load_dotenv

from alien_obfuscator.config import (
    DEFAULT_BACKEND,
    HF_DEFAULT_MODEL,
    MODAL_DEFAULT_MODEL,
    OPENCODE_GO_DEFAULT_MODEL,
    OPENROUTER_DEFAULT_MODEL,
)
from alien_obfuscator.riddle_generator import (
    HuggingFaceBackend,
    MockBackend,
    ModalBackend,
    OpenCodeGoBackend,
    OpenRouterBackend,
    RiddleGenerator,
)

# ---------------------------------------------------------------------------
# Backend bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

backend = os.environ.get("HF_BACKEND", DEFAULT_BACKEND)
if backend == "mock":
    _backend = MockBackend()
elif backend == "openrouter":
    model = os.environ.get("OPENROUTER_MODEL", OPENROUTER_DEFAULT_MODEL)
    _backend = OpenRouterBackend(model)
elif backend == "opencode-go":
    model = os.environ.get("OPENCODE_GO_MODEL", OPENCODE_GO_DEFAULT_MODEL)
    _backend = OpenCodeGoBackend(model)
elif backend == "modal":
    model = os.environ.get("MODAL_MODEL", MODAL_DEFAULT_MODEL)
    _backend = ModalBackend(model)
else:
    _backend = HuggingFaceBackend(HF_DEFAULT_MODEL)

riddle_generator = RiddleGenerator(backend=_backend)

# ---------------------------------------------------------------------------
# Shared formatter
# ---------------------------------------------------------------------------


def _format_riddle_card(data: dict) -> str:
    """Format a riddle dict as a shareable text card.

    Parameters
    ----------
    data : dict
        Riddle response containing ``riddle``, ``options``, and
        ``correct_index``.

    Returns
    -------
    str
        Formatted markdown-like text suitable for copy-paste.
    """
    options_text = "\n".join(f"{chr(65 + i)}) {opt}" for i, opt in enumerate(data["options"]))
    return (
        f"Alien Obfuscator Riddle\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{data['riddle']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{options_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Can you decipher this before the alien does?"
    )


# ---------------------------------------------------------------------------
# Misc event handlers
# ---------------------------------------------------------------------------


def on_color_change(color: str) -> None:
    """Handle TUI terminal color changes.

    This function is triggered when the user selects a different color option
    from the dropdown menu. It accepts the selected color name but returns
    None, as styling modifications are applied client-side via JavaScript.

    Parameters
    ----------
    color : str
        The selected color name ("Green", "Blue", "Red", "Light gray").

    Returns
    -------
    None
    """
    pass
