from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from database.models import Game, Mistake, Player


@dataclass(slots=True)
class MistakeGameRef:
    game_id: int
    opponent: str
    game_date: str | None
    move_number: int
    color: str
    result: str


@dataclass(slots=True)
class MistakeGroup:
    mistake_type: str
    san: str
    occurrences: int
    avg_eval_loss: float
    example_description: str
    example_move_number: int
    example_color: str
    games: list[MistakeGameRef]


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
            games = await self._games_for_group(row.mistake_type, row.san)
            example = (
                await self.session.execute(
                    select(Mistake.description)
                    .where(Mistake.mistake_type == row.mistake_type, Mistake.san == row.san)
                    .limit(1)
                )
            ).scalar_one_or_none()
            groups.append(
                MistakeGroup(
                    mistake_type=row.mistake_type.value if hasattr(row.mistake_type, "value") else row.mistake_type,
                    san=row.san,
                    occurrences=row.occurrences,
                    avg_eval_loss=round(float(row.avg_eval_loss), 2),
                    example_description=example or "",
                    example_move_number=games[0].move_number if games else 0,
                    example_color=games[0].color if games else "",
                    games=games,
                )
            )
        return groups

    async def _games_for_group(self, mistake_type, san: str) -> list[MistakeGameRef]:
        """Every game this specific (mistake_type, san) occurred in, with enough
        detail (opponent, date, move, color, result) to link back to /games/{id}
        and explain *where* the recurring mistake happened -- not just that it did.
        """
        White = aliased(Player)
        Black = aliased(Player)

        stmt = (
            select(
                Mistake.game_id,
                Mistake.move_number,
                Mistake.color,
                Game.result,
                Game.game_date,
                White.name.label("white_name"),
                Black.name.label("black_name"),
            )
            .join(Game, Game.id == Mistake.game_id)
            .join(White, White.id == Game.white_player_id)
            .join(Black, Black.id == Game.black_player_id)
            .where(Mistake.mistake_type == mistake_type, Mistake.san == san)
            .order_by(Game.game_date.desc().nullslast(), Mistake.game_id.desc())
        )
        rows = (await self.session.execute(stmt)).all()

        refs: list[MistakeGameRef] = []
        for row in rows:
            color = row.color.value if hasattr(row.color, "value") else row.color
            opponent = row.black_name if color == "white" else row.white_name
            refs.append(
                MistakeGameRef(
                    game_id=row.game_id,
                    opponent=opponent,
                    game_date=row.game_date.isoformat() if row.game_date else None,
                    move_number=row.move_number,
                    color=color,
                    result=row.result.value if hasattr(row.result, "value") else row.result,
                )
            )
        return refs

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
