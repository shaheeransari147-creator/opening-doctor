from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Game, GameResult, Mistake, TheoryExit


@dataclass(slots=True)
class OpeningStats:
    opening_name: str
    eco: str | None
    games_played: int
    wins: int
    draws: int
    losses: int
    avg_theory_exit_move: float | None
    mistake_count: int


class OpeningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_opening_stats(
        self, *, search: str | None = None, limit: int = 20, offset: int = 0
    ) -> tuple[list[OpeningStats], int]:
        base = select(Game.opening_name, Game.eco_code).where(Game.opening_name.is_not(None))
        if search:
            base = base.where(Game.opening_name.ilike(f"%{search}%"))

        subq = base.subquery()
        distinct_openings_stmt = select(func.count(func.distinct(subq.c.opening_name)))
        total = await self.session.scalar(distinct_openings_stmt) or 0

        stmt = (
            select(
                Game.opening_name,
                func.max(Game.eco_code).label("eco_code"),
                func.count(func.distinct(Game.id)).label("games_played"),
                func.count(func.distinct(Game.id)).filter(Game.result == GameResult.WHITE_WIN).label("wins"),
                func.count(func.distinct(Game.id)).filter(Game.result == GameResult.DRAW).label("draws"),
                func.count(func.distinct(Game.id)).filter(Game.result == GameResult.BLACK_WIN).label("losses"),
            )
            .where(Game.opening_name.is_not(None))
            .group_by(Game.opening_name)
        )
        if search:
            stmt = stmt.where(Game.opening_name.ilike(f"%{search}%"))
        stmt = stmt.order_by(func.count(func.distinct(Game.id)).desc()).limit(limit).offset(offset)

        rows = (await self.session.execute(stmt)).all()
        opening_names = [row.opening_name for row in rows]

        # Two aggregate queries covering every opening on this page at once,
        # instead of N+1 per-opening round trips.
        exit_stmt = (
            select(Game.opening_name, func.avg(TheoryExit.exit_move_number).label("avg_exit"))
            .join(TheoryExit, TheoryExit.game_id == Game.id)
            .where(Game.opening_name.in_(opening_names))
            .group_by(Game.opening_name)
        )
        avg_exit_by_opening = {
            row.opening_name: round(float(row.avg_exit), 1)
            for row in (await self.session.execute(exit_stmt)).all()
        }

        mistake_stmt = (
            select(Game.opening_name, func.count(Mistake.id).label("mistake_count"))
            .join(Mistake, Mistake.game_id == Game.id)
            .where(Game.opening_name.in_(opening_names))
            .group_by(Game.opening_name)
        )
        mistake_count_by_opening = {
            row.opening_name: row.mistake_count for row in (await self.session.execute(mistake_stmt)).all()
        }

        results = [
            OpeningStats(
                opening_name=row.opening_name,
                eco=row.eco_code,
                games_played=row.games_played,
                wins=row.wins,
                draws=row.draws,
                losses=row.losses,
                avg_theory_exit_move=avg_exit_by_opening.get(row.opening_name),
                mistake_count=mistake_count_by_opening.get(row.opening_name, 0),
            )
            for row in rows
        ]

        return results, total

    async def most_played(self, limit: int = 5) -> list[tuple[str, int]]:
        stmt = (
            select(Game.opening_name, func.count(Game.id).label("count"))
            .where(Game.opening_name.is_not(None))
            .group_by(Game.opening_name)
            .order_by(func.count(Game.id).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row.opening_name, row.count) for row in rows]

    async def avg_theory_exit_move(self) -> float | None:
        value = await self.session.scalar(select(func.avg(TheoryExit.exit_move_number)))
        return round(float(value), 1) if value is not None else None
