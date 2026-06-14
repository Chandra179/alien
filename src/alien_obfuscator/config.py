"""Configuration and constants for the Alien Obfuscator application.

This module centralizes all static configuration, file paths, and
hyper-parameters so that the rest of the codebase can import them without
duplicating magic strings. Values are loaded from ``config.yaml`` at the
project root, with sensible defaults where applicable.
"""

from pathlib import Path
from typing import Any, Final

import yaml

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH: Final[Path] = PROJECT_ROOT / "config.yaml"
ASSETS_DIR: Final[Path] = PROJECT_ROOT / "assets"


def _load_config() -> dict[str, Any]:
    """Load config.yaml from the project root, returning an empty dict on failure.

    Returns
    -------
    dict[str, Any]
        Parsed YAML configuration.
    """
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_cfg: dict[str, Any] = _load_config()

# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------
THEME_LABELS: Final[dict[str, str]] = _cfg.get("themes", {}).get(
    "labels",
    {
        "greek_myth": "Greek / Roman Mythology",
        "shakespeare": "Shakespeare",
        "grimm": "Grimms' Fairy Tales / Folklore",
        "poetry": "Classic Poetry",
        "chinese_classics": "Chinese Classics",
        "surprise": "Surprise Me",
    },
)

THEME_KEYS: Final[list[str]] = sorted(k for k in THEME_LABELS if k != "surprise")

# ---------------------------------------------------------------------------
# Riddle generation constraints
# ---------------------------------------------------------------------------
_riddle_cfg: dict[str, Any] = _cfg.get("riddle", {})
MAX_PLAINTEXT_LENGTH: Final[int] = _riddle_cfg.get("max_plaintext_length", 100)
MAX_RIDDLE_LENGTH: Final[int] = _riddle_cfg.get("max_riddle_length", 500)
NUM_OPTIONS: Final[int] = _riddle_cfg.get("num_options", 5)
MAX_RETRIES: Final[int] = _riddle_cfg.get("max_retries", 2)

# ---------------------------------------------------------------------------
# LLM backend settings
# ---------------------------------------------------------------------------
DEFAULT_BACKEND: Final[str] = "mock"
_llm_cfg: dict[str, Any] = _cfg.get("llm", {})
LLM_TIMEOUT_SECONDS: Final[int] = _llm_cfg.get("timeout_seconds", 15)
LLM_MAX_TOKENS: Final[int] = _llm_cfg.get("max_tokens", 4096)
LLM_TEMPERATURE: Final[float] = _llm_cfg.get("temperature", 0.8)

# Model targets (for HF Spaces)
_models_cfg: dict[str, Any] = _cfg.get("models", {})
PRIMARY_MODEL: Final[str] = _models_cfg.get("primary", "google/gemma-4-31b-it")
FALLBACK_MODEL: Final[str] = _models_cfg.get("fallback", "google/gemma-4-26b-a4b-it")
MAX_PARAMETERS: Final[int] = _models_cfg.get("max_parameters", 32_000_000_000)

# Backend-specific settings
_backends_cfg: dict[str, Any] = _cfg.get("backends", {})
HF_DEFAULT_MODEL: Final[str] = _backends_cfg.get("hf", {}).get("default_model", "google/gemma-4-31b-it")
HF_API_TIMEOUT: Final[int] = _backends_cfg.get("hf", {}).get("timeout", 30)
OPENROUTER_DEFAULT_MODEL: Final[str] = _backends_cfg.get("openrouter", {}).get(
    "default_model", "google/gemma-4-31b-it"
)
OPENROUTER_URL: Final[str] = _backends_cfg.get("openrouter", {}).get(
    "url", "https://openrouter.ai/api/v1/chat/completions"
)
OPENROUTER_TIMEOUT: Final[int] = _backends_cfg.get("openrouter", {}).get("timeout", 120)
OPENCODE_GO_DEFAULT_MODEL: Final[str] = _backends_cfg.get("opencode-go", {}).get("default_model", "mimo-v2.5")
OPENCODE_GO_URL: Final[str] = _backends_cfg.get("opencode-go", {}).get(
    "url", "https://opencode.ai/zen/go/v1/chat/completions"
)
OPENCODE_GO_TIMEOUT: Final[int] = _backends_cfg.get("opencode-go", {}).get("timeout", 120)
MODAL_DEFAULT_MODEL: Final[str] = _backends_cfg.get("modal", {}).get(
    "default_model", "google/gemma-4-31b-it"
)
MODAL_TIMEOUT: Final[int] = _backends_cfg.get("modal", {}).get("timeout", 300)

# Challenge phrases
CHALLENGE_PHRASES: Final[list[str]] = _cfg.get(
    "challenge_phrases",
    [
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
    ],
)

# Mock backend distractors
MOCK_DISTRACTORS: Final[list[str]] = _cfg.get("mock_backend", {}).get(
    "distractors",
    ["a wrong answer", "another wrong answer", "yet another wrong answer", "the last wrong answer"],
)

# ---------------------------------------------------------------------------
# Game settings
# ---------------------------------------------------------------------------
_game_cfg: dict[str, Any] = _cfg.get("game", {})
DEFAULT_GAME_DURATION_MINUTES: Final[int] = _game_cfg.get("default_duration_minutes", 10)
MIN_GAME_DURATION_MINUTES: Final[int] = _game_cfg.get("min_duration_minutes", 1)
MAX_GAME_DURATION_MINUTES: Final[int] = _game_cfg.get("max_duration_minutes", 30)
POINTS_PER_CORRECT: Final[int] = _game_cfg.get("points_per_correct", 10)
SPEED_BONUS_SECONDS: Final[int] = _game_cfg.get("speed_bonus_seconds", 15)
SPEED_BONUS_POINTS: Final[int] = _game_cfg.get("speed_bonus_points", 5)
STREAK_BONUS_POINTS: Final[int] = _game_cfg.get("streak_bonus_points", 3)

# ---------------------------------------------------------------------------
# App / launch settings
# ---------------------------------------------------------------------------
_app_cfg: dict[str, Any] = _cfg.get("app", {})
APP_TITLE: Final[str] = _app_cfg.get("title", "Alien Obfuscator v1.0")
LAUNCH_SERVER_NAME: Final[str] = _app_cfg.get("launch", {}).get("server_name", "0.0.0.0")
LAUNCH_SERVER_PORT: Final[int] = _app_cfg.get("launch", {}).get("server_port", 7860)
LAUNCH_SHARE: Final[bool] = _app_cfg.get("launch", {}).get("share", False)
