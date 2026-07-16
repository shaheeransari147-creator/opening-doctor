from __future__ import annotations

from pydantic import BaseModel


class StudyPlanItemOut(BaseModel):
    activity: str
    minutes: int
    priority: str
    reason: str


class StudyPlanResponse(BaseModel):
    items: list[StudyPlanItemOut]
    total_minutes: int
