from __future__ import annotations

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.rag_context import RagContext
from backend.app.repositories.game_repository import GameRepository
from backend.app.repositories.mistake_repository import MistakeRepository
from backend.app.schemas.chat import ChatResponseOut
from backend.app.schemas.mistake import CitationOut
from rag.generation.chat import answer_chat_question
from rag.retrieval.hybrid import hybrid_retrieve

_RECENT_GAMES_FOR_CONTEXT = 5


async def build_player_context(session: AsyncSession) -> str | None:
    """Summarizes this player's own games and recurring mistakes into a short
    text block the chat LLM can use to personalize its answers. Returns None
    if no games have been analyzed yet, so the prompt stays generic.
    """
    game_repo = GameRepository(session)
    mistake_repo = MistakeRepository(session)

    games_analyzed = await game_repo.count_all()
    if games_analyzed == 0:
        return None

    common_mistakes = await mistake_repo.most_common_types(limit=5)
    weakest_openings = await mistake_repo.weakest_openings(limit=5)
    recent = await game_repo.list_games(limit=_RECENT_GAMES_FOR_CONTEXT, offset=0)

    lines = [f"Games analyzed: {games_analyzed}"]

    if common_mistakes:
        lines.append("\nMost common recurring mistakes:")
        for mistake_type, occurrences, avg_eval_loss in common_mistakes:
            lines.append(f"- {mistake_type.replace('_', ' ')}: {occurrences} occurrences, avg {avg_eval_loss:+.2f} eval loss")

    if weakest_openings:
        lines.append("\nWeakest openings (by average evaluation loss):")
        for opening_name, games_played, mistake_count, avg_eval_loss in weakest_openings:
            lines.append(f"- {opening_name}: {games_played} games, {mistake_count} mistakes, avg {avg_eval_loss:+.2f} eval loss")

    if recent.games:
        lines.append("\nMost recent games:")
        for game in recent.games:
            opening = game.opening_name or "unidentified opening"
            exit_note = f", left theory at move {game.theory_exit.exit_move_number}" if game.theory_exit else ""
            lines.append(
                f"- {game.white_player.name} vs {game.black_player.name} "
                f"({opening}), result {game.result.value}{exit_note}"
            )

    return "\n".join(lines)


async def answer_question(session: AsyncSession, rag_context: RagContext, question: str) -> ChatResponseOut:
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

    player_context = await build_player_context(session)
    response = await answer_chat_question(rag_context.llm_client, question, retrieved, player_context)

    return ChatResponseOut(
        answer_markdown=response.answer_markdown,
        citations=[CitationOut(opening=c.opening, theme=c.theme, source=c.source) for c in response.citations],
    )
