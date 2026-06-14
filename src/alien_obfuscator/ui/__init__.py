"""Alien Obfuscator UI package — Gradio interface components."""

from alien_obfuscator.ui.app import build_ui
from alien_obfuscator.ui.challenge import (
    ChallengeAnswerResult,
    GameOverResult,
    NextChallengeResult,
    generate_challenge_riddle,
)
from alien_obfuscator.ui.encrypt import encrypt_message
from alien_obfuscator.ui.helpers import _format_riddle_card, on_color_change, riddle_generator
from alien_obfuscator.ui.solve import check_answer, parse_riddle_card
from alien_obfuscator.ui.theme import (
    DISABLED_RADIO_CSS,
    FALLOUT_CSS,
    GOOGLE_FONT_HTML,
    TIMER_HTML,
)

__all__ = [
    "build_ui",
    "ChallengeAnswerResult",
    "GameOverResult",
    "NextChallengeResult",
    "generate_challenge_riddle",
    "encrypt_message",
    "_format_riddle_card",
    "on_color_change",
    "riddle_generator",
    "check_answer",
    "parse_riddle_card",
    "DISABLED_RADIO_CSS",
    "FALLOUT_CSS",
    "GOOGLE_FONT_HTML",
    "TIMER_HTML",
]
