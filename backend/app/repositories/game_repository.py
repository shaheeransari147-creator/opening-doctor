from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Game, Move, TheoryExit


@dataclass(slots=True)
class GameListPage:
    games: list[Game]
    total: int


class GameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, game: Game) -> Game:
        self.session.add(game)
        await self.session.flush()
        return game

    async def add_moves(self, moves: list[Move]) -> None:
        self.session.add_all(moves)
        await self.session.flush()

    async def set_theory_exit(self, theory_exit: TheoryExit) -> None:
        self.session.add(theory_exit)
        await self.session.flush()

    async def get(self, game_id: int) -> Game | None:
        stmt = (
            select(Game)
            .where(Game.id == game_id)
            .options(
                selectinload(Game.white_player),
                selectinload(Game.black_player),
                selectinload(Game.moves),
                selectinload(Game.mistakes),
                selectinload(Game.theory_exit),
            )
        )
        return await self.session.scalar(stmt)

    async def list_games(
        self,
        *,
        search: str | None = None,
        opening: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> GameListPage:
        stmt = select(Game).options(
            selectinload(Game.white_player),
            selectinload(Game.black_player),
            selectinload(Game.theory_exit),
        )
        count_stmt = select(func.count()).select_from(Game)

        if opening:
            stmt = stmt.where(Game.opening_name == opening)
            count_stmt = count_stmt.where(Game.opening_name == opening)

        if search:
            pattern = f"%{search}%"
            search_filter = Game.opening_name.ilike(pattern) | Game.event.ilike(pattern)
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = await self.session.scalar(count_stmt) or 0

        stmt = stmt.order_by(Game.created_at.desc()).limit(limit).offset(offset)
        games = list((await self.session.scalars(stmt)).all())

        return GameListPage(games=games, total=total)

    async def count_all(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(Game)) or 0
