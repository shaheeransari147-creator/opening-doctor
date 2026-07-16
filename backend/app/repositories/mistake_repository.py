from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Game, Mistake


@dataclass(slots=True)
class MistakeGroup:
    mistake_type: str
    san: str
    occurrences: int
    avg_eval_loss: float
    example_description: str
    example_move_number: int
    example_color: str
    game_ids: list[int]


class MistakeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(self, mistakes: list[Mistake]) -> None:
        self.session.add_all(mistakes)
        await self.session.flush()

    async def grouped(self, *, limit: int = 20, offset: int = 0, mistake_type: str | None = None) -> list[MistakeGroup]:
        stmt = (
            select(
                Mistake.mistake_type,
                Mistake.san,
                func.count(Mistake.id).label("occurrences"),
                func.avg(Mistake.eval_loss).label("avg_eval_loss"),
                func.array_agg(Mistake.game_id.distinct()).label("game_ids"),
            )
            .group_by(Mistake.mistake_type, Mistake.san)
            .order_by(func.count(Mistake.id).desc())
            .limit(limit)
            .offset(offset)
        )
        if mistake_type:
            stmt = stmt.where(Mistake.mistake_type == mistake_type)

        rows = (await self.session.execute(stmt)).all()

        groups: list[MistakeGroup] = []
        for row in rows:
            example = (
                await self.session.execute(
                    select(Mistake.description, Mistake.move_number, Mistake.color)
                    .where(Mistake.mistake_type == row.mistake_type, Mistake.san == row.san)
                    .limit(1)
                )
            ).first()
            groups.append(
                MistakeGroup(
                    mistake_type=row.mistake_type.value if hasattr(row.mistake_type, "value") else row.mistake_type,
                    san=row.san,
                    occurrences=row.occurrences,
                    avg_eval_loss=round(float(row.avg_eval_loss), 2),
                    example_description=example.description if example else "",
                    example_move_number=example.move_number if example else 0,
                    example_color=(example.color.value if hasattr(example.color, "value") else example.color) if example else "",
                    game_ids=list(row.game_ids),
                )
            )
        return groups

    async def most_common_types(self, limit: int = 5) -> list[tuple[str, int, float]]:
        stmt = (
            select(
                Mistake.mistake_type,
                func.count(Mistake.id).label("occurrences"),
                func.avg(Mistake.eval_loss).label("avg_eval_loss"),
            )
            .group_by(Mistake.mistake_type)
            .order_by(func.count(Mistake.id).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            (row.mistake_type.value if hasattr(row.mistake_type, "value") else row.mistake_type, row.occurrences, round(float(row.avg_eval_loss), 2))
            for row in rows
        ]

    async def weakest_openings(self, limit: int = 5) -> list[tuple[str, int, int, float]]:
        """Returns (opening_name, games_played, mistake_count, avg_eval_loss) ranked worst-first."""
        stmt = (
            select(
                Game.opening_name,
                func.count(func.distinct(Game.id)).label("games_played"),
                func.count(Mistake.id).label("mistake_count"),
                func.avg(Mistake.eval_loss).label("avg_eval_loss"),
            )
            .join(Mistake, Mistake.game_id == Game.id)
            .where(Game.opening_name.is_not(None))
            .group_by(Game.opening_name)
            .order_by(func.avg(Mistake.eval_loss).asc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row.opening_name, row.games_played, row.mistake_count, round(float(row.avg_eval_loss), 2)) for row in rows]
