from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.opening_repository import OpeningRepository
from backend.app.schemas.opening import OpeningListResponse, OpeningStatsOut


async def list_openings(session: AsyncSession, *, search: str | None, limit: int, offset: int) -> OpeningListResponse:
    repo = OpeningRepository(session)
    stats, total = await repo.list_opening_stats(search=search, limit=limit, offset=offset)

    return OpeningListResponse(
        openings=[
            OpeningStatsOut(
                opening_name=s.opening_name,
                eco=s.eco,
                games_played=s.games_played,
                wins=s.wins,
                draws=s.draws,
                losses=s.losses,
                avg_theory_exit_move=s.avg_theory_exit_move,
                mistake_count=s.mistake_count,
            )
            for s in stats
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
