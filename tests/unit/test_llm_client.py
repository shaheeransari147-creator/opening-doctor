import pytest

from backend.app.core.config import Settings
from rag.generation.llm_client import LLMClient, LLMNotConfiguredError, resolve_provider_config


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_defaults_to_openrouter_provider():
    config = resolve_provider_config(_settings())
    assert config.provider == "openrouter"
    assert config.base_url == "https://openrouter.ai/api/v1"
    assert config.model == "nvidia/nemotron-3-ultra-550b-a55b:free"


def test_resolves_openrouter_provider():
    config = resolve_provider_config(
        _settings(llm_provider="openrouter", openrouter_api_key="sk-or-test", openrouter_model="some/model:free")
    )
    assert config.provider == "openrouter"
    assert config.api_key == "sk-or-test"
    assert config.model == "some/model:free"


def test_openrouter_client_not_configured_without_api_key():
    client = LLMClient(_settings(llm_provider="openrouter", openrouter_api_key=""))
    assert client.is_configured is False


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
