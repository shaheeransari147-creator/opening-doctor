from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db
from backend.app.schemas.study_plan import StudyPlanResponse
from backend.app.services.study_plan_service import get_study_plan

router = APIRouter(tags=["study-plan"])


@router.get("/study-plan", response_model=StudyPlanResponse)
async def study_plan(session: AsyncSession = Depends(get_db)) -> StudyPlanResponse:
    """Today's prioritized study plan, built from the player's weakest
    openings and most common recurring mistakes.
    """
    return await get_study_plan(session)
