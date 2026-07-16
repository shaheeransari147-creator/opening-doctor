from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db
from backend.app.schemas.opening import OpeningListResponse
from backend.app.services.opening_service import list_openings

router = APIRouter(tags=["openings"])


@router.get("/openings", response_model=OpeningListResponse)
async def openings(
    search: str | None = Query(None, description="Search openings by name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> OpeningListResponse:
    """Per-opening stats aggregated from the player's own analyzed games
    (games played, win/draw/loss, average move leaving theory, mistakes).
    """
    return await list_openings(session, search=search, limit=limit, offset=offset)
