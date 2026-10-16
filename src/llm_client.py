"""Provider-agnostic LLM client used by the repair engines.

Every backend returns an `LLMResponse` with text, token usage and latency so
cost/latency metrics are comparable across providers. Backends:
- `gemini`: Google Gemini API (key from GEMINI_API_KEY, env or `.env`).
- `mock`:   deterministic canned output for tests and dry runs (0 tokens billed).
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


@dataclass
class LLMResponse:
    """One completion plus the accounting needed for cost analysis."""

    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False

    @property
    def total_tokens(self) -> int:
        """Billed tokens (thinking tokens are billed as output)."""
        return self.input_tokens + self.output_tokens + self.thinking_tokens


class LLMClient(Protocol):
    """Minimal interface every backend implements."""

    model: str

    def complete(self, prompt: str, system: str | None = None) -> LLMResponse:
        """Returns a single completion for `prompt`."""
        ...


def load_env(path: Path = ENV_FILE) -> None:
    """Loads KEY=VALUE lines from `.env` into os.environ without overriding.

    On Kaggle (no `.env`), falls back to the GEMINI_API_KEY notebook secret.
    """
    if not path.exists():
        if "GEMINI_API_KEY" not in os.environ and os.path.isdir("/kaggle"):
            try:
                from kaggle_secrets import UserSecretsClient  # type: ignore[import-not-found]

                os.environ["GEMINI_API_KEY"] = UserSecretsClient().get_secret("GEMINI_API_KEY")
            except Exception:
                pass
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


class GeminiClient:
    """Google Gemini backend via the `google-genai` SDK.

    Args:
        model: Gemini model id, e.g. "gemini-3.5-flash-lite".
        temperature: Sampling temperature (0 for reproducibility).
        max_output_tokens: Hard cap on generated tokens.
        seed: Sampling seed forwarded to the API.
        thinking_level: Gemini 3.x thinking depth ("minimal", "low", "medium", "high");
            None leaves the model default.
    """

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_output_tokens: int = 2048,
        seed: int | None = 42,
        thinking_level: str | None = "minimal",
    ) -> None:
        from google import genai

        load_env()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set (export it or add it to .env)")
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.seed = seed
        self.thinking_level = thinking_level

    def complete(self, prompt: str, system: str | None = None) -> LLMResponse:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            seed=self.seed,
            thinking_config=(
                types.ThinkingConfig(thinking_level=self.thinking_level)
                if self.thinking_level is not None
                else None
            ),
        )
        start = time.perf_counter()
        resp = self._client.models.generate_content(
            model=self.model, contents=prompt, config=config
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        usage = resp.usage_metadata
        return LLMResponse(
            text=resp.text or "",
            model=self.model,
            input_tokens=(usage.prompt_token_count or 0) if usage else 0,
            output_tokens=(usage.candidates_token_count or 0) if usage else 0,
            thinking_tokens=(usage.thoughts_token_count or 0) if usage else 0,
            latency_ms=latency_ms,
        )


class MockClient:
    """Deterministic backend: returns `reply` (or the prompt's code block) unchanged."""

    def __init__(self, reply: str = "", model: str = "mock") -> None:
        self.reply = reply
        self.model = model
        self.calls: list[str] = []

    def complete(self, prompt: str, system: str | None = None) -> LLMResponse:
        self.calls.append(prompt)
        return LLMResponse(
            text=self.reply,
            model=self.model,
            input_tokens=len(prompt) // 4,
            output_tokens=len(self.reply) // 4,
        )


def make_client(provider: str, model: str, **kwargs: object) -> LLMClient:
    """Factory used by configs: provider in {"gemini", "mock"}."""
    if provider == "gemini":
        return GeminiClient(model=model, **kwargs)  # type: ignore[arg-type]
    if provider == "mock":
        return MockClient(model=model, **kwargs)  # type: ignore[arg-type]
    raise ValueError(f"Unknown LLM provider: {provider}")
