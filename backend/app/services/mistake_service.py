"""Aggregates recurring mistakes across games ("you played h6 too early in
12 games") and, optionally, generates an AI coaching explanation for the
top groups using the hybrid RAG pipeline.
"""
from __future__ import annotations

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.rag_context import RagContext
from backend.app.repositories.mistake_repository import MistakeGroup, MistakeRepository
from backend.app.schemas.mistake import CitationOut, MistakeExplanationOut, MistakeGroupOut
from rag.generation.explainer import MistakeExplanationRequest, explain_mistake
from rag.retrieval.hybrid import hybrid_retrieve


def _headline(group: MistakeGroup) -> str:
    verb = {
        "early_queen_development": "developed the queen early with",
        "delayed_castling": "delayed castling, as seen with",
        "premature_pawn_push": "played a premature pawn push,",
        "ignored_center_control": "ignored the center,",
        "lost_tempo": "lost a tempo with",
        "repeated_piece_moves": "shuffled the same piece back to",
        "theory_deviation": "left known theory with",
    }.get(group.mistake_type, "made a recurring mistake:")
    return f"You {verb} {group.san} in {group.occurrences} game{'s' if group.occurrences != 1 else ''}."


async def get_grouped_mistakes(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    mistake_type: str | None,
    explain: bool,
    rag_context: RagContext | None = None,
) -> list[MistakeGroupOut]:
    repo = MistakeRepository(session)
    groups = await repo.grouped(limit=limit, offset=offset, mistake_type=mistake_type)

    outputs: list[MistakeGroupOut] = []
    for group in groups:
        explanation_out: MistakeExplanationOut | None = None

        if explain and rag_context is not None:
            query = f"{group.mistake_type.replace('_', ' ')}: {group.example_description}"
            retrieved = await run_in_threadpool(
                hybrid_retrieve,
                rag_context.qdrant_client,
                rag_context.bm25_index,
                rag_context.settings.qdrant_collection,
                query,
                embedding_model=rag_context.settings.embedding_model,
                reranker_model=rag_context.settings.reranker_model,
                top_k_bm25=rag_context.settings.retrieval_top_k_bm25,
                top_k_dense=rag_context.settings.retrieval_top_k_dense,
                top_k_final=rag_context.settings.retrieval_top_k_final,
            )
            explanation = await explain_mistake(
                rag_context.llm_client,
                MistakeExplanationRequest(
                    opening="(various games)",
                    san=group.san,
                    move_number=group.example_move_number,
                    color=group.example_color,
                    mistake_type=group.mistake_type,
                    description=group.example_description,
                    eval_loss=group.avg_eval_loss,
                ),
                retrieved,
            )
            explanation_out = MistakeExplanationOut(
                explanation_markdown=explanation.explanation_markdown,
                citations=[CitationOut(opening=c.opening, theme=c.theme, source=c.source) for c in explanation.citations],
            )

        outputs.append(
            MistakeGroupOut(
                mistake_type=group.mistake_type,
                san=group.san,
                occurrences=group.occurrences,
                avg_eval_loss=group.avg_eval_loss,
                example_description=group.example_description,
                game_ids=group.game_ids,
                headline=_headline(group),
                explanation=explanation_out,
            )
        )

    return outputs
