"""Alien Obfuscator — Gradio application entry point.

This module is a thin launcher that delegates UI construction to the
``alien_obfuscator.ui`` package and injects the retro terminal theme.
Re-exports kept for backward compatibility with existing tests.
"""

import sys

sys.path.insert(0, "src")

from alien_obfuscator.ui.app import build_ui
from alien_obfuscator.ui.challenge import ChallengeAnswerResult, GameOverResult
from alien_obfuscator.ui.helpers import on_color_change
from alien_obfuscator.ui.theme import FALLOUT_CSS, GOOGLE_FONT_HTML, TIMER_HTML

__all__ = [
    "build_ui",
    "ChallengeAnswerResult",
    "GameOverResult",
    "on_color_change",
]

if __name__ == "__main__":
    app = build_ui()
    head_html_content = TIMER_HTML + "\n" + GOOGLE_FONT_HTML + "\n<style id='terminal-theme-css'>" + FALLOUT_CSS + "</style>"
    app.launch(head=head_html_content)
