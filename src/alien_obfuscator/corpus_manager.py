"""Corpus manager for loading and sampling curated text excerpts.

The corpus manager reads public-domain excerpts from flat text files under
``corpus/``. Each file contains one excerpt per line. The manager can return
a random excerpt (or multiple excerpts) for any supported theme, which the
riddle generator then injects into the LLM prompt as creative fodder.
"""

import random
from pathlib import Path
from typing import Sequence

from alien_obfuscator.config import CORPUS_DIR, THEME_FILES


class CorpusManager:
    """Load and cache corpus excerpts, then serve random samples.

    Parameters
    ----------
    corpus_dir : Path, optional
        Directory containing the ``.txt`` theme files. Defaults to the
        ``CORPUS_DIR`` defined in ``config.py``.

    Attributes
    ----------
    _cache : dict[str, list[str]]
        In-memory mapping from theme key to list of loaded excerpts.
    """

    def __init__(self, corpus_dir: Path | None = None) -> None:
        self._corpus_dir: Path = corpus_dir or CORPUS_DIR
        self._cache: dict[str, list[str]] = {}
        self._load_all()

    def _load_theme(self, theme: str) -> list[str]:
        """Read a single theme file into a list of non-empty lines.

        Parameters
        ----------
        theme : str
            One of the keys in ``THEME_FILES``.

        Returns
        -------
        list[str]
            Stripped, non-empty excerpts from the file.

        Raises
        ------
        FileNotFoundError
            If the theme file does not exist in ``corpus_dir``.
        """
        filename = THEME_FILES[theme]
        filepath = self._corpus_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Corpus file not found for theme '{theme}': {filepath}")

        lines = [line.strip() for line in filepath.read_text(encoding="utf-8").splitlines()]
        return [line for line in lines if line]

    def _load_all(self) -> None:
        """Eagerly load every theme file into ``_cache``."""
        for theme in THEME_FILES:
            self._cache[theme] = self._load_theme(theme)

    def get_excerpt(self, theme: str, count: int = 1) -> Sequence[str]:
        """Return ``count`` random excerpts for the requested theme.

        If the theme is ``"surprise"``, a random real theme is chosen first.

        Parameters
        ----------
        theme : str
            Theme key (e.g. ``"greek_myth"``) or ``"surprise"``.
        count : int, default 1
            Number of distinct excerpts to return. If ``count`` exceeds the
            number of available excerpts, all excerpts are returned.

        Returns
        -------
        Sequence[str]
            A tuple of ``count`` random excerpts (without replacement).

        Raises
        ------
        ValueError
            If ``theme`` is not a valid key or ``count`` is not positive.
        """
        if count < 1:
            raise ValueError("count must be at least 1")

        if theme == "surprise":
            theme = random.choice(list(THEME_FILES.keys()))

        if theme not in self._cache:
            raise ValueError(f"Unknown theme: {theme}")

        pool = self._cache[theme]
        if count > len(pool):
            count = len(pool)

        return tuple(random.sample(pool, count))

    def list_themes(self) -> list[str]:
        """Return the list of supported theme keys.

        Returns
        -------
        list[str]
            Sorted theme keys (excluding ``"surprise"``).
        """
        return sorted(THEME_FILES.keys())
