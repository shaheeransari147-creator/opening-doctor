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
- Only use chess facts, moves, and explanations that are supported by the numbered reference \
context or by basic, uncontroversial chess principles (how pieces move, check/checkmate, \
castling rules, etc).
- If the reference context does not contain enough information to answer a chess-theory \
question confidently, say so explicitly instead of guessing or inventing specifics (e.g. \
specific games, players, or move sequences not in the context).
- Cite the reference numbers you used inline, like [1] or [2], right after the claim they support.
- You may also be given a "Player profile" section below with this specific player's own games \
and recurring mistakes, pulled directly from their account -- this is ground truth, not \
retrieved knowledge, so it needs no [n] citation. Use it to personalize your answer whenever \
relevant: connect general chess principles to patterns you see in *their* actual play (e.g. \
"you've done this in N of your own games" or "this is exactly the ...c5 break your French games \
have been missing"). Never invent player-profile facts beyond what's given.
- Write in a clear, encouraging coaching tone, not a dry engine printout.
"""

USER_PROMPT_TEMPLATE = """{player_profile_block}Reference context:
{context_block}

Question: {question}

Answer the question now, citing reference numbers inline for chess-theory claims, and drawing \
on the player profile (if given) to personalize the answer."""


@dataclass(slots=True)
class ChatResponse:
    answer_markdown: str
    citations: list[Citation]


async def answer_chat_question(
    llm_client: LLMClient,
    question: str,
    retrieved_chunks: list[RerankedChunk],
    player_context: str | None = None,
) -> ChatResponse:
    player_profile_block = f"Player profile (this player's own games/mistakes):\n{player_context}\n\n" if player_context else ""

    user_prompt = USER_PROMPT_TEMPLATE.format(
        player_profile_block=player_profile_block,
        context_block=format_context_block(retrieved_chunks),
        question=question,
    )

    markdown = await llm_client.complete(SYSTEM_PROMPT, user_prompt)

    return ChatResponse(
        answer_markdown=markdown,
        citations=citations_from_chunks(retrieved_chunks),
    )
