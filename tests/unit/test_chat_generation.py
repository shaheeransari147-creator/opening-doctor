import pytest

from rag.generation.chat import answer_chat_question
from rag.retrieval.reranker import RerankedChunk


class _FakeLLMClient:
    """Captures the prompts it was called with instead of hitting a real provider."""

    def __init__(self) -> None:
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return "fake answer [1]"


def _chunk(text: str, opening: str, theme: str, source: str) -> RerankedChunk:
    return RerankedChunk(text=text, payload={"opening": opening, "theme": theme, "source": source}, rerank_score=1.0)


@pytest.mark.asyncio
async def test_chat_includes_player_profile_when_given():
    llm = _FakeLLMClient()
    chunks = [_chunk("Castle early.", "Italian Game", "common_mistakes", "italian_game.md")]

    response = await answer_chat_question(
        llm,
        "Why do I keep losing?",
        chunks,
        player_context="Games analyzed: 5\nMost common recurring mistakes:\n- premature_pawn_push: 3 occurrences",
    )

    assert "Player profile" in llm.last_user_prompt
    assert "premature_pawn_push" in llm.last_user_prompt
    assert response.answer_markdown == "fake answer [1]"
    assert response.citations[0].opening == "Italian Game"


@pytest.mark.asyncio
async def test_chat_omits_player_profile_block_when_not_given():
    llm = _FakeLLMClient()
    chunks = [_chunk("Castle early.", "Italian Game", "common_mistakes", "italian_game.md")]

    await answer_chat_question(llm, "Explain the Italian Game.", chunks)

    assert "Player profile" not in llm.last_user_prompt


@pytest.mark.asyncio
async def test_chat_system_prompt_instructs_not_to_cite_player_profile():
    llm = _FakeLLMClient()
    await answer_chat_question(llm, "q", [], player_context="Games analyzed: 1")

    assert "ground truth" in llm.last_system_prompt
    assert "no [n] citation" in llm.last_system_prompt or "needs no [n] citation" in llm.last_system_prompt
