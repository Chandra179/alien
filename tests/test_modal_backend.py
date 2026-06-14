"""Unit tests for the Modal vLLM backend."""

import pytest
from pytest_mock import MockerFixture

from alien_obfuscator.riddle_generator import ModalBackend


class TestModalBackend:
    """Tests for the Modal-deployed vLLM backend."""

    def test_construction_with_explicit_url(self) -> None:
        """Backend should accept an explicit API URL."""
        backend = ModalBackend("google/gemma-4-31b-it", api_url="https://test.modal.run")
        assert backend.model_id == "google/gemma-4-31b-it"
        assert backend._api_url == "https://test.modal.run/v1/chat/completions"

    def test_construction_from_env(self, mocker: MockerFixture) -> None:
        """Backend should read the URL from MODAL_API_URL env var."""
        mocker.patch.dict("os.environ", {"MODAL_API_URL": "https://env.modal.run"})
        backend = ModalBackend("google/gemma-4-31b-it")
        assert backend._api_url == "https://env.modal.run/v1/chat/completions"

    def test_raises_without_url(self, mocker: MockerFixture) -> None:
        """If no URL is provided and MODAL_API_URL is absent, ``ValueError`` is raised."""
        mocker.patch.dict("os.environ", {}, clear=True)
        with pytest.raises(ValueError, match="MODAL_API_URL"):
            ModalBackend("google/gemma-4-31b-it")

    def test_explicit_url_overrides_env(self, mocker: MockerFixture) -> None:
        """An explicit URL should take precedence over the env var."""
        mocker.patch.dict("os.environ", {"MODAL_API_URL": "https://env.modal.run"})
        backend = ModalBackend("google/gemma-4-31b-it", api_url="https://explicit.modal.run")
        assert backend._api_url == "https://explicit.modal.run/v1/chat/completions"

    def test_api_success(self, mocker: MockerFixture) -> None:
        """A successful API call should return the generated text."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "some riddle"}}],
        }
        mocker.patch("requests.post", return_value=mock_response)

        backend = ModalBackend("google/gemma-4-31b-it", api_url="https://test.modal.run")
        result = backend.generate("hello")
        assert result == "some riddle"

    def test_api_error(self, mocker: MockerFixture) -> None:
        """A non-200 status code should raise ``RuntimeError``."""
        mock_response = mocker.Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mocker.patch("requests.post", return_value=mock_response)

        backend = ModalBackend("google/gemma-4-31b-it", api_url="https://test.modal.run")
        with pytest.raises(RuntimeError, match="Modal API error"):
            backend.generate("hello")
