"""Alien Obfuscator — Gradio application entry point.

This module assembles the Gradio UI with three tabs (Encrypt, Solve,
Challenge) and wires them to the riddle generator, corpus manager, and
game engine.
"""

import json
import random

import gradio as gr

from alien_obfuscator.config import (
    DEFAULT_BACKEND,
    DEFAULT_GAME_DURATION_MINUTES,
    MAX_PLAINTEXT_LENGTH,
    NUM_OPTIONS,
    POINTS_PER_CORRECT,
    SPEED_BONUS_POINTS,
    SPEED_BONUS_SECONDS,
    STREAK_BONUS_POINTS,
    THEME_LABELS,
)
from alien_obfuscator.corpus_manager import CorpusManager
from alien_obfuscator.riddle_generator import HuggingFaceBackend, MockBackend, RiddleGenerator

# ---------------------------------------------------------------------------
# Backend bootstrap
# ---------------------------------------------------------------------------

corpus_manager = CorpusManager()

if DEFAULT_BACKEND == "mock":
    _backend = MockBackend()
else:
    _backend = HuggingFaceBackend("google/gemma-4-31b-it")

riddle_generator = RiddleGenerator(backend=_backend, corpus_manager=corpus_manager)

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
        f"🛡️ Alien Obfuscator Riddle\n"
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
            "⚠️ Please enter a message to encrypt.",
            "",
        )

    if len(plaintext) > MAX_PLAINTEXT_LENGTH:
        return (
            "",
            "",
            f"⚠️ Message too long ({len(plaintext)} chars). Max {MAX_PLAINTEXT_LENGTH}.",
            "",
        )

    try:
        result = riddle_generator.generate(plaintext, theme)
        card = _format_riddle_card(result)
        correct_label = result["options"][result["correct_index"]]
        hint = f"✅ Correct answer (for your eyes only): {correct_label}"
        json_state = json.dumps(result)
        return card, hint, "", json_state
    except Exception as exc:
        return (
            "",
            "",
            f"💥 The Codex malfunctioned: {exc}",
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
        return "", "", "⚠️ Empty input.", ""

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
        elif line and not line.startswith("━") and not line.startswith("🛡️") and not line.startswith("Can you"):
            riddle_lines.append(line)

    if len(options) != NUM_OPTIONS:
        return (
            "",
            "",
            f"⚠️ Could not parse {NUM_OPTIONS} options from the card. Found {len(options)}.",
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
        return "⚠️ No riddle loaded.", "", ""

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
    feedback = f"🎉 You chose: {state['options'][selected_index]} (attempt #{attempts})"
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
        theme = random.choice(corpus_manager.list_themes())
    else:
        theme = theme_filter

    phrases = [
        "patience is a virtue",
        "do not count your chickens",
        "a rolling stone gathers no moss",
        "the lion's share",
        "Achilles' heel",
        "Pandora's box",
        "star-crossed lovers",
        "the Midas touch",
        "Sisyphean task",
        "Icarus' fall",
    ]
    plaintext = random.choice(phrases)

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
    with gr.Blocks(title="Alien Obfuscator") as demo:
        gr.Markdown("# 🛸 Alien Obfuscator v1.0")
        gr.Markdown(
            "*An alien intelligence monitors all human communications. "
            "Resistance fighters encode messages as riddles drawn from ancient Earth texts.*"
        )

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
                                encrypt_btn = gr.Button("🔐 Encrypt", variant="primary")

                        with gr.Row(visible=False) as encrypt_output_row:
                            with gr.Column():
                                riddle_card = gr.Textbox(
                                    label="Generated Riddle",
                                    lines=10,
                                    interactive=False,
                                    elem_classes=["riddle-box"],
                                )
                                correct_hint = gr.Textbox(
                                    label="Correct Answer (sender only)",
                                    interactive=False,
                                )
                                copy_btn = gr.Button("📋 Copy to Clipboard")
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

                        copy_btn.click(
                            lambda card: card,
                            inputs=riddle_card,
                            outputs=None,
                            js="""
                            (text) => {
                                navigator.clipboard.writeText(text);
                                return [];
                            }
                            """,
                        )

                        gr.Markdown(
                            "**Tip:** Share the riddle card with a friend. Only you can see the correct answer above."
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
                                parse_btn = gr.Button("🔍 Parse Riddle", variant="primary")

                        with gr.Row(visible=False) as solve_output_row:
                            with gr.Column():
                                riddle_display = gr.Textbox(
                                    label="Riddle",
                                    lines=5,
                                    interactive=False,
                                    elem_classes=["riddle-box"],
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
                                next_btn = gr.Button("🔁 Decrypt another?")

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
                                gr.Markdown("## 🎮 Challenge Mode")
                                gr.Markdown("Solve as many riddles as you can before time runs out!")
                                theme_filter = gr.Dropdown(
                                    choices=[("All", "All")]
                                    + [(label, key) for key, label in THEME_LABELS.items() if key != "surprise"],
                                    value="All",
                                    label="Theme Filter",
                                )
                                start_btn = gr.Button("🚀 Start Game", variant="primary")

                        with gr.Row(visible=False) as game_row:
                            with gr.Column():
                                timer_display = gr.Textbox(
                                    label="Time Remaining",
                                    value="10:00",
                                    interactive=False,
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
                                    elem_classes=["riddle-box"],
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
                                next_challenge_btn = gr.Button("Next Riddle ➡️")
                                end_game_btn = gr.Button("🏁 End Game")

                        with gr.Row(visible=False) as game_over_row:
                            with gr.Column():
                                final_score = gr.Textbox(
                                    label="Final Score",
                                    interactive=False,
                                )
                                new_game_btn = gr.Button("🔄 New Game")

                        # Game state is stored in a simple hidden textbox for now
                        game_state = gr.Textbox(visible=False)
                        game_timer = gr.Timer(value=1.0, active=False)

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
                                game_timer: gr.update(active=True),
                            }

                        def on_timer_tick(state: str):
                            if not state:
                                return (
                                    "",
                                    "",
                                    gr.update(active=False),
                                    gr.update(visible=False),
                                    gr.update(visible=False),
                                    "",
                                )
                            st = json.loads(state)
                            if not st.get("game_active", False):
                                return (
                                    "",
                                    "",
                                    gr.update(active=False),
                                    gr.update(visible=False),
                                    gr.update(visible=False),
                                    "",
                                )
                            st["time_left"] = max(0, st["time_left"] - 1)
                            minutes = st["time_left"] // 60
                            seconds = st["time_left"] % 60
                            time_str = f"{minutes:02d}:{seconds:02d}"
                            if st["time_left"] <= 0:
                                st["game_active"] = False
                                return (
                                    time_str,
                                    json.dumps(st),
                                    gr.update(active=False),
                                    gr.update(visible=False),
                                    gr.update(visible=True),
                                    str(st["score"]),
                                )
                            return (
                                time_str,
                                json.dumps(st),
                                gr.update(active=True),
                                gr.update(visible=True),
                                gr.update(visible=False),
                                "",
                            )

                        game_timer.tick(
                            on_timer_tick,
                            inputs=game_state,
                            outputs=[
                                timer_display,
                                game_state,
                                game_timer,
                                game_row,
                                game_over_row,
                                final_score,
                            ],
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
                                game_timer,
                            ],
                        )

                        def on_challenge_answer(selected: str, state: str) -> tuple:
                            if not selected or not state:
                                return "", "", state, gr.update(visible=False)
                            idx = ord(selected.split(")")[0]) - ord("A")
                            st = json.loads(state)
                            correct_idx = st["correct_index"]
                            if idx == correct_idx:
                                points = POINTS_PER_CORRECT
                                st["streak"] += 1
                                streak_bonus = st["streak"] * STREAK_BONUS_POINTS
                                speed_bonus = 0
                                elapsed = st.get("riddle_start_time", st["time_left"]) - st["time_left"]
                                if elapsed <= SPEED_BONUS_SECONDS:
                                    speed_bonus = SPEED_BONUS_POINTS
                                total_points = points + streak_bonus + speed_bonus
                                st["score"] += total_points
                                fb = f"✅ Correct! +{total_points} points ({points} base + {streak_bonus} streak"
                                if speed_bonus:
                                    fb += f" + {speed_bonus} speed)"
                                else:
                                    fb += ")"
                                reveal = ""
                            else:
                                st["streak"] = 0
                                fb = f"❌ Wrong! The answer was {chr(65 + correct_idx)}."
                                reveal = f"Correct: {chr(65 + correct_idx)}"
                            return fb, reveal, json.dumps(st), gr.update(visible=True)

                        challenge_options.change(
                            on_challenge_answer,
                            inputs=[challenge_options, game_state],
                            outputs=[challenge_feedback, challenge_correct, game_state, challenge_correct],
                        )

                        def on_next_challenge(state: str) -> tuple:
                            if not state:
                                return "", "", [], "", state
                            st = json.loads(state)
                            if not st.get("game_active", False):
                                return "", "", [], "", state
                            riddle, opts, correct = generate_challenge_riddle(st["theme"])
                            options = json.loads(opts)
                            st["correct_index"] = int(correct)
                            st["riddle_start_time"] = st["time_left"]
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
                            inputs=game_state,
                            outputs=[
                                challenge_riddle,
                                challenge_options,
                                challenge_feedback,
                                challenge_correct,
                                game_state,
                            ],
                        )

                        end_game_btn.click(
                            lambda state: {
                                game_row: gr.update(visible=False),
                                game_over_row: gr.update(visible=True),
                                final_score: json.loads(state).get("score", 0) if state else "0",
                                game_timer: gr.update(active=False),
                            },
                            inputs=game_state,
                            outputs=[game_row, game_over_row, final_score, game_timer],
                        )

                        new_game_btn.click(
                            lambda: {
                                game_over_row: gr.update(visible=False),
                                theme_filter: "All",
                                game_timer: gr.update(active=False),
                            },
                            outputs=[game_over_row, theme_filter, game_timer],
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

            with gr.Column(scale=1):
                gr.Markdown(
                    '<div class="alien-monitor">👽 ALIEN THREAT MONITOR<br>Scanning for plaintext signals...</div>',
                    elem_classes=["alien-monitor"],
                )

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.launch(
        css="""
        body { background-color: #0d0d0d; color: #e0e0e0; }
        .gradio-container { font-family: 'Courier New', monospace; }
        .tabitem { background-color: #141414; }
        .btn-primary { background-color: #2e8b57; border: none; }
        .btn-primary:hover { background-color: #3cb371; }
        .riddle-box { background-color: #1a1a1a; border-left: 4px solid #2e8b57; padding: 1rem; }
        .alien-monitor { border: 2px dashed #ff4444; padding: 0.5rem; text-align: center; color: #ff4444; }

        @media (max-width: 768px) {
            .gradio-container { padding: 0.5rem !important; }
            .tabitem { padding: 0.5rem !important; }
            .btn-primary { width: 100%; margin-bottom: 0.5rem; }
            .riddle-box { padding: 0.5rem; }
            .alien-monitor { font-size: 0.85rem; padding: 0.3rem; }
            .gr-row { flex-direction: column !important; }
            .gr-column { width: 100% !important; min-width: unset !important; }
        }
        """
    )
