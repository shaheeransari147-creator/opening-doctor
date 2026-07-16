from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.game_repository import GameRepository
from backend.app.repositories.mistake_repository import MistakeRepository
from backend.app.repositories.opening_repository import OpeningRepository
from backend.app.schemas.dashboard import CommonMistakeOut, DashboardResponse, OpeningCountOut, WeakOpeningOut


def _opening_score(games_analyzed: int, avg_eval_loss_total: float) -> float:
    """A simple 0-100 heuristic score: starts at 100, docked by how much
    average evaluation is being lost per game across all detected mistakes.
    This is a coaching heuristic, not an engine-calibrated rating -- see
    docs/ARCHITECTURE.md for the full rationale.
    """
    if games_analyzed == 0:
        return 100.0
    penalty = min(60.0, abs(avg_eval_loss_total) * 20)
    return round(100.0 - penalty, 1)


async def get_dashboard(session: AsyncSession) -> DashboardResponse:
    game_repo = GameRepository(session)
    mistake_repo = MistakeRepository(session)
    opening_repo = OpeningRepository(session)

    games_analyzed = await game_repo.count_all()
    most_played = await opening_repo.most_played(limit=5)
    weakest = await mistake_repo.weakest_openings(limit=5)
    avg_exit = await opening_repo.avg_theory_exit_move()
    common_mistakes = await mistake_repo.most_common_types(limit=5)

    avg_loss_overall = sum(loss for _, _, loss in common_mistakes) / len(common_mistakes) if common_mistakes else 0.0

    return DashboardResponse(
        games_analyzed=games_analyzed,
        opening_score=_opening_score(games_analyzed, avg_loss_overall),
        most_played_openings=[OpeningCountOut(opening_name=name, count=count) for name, count in most_played],
        weakest_openings=[
            WeakOpeningOut(opening_name=name, games_played=games, mistake_count=mistakes, avg_eval_loss=loss)
            for name, games, mistakes, loss in weakest
        ],
        avg_move_leaving_theory=avg_exit,
        most_common_mistakes=[
            CommonMistakeOut(mistake_type=mtype, occurrences=count, avg_eval_loss=loss)
            for mtype, count, loss in common_mistakes
        ],
    )
