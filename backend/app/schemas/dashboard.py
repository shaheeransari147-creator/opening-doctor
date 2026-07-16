from __future__ import annotations

from pydantic import BaseModel


class OpeningCountOut(BaseModel):
    opening_name: str
    count: int


class WeakOpeningOut(BaseModel):
    opening_name: str
    games_played: int
    mistake_count: int
    avg_eval_loss: float


class CommonMistakeOut(BaseModel):
    mistake_type: str
    occurrences: int
    avg_eval_loss: float


class DashboardResponse(BaseModel):
    games_analyzed: int
    opening_score: float
    most_played_openings: list[OpeningCountOut]
    weakest_openings: list[WeakOpeningOut]
    avg_move_leaving_theory: float | None
    most_common_mistakes: list[CommonMistakeOut]
