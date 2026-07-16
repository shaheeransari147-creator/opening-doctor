"""Verifies the RAG-dependent endpoints fail gracefully (clean 503, not a
crash) when no LLM provider is configured -- the state every fresh install
starts in before the operator adds an API key or pulls an Ollama model.
conftest.py forces LLM_PROVIDER=groq with an empty key for exactly this.
"""
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_chat_returns_503_when_llm_not_configured(client):
    resp = await client.post("/api/chat", json={"question": "Why is h6 bad?"})
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"].lower()


async def test_chat_rejects_empty_question(client):
    resp = await client.post("/api/chat", json={"question": ""})
    assert resp.status_code == 422


async def test_mistakes_explain_returns_503_when_llm_not_configured(client):
    await client.post(
        "/api/upload",
        data={
            "pgn_text": (
                '[Event "Casual Game"]\n[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n'
                "1. Nf3 h6 2. g3 h5 3. Bg2 c5 4. O-O Qb6 5. d4 Nc6 6. c3 Nb4 7. Na3 Nc6 8. e3 e6 1-0\n"
            ),
            "player_name": "Bob",
        },
    )

    resp = await client.get("/api/mistakes", params={"explain": "true"})
    assert resp.status_code == 503


async def test_mistakes_without_explain_still_works(client):
    resp = await client.get("/api/mistakes")
    assert resp.status_code == 200
