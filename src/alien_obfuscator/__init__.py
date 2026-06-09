"""Alien Obfuscator — Encode messages as riddles drawn from ancient texts."""

from alien_obfuscator.config import MAX_PLAINTEXT_LENGTH, NUM_OPTIONS
from alien_obfuscator.riddle_generator import (
    HuggingFaceBackend,
    LLMBackend,
    MockBackend,
    OpenAICompatibleBackend,
    OpenCodeGoBackend,
    OpenRouterBackend,
    RiddleGenerator,
    _validate_riddle_json,
)

__all__ = [
    "HuggingFaceBackend",
    "LLMBackend",
    "MockBackend",
    "OpenAICompatibleBackend",
    "OpenCodeGoBackend",
    "OpenRouterBackend",
    "RiddleGenerator",
    "MAX_PLAINTEXT_LENGTH",
    "NUM_OPTIONS",
    "_validate_riddle_json",
]
