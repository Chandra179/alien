"""Alien Obfuscator — Gradio application entry point.

This module assembles the Gradio UI with three tabs (Encrypt, Solve,
Challenge) and wires them to the riddle generator, corpus manager, and
game engine.
"""

import json
import os
import random
from typing import Any, NamedTuple, Union

import gradio as gr
from dotenv import load_dotenv

from alien_obfuscator.config import (
    CHALLENGE_PHRASES,
    DEFAULT_BACKEND,
    DEFAULT_GAME_DURATION_MINUTES,
    HF_DEFAULT_MODEL,
    MAX_PLAINTEXT_LENGTH,
    NUM_OPTIONS,
    OPENCODE_GO_DEFAULT_MODEL,
    OPENROUTER_DEFAULT_MODEL,
    POINTS_PER_CORRECT,
    SPEED_BONUS_POINTS,
    SPEED_BONUS_SECONDS,
    STREAK_BONUS_POINTS,
    THEME_KEYS,
    THEME_LABELS,
)
from alien_obfuscator.riddle_generator import (
    HuggingFaceBackend,
    MockBackend,
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
else:
    _backend = HuggingFaceBackend(HF_DEFAULT_MODEL)

riddle_generator = RiddleGenerator(backend=_backend)

TIMER_HTML = """
<script>
(function() {
    function findTimerInput() {
        var el = document.getElementById('timer-display');
        if (!el) return null;
        return el.querySelector('input, textarea');
    }

    window.startGameTimer = function(durationSeconds) {
        window.gameEndTime = Date.now() + durationSeconds * 1000;
        window.riddleStartTime = Date.now();
        if (window.gameTimerInterval) {
            clearInterval(window.gameTimerInterval);
        }

        function updateTimer() {
            var remainingMs = Math.max(0, window.gameEndTime - Date.now());
            var remainingSec = Math.floor(remainingMs / 1000);
            var minutes = Math.floor(remainingSec / 60);
            var seconds = remainingSec % 60;
            var timeStr = (minutes < 10 ? '0' : '') + minutes + ':' + (seconds < 10 ? '0' : '') + seconds;

            var timerInput = findTimerInput();
            if (timerInput) {
                timerInput.value = timeStr;
            }

            if (remainingMs <= 0) {
                clearInterval(window.gameTimerInterval);
                var btn = document.getElementById('game-over-trigger');
                if (btn) {
                    btn.click();
                }
            }
        }

        updateTimer();
        window.gameTimerInterval = setInterval(updateTimer, 500);
    };

    window.stopGameTimer = function() {
        if (window.gameTimerInterval) {
            clearInterval(window.gameTimerInterval);
        }
    };
})();
</script>
"""

# ---------------------------------------------------------------------------
# Custom Fallout / RobCo Terminal Styling
# ---------------------------------------------------------------------------

FALLOUT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');

:root {
    --terminal-color: #33ff33;
    --terminal-color-glow: rgba(51, 255, 51, 0.8);
    --terminal-color-glow-low: rgba(51, 255, 51, 0.5);
    --terminal-color-glow-container: rgba(51, 255, 51, 0.25);
    --terminal-color-glow-container-outer: rgba(51, 255, 51, 0.15);
    --terminal-bg-glow: #0d1f0d;
    --terminal-bg: #030703;
    --terminal-placeholder: #1a5c1a;
    --terminal-disabled-bg: #010301;
    --terminal-disabled-color: #114411;
    --terminal-border-dim: #22aa22;
}

/* Apply VT323 retro font and scanline styles to all components */
body, .gradio-container, .gradio-container * {
    font-family: 'VT323', 'Courier New', Courier, monospace !important;
    font-size: 1.25rem !important;
    border-radius: 0px !important;
    box-shadow: none !important;
    line-height: 1.3 !important;
}

body {
    background-color: var(--terminal-bg) !important;
    color: var(--terminal-color) !important;
    margin: 0;
    padding: 0;
}

/* Subtle scanlines overlay simulating CRT screen */
body::before {
    content: " ";
    display: block;
    position: fixed;
    top: 0; left: 0; bottom: 0; right: 0;
    background: linear-gradient(
        rgba(18, 16, 16, 0) 50%, 
        rgba(0, 0, 0, 0.22) 50%
    );
    background-size: 100% 4px;
    z-index: 99999;
    pointer-events: none;
}

/* Container framing with classic terminal border and CRT glow */
.gradio-container {
    background-color: var(--terminal-bg) !important;
    border: 3px solid var(--terminal-color) !important;
    box-shadow: 0 0 25px var(--terminal-color-glow-container) inset, 0 0 15px var(--terminal-color-glow-container-outer) !important;
    max-width: 950px !important;
    margin: 40px auto !important;
    padding: 25px !important;
}

/* Headers with glow effects */
h1, h2, h3, h4, h5, h6 {
    color: var(--terminal-color) !important;
    text-shadow: 0 0 8px var(--terminal-color-glow) !important;
    font-weight: bold !important;
    text-transform: uppercase !important;
}
h1 { font-size: 2.4rem !important; }
h2 { font-size: 1.9rem !important; }
h3 { font-size: 1.6rem !important; }

/* Plain text and label adjustments */
p, span, li {
    color: var(--terminal-color) !important;
    text-shadow: 0 0 3px var(--terminal-color-glow-low) !important;
}

/* Flat solid terminal panels for all Gradio blocks */
.block, .form, .panel, .gr-box, .gr-panel, .gr-block {
    background-color: #000000 !important;
    border: 1px solid var(--terminal-color) !important;
    padding: 15px !important;
    margin-bottom: 12px !important;
}

/* Text Inputs, textareas, and select menus */
input, textarea, select, .gr-input, .gr-textarea {
    background-color: #000000 !important;
    color: var(--terminal-color) !important;
    border: 1px solid var(--terminal-color) !important;
    font-family: 'VT323', monospace !important;
    padding: 8px !important;
    text-shadow: 0 0 3px var(--terminal-color-glow-low) !important;
}
input::placeholder, textarea::placeholder {
    color: var(--terminal-placeholder) !important;
    text-shadow: none !important;
}
input:focus, textarea:focus, select:focus {
    border-color: var(--terminal-color) !important;
    box-shadow: 0 0 10px var(--terminal-color-glow) !important;
    outline: none !important;
}

/* Dropdown menus & wrappers */
.dropdown-menu, .options, .select-wrap, .dropdown, select {
    background-color: #000000 !important;
    color: var(--terminal-color) !important;
    border: 1px solid var(--terminal-color) !important;
}

/* Retro buttons with glowing hover state */
button, .gr-button {
    background-color: var(--terminal-bg-glow) !important;
    color: var(--terminal-color) !important;
    border: 1px solid var(--terminal-color) !important;
    text-transform: uppercase !important;
    font-weight: bold !important;
    font-family: 'VT323', monospace !important;
    padding: 8px 16px !important;
    cursor: pointer !important;
    transition: all 0.15s ease-in-out !important;
    text-shadow: 0 0 3px var(--terminal-color-glow-low) !important;
}
button:hover, .gr-button:hover {
    background-color: var(--terminal-color) !important;
    color: #000000 !important;
    box-shadow: 0 0 12px var(--terminal-color-glow) !important;
    text-shadow: none !important;
}
button:disabled, .gr-button:disabled {
    background-color: var(--terminal-disabled-bg) !important;
    color: var(--terminal-disabled-color) !important;
    border-color: var(--terminal-disabled-color) !important;
    cursor: not-allowed !important;
    text-shadow: none !important;
}

/* Tab bar customization */
.tab-nav, [role="tablist"], .tabs {
    border-bottom: 2px solid var(--terminal-color) !important;
    background-color: #000000 !important;
    margin-bottom: 15px !important;
}
.tab-nav button, [role="tab"], .tabs button {
    background-color: transparent !important;
    color: var(--terminal-border-dim) !important;
    border: none !important;
    font-size: 1.5rem !important;
    padding: 10px 18px !important;
}
.tab-nav button:hover, [role="tab"]:hover, .tabs button:hover {
    color: var(--terminal-color) !important;
}
.tab-nav button.selected, [aria-selected="true"], .tabs button.selected, .tabitem.selected {
    color: var(--terminal-color) !important;
    border: 1px solid var(--terminal-color) !important;
    border-bottom: 1px solid var(--terminal-bg) !important;
    background-color: var(--terminal-bg-glow) !important;
    text-shadow: 0 0 6px var(--terminal-color-glow) !important;
}

/* Header style specifically for terminal branding */
.terminal-header {
    border-bottom: 2px dashed var(--terminal-color) !important;
    margin-bottom: 20px !important;
    padding-bottom: 10px !important;
}
.terminal-header-text {
    font-family: 'VT323', monospace !important;
    color: var(--terminal-color) !important;
    text-shadow: 0 0 5px var(--terminal-color-glow) !important;
    line-height: 1.2 !important;
    white-space: pre;
}

/* Text labels on panels and widgets */
.block-label, .gr-block-label, label, label span {
    background-color: #000000 !important;
    color: var(--terminal-color) !important;
    font-family: 'VT323', monospace !important;
    text-transform: uppercase !important;
    font-weight: bold !important;
}

/* Custom styles for checkboxes and radios */
.gr-radio, input[type="radio"], input[type="checkbox"] {
    accent-color: var(--terminal-color) !important;
}
.gr-radio label, .radio-group label {
    border: 1px solid var(--terminal-border-dim) !important;
    color: var(--terminal-border-dim) !important;
    background-color: #000000 !important;
}
.gr-radio label.selected, .radio-group label.selected {
    border-color: var(--terminal-color) !important;
    color: var(--terminal-color) !important;
    background-color: var(--terminal-bg-glow) !important;
    text-shadow: 0 0 4px var(--terminal-color-glow-low) !important;
}

/* Inner elements for custom look */
.copy-btn, button.svelte-custom {
    background-color: var(--terminal-bg-glow) !important;
    border: 1px solid var(--terminal-color) !important;
    color: var(--terminal-color) !important;
}

#game-state-input, #answer-time-left {
    display: none !important;
}
"""

GOOGLE_FONT_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
"""


# ---------------------------------------------------------------------------
# Shared UI helpers
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
# Encrypt tab
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Solve tab
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Challenge tab
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


class GameOverResult(NamedTuple):
    """Result returned by the game over event handler.

    Attributes
    ----------
    timer_display : str
        Display string for the timer, typically set to "00:00".
    game_state : str
        JSON-encoded game state.
    game_row : Any
        Gradio update dict for the game row visibility.
    game_over_row : Any
        Gradio update dict for the game over row visibility.
    final_score : str
        The final score as a string.
    """

    timer_display: str
    game_state: str
    game_row: Any
    game_over_row: Any
    final_score: str


class ChallengeAnswerResult(NamedTuple):
    """Result returned by the challenge answer event handler.

    Attributes
    ----------
    feedback : str
        Response message regarding correctness and points.
    reveal : str
        Correct answer representation if incorrect, else empty string.
    updated_state : str
        Updated JSON-serialized game state.
    visibility_update : Any
        Gradio update dict for solution visibility.
    interactive_update : Any
        Gradio update dict to disable challenge options.
    score_update : str
        The updated score to display.
    streak_update : str
        The updated streak to display.
    """

    feedback: str
    reveal: str
    updated_state: str
    visibility_update: Any
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


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------


def build_ui() -> gr.Blocks:
    """Construct and return the Gradio Blocks application.

    Returns
    -------
    gr.Blocks
        The fully assembled Gradio interface with Fallout themed terminal style.
    """
    with gr.Blocks(title="Alien Obfuscator") as demo:
        gr.HTML("""
        <div class="terminal-header">
            <div class="terminal-header-text">========================================================================
ROBCO INDUSTRIES (TM) UNIFIED OPERATING SYSTEM
COPYRIGHT 2075-2077 ROBCO INTERNATIONAL
- USER: OUTLANDER
- SECURE TERMINAL: ALIEN-OBFUSCATOR-v1.0
        </div>
        """)

        with gr.Row():
            with gr.Column(scale=3):
                color_dropdown = gr.Dropdown(
                    choices=["Green", "Blue", "Red", "Light gray"],
                    value="Green",
                    label="[ PARAM: TERMINAL COLOR ]",
                    interactive=True,
                )
                color_dropdown.change(
                    on_color_change,
                    inputs=color_dropdown,
                    outputs=None,
                    js="""(color) => {
                        const root = document.documentElement;
                        if (color === "Green") {
                            root.style.setProperty('--terminal-color', '#33ff33');
                            root.style.setProperty('--terminal-color-glow', 'rgba(51, 255, 51, 0.8)');
                            root.style.setProperty('--terminal-color-glow-low', 'rgba(51, 255, 51, 0.5)');
                            root.style.setProperty('--terminal-color-glow-container', 'rgba(51, 255, 51, 0.25)');
                            root.style.setProperty('--terminal-color-glow-container-outer', 'rgba(51, 255, 51, 0.15)');
                            root.style.setProperty('--terminal-bg-glow', '#0d1f0d');
                            root.style.setProperty('--terminal-bg', '#030703');
                            root.style.setProperty('--terminal-placeholder', '#1a5c1a');
                            root.style.setProperty('--terminal-disabled-bg', '#010301');
                            root.style.setProperty('--terminal-disabled-color', '#114411');
                            root.style.setProperty('--terminal-border-dim', '#22aa22');
                        } else if (color === "Blue") {
                            root.style.setProperty('--terminal-color', '#3399ff');
                            root.style.setProperty('--terminal-color-glow', 'rgba(51, 153, 255, 0.8)');
                            root.style.setProperty('--terminal-color-glow-low', 'rgba(51, 153, 255, 0.5)');
                            root.style.setProperty('--terminal-color-glow-container', 'rgba(51, 153, 255, 0.25)');
                            root.style.setProperty('--terminal-color-glow-container-outer', 'rgba(51, 153, 255, 0.15)');
                            root.style.setProperty('--terminal-bg-glow', '#0a1c33');
                            root.style.setProperty('--terminal-bg', '#02050a');
                            root.style.setProperty('--terminal-placeholder', '#153e66');
                            root.style.setProperty('--terminal-disabled-bg', '#000103');
                            root.style.setProperty('--terminal-disabled-color', '#0f2d4a');
                            root.style.setProperty('--terminal-border-dim', '#2277aa');
                        } else if (color === "Red") {
                            root.style.setProperty('--terminal-color', '#ff3333');
                            root.style.setProperty('--terminal-color-glow', 'rgba(255, 51, 51, 0.8)');
                            root.style.setProperty('--terminal-color-glow-low', 'rgba(255, 51, 51, 0.5)');
                            root.style.setProperty('--terminal-color-glow-container', 'rgba(255, 51, 51, 0.25)');
                            root.style.setProperty('--terminal-color-glow-container-outer', 'rgba(255, 51, 51, 0.15)');
                            root.style.setProperty('--terminal-bg-glow', '#2b0a0a');
                            root.style.setProperty('--terminal-bg', '#0a0202');
                            root.style.setProperty('--terminal-placeholder', '#661515');
                            root.style.setProperty('--terminal-disabled-bg', '#030000');
                            root.style.setProperty('--terminal-disabled-color', '#4a0f0f');
                            root.style.setProperty('--terminal-border-dim', '#aa2222');
                        } else if (color === "Light gray") {
                            root.style.setProperty('--terminal-color', '#e0e0e0');
                            root.style.setProperty('--terminal-color-glow', 'rgba(224, 224, 224, 0.8)');
                            root.style.setProperty('--terminal-color-glow-low', 'rgba(224, 224, 224, 0.5)');
                            root.style.setProperty('--terminal-color-glow-container', 'rgba(224, 224, 224, 0.25)');
                            root.style.setProperty('--terminal-color-glow-container-outer', 'rgba(224, 224, 224, 0.15)');
                            root.style.setProperty('--terminal-bg-glow', '#242424');
                            root.style.setProperty('--terminal-bg', '#0a0a0a');
                            root.style.setProperty('--terminal-placeholder', '#5c5c5c');
                            root.style.setProperty('--terminal-disabled-bg', '#030303');
                            root.style.setProperty('--terminal-disabled-color', '#444444');
                            root.style.setProperty('--terminal-border-dim', '#aaaaaa');
                        }
                        return color;
                    }"""
                )
                with gr.Tabs():
                    # ---------------- Encrypt ----------------
                    with gr.Tab("Encrypt"):
                        with gr.Row():
                            with gr.Column():
                                plaintext_input = gr.Textbox(
                                    label="[ INPUT: MESSAGE TO ENCRYPT ]",
                                    placeholder="Enter your secret message...",
                                    lines=2,
                                    max_lines=3,
                                )
                                theme_dropdown = gr.Dropdown(
                                    choices=[(label, key) for key, label in THEME_LABELS.items()],
                                    value="greek_myth",
                                    label="[ PARAM: THEME SELECT ]",
                                )
                                encrypt_btn = gr.Button("> ENCRYPT")

                        with gr.Row(visible=False) as encrypt_output_row:
                            with gr.Column():
                                riddle_card = gr.Textbox(
                                    label="[ OUTPUT: GENERATED RIDDLE CARD ]",
                                    lines=10,
                                    interactive=False,
                                    buttons=["copy"],
                                )
                                correct_hint = gr.Textbox(
                                    label="[ SECURE DATA: CORRECT ANSWER ]",
                                    interactive=False,
                                )
                                encrypt_error = gr.Textbox(
                                    label="[ SYSTEM STATUS ]",
                                    interactive=False,
                                    visible=False,
                                )
                                riddle_state = gr.Textbox(visible=False)

                        def on_encrypt(plain: str, theme: str):
                            card, hint, err, state = encrypt_message(plain, theme)
                            return {
                                encrypt_output_row: gr.update(visible=True),
                                riddle_card: card,
                                correct_hint: hint,
                                encrypt_error: gr.update(value=err, visible=bool(err)),
                                riddle_state: state,
                            }

                        encrypt_btn.click(
                            on_encrypt,
                            inputs=[plaintext_input, theme_dropdown],
                            outputs=[
                                encrypt_output_row,
                                riddle_card,
                                correct_hint,
                                encrypt_error,
                                riddle_state,
                            ],
                        )

                    # ---------------- Solve ----------------
                    with gr.Tab("Solve"):
                        with gr.Row():
                            with gr.Column():
                                paste_input = gr.Textbox(
                                    label="[ INPUT: PASTE RIDDLE CARD ]",
                                    placeholder="Paste the shared riddle here...",
                                    lines=10,
                                )
                                parse_btn = gr.Button("> PARSE RIDDLE")

                        with gr.Row(visible=False) as solve_output_row:
                            with gr.Column():
                                riddle_display = gr.Textbox(
                                    label="[ DECIPHERING: RIDDLE ]",
                                    lines=5,
                                    interactive=False,
                                )
                                solve_options = gr.Radio(
                                    label="[ SELECT ANSWER ]",
                                    choices=[],
                                    interactive=True,
                                )
                                solve_feedback = gr.Textbox(
                                    label="[ DECRYPTION RESULT ]",
                                    interactive=False,
                                )
                                solve_reveal = gr.Textbox(
                                    label="[ REVEALED ANSWER DATA ]",
                                    interactive=False,
                                )
                                solve_state = gr.Textbox(visible=False)
                                solve_attempts = gr.Textbox(
                                    label="[ ATTACK ATTEMPTS ]",
                                    interactive=False,
                                    visible=False,
                                )
                                next_btn = gr.Button("> DECRYPT ANOTHER?")

                        def on_parse(card: str):
                            riddle, opts_json, err, state = parse_riddle_card(card)
                            if err:
                                return {
                                    solve_output_row: gr.update(visible=False),
                                    solve_feedback: err,
                                }
                            options = json.loads(opts_json)
                            return {
                                solve_output_row: gr.update(visible=True),
                                riddle_display: riddle,
                                solve_options: gr.update(
                                    choices=[f"{chr(65 + i)}) {o}" for i, o in enumerate(options)], value=None
                                ),
                                solve_feedback: "",
                                solve_reveal: "",
                                solve_state: state,
                                solve_attempts: "",
                            }

                        parse_btn.click(
                            on_parse,
                            inputs=paste_input,
                            outputs=[
                                solve_output_row,
                                riddle_display,
                                solve_options,
                                solve_feedback,
                                solve_reveal,
                                solve_state,
                                solve_attempts,
                            ],
                        )

                        def on_answer(selected: str, state: str) -> tuple:
                            if not selected:
                                return "", "", state
                            idx = ord(selected.split(")")[0]) - ord("A")
                            fb, rev, new_state = check_answer(idx, state)
                            return fb, rev, new_state

                        solve_options.change(
                            on_answer,
                            inputs=[solve_options, solve_state],
                            outputs=[solve_feedback, solve_reveal, solve_state],
                        )

                        next_btn.click(
                            lambda: {
                                solve_output_row: gr.update(visible=False),
                                paste_input: "",
                            },
                            outputs=[solve_output_row, paste_input],
                        )

                    # ---------------- Challenge ----------------
                    with gr.Tab("Challenge"):
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("## > CHALLENGE PROTOCOL")
                                gr.Markdown(
                                    "Execute decryption sequences. Complete as many nodes as possible before terminal lockout."
                                )
                                theme_filter = gr.Dropdown(
                                    choices=[("All", "All")]
                                    + [(label, key) for key, label in THEME_LABELS.items() if key != "surprise"],
                                    value="All",
                                    label="[ PARAM: THEME FILTER ]",
                                )
                                start_btn = gr.Button("> START GAME")

                        with gr.Row(visible=False) as game_row:
                            with gr.Column():
                                timer_display = gr.Textbox(
                                    label="[ TIMER: TIME REMAINING ]",
                                    value="10:00",
                                    interactive=False,
                                    elem_id="timer-display",
                                )
                                score_display = gr.Textbox(
                                    label="[ ACCOUNT: SCORE ]",
                                    value="0",
                                    interactive=False,
                                )
                                streak_display = gr.Textbox(
                                    label="[ STATUS: STREAK ]",
                                    value="0",
                                    interactive=False,
                                )
                                challenge_riddle = gr.Textbox(
                                    label="[ ACTIVE RIDDLE ]",
                                    lines=5,
                                    interactive=False,
                                )
                                challenge_options = gr.Radio(
                                    label="[ CHOOSE SOLUTION ]",
                                    choices=[],
                                    interactive=True,
                                )
                                challenge_feedback = gr.Textbox(
                                    label="[ COMMAND FEEDBACK ]",
                                    interactive=False,
                                )
                                challenge_correct = gr.Textbox(
                                    label="[ REVEALED SOLUTION ]",
                                    interactive=False,
                                    visible=False,
                                )
                                next_challenge_btn = gr.Button("> NEXT RIDDLE")
                                end_game_btn = gr.Button("> END GAME")

                        with gr.Row(visible=False) as game_over_row:
                            with gr.Column():
                                final_score = gr.Textbox(
                                    label="[ SUMMARY: FINAL SCORE ]",
                                    interactive=False,
                                )
                                new_game_btn = gr.Button("> NEW GAME")

                        # Game state is stored in a simple hidden textbox for now
                        game_state = gr.Textbox(visible=True, elem_id="game-state-input")
                        answer_time_left = gr.Textbox(visible=True, elem_id="answer-time-left")
                        local_storage_score = gr.Textbox(visible=False)

                        with gr.Row(visible=False):
                            game_over_trigger = gr.Button(
                                "Game Over",
                                elem_id="game-over-trigger",
                            )

                        def on_start_game(theme: str):
                            duration_seconds = DEFAULT_GAME_DURATION_MINUTES * 60
                            riddle, opts, correct = generate_challenge_riddle(theme)
                            options = json.loads(opts)
                            state = json.dumps(
                                {
                                    "score": 0,
                                    "streak": 0,
                                    "time_left": duration_seconds,
                                    "correct_index": int(correct),
                                    "theme": theme,
                                    "riddle_start_time": duration_seconds,
                                    "game_active": True,
                                }
                            )
                            return {
                                game_row: gr.update(visible=True),
                                game_over_row: gr.update(visible=False),
                                challenge_riddle: riddle,
                                challenge_options: gr.update(
                                    choices=[f"{chr(65 + i)}) {o}" for i, o in enumerate(options)],
                                    value=None,
                                    interactive=True,
                                ),
                                challenge_feedback: "",
                                challenge_correct: gr.update(visible=False),
                                score_display: "0",
                                streak_display: "0",
                                timer_display: f"{DEFAULT_GAME_DURATION_MINUTES:02d}:00",
                                game_state: state,
                            }

                        def on_game_over(state: str) -> GameOverResult:
                            """Handle game over when the timer expires.

                            This function takes the current JSON-encoded state, marks the game as inactive,
                            sets remaining time to zero, and prepares the UI transition to the game over screen.

                            Parameters
                            ----------
                            state : str
                                JSON-encoded game state.

                            Returns
                            -------
                            GameOverResult
                                Custom result object containing timer display, game state, UI visibility
                                updates, and the final score.
                            """
                            if not state:
                                return GameOverResult(
                                    "00:00", "", gr.update(visible=False), gr.update(visible=True), "0"
                                )
                            st = json.loads(state)
                            st["game_active"] = False
                            st["time_left"] = 0
                            return GameOverResult(
                                "00:00",
                                json.dumps(st),
                                gr.update(visible=False),
                                gr.update(visible=True),
                                str(st.get("score", 0)),
                            )

                        game_over_trigger.click(
                            on_game_over,
                            inputs=game_state,
                            outputs=[
                                timer_display,
                                game_state,
                                game_row,
                                game_over_row,
                                final_score,
                            ],
                            js="""(state) => { window.stopGameTimer(); return state; }""",
                        )

                        start_btn.click(
                            on_start_game,
                            inputs=theme_filter,
                            outputs=[
                                game_row,
                                game_over_row,
                                challenge_riddle,
                                challenge_options,
                                challenge_feedback,
                                challenge_correct,
                                score_display,
                                streak_display,
                                timer_display,
                                game_state,
                            ],
                            js=f"""(theme) => {{
                                window.startGameTimer({DEFAULT_GAME_DURATION_MINUTES * 60});
                                return theme;
                            }}""",
                        )

                        def on_challenge_answer(
                            selected: str, state: str, current_time_left: Union[str, int]
                        ) -> ChallengeAnswerResult:
                            """Handle the submission of a challenge answer and update game state.

                            This function takes the selected answer, current JSON-encoded state,
                            and the remaining time. It parses the selected option, verifies it against
                            the correct option, calculates base points, streak bonuses, and speed bonuses,
                            and updates the state object before returning the feedback and updated state.

                            Parameters
                            ----------
                            selected : str
                                The option selected by the user (e.g., 'A) ...').
                            state : str
                                JSON-serialized string representing the current game state.
                            current_time_left : Union[str, int]
                                The time remaining in the game at the moment of submission.

                            Returns
                            -------
                            ChallengeAnswerResult
                                Custom result object containing feedback, reveal message, updated game state,
                                solution visibility update, interaction states, and score/streak updates.
                            """
                            try:
                                current_time_left_int = int(current_time_left)
                            except (ValueError, TypeError):
                                current_time_left_int = 0

                            if not selected or not state:
                                return ChallengeAnswerResult("", "", state, gr.update(visible=False), gr.update(), "", "")
                            idx = ord(selected.split(")")[0]) - ord("A")
                            st = json.loads(state)
                            correct_idx = st["correct_index"]
                            st["time_left"] = current_time_left_int
                            if idx == correct_idx:
                                points = POINTS_PER_CORRECT
                                st["streak"] += 1
                                streak_bonus = st["streak"] * STREAK_BONUS_POINTS
                                speed_bonus = 0
                                elapsed = st.get("riddle_start_time", current_time_left_int) - current_time_left_int
                                if elapsed <= SPEED_BONUS_SECONDS:
                                    speed_bonus = SPEED_BONUS_POINTS
                                total_points = points + streak_bonus + speed_bonus
                                st["score"] += total_points
                                fb = f"Correct! +{total_points} points ({points} base + {streak_bonus} streak"
                                if speed_bonus:
                                    fb += f" + {speed_bonus} speed)"
                                else:
                                    fb += ")"
                                reveal = ""
                            else:
                                st["streak"] = 0
                                fb = f"Wrong! The answer was {chr(65 + correct_idx)}."
                                reveal = f"Correct: {chr(65 + correct_idx)}"
                            return ChallengeAnswerResult(
                                fb,
                                reveal,
                                json.dumps(st),
                                gr.update(visible=True),
                                gr.update(interactive=False),
                                str(st.get("score", 0)),
                                str(st.get("streak", 0)),
                            )

                        challenge_options.change(
                            on_challenge_answer,
                            inputs=[challenge_options, game_state, answer_time_left],
                            outputs=[
                                challenge_feedback,
                                challenge_correct,
                                game_state,
                                challenge_correct,
                                challenge_options,
                                score_display,
                                streak_display,
                            ],
                            js="""(selected, state, _) => {
                                var remainingSec = window.gameEndTime
                                    ? Math.max(0, Math.floor((window.gameEndTime - Date.now()) / 1000))
                                    : 0;
                                return [selected, state, remainingSec];
                            }""",
                        ).then(
                            lambda score: score,
                            inputs=score_display,
                            outputs=local_storage_score,
                            js="""(score) => {
                                localStorage.setItem("game_score", score);
                                return score;
                            }""",
                        )

                        def on_next_challenge(state: str, current_time_left: Union[str, int]) -> NextChallengeResult:
                            """Generate the next riddle challenge and update game state.

                            This function parses the current state, generates a new challenge riddle
                            for the current theme, resets/records the starting time for this riddle,
                            and returns the updated options and state.

                            Parameters
                            ----------
                            state : str
                                JSON-serialized string representing the current game state.
                            current_time_left : Union[str, int]
                                The time remaining in the game.

                            Returns
                            -------
                            NextChallengeResult
                                Custom result object containing the new riddle, options update, cleared feedback,
                                cleared reveal message, and the updated game state.
                            """
                            try:
                                current_time_left_int = int(current_time_left)
                            except (ValueError, TypeError):
                                current_time_left_int = 0

                            if not state:
                                return NextChallengeResult("", "", [], "", state)
                            st = json.loads(state)
                            if not st.get("game_active", False):
                                return NextChallengeResult("", "", [], "", state)
                            st["time_left"] = current_time_left_int
                            riddle, opts, correct = generate_challenge_riddle(st["theme"])
                            options = json.loads(opts)
                            st["correct_index"] = int(correct)
                            st["riddle_start_time"] = current_time_left_int
                            return NextChallengeResult(
                                riddle,
                                gr.update(
                                    choices=[f"{chr(65 + i)}) {o}" for i, o in enumerate(options)],
                                    value=None,
                                    interactive=True,
                                ),
                                "",
                                "",
                                json.dumps(st),
                            )

                        next_challenge_btn.click(
                            on_next_challenge,
                            inputs=[game_state, answer_time_left],
                            outputs=[
                                challenge_riddle,
                                challenge_options,
                                challenge_feedback,
                                challenge_correct,
                                game_state,
                            ],
                            js="""(state, _) => {
                                window.riddleStartTime = Date.now();
                                var remainingSec = window.gameEndTime
                                    ? Math.max(0, Math.floor((window.gameEndTime - Date.now()) / 1000))
                                    : 0;
                                return [state, remainingSec];
                            }""",
                        )

                        end_game_btn.click(
                            on_game_over,
                            inputs=game_state,
                            outputs=[
                                timer_display,
                                game_state,
                                game_row,
                                game_over_row,
                                final_score,
                            ],
                            js="""(state) => {
                                window.stopGameTimer();
                                try {
                                    var st = JSON.parse(state);
                                    var lsScore = localStorage.getItem("game_score");
                                    if (lsScore !== null) {
                                        st.score = parseInt(lsScore, 10);
                                    }
                                    state = JSON.stringify(st);
                                } catch (e) {}
                                return state;
                            }""",
                        )

                        new_game_btn.click(
                            lambda: {
                                game_over_row: gr.update(visible=False),
                                theme_filter: "All",
                            },
                            outputs=[game_over_row, theme_filter],
                            js="""() => { window.stopGameTimer(); }""",
                        )

                    # ---------------- About ----------------
                    with gr.Tab("About"):
                        gr.Markdown("""
                        ## > SYSTEM SPECIFICATION: ALIEN OBFUSCATOR v1.0
                        
                        ROBCO INDUSTRIES DEFENSE PROTOCOL (SECURE PORT)

                        ### OPERATION DIRECTIVES
                        1. **[ ENCRYPT ]** — Input plaintext message and select theme cipher.
                           The cryptographic engine will construct a human-resolvable riddle.
                        2. **[ SOLVE ]** — Paste target riddle card and process decryption.
                        3. **[ CHALLENGE ]** — Race against the system timer to solve multiple nodes.

                        ### HARDWARE ARCHITECTURE
                        - User Interface: Gradio Monospace TUI Terminal
                        - Decryption Engine: LLM-powered multi-modal cipher generation
                        - Local Database: Curated public-domain text corpus

                        ### RESOURCE BUDGET
                        - Primary Core: up to 31 Billion parameters
                        - System Allocation: ≤ 32 Billion parameters total
                        """)

    return demo


if __name__ == "__main__":
    app = build_ui()
    head_html_content = TIMER_HTML + "\n" + GOOGLE_FONT_HTML
    app.launch(css=FALLOUT_CSS, head=head_html_content)
