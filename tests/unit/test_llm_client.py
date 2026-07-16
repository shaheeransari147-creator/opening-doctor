import pytest

from backend.app.core.config import Settings
from rag.generation.llm_client import LLMClient, LLMNotConfiguredError, resolve_provider_config


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_defaults_to_ollama_provider():
    config = resolve_provider_config(_settings())
    assert config.provider == "ollama"
    assert config.base_url == "http://localhost:11434/v1"


def test_resolves_openai_provider():
    config = resolve_provider_config(_settings(llm_provider="openai", openai_api_key="sk-test", openai_model="gpt-5"))
    assert config.provider == "openai"
    assert config.api_key == "sk-test"
    assert config.model == "gpt-5"


def test_resolves_ollama_provider_without_requiring_a_key():
    config = resolve_provider_config(_settings(llm_provider="ollama"))
    assert config.provider == "ollama"
    assert config.api_key  # non-empty placeholder, required by the OpenAI SDK


def test_ollama_client_is_always_considered_configured():
    client = LLMClient(_settings(llm_provider="ollama"))
    assert client.is_configured is True


def test_groq_client_not_configured_without_api_key():
    client = LLMClient(_settings(llm_provider="groq", groq_api_key=""))
    assert client.is_configured is False


@pytest.mark.asyncio
async def test_complete_raises_when_not_configured():
    client = LLMClient(_settings(llm_provider="groq", groq_api_key=""))
    with pytest.raises(LLMNotConfiguredError):
        await client.complete("system", "user")
