from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.mistake_repository import MistakeRepository
from backend.app.schemas.study_plan import StudyPlanItemOut, StudyPlanResponse
from rag.generation.study_plan import OpeningWeakness, RecurringMistake, generate_study_plan


async def get_study_plan(session: AsyncSession) -> StudyPlanResponse:
    mistake_repo = MistakeRepository(session)

    weakest_openings_raw = await mistake_repo.weakest_openings(limit=3)
    weaknesses = [
        OpeningWeakness(opening=name, games_played=games, mistake_count=count, avg_eval_loss=loss)
        for name, games, count, loss in weakest_openings_raw
    ]

    grouped = await mistake_repo.grouped(limit=10)
    recurring = [
        RecurringMistake(mistake_type=g.mistake_type, san=g.san, occurrences=g.occurrences, avg_eval_loss=g.avg_eval_loss)
        for g in grouped
    ]

    items = generate_study_plan(weaknesses, recurring)
    plan_items = [
        StudyPlanItemOut(activity=i.activity, minutes=i.minutes, priority=i.priority, reason=i.reason) for i in items
    ]

    return StudyPlanResponse(items=plan_items, total_minutes=sum(i.minutes for i in plan_items))
