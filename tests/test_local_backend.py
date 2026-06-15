"""Unit tests for the LocalGPU4BitBackend and AutoBackend classes."""

import json

import pytest
from pytest_mock import MockerFixture


class TestLocalGPU4BitBackendIsAvailable:
    """Tests for the static ``is_available`` method."""

    def test_returns_false_when_torch_not_importable(self, mocker: MockerFixture) -> None:
        """When torch cannot be imported, is_available returns False."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("No module named 'torch'")
            return original_import(name, *args, **kwargs)

        mocker.patch("builtins.__import__", side_effect=mock_import)

        from importlib import reload

        import alien_obfuscator.riddle_generator as mod

        reload(mod)
        result = mod.LocalGPU4BitBackend.is_available()
        assert result is False

    def test_returns_false_when_no_cuda(self, mocker: MockerFixture) -> None:
        """When torch is available but CUDA is not, is_available returns False."""
        mock_torch = mocker.MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mocker.patch.dict("sys.modules", {"torch": mock_torch})

        from alien_obfuscator.riddle_generator import LocalGPU4BitBackend

        result = LocalGPU4BitBackend.is_available()
        assert result is False

    def test_returns_true_when_torch_and_cuda_available(self, mocker: MockerFixture) -> None:
        """When torch and CUDA are both available, is_available returns True."""
        mock_torch = mocker.MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mocker.patch.dict("sys.modules", {"torch": mock_torch})

        from alien_obfuscator.riddle_generator import LocalGPU4BitBackend

        result = LocalGPU4BitBackend.is_available()
        assert result is True


class TestLocalGPU4BitBackend:
    """Tests for the local GPU backend."""

    def test_init_raises_without_cuda(self, mocker: MockerFixture) -> None:
        """When CUDA is not available, __init__ raises RuntimeError."""
        mock_torch = mocker.MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mocker.patch.dict("sys.modules", {"torch": mock_torch})

        from alien_obfuscator.riddle_generator import LocalGPU4BitBackend

        with pytest.raises(RuntimeError, match="CUDA-capable GPU"):
            LocalGPU4BitBackend("dummy-model")

    def test_init_loads_model_on_startup(self, mocker: MockerFixture) -> None:
        """When CUDA is available, the model and tokenizer are loaded on init."""
        mock_torch = mocker.MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.float16 = "float16"
        mock_torch.no_grad.return_value.__enter__ = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"torch": mock_torch})

        mock_tokenizer = mocker.MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "[EOS]"
        mock_model = mocker.MagicMock()

        mock_auto_model = mocker.MagicMock()
        mock_auto_model.from_pretrained.return_value = mock_model
        mock_auto_tokenizer = mocker.MagicMock()
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer
        mock_bnb = mocker.MagicMock()

        mock_transformers = mocker.MagicMock()
        mock_transformers.AutoModelForCausalLM = mock_auto_model
        mock_transformers.AutoTokenizer = mock_auto_tokenizer
        mock_transformers.BitsAndBytesConfig = mock_bnb
        mocker.patch.dict("sys.modules", {"transformers": mock_transformers})

        from alien_obfuscator.riddle_generator import LocalGPU4BitBackend

        backend = LocalGPU4BitBackend("dummy-model", quantize="fp16")

        assert backend._model is mock_model
        assert backend._tokenizer is mock_tokenizer
        mock_auto_tokenizer.from_pretrained.assert_called_once_with("dummy-model")
        mock_auto_model.from_pretrained.assert_called_once()


class TestAutoBackend:
    """Tests for the configurable auto-backend with fallback chain."""

    def test_default_order_modal_local_mock(self, mocker: MockerFixture) -> None:
        """Default fallback chain is modal → local → mock when all available."""
        mocker.patch.dict("os.environ", {"MODAL_API_URL": "https://foo.modal.run"}, clear=True)

        mock_torch = mocker.MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.float16 = "float16"
        mocker.patch.dict("sys.modules", {"torch": mock_torch})

        mock_transformers = mocker.MagicMock()
        mock_tokenizer_cls = mocker.MagicMock()
        mock_tokenizer = mocker.MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "[EOS]"
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        mock_model_cls = mocker.MagicMock()
        mock_model_cls.from_pretrained.return_value = mocker.MagicMock()
        mock_transformers.AutoTokenizer = mock_tokenizer_cls
        mock_transformers.AutoModelForCausalLM = mock_model_cls
        mock_transformers.BitsAndBytesConfig = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"transformers": mock_transformers})

        mocker.patch("alien_obfuscator.riddle_generator.ModalBackend.__init__", return_value=None)

        from alien_obfuscator.riddle_generator import AutoBackend

        backend = AutoBackend("test-model")
        names = [type(b).__name__ for b in backend._backends]
        assert names == ["ModalBackend", "LocalGPU4BitBackend", "MockBackend"]

    def test_custom_fallback_order(self, mocker: MockerFixture) -> None:
        """Custom fallback_order is respected."""
        mocker.patch.dict("os.environ", {}, clear=True)
        mocker.patch(
            "alien_obfuscator.riddle_generator.LocalGPU4BitBackend.is_available",
            return_value=False,
        )

        from alien_obfuscator.riddle_generator import AutoBackend

        backend = AutoBackend("test-model", fallback_order=["local", "mock"])
        names = [type(b).__name__ for b in backend._backends]
        # local unavailable, so only mock
        assert names == ["MockBackend"]

    def test_skips_unavailable_modal(self, mocker: MockerFixture) -> None:
        """When MODAL_API_URL is not set, modal is skipped."""
        mocker.patch.dict("os.environ", {}, clear=True)
        mocker.patch(
            "alien_obfuscator.riddle_generator.LocalGPU4BitBackend.is_available",
            return_value=False,
        )

        from alien_obfuscator.riddle_generator import AutoBackend

        backend = AutoBackend("test-model")
        names = [type(b).__name__ for b in backend._backends]
        assert names == ["MockBackend"]

    def test_skips_unavailable_local(self, mocker: MockerFixture) -> None:
        """When local GPU is not available, it is skipped."""
        mocker.patch.dict("os.environ", {"MODAL_API_URL": "https://foo.modal.run"}, clear=True)
        mocker.patch(
            "alien_obfuscator.riddle_generator.LocalGPU4BitBackend.is_available",
            return_value=False,
        )
        mocker.patch(
            "alien_obfuscator.riddle_generator.ModalBackend.__init__",
            return_value=None,
        )

        from alien_obfuscator.riddle_generator import AutoBackend

        backend = AutoBackend("test-model", fallback_order=["local", "modal", "mock"])
        names = [type(b).__name__ for b in backend._backends]
        assert names == ["ModalBackend", "MockBackend"]

    def test_tries_first_then_falls_back(self, mocker: MockerFixture) -> None:
        """When first backend fails, the second is tried."""
        from alien_obfuscator.riddle_generator import AutoBackend

        mock_primary = mocker.MagicMock()
        mock_primary.generate.side_effect = RuntimeError("boom")
        mock_fallback = mocker.MagicMock()
        mock_fallback.generate.return_value = (
            '{"riddle":"r","options":["a","b","c","d","e"],"correct_index":0,"theme":"t"}'
        )

        backend = AutoBackend.__new__(AutoBackend)
        backend._backends = [mock_primary, mock_fallback]

        result = backend.generate("test prompt")
        mock_primary.generate.assert_called_once()
        mock_fallback.generate.assert_called_once()
        data = json.loads(result)
        assert data["riddle"] == "r"

    def test_falls_through_all_to_mock(self, mocker: MockerFixture) -> None:
        """When all backends fail, mock always succeeds."""
        from alien_obfuscator.riddle_generator import AutoBackend

        mock_one = mocker.MagicMock()
        mock_one.generate.side_effect = RuntimeError("fail1")
        mock_two = mocker.MagicMock()
        mock_two.generate.side_effect = RuntimeError("fail2")
        mock_mock = mocker.MagicMock()
        mock_mock.generate.return_value = '{"riddle":"r","options":["a","b","c","d","e"],"correct_index":0,"theme":"t"}'

        backend = AutoBackend.__new__(AutoBackend)
        backend._backends = [mock_one, mock_two, mock_mock]

        result = backend.generate("test prompt")
        mock_one.generate.assert_called_once()
        mock_two.generate.assert_called_once()
        mock_mock.generate.assert_called_once()
        data = json.loads(result)
        assert data["riddle"] == "r"

    def test_unknown_backend_name_skipped(self, mocker: MockerFixture) -> None:
        """Unknown backend names in fallback_order are silently skipped."""
        mocker.patch.dict("os.environ", {}, clear=True)

        from alien_obfuscator.riddle_generator import AutoBackend

        backend = AutoBackend("test-model", fallback_order=["bogus", "mock"])
        names = [type(b).__name__ for b in backend._backends]
        assert names == ["MockBackend"]
