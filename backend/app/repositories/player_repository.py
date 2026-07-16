from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Player


class PlayerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, name: str) -> Player:
        existing = await self.session.scalar(select(Player).where(Player.name == name, Player.fide_id.is_(None)))
        if existing is not None:
            return existing

        player = Player(name=name)
        self.session.add(player)
        await self.session.flush()
        return player
