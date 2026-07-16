"""Provider-agnostic LLM client.

The provider is fully configurable via .env (LLM_PROVIDER=groq|openai|ollama).
Groq and Ollama both expose OpenAI-compatible `/v1/chat/completions` endpoints,
so a single `openai.AsyncOpenAI` client with a swapped `base_url`/`api_key`/
`model` covers all three -- including OpenAI's GPT-5 itself. This keeps the
rest of the RAG pipeline (explainer, chat, study plan) completely unaware of
which concrete provider is in use.
"""
from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.app.core.config import Settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class LLMNotConfiguredError(RuntimeError):
    """Raised when the configured LLM provider has no API key set."""


@dataclass(slots=True)
class LLMProviderConfig:
    provider: str
    base_url: str
    api_key: str
    model: str


def resolve_provider_config(settings: Settings) -> LLMProviderConfig:
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return LLMProviderConfig("openai", settings.openai_base_url, settings.openai_api_key, settings.openai_model)
    if provider == "ollama":
        # Ollama's local server doesn't require a real API key, but the OpenAI
        # SDK requires a non-empty string to be passed.
        return LLMProviderConfig("ollama", settings.ollama_base_url, "ollama", settings.ollama_model)

    return LLMProviderConfig("groq", settings.groq_base_url, settings.groq_api_key, settings.groq_model)


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.config = resolve_provider_config(settings)
        self._client: AsyncOpenAI | None = None

    @property
    def is_configured(self) -> bool:
        # Ollama doesn't need a real key (local server); other providers do.
        return self.config.provider == "ollama" or bool(self.config.api_key)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(base_url=self.config.base_url, api_key=self.config.api_key)
        return self._client

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured:
            raise LLMNotConfiguredError(
                f"LLM provider '{self.config.provider}' is not configured "
                f"(missing API key). Set the relevant *_API_KEY in .env."
            )
        return await self._complete_with_retry(system_prompt, user_prompt)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _complete_with_retry(self, system_prompt: str, user_prompt: str) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
        )
        return response.choices[0].message.content or ""
