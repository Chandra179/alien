"""Challenge tab callbacks and types for the Alien Obfuscator.

This module provides the function that generates a random challenge riddle
and the NamedTuple result types used by the challenge event handlers.
"""

import json
import random
from typing import Any, NamedTuple

from alien_obfuscator.config import CHALLENGE_PHRASES, THEME_KEYS
from alien_obfuscator.ui.helpers import riddle_generator


# ---------------------------------------------------------------------------
# NamedTuple result types
# ---------------------------------------------------------------------------


class GameOverResult(NamedTuple):
    """Result returned by the game over event handler.

    Attributes
    ----------
    timer_display : str
        Display string for the timer, typically set to "00:00".
    state_json : str
        JSON-encoded game state.
    game_row : Any
        Gradio update dict for the game row visibility.
    game_over_row : Any
        Gradio update dict for the game over row visibility.
    final_score : Any
        The final score component.
    """

    timer_display: str
    state_json: str
    game_row: Any
    game_over_row: Any
    final_score: Any


class ChallengeAnswerResult(NamedTuple):
    """Result returned by the challenge answer event handler.

    Attributes
    ----------
    feedback : str
        Response message regarding correctness and points.
    correct_update : Any
        Gradio update combining value and visibility properties.
    updated_state : str
        Updated JSON-serialized game state.
    interactive_update : Any
        Gradio update dict to disable challenge options.
    score_update : str
        The updated score to display.
    streak_update : str
        The updated streak to display.
    """

    feedback: str
    correct_update: Any  # Combines both value and visibility properties
    updated_state: str
    interactive_update: Any
    score_update: str
    streak_update: str


class NextChallengeResult(NamedTuple):
    """Result returned by the next challenge event handler.

    Attributes
    ----------
    riddle : str
        The new riddle question.
    options_update : Any
        Gradio update containing new answer options.
    feedback : Any
        Cleared feedback message or updated component.
    reveal : str
        Cleared correct answer reveal message.
    updated_state : str
        Updated JSON-serialized game state.
    """

    riddle: str
    options_update: Any
    feedback: Any
    reveal: str
    updated_state: str


# ---------------------------------------------------------------------------
# Challenge riddle generator
# ---------------------------------------------------------------------------


def generate_challenge_riddle(theme_filter: str) -> tuple[str, str, str]:
    """Generate a random challenge riddle for game mode.

    Parameters
    ----------
    theme_filter : str
        "All" or a specific theme key.

    Returns
    -------
    tuple[str, str, str]
        (riddle_text, options_json, correct_index)
    """
    if theme_filter == "All":
        theme = random.choice(THEME_KEYS)
    else:
        theme = theme_filter

    plaintext = random.choice(CHALLENGE_PHRASES)

    try:
        result = riddle_generator.generate(plaintext, theme)
        return result["riddle"], json.dumps(result["options"]), str(result["correct_index"])
    except Exception as exc:
        return f"Error: {exc}", "[]", "-1"
