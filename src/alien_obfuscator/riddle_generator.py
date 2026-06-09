"""Riddle generator and LLM backend abstraction.

This module hides the details of *how* a riddle is produced (local model,
HF Inference API, or a hard-coded mock) behind a single ``generate``
function.  It also handles prompt construction, JSON schema validation,
and retry logic.
"""

import json
import logging
import random
from abc import ABC, abstractmethod
from typing import Any

from alien_obfuscator.config import MAX_PLAINTEXT_LENGTH, MAX_RETRIES, NUM_OPTIONS, LLM_MAX_TOKENS
from alien_obfuscator.corpus_manager import CorpusManager

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

        distractors = [
            "a wrong answer",
            "another wrong answer",
            "yet another wrong answer",
            "the last wrong answer",
        ]
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
            "parameters": {"max_new_tokens": LLM_MAX_TOKENS, "temperature": 0.8, "return_full_text": False},
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
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
    ) -> None:
        self.model_id = model_id
        self.api_key = api_key
        self._api_url = api_url
        self._key_env_var = key_env_var
        self._provider_name = provider_name
        self._extra_headers = extra_headers or {}

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
            "temperature": 0.8,
        }

        response = requests.post(self._api_url, headers=headers, json=payload, timeout=120)
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
            api_url="https://openrouter.ai/api/v1/chat/completions",
            key_env_var="OPENROUTER_API_KEY",
            provider_name="OpenRouter",
            extra_headers={
                "HTTP-Referer": "https://github.com/koala/alien-obfuscator",
                "X-Title": "Alien Obfuscator",
            },
        )


class OpenCodeGoBackend(OpenAICompatibleBackend):
    """Backend for OpenCode Go chat completions API."""

    def __init__(self, model_id: str, api_key: str | None = None) -> None:
        super().__init__(
            model_id=model_id,
            api_key=api_key,
            api_url="https://opencode.ai/zen/go/v1/chat/completions",
            key_env_var="OPENCODE_GO_API_KEY",
            provider_name="OpenCode Go",
        )


# ---------------------------------------------------------------------------
# Riddle generator
# ---------------------------------------------------------------------------
class RiddleGenerator:
    """Orchestrate prompt building, LLM inference, and response validation.

    Parameters
    ----------
    backend : LLMBackend
        The concrete LLM implementation to use.
    corpus_manager : CorpusManager
        Source of random corpus excerpts for prompt enrichment.
    max_retries : int, default 2
        How many times to retry on JSON parse / validation errors.
    """

    def __init__(
        self,
        backend: LLMBackend,
        corpus_manager: CorpusManager,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._backend = backend
        self._corpus = corpus_manager
        self._max_retries = max_retries

    def _build_prompt(self, plaintext: str, theme: str, excerpt: str) -> str:
        """Construct the full prompt for the LLM.

        Parameters
        ----------
        plaintext : str
            The secret message to encode.
        theme : str
            Theme key (e.g. ``"greek_myth"``).
        excerpt : str
            A corpus excerpt to inject as creative inspiration.

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
        prompt += f"\n\nSource text inspiration:\n{excerpt}\n"
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
            text = text.removeprefix("```json").removeprefix("```")
            text = text.removesuffix("```").strip()

        # Try full text first
        if text.startswith("{"):
            try:
                data = json.loads(text)
                return _validate_riddle_json(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: extract the first JSON object from the text
        start = text.find("{")
        if start >= 0:
            depth = 0
            for end in range(start, len(text)):
                if text[end] == "{":
                    depth += 1
                elif text[end] == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : end + 1]
                        try:
                            data = json.loads(candidate)
                            logger.info("Extracted JSON from text (len=%d)", len(candidate))
                            return _validate_riddle_json(data)
                        except (json.JSONDecodeError, ValueError):
                            pass
                        break  # outermost brace pair didn't parse; stop

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

        excerpt = self._corpus.get_excerpt(theme, count=1)[0]
        last_error: Exception | None = None

        for _attempt in range(self._max_retries + 1):
            try:
                prompt = self._build_prompt(plaintext, theme, excerpt)
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
