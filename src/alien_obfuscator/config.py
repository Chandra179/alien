"""Configuration and constants for the Alien Obfuscator application.

This module centralizes all static configuration, file paths, and
hyper-parameters so that the rest of the codebase can import them without
duplicating magic strings.
"""

from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent
CORPUS_DIR: Final[Path] = PROJECT_ROOT / "corpus"
ASSETS_DIR: Final[Path] = PROJECT_ROOT / "assets"

# ---------------------------------------------------------------------------
# Corpus themes
# ---------------------------------------------------------------------------
THEME_FILES: Final[dict[str, str]] = {
    "greek_myth": "greek_myth.txt",
    "shakespeare": "shakespeare.txt",
    "grimm": "grimm.txt",
    "poetry": "poetry.txt",
    "chinese_classics": "chinese_classics.txt",
}

THEME_LABELS: Final[dict[str, str]] = {
    "greek_myth": "Greek / Roman Mythology",
    "shakespeare": "Shakespeare",
    "grimm": "Grimms' Fairy Tales / Folklore",
    "poetry": "Classic Poetry",
    "chinese_classics": "Chinese Classics",
    "surprise": "Surprise Me",
}

# ---------------------------------------------------------------------------
# Riddle generation constraints
# ---------------------------------------------------------------------------
MAX_PLAINTEXT_LENGTH: Final[int] = 100
MAX_RIDDLE_LENGTH: Final[int] = 500
NUM_OPTIONS: Final[int] = 5
MAX_RETRIES: Final[int] = 2

# ---------------------------------------------------------------------------
# LLM backend settings
# ---------------------------------------------------------------------------
DEFAULT_BACKEND: Final[str] = "mock"
LLM_TIMEOUT_SECONDS: Final[int] = 15

# Model targets (for HF Spaces)
PRIMARY_MODEL: Final[str] = "google/gemma-4-31b-it"
FALLBACK_MODEL: Final[str] = "google/gemma-4-26b-a4b-it"
MAX_PARAMETERS: Final[int] = 32_000_000_000

# ---------------------------------------------------------------------------
# Game settings
# ---------------------------------------------------------------------------
DEFAULT_GAME_DURATION_MINUTES: Final[int] = 10
MIN_GAME_DURATION_MINUTES: Final[int] = 1
MAX_GAME_DURATION_MINUTES: Final[int] = 30
POINTS_PER_CORRECT: Final[int] = 10
SPEED_BONUS_SECONDS: Final[int] = 15
SPEED_BONUS_POINTS: Final[int] = 5
STREAK_BONUS_POINTS: Final[int] = 3
