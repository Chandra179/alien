"""Shared UI helpers and backend bootstrap for the Alien Obfuscator.

This module initialises the LLM backend and RiddleGenerator singleton, and
provides shared formatting and event-handler utilities used across the
Gradio tabs.
"""

import os

from dotenv import load_dotenv

from alien_obfuscator.config import (
    AUTO_FALLBACK_ORDER,
    DEFAULT_BACKEND,
    HF_DEFAULT_MODEL,
    LOCAL_DEFAULT_MODEL,
    LOCAL_QUANTIZE,
    LOCAL_TIMEOUT,
    MODAL_DEFAULT_MODEL,
    OPENCODE_GO_DEFAULT_MODEL,
    OPENROUTER_DEFAULT_MODEL,
)
from alien_obfuscator.riddle_generator import (
    AutoBackend,
    HuggingFaceBackend,
    LocalGPU4BitBackend,
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
elif backend == "local":
    model = os.environ.get("LOCAL_MODEL", LOCAL_DEFAULT_MODEL)
    quantize = os.environ.get("LOCAL_QUANTIZE", LOCAL_QUANTIZE)
    _backend = LocalGPU4BitBackend(model, timeout=LOCAL_TIMEOUT, quantize=quantize)
elif backend == "auto":
    model = os.environ.get("AUTO_MODEL", MODAL_DEFAULT_MODEL)
    quantize = os.environ.get("AUTO_QUANTIZE", LOCAL_QUANTIZE)
    fallback_order_str = os.environ.get("AUTO_FALLBACK_ORDER", AUTO_FALLBACK_ORDER)
    fallback_order = [s.strip() for s in fallback_order_str.split(",")]
    _backend = AutoBackend(model, quantize=quantize, fallback_order=fallback_order)
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
