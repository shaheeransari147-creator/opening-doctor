from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db, get_rag_ctx
from backend.app.core.rag_context import RagContext
from backend.app.schemas.chat import ChatRequest, ChatResponseOut
from backend.app.services.chat_service import answer_question

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponseOut)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    rag_context: RagContext = Depends(get_rag_ctx),
) -> ChatResponseOut:
    """RAG-only chess Q&A ("Why is h6 bad?", "Explain the Italian Game").
    Answers are grounded strictly in the retrieved knowledge base and always
    cite their sources; the model is instructed not to hallucinate beyond
    the provided context and basic chess rules. Also personalized with a
    summary of the player's own analyzed games and recurring mistakes, when
    any exist, so answers can connect general theory to their actual play.
    """
    return await answer_question(session, rag_context, request.question)
