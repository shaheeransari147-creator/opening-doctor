"""Generates coach-style natural-language explanations for a single detected
mistake, grounded in retrieved knowledge-base context (never engine-only
output: every explanation must connect the move to a strategic idea).
"""
from __future__ import annotations

from dataclasses import dataclass

from rag.generation.citations import Citation, citations_from_chunks, format_context_block
from rag.generation.llm_client import LLMClient
from rag.retrieval.reranker import RerankedChunk

SYSTEM_PROMPT = """You are Opening Doctor, a warm, expert chess coach who teaches opening \
principles, not just engine evaluations. You are given one specific mistake a student made, \
plus reference material retrieved from a curated opening knowledge base.

Rules:
- Ground every claim in the provided reference context and general opening principles. \
Do not invent specific games, players, or theoretical novelties that are not in the context.
- Never just say "the engine prefers X" -- always explain the underlying idea in words a \
club player can learn from and reuse in future games.
- Structure your response with exactly these five markdown headings, in this order:
  ### Why This Is Inaccurate
  ### A Better Move
  ### Strategic Explanation
  ### Long-Term Plan
  ### Typical Ideas
- Keep each section to 2-4 sentences. Be concrete and specific to this position, not generic.
"""

USER_PROMPT_TEMPLATE = """Student's mistake:
- Opening: {opening}
- Move played: {san} (move {move_number}, {color} to move)
- Mistake type: {mistake_type}
- Automatic detector note: {description}
- Heuristic severity: {eval_loss} pawns

Reference context retrieved from the knowledge base:
{context_block}

Write the coaching explanation now, following the required heading structure."""


@dataclass(slots=True)
class MistakeExplanationRequest:
    opening: str
    san: str
    move_number: int
    color: str
    mistake_type: str
    description: str
    eval_loss: float


@dataclass(slots=True)
class MistakeExplanation:
    explanation_markdown: str
    citations: list[Citation]


async def explain_mistake(
    llm_client: LLMClient,
    request: MistakeExplanationRequest,
    retrieved_chunks: list[RerankedChunk],
) -> MistakeExplanation:
    user_prompt = USER_PROMPT_TEMPLATE.format(
        opening=request.opening,
        san=request.san,
        move_number=request.move_number,
        color=request.color,
        mistake_type=request.mistake_type,
        description=request.description,
        eval_loss=request.eval_loss,
        context_block=format_context_block(retrieved_chunks),
    )

    markdown = await llm_client.complete(SYSTEM_PROMPT, user_prompt)

    return MistakeExplanation(
        explanation_markdown=markdown,
        citations=citations_from_chunks(retrieved_chunks),
    )
