"""Solve tab callbacks for the Alien Obfuscator Gradio application.

This module provides functions to parse a pasted riddle card and check a
user's selected answer against its state.
"""

import json

from alien_obfuscator.config import NUM_OPTIONS


def parse_riddle_card(card_text: str) -> tuple[str, str, str, str]:
    """Parse a pasted riddle card and extract the riddle + options.

    Parameters
    ----------
    card_text : str
        Raw pasted text from a shared riddle card.

    Returns
    -------
    tuple[str, str, str, str]
        (riddle_display, options_json, error_message, parsed_state)
    """
    lines = [line.strip() for line in card_text.splitlines() if line.strip()]
    if not lines:
        return "", "", "Empty input.", ""

    # Very naive parser: look for lines starting with A) B) C) D) E)
    options = []
    riddle_lines = []
    for line in lines:
        if (
            line.startswith("A) ")
            or line.startswith("B) ")
            or line.startswith("C) ")
            or line.startswith("D) ")
            or line.startswith("E) ")
        ):
            options.append(line[3:].strip())
        elif (
            line
            and not line.startswith("━")
            and not line.startswith("Alien Obfuscator")
            and not line.startswith("Can you")
        ):
            riddle_lines.append(line)

    if len(options) != NUM_OPTIONS:
        return (
            "",
            "",
            f"Could not parse {NUM_OPTIONS} options from the card. Found {len(options)}.",
            "",
        )

    riddle_text = "\n".join(riddle_lines)
    parsed_state = json.dumps({"riddle": riddle_text, "options": options, "attempts": 0})
    return riddle_text, json.dumps(options), "", parsed_state


def check_answer(selected_index: int, parsed_state: str) -> tuple[str, str, str]:
    """Check the selected answer against the parsed state.

    Parameters
    ----------
    selected_index : int
        Index of the selected option (0-4).
    parsed_state : str
        JSON string with the parsed riddle state.

    Returns
    -------
    tuple[str, str, str]
        (feedback_message, reveal_message, updated_state)
    """
    if not parsed_state:
        return "No riddle loaded.", "", ""

    state = json.loads(parsed_state)
    attempts = state.get("attempts", 0) + 1
    state["attempts"] = attempts

    # We don't know the correct answer here because the card doesn't
    # include it. The solver must rely on their own knowledge. We can
    # simulate a "correct" check by accepting any answer as potentially
    # correct and showing a generic reveal, but the real design requires the
    # sender to confirm. For the demo, we show a "reveal" button that the
    # sender can share separately.
    # Instead, we just celebrate the choice and ask the sender for the key.
    feedback = f"You chose: {state['options'][selected_index]} (attempt #{attempts})"
    reveal = "Ask the sender to confirm if you got it right!"
    return feedback, reveal, json.dumps(state)
