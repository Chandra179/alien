"""Alien Obfuscator — Encode messages as riddles drawn from ancient texts."""

from alien_obfuscator.config import MAX_PLAINTEXT_LENGTH, NUM_OPTIONS
from alien_obfuscator.riddle_generator import (
    AutoBackend,
    HuggingFaceBackend,
    LLMBackend,
    LocalGPU4BitBackend,
    MockBackend,
    ModalBackend,
    OpenAICompatibleBackend,
    OpenCodeGoBackend,
    OpenRouterBackend,
    RiddleGenerator,
    _validate_riddle_json,
)

__all__ = [
    "AutoBackend",
    "HuggingFaceBackend",
    "LLMBackend",
    "LocalGPU4BitBackend",
    "MockBackend",
    "ModalBackend",
    "OpenAICompatibleBackend",
    "OpenCodeGoBackend",
    "OpenRouterBackend",
    "RiddleGenerator",
    "MAX_PLAINTEXT_LENGTH",
    "NUM_OPTIONS",
    "_validate_riddle_json",
]
