"""Unit tests for Challenge mode event handlers in app.py.

This module verifies that on_challenge_answer and on_next_challenge
correctly parse and handle string-typed time values from Gradio components.
"""

import json
import sys
from pathlib import Path

# Ensure root directory is in path so we can import app.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import build_ui


def test_challenge_handlers() -> None:
    """Verify that challenge mode handlers handle string-typed time inputs correctly.

    This test extracts the registered event handlers from the built Gradio
    UI Blocks object, executes them with both string and integer time inputs,
    and asserts that they calculate scoring, streaks, and elapsed times
    without throwing any TypeError.
    """
    demo = build_ui()

    on_challenge_answer_fn = None
    on_next_challenge_fn = None

    for bf in demo.fns.values():
        fn = getattr(bf, "fn", None)
        if fn:
            if fn.__name__ == "on_challenge_answer":
                on_challenge_answer_fn = fn
            elif fn.__name__ == "on_next_challenge":
                on_next_challenge_fn = fn

    assert on_challenge_answer_fn is not None, "on_challenge_answer not found"
    assert on_next_challenge_fn is not None, "on_next_challenge not found"

    # Test state dictionary
    initial_state = {
        "score": 10,
        "streak": 2,
        "time_left": 120,
        "correct_index": 0,  # 'A'
        "theme": "All",
        "riddle_start_time": 120,
        "game_active": True,
    }
    state_str = json.dumps(initial_state)

    # 1. Test on_challenge_answer with a string for current_time_left
    # selected option is 'A', which is correct (index 0)
    fb, reveal, next_state, update = on_challenge_answer_fn("A) Option A", state_str, "115")

    assert "Correct!" in fb
    assert reveal == ""
    st = json.loads(next_state)
    assert st["time_left"] == 115
    assert st["streak"] == 3
    assert st["score"] > 10

    # 2. Test on_challenge_answer with integer current_time_left
    fb_int, reveal_int, next_state_int, _ = on_challenge_answer_fn("B) Option B", state_str, 115)
    assert "Wrong!" in fb_int
    st_int = json.loads(next_state_int)
    assert st_int["time_left"] == 115
    assert st_int["streak"] == 0

    # 3. Test on_next_challenge with string current_time_left
    riddle, opt_upd, fb_nc, rev_nc, state_nc = on_next_challenge_fn(state_str, "100")
    assert fb_nc == ""
    assert rev_nc == ""
    st_nc = json.loads(state_nc)
    assert st_nc["time_left"] == 100
    assert st_nc["riddle_start_time"] == 100
