from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db
from backend.app.schemas.game import GameDetailOut, GameListResponse
from backend.app.services.game_service import get_game_detail, list_games

router = APIRouter(tags=["games"])


@router.get("/games", response_model=GameListResponse)
async def games(
    search: str | None = Query(None, description="Search by opening name or event"),
    opening: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> GameListResponse:
    return await list_games(session, search=search, opening=opening, limit=limit, offset=offset)


@router.get("/games/{game_id}", response_model=GameDetailOut)
async def game_detail(game_id: int, session: AsyncSession = Depends(get_db)) -> GameDetailOut:
    result = await get_game_detail(session, game_id)
    if result is None:
        raise HTTPException(404, f"Game {game_id} not found")
    return result
