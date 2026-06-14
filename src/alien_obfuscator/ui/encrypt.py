"""Encrypt tab callbacks for the Alien Obfuscator Gradio application.

This module provides the function that transforms a plaintext message and
theme selection into an obfuscated riddle.
"""

import json

from alien_obfuscator.config import MAX_PLAINTEXT_LENGTH
from alien_obfuscator.ui.helpers import _format_riddle_card, riddle_generator


def encrypt_message(plaintext: str, theme: str) -> tuple[str, str, str, str]:
    """Generate a riddle from the plaintext and theme.

    Parameters
    ----------
    plaintext : str
        The secret message.
    theme : str
        Selected theme key.

    Returns
    -------
    tuple[str, str, str, str]
        (riddle_card, plaintext_hint, error_message, json_state)
    """
    if not plaintext.strip():
        return (
            "",
            "",
            "Please enter a message to encrypt.",
            "",
        )

    if len(plaintext) > MAX_PLAINTEXT_LENGTH:
        return (
            "",
            "",
            f"Message too long ({len(plaintext)} chars). Max {MAX_PLAINTEXT_LENGTH}.",
            "",
        )

    try:
        result = riddle_generator.generate(plaintext, theme)
        card = _format_riddle_card(result)
        correct_label = result["options"][result["correct_index"]]
        hint = f"Correct answer (for your eyes only): {correct_label}"
        json_state = json.dumps(result)
        return card, hint, "", json_state
    except Exception as exc:
        return (
            "",
            "",
            f"The Codex malfunctioned: {exc}",
            "",
        )
