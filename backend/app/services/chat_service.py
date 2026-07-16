from __future__ import annotations

from fastapi.concurrency import run_in_threadpool

from backend.app.core.rag_context import RagContext
from backend.app.schemas.chat import ChatResponseOut
from backend.app.schemas.mistake import CitationOut
from rag.generation.chat import answer_chat_question
from rag.retrieval.hybrid import hybrid_retrieve


async def answer_question(rag_context: RagContext, question: str) -> ChatResponseOut:
    settings = rag_context.settings
    retrieved = await run_in_threadpool(
        hybrid_retrieve,
        rag_context.qdrant_client,
        rag_context.bm25_index,
        settings.qdrant_collection,
        question,
        embedding_model=settings.embedding_model,
        reranker_model=settings.reranker_model,
        top_k_bm25=settings.retrieval_top_k_bm25,
        top_k_dense=settings.retrieval_top_k_dense,
        top_k_final=settings.retrieval_top_k_final,
    )

    response = await answer_chat_question(rag_context.llm_client, question, retrieved)

    return ChatResponseOut(
        answer_markdown=response.answer_markdown,
        citations=[CitationOut(opening=c.opening, theme=c.theme, source=c.source) for c in response.citations],
    )
