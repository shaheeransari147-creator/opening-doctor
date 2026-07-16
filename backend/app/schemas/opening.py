from __future__ import annotations

from pydantic import BaseModel


class OpeningStatsOut(BaseModel):
    opening_name: str
    eco: str | None
    games_played: int
    wins: int
    draws: int
    losses: int
    avg_theory_exit_move: float | None
    mistake_count: int


class OpeningListResponse(BaseModel):
    openings: list[OpeningStatsOut]
    total: int
    limit: int
    offset: int
