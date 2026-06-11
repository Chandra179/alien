"""Unit tests for Challenge mode event handlers in app.py.

This module verifies that on_challenge_answer and on_next_challenge
correctly parse and handle string-typed time values from Gradio components.
"""

import json
import sys
from pathlib import Path

# Ensure root directory is in path so we can import app.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import build_ui, GameOverResult, ChallengeAnswerResult, NextChallengeResult


def test_challenge_handlers() -> None:
    """Verify that challenge mode handlers handle string-typed time inputs correctly.

    This test extracts the registered event handlers from the built Gradio
    UI Blocks object, executes them with both string and integer time inputs,
    and asserts that they calculate scoring, streaks, and elapsed times
    without throwing any TypeError. It also validates that the returned
    values are instances of our custom class results and their properties.
    """
    demo = build_ui()

    on_challenge_answer_fn = None
    on_next_challenge_fn = None
    on_game_over_fn = None

    for bf in demo.fns.values():
        fn = getattr(bf, "fn", None)
        if fn:
            if fn.__name__ == "on_challenge_answer":
                on_challenge_answer_fn = fn
            elif fn.__name__ == "on_next_challenge":
                on_next_challenge_fn = fn
            elif fn.__name__ == "on_game_over":
                on_game_over_fn = fn

    assert on_challenge_answer_fn is not None, "on_challenge_answer not found"
    assert on_next_challenge_fn is not None, "on_next_challenge not found"
    assert on_game_over_fn is not None, "on_game_over not found"

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
    res_ans = on_challenge_answer_fn("A) Option A", state_str, "115")
    assert isinstance(res_ans, ChallengeAnswerResult)
    assert "Correct!" in res_ans.feedback
    assert res_ans.reveal == ""
    st = json.loads(res_ans.updated_state)
    assert st["time_left"] == 115
    assert st["streak"] == 3
    assert st["score"] > 10
    assert res_ans.interactive_update.get("interactive") is False

    # Unpack to verify tuple unpacking compatibility
    fb, reveal, next_state, update, radio_update, score_upd, streak_upd = res_ans
    assert fb == res_ans.feedback
    assert reveal == res_ans.reveal

    # Verify that calling on_game_over with the updated state (after correct answer)
    # returns the updated state including the score.
    res_go_correct = on_game_over_fn(res_ans.updated_state)
    assert isinstance(res_go_correct, GameOverResult)
    st_go_correct = json.loads(res_go_correct.state_json)
    assert st_go_correct["score"] == st["score"]

    # 2. Test on_challenge_answer with integer current_time_left
    res_ans_wrong = on_challenge_answer_fn("B) Option B", state_str, 115)
    assert isinstance(res_ans_wrong, ChallengeAnswerResult)
    assert "Wrong!" in res_ans_wrong.feedback
    st_int = json.loads(res_ans_wrong.updated_state)
    assert st_int["time_left"] == 115
    assert st_int["streak"] == 0
    assert res_ans_wrong.interactive_update.get("interactive") is False

    # 3. Test on_next_challenge with string current_time_left
    res_nc = on_next_challenge_fn(state_str, "100")
    assert isinstance(res_nc, NextChallengeResult)
    assert res_nc.feedback == ""
    assert res_nc.reveal == ""
    assert res_nc.options_update.get("interactive") is True
    st_nc = json.loads(res_nc.updated_state)
    assert st_nc["time_left"] == 100
    assert st_nc["riddle_start_time"] == 100

    # Unpack to verify tuple unpacking compatibility
    riddle, opt_upd, fb_nc, rev_nc, state_nc = res_nc
    assert riddle == res_nc.riddle

    # 4. Test on_game_over
    res_go = on_game_over_fn(state_str)
    assert isinstance(res_go, GameOverResult)
    assert res_go.timer_display == "00:00"
    st_go = json.loads(res_go.state_json)
    assert st_go["game_active"] is False
    assert st_go["time_left"] == 0
    st_go = json.loads(res_go.state_json)
    assert st_go["score"] == 10

    # Unpack to verify tuple unpacking compatibility
    timer_display, state_json_val, game_row_val, game_over_row_val = res_go
    assert timer_display == "00:00"

    # 5. Verify that both "Game Over" trigger and "End Game" buttons are wired to on_game_over
    game_over_targets = []
    for bf in demo.fns.values():
        fn = getattr(bf, "fn", None)
        if fn and fn.__name__ == "on_game_over":
            for target_id in bf.targets:
                if target_id[0] in demo.blocks:
                    block = demo.blocks[target_id[0]]
                    game_over_targets.append(getattr(block, "value", None))

    assert "Game Over" in game_over_targets
    assert "> END GAME" in game_over_targets
