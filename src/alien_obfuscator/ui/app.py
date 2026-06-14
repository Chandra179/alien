"""Gradio UI assembly for the Alien Obfuscator.

This module constructs the Gradio Blocks interface with three tabs (Encrypt,
Solve, Challenge) and wires them to the riddle generator, parser, and game
engine callbacks.
"""

import json
from typing import Union

import gradio as gr

from alien_obfuscator.config import (
    APP_TITLE,
    DEFAULT_GAME_DURATION_MINUTES,
    POINTS_PER_CORRECT,
    SPEED_BONUS_POINTS,
    SPEED_BONUS_SECONDS,
    STREAK_BONUS_POINTS,
    THEME_LABELS,
)
from alien_obfuscator.ui.challenge import (
    ChallengeAnswerResult,
    GameOverResult,
    generate_challenge_riddle,
)
from alien_obfuscator.ui.encrypt import encrypt_message
from alien_obfuscator.ui.helpers import on_color_change
from alien_obfuscator.ui.solve import check_answer, parse_riddle_card
from alien_obfuscator.ui.theme import DISABLED_RADIO_CSS, TIMER_HTML


def build_ui() -> gr.Blocks:
    """Construct and return the Gradio Blocks application.

    Returns
    -------
    gr.Blocks
        The fully assembled Gradio interface with Fallout themed terminal style.
    """
    with gr.Blocks(title="Alien Obfuscator", head=TIMER_HTML, css=DISABLED_RADIO_CSS) as demo:
        gr.Markdown(f"# {APP_TITLE}")

        with gr.Row():
            with gr.Column(scale=3):
                color_dropdown = gr.Dropdown(
                    choices=["Green", "Blue", "Red", "Light gray", "No Theme"],
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
                        const theme = document.getElementById('terminal-theme-css');
                        if (color === "No Theme") {
                            if (theme) theme.disabled = true;
                            return color;
                        }
                        if (theme) theme.disabled = false;
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
                    }""",
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
                                encrypt_btn = gr.Button("ENCRYPT")

                        with gr.Row(visible=False) as encrypt_output_row:
                            with gr.Column():
                                riddle_card = gr.Textbox(
                                    label="Generated Riddle",
                                    lines=10,
                                    interactive=False,
                                    elem_id="riddle-card",
                                )
                                copy_riddle_btn = gr.Button("Copy Riddle")
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

                        copy_riddle_btn.click(
                            fn=None,
                            js="""() => {
                                const ta = document.querySelector('#riddle-card textarea, #riddle-card input');
                                if (!ta) return;
                                navigator.clipboard.writeText(ta.value).catch(() => {
                                    const orig = ta.readOnly;
                                    ta.readOnly = false;
                                    ta.select();
                                    document.execCommand('copy');
                                    ta.readOnly = orig;
                                    ta.blur();
                                });
                            }""",
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
                                parse_btn = gr.Button("PARSE RIDDLE")

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

                        def on_answer(selected: Union[str, None], state: str) -> tuple:
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
                                gr.Markdown("## CHALLENGE PROTOCOL")
                                gr.Markdown(
                                    "Execute decryption sequences. Complete as many nodes as possible before terminal lockout."
                                )
                                theme_filter = gr.Dropdown(
                                    choices=[("All", "All")]
                                    + [(label, key) for key, label in THEME_LABELS.items() if key != "surprise"],
                                    value="All",
                                    label="[ PARAM: THEME FILTER ]",
                                )
                                start_btn = gr.Button("START GAME")

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
                                    elem_id="challenge-options",
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

                        # State is bridged through localStorage; state_buffer holds temporary JSON
                        state_bridge = gr.Textbox(visible=False)
                        answer_time_left = gr.Textbox(visible=True, elem_id="answer-time-left")

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
                                    "active": True,
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
                                state_bridge: state,
                            }

                        def on_game_over(state: str) -> GameOverResult:
                            """Handle game over when the timer expires.

                            This function takes the current JSON-encoded state, marks the game as inactive,
                            sets remaining time to zero, and prepares the UI transition to the game over screen.
                            It also extracts the final score to be displayed.

                            Parameters
                            ----------
                            state : str
                                JSON-encoded game state.

                            Returns
                            -------
                            GameOverResult
                                Custom result object containing timer display, game state, final score, and UI visibility
                                updates.
                            """
                            if not state:
                                return GameOverResult("00:00", "", gr.update(visible=False), gr.update(visible=True), "0")
                            st = json.loads(state)
                            st["active"] = False
                            st["time_left"] = 0
                            final_score_value = str(st.get("score", 0))
                            return GameOverResult(
                                "00:00",
                                json.dumps(st),
                                gr.update(visible=False),
                                gr.update(visible=True),
                                gr.update(value=final_score_value),
                            )

                        game_over_trigger.click(
                            on_game_over,
                            inputs=[state_bridge],
                            outputs=[
                                timer_display,
                                state_bridge,
                                game_row,
                                game_over_row,
                                final_score,
                            ],
                            js="""() => {
                                window.stopGameTimer();
                                return [JSON.stringify(window.readGameState())];
                            }""",
                        ).then(
                            lambda x: x,
                            inputs=state_bridge,
                            outputs=state_bridge,
                            js="""(state_json) => {
                                try {
                                    window.writeGameState(JSON.parse(state_json));
                                } catch (e) { console.error('writeGameState failed:', e); }
                                return state_json;
                            }""",
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
                                state_bridge,
                            ],
                            js=f"""(theme) => {{
                                window.startGameTimer({DEFAULT_GAME_DURATION_MINUTES * 60});
                                return theme;
                            }}""",
                        ).then(
                            lambda x: x,
                            inputs=state_bridge,
                            outputs=state_bridge,
                            js="""(state_json) => {
                                try {
                                    window.writeGameState(JSON.parse(state_json));
                                } catch (e) { console.error('writeGameState failed:', e); }
                                return state_json;
                            }""",
                        )

                        def on_challenge_answer(
                            selected: Union[str, None], state: str, current_time_left: Union[str, int]
                        ) -> ChallengeAnswerResult:
                            try:
                                current_time_left_int = int(current_time_left)
                            except (ValueError, TypeError):
                                current_time_left_int = 0

                            if not selected or not state:
                                return ChallengeAnswerResult(
                                    "", gr.update(visible=False), state, gr.update(), "", ""
                                )

                            idx = ord(selected.split(")")[0]) - ord("A")
                            st = json.loads(state)
                            correct_idx = st["correct_index"]
                            st["time_left"] = current_time_left_int

                            if idx == correct_idx:
                                points = POINTS_PER_CORRECT
                                st["streak"] += 1
                                streak_bonus = st["streak"] * STREAK_BONUS_POINTS
                                speed_bonus = 0
                                elapsed = int(st.get("riddle_start_time", current_time_left_int)) - current_time_left_int
                                if elapsed <= SPEED_BONUS_SECONDS:
                                    speed_bonus = SPEED_BONUS_POINTS
                                total_points = points + streak_bonus + speed_bonus
                                st["score"] += total_points
                                fb = f"Correct! +{total_points} points ({points} base + {streak_bonus} streak"
                                if speed_bonus:
                                    fb += f" + {speed_bonus} speed)"
                                else:
                                    fb += ")"
                                return ChallengeAnswerResult(
                                    fb,
                                    gr.update(value="", visible=False),
                                    json.dumps(st),
                                    gr.update(value=None),
                                    str(st["score"]),
                                    str(st["streak"]),
                                )
                            else:
                                st["streak"] = 0
                                fb = f"Wrong! The answer was {chr(65 + correct_idx)}."
                                reveal = f"Correct: {chr(65 + correct_idx)}"
                                return ChallengeAnswerResult(
                                    fb,
                                    gr.update(value=reveal, visible=True),
                                    json.dumps(st),
                                    gr.update(value=None),
                                    str(st["score"]),
                                    str(st["streak"]),
                                )

                        challenge_options.select(
                            on_challenge_answer,
                            inputs=[challenge_options, state_bridge, answer_time_left],
                            outputs=[challenge_feedback, challenge_correct, state_bridge, challenge_options, score_display, streak_display],
                            js="""(selected, state, _) => {
                                var remainingSec = window.gameEndTime
                                    ? Math.max(0, Math.floor((window.gameEndTime - Date.now()) / 1000))
                                    : 0;
                                return [selected, JSON.stringify(window.readGameState()), remainingSec];
                            }""",
                        ).then(
                            lambda x: x,
                            inputs=state_bridge,
                            outputs=state_bridge,
                            js="""(state_json) => {
                                try {
                                    window.writeGameState(JSON.parse(state_json));
                                } catch (e) { console.error('writeGameState failed:', e); }
                                var inputs = document.querySelectorAll('#challenge-options input[type="radio"]');
                                inputs.forEach(function(el) { el.disabled = true; });
                                return state_json;
                            }""",
                        )

                        def on_next_challenge(state: str, current_time_left: Union[str, int]):
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
                            dict
                                Mapping of Gradio components to their updated values.
                            """
                            try:
                                current_time_left_int = int(current_time_left)
                            except (ValueError, TypeError):
                                current_time_left_int = 0

                            if not state:
                                return {
                                    challenge_riddle: "ERROR: Game state is missing. Please start a new game.",
                                    challenge_options: gr.update(choices=[], value=None, interactive=True),
                                    challenge_feedback: "",
                                    challenge_correct: gr.update(visible=False),
                                    state_bridge: state,
                                }
                            try:
                                st = json.loads(state)
                            except (json.JSONDecodeError, TypeError):
                                return {
                                    challenge_riddle: "ERROR: Game state is corrupted. Please start a new game.",
                                    challenge_options: gr.update(choices=[], value=None, interactive=True),
                                    challenge_feedback: "",
                                    challenge_correct: gr.update(visible=False),
                                    state_bridge: state,
                                }
                            if not st.get("active", False):
                                return {
                                    challenge_riddle: "SESSION EXPIRED: Click START GAME to begin a new session.",
                                    challenge_options: gr.update(choices=[], value=None, interactive=True),
                                    challenge_feedback: "",
                                    challenge_correct: gr.update(visible=False),
                                    state_bridge: json.dumps(st),
                                }

                            st["time_left"] = current_time_left_int
                            try:
                                riddle, opts, correct = generate_challenge_riddle(st["theme"])
                                options = json.loads(opts)
                            except Exception as exc:
                                return {
                                    challenge_riddle: f"Error: {exc}",
                                    challenge_options: gr.update(choices=[], value=None, interactive=True),
                                    challenge_feedback: "",
                                    challenge_correct: gr.update(visible=False),
                                    state_bridge: json.dumps(st),
                                }
                            st["correct_index"] = int(correct)
                            st["riddle_start_time"] = current_time_left_int
                            return {
                                challenge_riddle: riddle,
                                challenge_options: gr.update(
                                    choices=[f"{chr(65 + i)}) {o}" for i, o in enumerate(options)],
                                    value=None,
                                    interactive=True,
                                ),
                                challenge_feedback: "",
                                challenge_correct: gr.update(visible=False),
                                state_bridge: json.dumps(st),
                            }

                        next_challenge_btn.click(
                            on_next_challenge,
                            inputs=[state_bridge, answer_time_left],
                            outputs=[
                                challenge_riddle,
                                challenge_options,
                                challenge_feedback,
                                challenge_correct,
                                state_bridge,
                            ],
                            js="""(_) => {
                                window.riddleStartTime = Date.now();
                                var remainingSec = window.gameEndTime
                                    ? Math.max(0, Math.floor((window.gameEndTime - Date.now()) / 1000))
                                    : 0;
                                return [JSON.stringify(window.readGameState()), remainingSec];
                            }""",
                        ).then(
                            lambda x: x,
                            inputs=state_bridge,
                            outputs=state_bridge,
                            js="""(state_json) => {
                                try {
                                    window.writeGameState(JSON.parse(state_json));
                                } catch (e) { console.error('writeGameState failed:', e); }
                                var inputs = document.querySelectorAll('#challenge-options input[type="radio"]');
                                inputs.forEach(function(el) { el.disabled = false; });
                                return state_json;
                            }""",
                        )

                        end_game_btn.click(
                            on_game_over,
                            inputs=[state_bridge],
                            outputs=[
                                timer_display,
                                state_bridge,
                                game_row,
                                game_over_row,
                                final_score,
                            ],
                            js="""() => {
                                window.stopGameTimer();
                                return [JSON.stringify(window.readGameState())];
                            }""",
                        ).then(
                            lambda x: x,
                            inputs=state_bridge,
                            outputs=state_bridge,
                            js="""(state_json) => {
                                try {
                                    window.writeGameState(JSON.parse(state_json));
                                } catch (e) { console.error('writeGameState failed:', e); }
                                return state_json;
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
                        gr.Markdown(
                            """
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
                        """
                        )

        return demo
