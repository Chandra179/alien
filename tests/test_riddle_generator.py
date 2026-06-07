"""Unit tests for the riddle generator and LLM backends."""

import json

import pytest
from pytest_mock import MockerFixture

from alien_obfuscator.config import MAX_PLAINTEXT_LENGTH, NUM_OPTIONS
from alien_obfuscator.corpus_manager import CorpusManager
from alien_obfuscator.riddle_generator import (
    HuggingFaceBackend,
    MockBackend,
    RiddleGenerator,
    _validate_riddle_json,
)


class TestValidateRiddleJson:
    """Tests for the JSON schema validator."""

    def test_valid_data(self) -> None:
        """A fully populated dict with the correct shape should pass."""
        data = {
            "riddle": "What has roots that nobody sees?",
            "options": ["a", "b", "c", "d", "e"],
            "correct_index": 2,
            "theme": "poetry",
        }
        result = _validate_riddle_json(data)
        assert result == data

    def test_missing_riddle(self) -> None:
        """Missing ``riddle`` should raise ``ValueError``."""
        data = {"options": ["a"] * NUM_OPTIONS, "correct_index": 0, "theme": "t"}
        with pytest.raises(ValueError, match="Missing required field"):
            _validate_riddle_json(data)

    def test_empty_riddle(self) -> None:
        """An empty riddle string should raise ``ValueError``."""
        data = {"riddle": "", "options": ["a"] * NUM_OPTIONS, "correct_index": 0, "theme": "t"}
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_riddle_json(data)

    def test_wrong_option_count(self) -> None:
        """``options`` must contain exactly ``NUM_OPTIONS`` items."""
        data = {"riddle": "r", "options": ["a", "b"], "correct_index": 0, "theme": "t"}
        with pytest.raises(ValueError, match="exactly"):
            _validate_riddle_json(data)

    def test_non_string_option(self) -> None:
        """Every option must be a string."""
        data = {"riddle": "r", "options": [1, 2, 3, 4, 5], "correct_index": 0, "theme": "t"}
        with pytest.raises(ValueError, match="string"):
            _validate_riddle_json(data)

    def test_correct_index_out_of_range(self) -> None:
        """``correct_index`` must be between 0 and ``NUM_OPTIONS - 1``."""
        data = {"riddle": "r", "options": ["a"] * NUM_OPTIONS, "correct_index": 99, "theme": "t"}
        with pytest.raises(ValueError, match="correct_index"):
            _validate_riddle_json(data)

    def test_missing_correct_index(self) -> None:
        """Missing ``correct_index`` should raise ``ValueError``."""
        data = {"riddle": "r", "options": ["a"] * NUM_OPTIONS, "theme": "t"}
        with pytest.raises(ValueError, match="Missing required field"):
            _validate_riddle_json(data)


class TestMockBackend:
    """Tests for the offline mock LLM backend."""

    def test_returns_valid_json(self) -> None:
        """The mock backend should return parseable JSON."""
        backend = MockBackend()
        raw = backend.generate("test prompt")
        data = json.loads(raw)
        assert "riddle" in data
        assert "options" in data
        assert "correct_index" in data

    def test_extracts_plaintext_from_prompt(self) -> None:
        """The mock should extract the plaintext answer from the prompt."""
        backend = MockBackend()
        raw = backend.generate("ANSWER is: pizza")
        data = json.loads(raw)
        assert data["options"][0] == "pizza"


class TestRiddleGenerator:
    """Tests for the riddle generator orchestrator."""

    @pytest.fixture
    def corpus(self) -> CorpusManager:
        return CorpusManager()

    @pytest.fixture
    def mock_gen(self, corpus: CorpusManager) -> RiddleGenerator:
        return RiddleGenerator(backend=MockBackend(), corpus_manager=corpus)

    def test_generate_produces_valid_riddle(self, mock_gen: RiddleGenerator) -> None:
        """A full generation cycle should return a validated, shuffled dict."""
        result = mock_gen.generate("pizza", "greek_myth")
        assert "riddle" in result
        assert len(result["options"]) == NUM_OPTIONS
        assert 0 <= result["correct_index"] < NUM_OPTIONS
        assert result["options"][result["correct_index"]] == "pizza"
        assert result["theme"] == "greek_myth"

    def test_generate_empty_plaintext(self, mock_gen: RiddleGenerator) -> None:
        """Empty plaintext should raise ``ValueError``."""
        with pytest.raises(ValueError, match="empty"):
            mock_gen.generate("", "greek_myth")

    def test_generate_too_long_plaintext(self, mock_gen: RiddleGenerator) -> None:
        """Plaintext over the character limit should raise ``ValueError``."""
        long_text = "x" * (MAX_PLAINTEXT_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds"):
            mock_gen.generate(long_text, "greek_myth")

    def test_generate_retry_on_malformed_json(self, corpus: CorpusManager, mocker: MockerFixture) -> None:
        """If the backend returns bad JSON once, the generator should retry."""
        backend = MockBackend()
        mocker.patch.object(
            backend,
            "generate",
            side_effect=[
                "not json",
                json.dumps(
                    {
                        "riddle": "r",
                        "options": ["hello"] + ["wrong"] * (NUM_OPTIONS - 1),
                        "correct_index": 0,
                        "theme": "t",
                    }
                ),
            ],
        )
        gen = RiddleGenerator(backend=backend, corpus_manager=corpus, max_retries=1)
        result = gen.generate("hello", "poetry")
        assert result["options"][result["correct_index"]] == "hello"

    def test_generate_all_retries_fail(self, corpus: CorpusManager, mocker: MockerFixture) -> None:
        """If every attempt fails, ``RuntimeError`` is raised."""
        backend = MockBackend()
        mocker.patch.object(backend, "generate", return_value="not json")
        gen = RiddleGenerator(backend=backend, corpus_manager=corpus, max_retries=1)
        with pytest.raises(RuntimeError, match="Failed"):
            gen.generate("hello", "poetry")

    def test_generate_shuffles_options(self, mock_gen: RiddleGenerator) -> None:
        """The correct answer should not always be at index 0."""
        # Mock backend always puts correct at index 0, but RiddleGenerator shuffles
        backend = MockBackend()
        gen = RiddleGenerator(backend=backend, corpus_manager=mock_gen._corpus)
        indices = [gen.generate("test", "shakespeare")["correct_index"] for _ in range(20)]
        # Statistically unlikely that all 20 remain at 0 after shuffling
        assert any(i != 0 for i in indices)


class TestHuggingFaceBackend:
    """Tests for the HuggingFace Inference API backend."""

    def test_raises_without_token(self, mocker: MockerFixture) -> None:
        """If no token is provided and HF_TOKEN is absent, ``RuntimeError`` is raised."""
        mocker.patch.dict("os.environ", {}, clear=True)
        backend = HuggingFaceBackend("dummy-model")
        with pytest.raises(RuntimeError, match="HF_TOKEN"):
            backend.generate("hello")

    def test_api_error(self, mocker: MockerFixture) -> None:
        """A non-200 status code should raise ``RuntimeError``."""
        mocker.patch.dict("os.environ", {"HF_TOKEN": "fake"})
        mock_response = mocker.Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mocker.patch("requests.post", return_value=mock_response)

        backend = HuggingFaceBackend("dummy-model")
        with pytest.raises(RuntimeError, match="HF API error"):
            backend.generate("hello")

    def test_api_success(self, mocker: MockerFixture) -> None:
        """A successful API call should return the generated text."""
        mocker.patch.dict("os.environ", {"HF_TOKEN": "fake"})
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"generated_text": "some riddle"}]
        mocker.patch("requests.post", return_value=mock_response)

        backend = HuggingFaceBackend("dummy-model")
        result = backend.generate("hello")
        assert result == "some riddle"
