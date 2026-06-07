"""Unit tests for the corpus manager."""

import pytest

from alien_obfuscator.config import THEME_FILES
from alien_obfuscator.corpus_manager import CorpusManager


class TestCorpusManager:
    """Tests for ``CorpusManager`` loading and sampling."""

    def test_loads_all_themes_on_init(self) -> None:
        """All theme files should be eagerly loaded into memory."""
        manager = CorpusManager()
        assert len(manager._cache) == len(THEME_FILES)
        for theme in THEME_FILES:
            assert theme in manager._cache
            assert len(manager._cache[theme]) > 0

    def test_get_excerpt_returns_non_empty_string(self) -> None:
        """A single excerpt should be a non-empty string."""
        manager = CorpusManager()
        for theme in THEME_FILES:
            excerpt = manager.get_excerpt(theme)
            assert len(excerpt) == 1
            assert isinstance(excerpt[0], str)
            assert excerpt[0].strip()

    def test_get_excerpt_multiple(self) -> None:
        """Requesting ``count=2`` returns two distinct excerpts."""
        manager = CorpusManager()
        excerpts = manager.get_excerpt("greek_myth", count=2)
        assert len(excerpts) == 2
        assert excerpts[0] != excerpts[1]

    def test_get_excerpt_surprise_selects_real_theme(self) -> None:
        """The ``surprise`` theme should map to a real theme key."""
        manager = CorpusManager()
        excerpt = manager.get_excerpt("surprise")
        assert len(excerpt) == 1
        assert isinstance(excerpt[0], str)

    def test_get_excerpt_count_larger_than_pool(self) -> None:
        """If count exceeds pool size, return all available excerpts."""
        manager = CorpusManager()
        pool_size = len(manager._cache["greek_myth"])
        excerpts = manager.get_excerpt("greek_myth", count=pool_size + 10)
        assert len(excerpts) == pool_size

    def test_get_excerpt_invalid_theme(self) -> None:
        """An unknown theme key should raise ``ValueError``."""
        manager = CorpusManager()
        with pytest.raises(ValueError, match="Unknown theme"):
            manager.get_excerpt("not_a_theme")

    def test_get_excerpt_invalid_count(self) -> None:
        """A non-positive count should raise ``ValueError``."""
        manager = CorpusManager()
        with pytest.raises(ValueError, match="count must be at least 1"):
            manager.get_excerpt("greek_myth", count=0)

    def test_list_themes(self) -> None:
        """``list_themes`` should return sorted keys."""
        manager = CorpusManager()
        themes = manager.list_themes()
        assert themes == sorted(THEME_FILES.keys())

    def test_missing_file_raises(self) -> None:
        """If a corpus file is missing, ``FileNotFoundError`` is raised."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)
            with pytest.raises(FileNotFoundError):
                CorpusManager(corpus_dir=empty_dir)
