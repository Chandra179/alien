"""Riddle generator and LLM backend abstraction.

This module hides the details of *how* a riddle is produced (local model,
HF Inference API, or a hard-coded mock) behind a single ``generate``
function.  It also handles prompt construction, JSON schema validation,
and retry logic.
"""

import json
import logging
import os
import random
from abc import ABC, abstractmethod
from typing import Any

from alien_obfuscator.config import (
    HF_API_TIMEOUT,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LOCAL_QUANTIZE,
    LOCAL_TIMEOUT,
    MAX_PLAINTEXT_LENGTH,
    MAX_RETRIES,
    MODAL_TIMEOUT,
    MOCK_DISTRACTORS,
    NUM_OPTIONS,
    OPENCODE_GO_TIMEOUT,
    OPENCODE_GO_URL,
    OPENROUTER_TIMEOUT,
    OPENROUTER_URL,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON schema that a riddle response must satisfy
# ---------------------------------------------------------------------------
RIDDLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "riddle": {"type": "string"},
        "options": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": NUM_OPTIONS,
            "maxItems": NUM_OPTIONS,
        },
        "correct_index": {"type": "integer", "minimum": 0, "maximum": NUM_OPTIONS - 1},
        "theme": {"type": "string"},
    },
    "required": ["riddle", "options", "correct_index", "theme"],
}


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_TEMPLATE: str = (
    "You are a mischievous alien archaeologist who has spent centuries studying "
    "ancient human texts. You craft riddles in the voice of {theme_description}.\n\n"
    "Generate a riddle whose ANSWER is: {plaintext}\n\n"
    "Rules:\n"
    "- The riddle must be solvable by a human familiar with {theme_name}, "
    "but confusing to anyone without cultural context.\n"
    "- The riddle should be 2–4 sentences, poetic, and contain at least one clever twist.\n"
    "- Generate exactly {num_options} answer options: 1 correct (the PLAINTEXT itself), "
    "{num_distractors} plausible distractors.\n"
    "- Distractors should be thematically adjacent (same domain, same era, similar concepts).\n"
    "- Output ONLY valid JSON.\n"
)

STRICT_JSON_PROMPT: str = (
    "\n\nIMPORTANT: Return ONLY a raw JSON object. No explanations, no reasoning, "
    "no chain-of-thought, no markdown, no code fences. "
    "Output nothing except the JSON object itself.\n"
    'Schema: {"riddle": "string", "options": ["string", "string", "string", "string", "string"], '
    '"correct_index": 0, "theme": "string"}'
)


def _validate_riddle_json(data: dict[str, Any]) -> dict[str, Any]:
    """Validate a parsed JSON dict against the riddle schema.

    Parameters
    ----------
    data : dict[str, Any]
        The parsed JSON object from the LLM.

    Returns
    -------
    dict[str, Any]
        The validated data dict (unchanged).

    Raises
    ------
    ValueError
        If any required field is missing or has the wrong type / length.
    """
    required = RIDDLE_SCHEMA["required"]
    for key in required:
        if key not in data:
            logger.warning("Missing required field: %s", key)
            raise ValueError(f"Missing required field: {key}")

    if not isinstance(data["riddle"], str) or not data["riddle"].strip():
        logger.warning("Field 'riddle' is empty or not a string")
        raise ValueError("Field 'riddle' must be a non-empty string.")

    opts = data["options"]
    if not isinstance(opts, list) or len(opts) != NUM_OPTIONS:
        logger.warning(
            "Field 'options' has wrong type or length: type=%s, length=%d",
            type(opts).__name__,
            len(opts) if isinstance(opts, list) else -1,
        )
        raise ValueError(f"Field 'options' must be a list of exactly {NUM_OPTIONS} strings.")
    for o in opts:
        if not isinstance(o, str):
            logger.warning("Non-string option found: %r", o)
            raise ValueError("Every item in 'options' must be a string.")

    ci = data["correct_index"]
    if not isinstance(ci, int) or ci < 0 or ci >= NUM_OPTIONS:
        logger.warning("Invalid correct_index: %r", ci)
        raise ValueError(f"Field 'correct_index' must be an integer between 0 and {NUM_OPTIONS - 1}.")

    if not isinstance(data.get("theme", ""), str):
        logger.warning("Field 'theme' is not a string: %r", data.get("theme"))
        raise ValueError("Field 'theme' must be a string.")

    return data


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------
class LLMBackend(ABC):
    """Abstract interface for an LLM inference backend."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send ``prompt`` to the model and return the raw text response.

        Parameters
        ----------
        prompt : str
            The fully formatted prompt.

        Returns
        -------
        str
            Raw model output.
        """
        ...


class MockBackend(LLMBackend):
    """Hard-coded backend that returns predictable JSON for testing.

    Useful for offline development, CI, and rapid UI iteration without
    waiting for real model inference.
    """

    def generate(self, prompt: str) -> str:
        """Return a canned riddle JSON based on the plaintext in the prompt.

        Parameters
        ----------
        prompt : str
            Ignored except for extracting the plaintext answer.

        Returns
        -------
        str
            A JSON string matching the riddle schema.
        """
        # Try to extract the plaintext from the prompt line "ANSWER is: X"
        plaintext = "the secret message"
        for line in prompt.splitlines():
            if "ANSWER is:" in line:
                plaintext = line.split("ANSWER is:", 1)[-1].strip()
                break

        distractors = list(MOCK_DISTRACTORS)
        return json.dumps(
            {
                "riddle": (
                    "I am the thing that humans whisper when the stars are right, "
                    "the phrase that unlocks the hidden door. What am I?"
                ),
                "options": [plaintext] + distractors,
                "correct_index": 0,
                "theme": "mock",
            },
            indent=2,
        )


class HuggingFaceBackend(LLMBackend):
    """Backend that calls the Hugging Face Inference API (serverless).

    Parameters
    ----------
    model_id : str
        Hugging Face model identifier (e.g. ``"google/gemma-4-31b-it"``).
    api_token : str | None
        Hugging Face API token. If ``None``, the token is read from the
        ``HF_TOKEN`` environment variable.
    """

    def __init__(self, model_id: str, api_token: str | None = None) -> None:
        self.model_id = model_id
        self.api_token = api_token

    def generate(self, prompt: str) -> str:
        """Call the Hugging Face Inference API and return the generated text.

        Parameters
        ----------
        prompt : str
            The prompt to send.

        Returns
        -------
        str
            Raw model output.

        Raises
        ------
        RuntimeError
            If the API request fails or returns an error.
        """
        import os

        import requests

        token = self.api_token or os.environ.get("HF_TOKEN")
        if not token:
            logger.error("HF_TOKEN not found in environment")
            raise RuntimeError("HF_TOKEN not provided and not found in environment.")

        url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": LLM_MAX_TOKENS,
                "temperature": LLM_TEMPERATURE,
                "return_full_text": False,
            },
        }

        response = requests.post(url, headers=headers, json=payload, timeout=HF_API_TIMEOUT)
        if response.status_code != 200:
            logger.error("HF API error %d: %s", response.status_code, response.text)
            raise RuntimeError(f"HF API error {response.status_code}: {response.text}")

        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("generated_text", "")
        logger.warning("HF API returned unexpected format: %s", str(data)[:200])
        return str(data)


class OpenAICompatibleBackend(LLMBackend):
    """Generic backend for any OpenAI-compatible chat completions API.

    Parameters
    ----------
    model_id : str
        Model identifier (e.g. ``"google/gemma-4-31b-it"``).
    api_key : str | None
        API key. If ``None``, read from ``key_env_var`` env variable.
    api_url : str
        The chat completions endpoint URL.
    key_env_var : str
        Environment variable name to look for the API key.
    provider_name : str
        Human-readable provider name for error messages.
    extra_headers : dict
        Additional HTTP headers to send with each request.
    """

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        api_url: str = "",
        key_env_var: str = "",
        provider_name: str = "API",
        extra_headers: dict | None = None,
        timeout: int = 120,
    ) -> None:
        self.model_id = model_id
        self.api_key = api_key
        self._api_url = api_url
        self._key_env_var = key_env_var
        self._provider_name = provider_name
        self._extra_headers = extra_headers or {}
        self._timeout = timeout

    def generate(self, prompt: str) -> str:
        """Call the chat completions API and return the generated text.

        Parameters
        ----------
        prompt : str
            The prompt to send.

        Returns
        -------
        str
            Raw model output.

        Raises
        ------
        RuntimeError
            If the API request fails or returns an error.
        """
        import os

        import requests

        key = self.api_key or os.environ.get(self._key_env_var)
        if not key:
            logger.error("%s API key not found in environment var %s", self._provider_name, self._key_env_var)
            raise RuntimeError(
                f"{self._provider_name} API key not provided and {self._key_env_var} not found in environment."
            )

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": LLM_TEMPERATURE,
        }

        response = requests.post(self._api_url, headers=headers, json=payload, timeout=self._timeout)
        if response.status_code != 200:
            logger.error("%s API error %d: %s", self._provider_name, response.status_code, response.text)
            raise RuntimeError(f"{self._provider_name} API error {response.status_code}: {response.text}")

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            logger.error("%s returned no choices. Response: %s", self._provider_name, str(data)[:500])
            raise RuntimeError(f"{self._provider_name} returned no choices.")
        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        # Reasoning models (e.g. DeepSeek) sometimes put output in
        # reasoning_content instead of content.
        if not content:
            content = msg.get("reasoning_content", "")
            if content:
                logger.warning(
                    "%s returned content in reasoning_content field (model=%s)",
                    self._provider_name,
                    data.get("model", "unknown"),
                )
        if not content:
            logger.error(
                "%s returned empty content. Full response: %s",
                self._provider_name,
                str(data)[:500],
            )
            raise RuntimeError(f"{self._provider_name} returned empty content.")
        return content


class OpenRouterBackend(OpenAICompatibleBackend):
    """Backend for OpenRouter's chat completions API."""

    def __init__(self, model_id: str, api_key: str | None = None) -> None:
        super().__init__(
            model_id=model_id,
            api_key=api_key,
            api_url=OPENROUTER_URL,
            key_env_var="OPENROUTER_API_KEY",
            provider_name="OpenRouter",
            extra_headers={
                "HTTP-Referer": "https://github.com/koala/alien-obfuscator",
                "X-Title": "Alien Obfuscator",
            },
            timeout=OPENROUTER_TIMEOUT,
        )


class OpenCodeGoBackend(OpenAICompatibleBackend):
    """Backend for OpenCode Go chat completions API."""

    def __init__(self, model_id: str, api_key: str | None = None) -> None:
        super().__init__(
            model_id=model_id,
            api_key=api_key,
            api_url=OPENCODE_GO_URL,
            key_env_var="OPENCODE_GO_API_KEY",
            provider_name="OpenCode Go",
            timeout=OPENCODE_GO_TIMEOUT,
        )


class ModalBackend(OpenAICompatibleBackend):
    """Backend for a Modal-deployed vLLM server (OpenAI-compatible).

    Connects to a pre-deployed Modal vLLM instance serving an LLM.
    The Modal API URL is public by default — no authentication is needed
    beyond the URL itself.

    Parameters
    ----------
    model_id : str
        Model identifier served by the Modal endpoint
        (e.g. ``"google/gemma-4-31b-it"``).
    api_url : str | None
        Base URL of the Modal-deployed vLLM server. If ``None``, read from
        the ``MODAL_API_URL`` environment variable.
    """

    def __init__(
        self,
        model_id: str,
        api_url: str | None = None,
    ) -> None:
        import os

        resolved_url = api_url or os.environ.get("MODAL_API_URL", "")
        if not resolved_url:
            raise ValueError("Modal API URL not provided and MODAL_API_URL not set in environment.")

        super().__init__(
            model_id=model_id,
            api_key=None,
            api_url=resolved_url.rstrip("/") + "/v1/chat/completions",
            key_env_var="",
            provider_name="Modal",
            timeout=MODAL_TIMEOUT,
        )

    def generate(self, prompt: str) -> str:
        """Call the Modal-deployed vLLM server and return the generated text.

        Modal web endpoints are public, so no API key is required.

        Parameters
        ----------
        prompt : str
            The prompt to send.

        Returns
        -------
        str
            Raw model output.

        Raises
        ------
        RuntimeError
            If the API request fails or returns an error.
        """
        import requests

        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": LLM_TEMPERATURE,
        }

        response = requests.post(self._api_url, headers=headers, json=payload, timeout=self._timeout)
        if response.status_code != 200:
            logger.error(
                "%s API error %d: %s",
                self._provider_name,
                response.status_code,
                response.text,
            )
            raise RuntimeError(f"{self._provider_name} API error {response.status_code}: {response.text}")

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            logger.error(
                "%s returned no choices. Response: %s",
                self._provider_name,
                str(data)[:500],
            )
            raise RuntimeError(f"{self._provider_name} returned no choices.")
        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        if not content:
            content = msg.get("reasoning_content", "")
        if not content:
            logger.error(
                "%s returned empty content. Full response: %s",
                self._provider_name,
                str(data)[:500],
            )
            raise RuntimeError(f"{self._provider_name} returned empty content.")
        return content


class LocalGPU4BitBackend(LLMBackend):
    """Backend that runs the model locally on the host GPU using transformers.

    Loads a Hugging Face causal LM at startup and runs inference directly on
    the local GPU. Supports fp16, bf16, 8-bit, and 4-bit quantization.
    Designed for Hugging Face Spaces with dedicated GPU hardware
    (e.g. RTX Pro 6000 with 96 GB VRAM).

    Parameters
    ----------
    model_id : str
        Hugging Face model identifier (e.g. ``"google/gemma-4-31b-it"``).
    timeout : int
        Maximum seconds allowed for generation. Default is 600.
    quantize : str
        Quantization mode: ``"fp16"``, ``"bf16"``, ``"8bit"``, or ``"4bit"``.
        Default is ``"fp16"``.

    Raises
    ------
    ImportError
        If ``torch`` or ``transformers`` are not installed.
    RuntimeError
        If no CUDA-capable GPU is available or the model fails to load.
    """

    def __init__(
        self,
        model_id: str,
        timeout: int = LOCAL_TIMEOUT,
        quantize: str = LOCAL_QUANTIZE,
    ) -> None:
        import torch

        self._model_id = model_id
        self._timeout = timeout
        self._quantize = quantize
        self._model = None
        self._tokenizer = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

        if self._device != "cuda":
            raise RuntimeError(
                "LocalGPU4BitBackend requires a CUDA-capable GPU, "
                f"but torch.cuda.is_available() returned {torch.cuda.is_available()}"
            )

        logger.info(
            "LocalGPU4BitBackend: model=%s quantize=%s device=%s",
            model_id,
            quantize,
            self._device,
        )

        self._load_model()

    @staticmethod
    def is_available() -> bool:
        """Check whether local GPU inference can be used.

        Returns
        -------
        bool
            ``True`` if ``torch`` and ``transformers`` are importable and a
            CUDA-capable GPU is detected.
        """
        try:
            import torch  # noqa: F401
        except ImportError:
            return False
        return torch.cuda.is_available()

    def _load_model(self) -> None:
        """Load tokenizer and model with the configured quantization settings.

        The model is loaded onto the GPU. Quantization is configured via
        ``BitsAndBytesConfig`` for 4/8-bit or via ``torch_dtype`` for fp16/bf16.

        Raises
        ------
        ImportError
            If ``transformers`` is not installed.
        RuntimeError
            If the model fails to load.
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        logger.info("Loading tokenizer for %s ...", self._model_id)
        tokenizer = AutoTokenizer.from_pretrained(self._model_id)
        if tokenizer.pad_token is None:  # type: ignore
            tokenizer.pad_token = tokenizer.eos_token  # type: ignore

        quantization_config = None
        torch_dtype: torch.dtype | str = torch.float16

        if self._quantize == "4bit":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
            torch_dtype = "auto"
        elif self._quantize == "8bit":
            quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            torch_dtype = "auto"
        elif self._quantize in ("bf16", "bfloat16"):
            torch_dtype = torch.bfloat16

        logger.info(
            "Loading model %s with quantize=%s ...",
            self._model_id,
            self._quantize,
        )
        model = AutoModelForCausalLM.from_pretrained(
            self._model_id,
            quantization_config=quantization_config,
            torch_dtype=torch_dtype,
            device_map="auto",
        )
        logger.info("Model loaded successfully on %s", self._device)

        self._tokenizer = tokenizer
        self._model = model

    def generate(self, prompt: str) -> str:
        """Run inference on the local GPU and return generated text.

        Parameters
        ----------
        prompt : str
            The prompt to send.

        Returns
        -------
        str
            Raw model output.

        Raises
        ------
        RuntimeError
            If the model has not been loaded or generation fails.
        """
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("Model not loaded. Call _load_model() first.")

        import torch

        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)

        with torch.no_grad():
            outputs = self._model.generate(  # type: ignore
                **inputs,
                max_new_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                do_sample=True,
                pad_token_id=self._tokenizer.pad_token_id,
            )

        generated = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        prompt_len = len(self._tokenizer.decode(inputs["input_ids"][0], skip_special_tokens=True))
        if isinstance(generated, str):
            response = generated[prompt_len:].strip()
        else:
            response = str(generated)[prompt_len:].strip()

        return response


class AutoBackend(LLMBackend):
    """Smart backend that tries a configurable sequence of inference backends.

    On each ``generate`` call the wrapper iterates through the ordered
    fallback list, returning the first successful response. The default
    order is **Modal → local GPU → mock**, configurable via the
    ``AUTO_FALLBACK_ORDER`` environment variable or ``config.yaml``.

    Recognised backend names in the fallback order:

    * ``"modal"`` — ``ModalBackend`` (requires ``MODAL_API_URL`` env var)
    * ``"local"`` — ``LocalGPU4BitBackend`` (requires CUDA + torch/transformers)
    * ``"mock"`` — ``MockBackend`` (always available)

    Parameters
    ----------
    model_id : str
        Model identifier used by both Modal and local backends.
    quantize : str
        Quantization mode for local GPU. Default is ``"fp16"``.
    fallback_order : list[str]
        Ordered list of backend names to try. Default is
        ``["modal", "local", "mock"]``.
    """

    # Map backend name → (class_or_none, availability_check)
    _BACKEND_REGISTRY: dict[str, Any] = {
        "modal": (ModalBackend, lambda: bool(os.environ.get("MODAL_API_URL"))),
        "local": (LocalGPU4BitBackend, LocalGPU4BitBackend.is_available),
        "mock": (MockBackend, lambda: True),
    }

    def __init__(
        self,
        model_id: str,
        quantize: str = LOCAL_QUANTIZE,
        fallback_order: list[str] | None = None,
    ) -> None:
        if fallback_order is None:
            fallback_order = ["modal", "local", "mock"]

        self._backends: list[LLMBackend] = []

        for name in fallback_order:
            name = name.strip().lower()
            if name not in self._BACKEND_REGISTRY:
                logger.warning("AutoBackend: unknown backend '%s', skipping", name)
                continue

            backend_cls, availability_fn = self._BACKEND_REGISTRY[name]
            try:
                if not availability_fn():
                    logger.info("AutoBackend: backend '%s' not available", name)
                    continue
            except Exception as exc:
                logger.warning("AutoBackend: availability check for '%s' failed: %s", name, exc)
                continue

            try:
                if name == "modal":
                    backend = backend_cls(model_id)
                elif name == "local":
                    backend = backend_cls(model_id, quantize=quantize)
                elif name == "mock":
                    backend = backend_cls()
                else:
                    backend = backend_cls(model_id)
                self._backends.append(backend)
                logger.info("AutoBackend: registered '%s'", name)
            except Exception as exc:
                logger.warning("AutoBackend: failed to init '%s': %s", name, exc)

        if not self._backends:
            logger.warning("AutoBackend: no backends available, forcing mock")
            self._backends = [MockBackend()]

        logger.info(
            "AutoBackend: fallback chain = %s",
            [type(b).__name__ for b in self._backends],
        )

    def generate(self, prompt: str) -> str:
        """Try each backend in fallback order, return first successful response.

        Parameters
        ----------
        prompt : str
            The prompt to send.

        Returns
        -------
        str
            Raw model output.
        """
        for i, backend in enumerate(self._backends):
            try:
                return backend.generate(prompt)
            except Exception as exc:
                logger.warning(
                    "AutoBackend: backend %d/%d (%s) failed: %s",
                    i + 1,
                    len(self._backends),
                    type(backend).__name__,
                    exc,
                )

        # Should be unreachable (mock always succeeds)
        logger.error("AutoBackend: all %d backends exhausted", len(self._backends))
        raise RuntimeError("All backends exhausted")


# ---------------------------------------------------------------------------
# Riddle generator
# ---------------------------------------------------------------------------
class RiddleGenerator:
    """Orchestrate prompt building, LLM inference, and response validation.

    The LLM draws on its own training knowledge of literary and mythological
    themes — no static corpus is needed.

    Parameters
    ----------
    backend : LLMBackend
        The concrete LLM implementation to use.
    max_retries : int, default 2
        How many times to retry on JSON parse / validation errors.
    """

    def __init__(
        self,
        backend: LLMBackend,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._backend = backend
        self._max_retries = max_retries

    def _build_prompt(self, plaintext: str, theme: str) -> str:
        """Construct the full prompt for the LLM.

        No static corpus excerpt is injected — the LLM draws on its
        training knowledge to produce authentic thematically-grounded
        riddles.

        Parameters
        ----------
        plaintext : str
            The secret message to encode.
        theme : str
            Theme key (e.g. ``"greek_myth"``).

        Returns
        -------
        str
            The formatted prompt.
        """
        from alien_obfuscator.config import THEME_LABELS

        theme_label = THEME_LABELS.get(theme, theme)
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            theme_description=theme_label,
            theme_name=theme_label,
            plaintext=plaintext,
            num_options=NUM_OPTIONS,
            num_distractors=NUM_OPTIONS - 1,
        )
        prompt += STRICT_JSON_PROMPT
        return prompt

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Clean and parse the raw LLM output into a validated dict.

        Strips markdown fences (```json ... ```) if present. If the full text
        is not valid JSON, attempts to extract the first JSON object ``{...}``
        from within the text (handles some models that wrap JSON in
        chain-of-thought).

        Parameters
        ----------
        raw : str
            Raw text from the LLM.

        Returns
        -------
        dict[str, Any]
            Validated riddle dict.

        Raises
        ------
        ValueError
            If the text cannot be parsed or validated.
        """
        text = raw.strip()
        if not text:
            logger.error("LLM returned empty response")
            raise ValueError("LLM returned empty response")
        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline >= 0:
                text = text[first_newline + 1 :]
            else:
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        # Try full text first
        if text.startswith("{"):
            try:
                data = json.loads(text)
                return _validate_riddle_json(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: scan for the first valid JSON object in the text
        pos = 0
        while True:
            start = text.find("{", pos)
            if start < 0:
                break
            depth = 0
            matched = False
            for end in range(start, len(text)):
                if text[end] == "{":
                    depth += 1
                elif text[end] == "}":
                    depth -= 1
                    if depth == 0:
                        matched = True
                        candidate = text[start : end + 1]
                        try:
                            data = json.loads(candidate)
                            logger.info("Extracted JSON from text (len=%d)", len(candidate))
                            return _validate_riddle_json(data)
                        except (json.JSONDecodeError, ValueError):
                            pass
                        break
            if not matched:
                pos = start + 1
            else:
                pos = end + 1

        logger.warning(
            "Failed to parse LLM output as JSON: Raw text (len=%d): %.400s",
            len(raw),
            text[:400],
        )
        raise ValueError("Could not extract valid JSON from LLM response.")

    def generate(self, plaintext: str, theme: str) -> dict[str, Any]:
        """Generate a riddle + MCQ options for the given plaintext and theme.

        Retries up to ``max_retries`` times if the LLM returns malformed
        JSON. On success, the ``options`` list is shuffled and
        ``correct_index`` is updated accordingly.

        Parameters
        ----------
        plaintext : str
            The secret message to encode.
        theme : str
            Theme key or ``"surprise"``.

        Returns
        -------
        dict[str, Any]
            A validated riddle dict with shuffled options.

        Raises
        ------
        ValueError
            If the plaintext is empty or exceeds the length limit, or if the
            LLM output cannot be parsed as valid JSON.
        RuntimeError
            If all retries are exhausted without producing valid JSON.
        """
        if not plaintext or not plaintext.strip():
            raise ValueError("Plaintext must not be empty.")
        if len(plaintext) > MAX_PLAINTEXT_LENGTH:
            raise ValueError(f"Plaintext exceeds {MAX_PLAINTEXT_LENGTH} characters.")

        last_error: Exception | None = None

        for _attempt in range(self._max_retries + 1):
            try:
                prompt = self._build_prompt(plaintext, theme)
                raw = self._backend.generate(prompt)
                data = self._parse_response(raw)
                break
            except (json.JSONDecodeError, ValueError, RuntimeError) as exc:
                logger.warning("Attempt %d/%d failed: %s", _attempt + 1, self._max_retries + 1, exc)
                last_error = exc
                continue
        else:
            logger.error("All %d attempts exhausted", self._max_retries + 1)
            raise RuntimeError(
                f"Failed to generate valid riddle after {self._max_retries + 1} attempts."
            ) from last_error

        # Shuffle options so the correct answer moves to a random position
        options = data["options"]
        correct_answer = options[data["correct_index"]]
        random.shuffle(options)
        data["correct_index"] = options.index(correct_answer)
        data["theme"] = theme
        return data
