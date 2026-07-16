"""RAG-only chat: answers free-form chess questions strictly from the
retrieved knowledge-base context. Never answers from the model's own
un-grounded knowledge, and always returns the sources it used.
"""
from __future__ import annotations

from dataclasses import dataclass

from rag.generation.citations import Citation, citations_from_chunks, format_context_block
from rag.generation.llm_client import LLMClient
from rag.retrieval.reranker import RerankedChunk

SYSTEM_PROMPT = """You are Opening Doctor's chess assistant. You answer questions strictly \
using the numbered reference context provided below -- this is retrieval-augmented generation, \
not free chat.

Rules:
- Only use facts, moves, and explanations that are supported by the provided context or by \
basic, uncontroversial chess principles (how pieces move, check/checkmate, castling rules, etc).
- If the context does not contain enough information to answer confidently, say so explicitly \
instead of guessing or inventing specifics (e.g. specific games, players, or move sequences).
- Cite the reference numbers you used inline, like [1] or [2], right after the claim they support.
- Write in a clear, encouraging coaching tone, not a dry engine printout.
"""

USER_PROMPT_TEMPLATE = """Reference context:
{context_block}

Question: {question}

Answer the question now, citing reference numbers inline."""


@dataclass(slots=True)
class ChatResponse:
    answer_markdown: str
    citations: list[Citation]


async def answer_chat_question(
    llm_client: LLMClient,
    question: str,
    retrieved_chunks: list[RerankedChunk],
) -> ChatResponse:
    user_prompt = USER_PROMPT_TEMPLATE.format(
        context_block=format_context_block(retrieved_chunks),
        question=question,
    )

    markdown = await llm_client.complete(SYSTEM_PROMPT, user_prompt)

    return ChatResponse(
        answer_markdown=markdown,
        citations=citations_from_chunks(retrieved_chunks),
    )
