"""Alien Obfuscator — Gradio application entry point.

This module assembles the Gradio UI with three tabs (Encrypt, Solve,
Challenge) and wires them to the riddle generator, corpus manager, and
game engine.
"""

import json
import os
import random

import gradio as gr
from dotenv import load_dotenv

from alien_obfuscator.config import (
    APP_TITLE,
    CHALLENGE_PHRASES,
    DEFAULT_BACKEND,
    DEFAULT_GAME_DURATION_MINUTES,
    HF_DEFAULT_MODEL,
    LAUNCH_SERVER_NAME,
    LAUNCH_SERVER_PORT,
    LAUNCH_SHARE,
    MAX_PLAINTEXT_LENGTH,
    MODAL_DEFAULT_MODEL,
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
        elif line and not line.startswith("━") and not line.startswith("Alien Obfuscator") and not line.startswith("Can you"):
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


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------


def build_ui() -> gr.Blocks:
    """Construct and return the Gradio Blocks application.

    Returns
    -------
    gr.Blocks
        The fully assembled Gradio interface.
    """
    with gr.Blocks(title="Alien Obfuscator", head=TIMER_HTML) as demo:
        gr.Markdown(f"# {APP_TITLE}")

        with gr.Row():
            with gr.Column(scale=3):
                with gr.Tabs():
                    # ---------------- Encrypt ----------------
                    with gr.Tab("Encrypt"):
                        with gr.Row():
                            with gr.Column():
                                plaintext_input = gr.Textbox(
                                    label="Message to encrypt",
                                    placeholder="Enter your secret message...",
                                    lines=2,
                                    max_lines=3,
                                )
                                theme_dropdown = gr.Dropdown(
                                    choices=[(label, key) for key, label in THEME_LABELS.items()],
                                    value="greek_myth",
                                    label="Theme",
                                )
                                encrypt_btn = gr.Button("Encrypt")

                        with gr.Row(visible=False) as encrypt_output_row:
                            with gr.Column():
                                riddle_card = gr.Textbox(
                                    label="Generated Riddle",
                                    lines=10,
                                    interactive=False,
                                    buttons=["copy"],
                                )
                                correct_hint = gr.Textbox(
                                    label="Correct Answer (sender only)",
                                    interactive=False,
                                )
                                encrypt_error = gr.Textbox(
                                    label="Status",
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
                                    label="Paste a riddle card",
                                    placeholder="Paste the shared riddle here...",
                                    lines=10,
                                )
                                parse_btn = gr.Button("Parse Riddle")

                        with gr.Row(visible=False) as solve_output_row:
                            with gr.Column():
                                riddle_display = gr.Textbox(
                                    label="Riddle",
                                    lines=5,
                                    interactive=False,
                                )
                                solve_options = gr.Radio(
                                    label="Choose your answer",
                                    choices=[],
                                    interactive=True,
                                )
                                solve_feedback = gr.Textbox(
                                    label="Result",
                                    interactive=False,
                                )
                                solve_reveal = gr.Textbox(
                                    label="Reveal",
                                    interactive=False,
                                )
                                solve_state = gr.Textbox(visible=False)
                                solve_attempts = gr.Textbox(
                                    label="Attempts",
                                    interactive=False,
                                    visible=False,
                                )
                                next_btn = gr.Button("Decrypt another?")

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
                                gr.Markdown("## Challenge Mode")
                                gr.Markdown("Solve as many riddles as you can before time runs out.")
                                theme_filter = gr.Dropdown(
                                    choices=[("All", "All")]
                                    + [(label, key) for key, label in THEME_LABELS.items() if key != "surprise"],
                                    value="All",
                                    label="Theme Filter",
                                )
                                start_btn = gr.Button("Start Game")

                        with gr.Row(visible=False) as game_row:
                            with gr.Column():
                                timer_display = gr.Textbox(
                                    label="Time Remaining",
                                    value="10:00",
                                    interactive=False,
                                    elem_id="timer-display",
                                )
                                score_display = gr.Textbox(
                                    label="Score",
                                    value="0",
                                    interactive=False,
                                )
                                streak_display = gr.Textbox(
                                    label="Streak",
                                    value="0",
                                    interactive=False,
                                )
                                challenge_riddle = gr.Textbox(
                                    label="Riddle",
                                    lines=5,
                                    interactive=False,
                                )
                                challenge_options = gr.Radio(
                                    label="Choose",
                                    choices=[],
                                    interactive=True,
                                )
                                challenge_feedback = gr.Textbox(
                                    label="Feedback",
                                    interactive=False,
                                )
                                challenge_correct = gr.Textbox(
                                    label="Correct Answer",
                                    interactive=False,
                                    visible=False,
                                )
                                next_challenge_btn = gr.Button("Next Riddle")
                                end_game_btn = gr.Button("End Game")

                        with gr.Row(visible=False) as game_over_row:
                            with gr.Column():
                                final_score = gr.Textbox(
                                    label="Final Score",
                                    interactive=False,
                                )
                                new_game_btn = gr.Button("New Game")

                        # Game state is stored in a simple hidden textbox for now
                        game_state = gr.Textbox(visible=False)
                        answer_time_left = gr.Textbox(visible=False)

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
                                ),
                                challenge_feedback: "",
                                challenge_correct: gr.update(visible=False),
                                score_display: "0",
                                streak_display: "0",
                                timer_display: f"{DEFAULT_GAME_DURATION_MINUTES:02d}:00",
                                game_state: state,
                            }

                        def on_game_over(state: str) -> tuple:
                            """Handle game over when the timer expires.

                            Parameters
                            ----------
                            state : str
                                JSON-encoded game state.

                            Returns
                            -------
                            tuple
                                Updates for ``timer_display``, ``game_state``,
                                ``game_row``, ``game_over_row``, and
                                ``final_score``.
                            """
                            if not state:
                                return "00:00", "", gr.update(visible=False), gr.update(visible=True), "0"
                            st = json.loads(state)
                            st["game_active"] = False
                            st["time_left"] = 0
                            return (
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
                            selected: str, state: str, current_time_left: int
                        ) -> tuple:
                            if not selected or not state:
                                return "", "", state, gr.update(visible=False)
                            idx = ord(selected.split(")")[0]) - ord("A")
                            st = json.loads(state)
                            correct_idx = st["correct_index"]
                            st["time_left"] = current_time_left
                            if idx == correct_idx:
                                points = POINTS_PER_CORRECT
                                st["streak"] += 1
                                streak_bonus = st["streak"] * STREAK_BONUS_POINTS
                                speed_bonus = 0
                                elapsed = st.get("riddle_start_time", current_time_left) - current_time_left
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
                            return fb, reveal, json.dumps(st), gr.update(visible=True)

                        challenge_options.change(
                            on_challenge_answer,
                            inputs=[challenge_options, game_state, answer_time_left],
                            outputs=[challenge_feedback, challenge_correct, game_state, challenge_correct],
                            js="""(selected, state, _) => {
                                var remainingSec = window.gameEndTime
                                    ? Math.max(0, Math.floor((window.gameEndTime - Date.now()) / 1000))
                                    : 0;
                                return [selected, state, remainingSec];
                            }""",
                        )

                        def on_next_challenge(state: str, current_time_left: int) -> tuple:
                            if not state:
                                return "", "", [], "", state
                            st = json.loads(state)
                            if not st.get("game_active", False):
                                return "", "", [], "", state
                            st["time_left"] = current_time_left
                            riddle, opts, correct = generate_challenge_riddle(st["theme"])
                            options = json.loads(opts)
                            st["correct_index"] = int(correct)
                            st["riddle_start_time"] = current_time_left
                            return (
                                riddle,
                                gr.update(
                                    choices=[f"{chr(65 + i)}) {o}" for i, o in enumerate(options)],
                                    value=None,
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
                            lambda state: {
                                game_row: gr.update(visible=False),
                                game_over_row: gr.update(visible=True),
                                final_score: json.loads(state).get("score", 0) if state else "0",
                            },
                            inputs=game_state,
                            outputs=[game_row, game_over_row, final_score],
                            js="""(state) => { window.stopGameTimer(); return state; }""",
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
                        ## Alien Obfuscator

                        Built for the **Hugging Face Build Small Hackathon**.

                        ### How to Play
                        1. **Encrypt** — Type a secret message and pick a theme.
                           The AI will generate a riddle that only humans can solve.
                        2. **Solve** — Paste a friend's riddle and guess the answer.
                        3. **Challenge** — Race against the clock to solve as many as you can.

                        ### Technology
                        - Gradio UI
                        - LLM-powered riddle generation
                        - Curated public-domain corpus

                        ### Parameter Budget
                        - Primary LLM: up to 31B parameters
                        - Total: ≤ 32B
                        """)

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.launch(server_name=LAUNCH_SERVER_NAME, server_port=LAUNCH_SERVER_PORT, share=LAUNCH_SHARE)
