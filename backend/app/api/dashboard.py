from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db
from backend.app.schemas.dashboard import DashboardResponse
from backend.app.services.dashboard_service import get_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(session: AsyncSession = Depends(get_db)) -> DashboardResponse:
    """Aggregate stats: opening score, most/least played openings, average
    move leaving theory, most common mistakes, games analyzed.
    """
    return await get_dashboard(session)
