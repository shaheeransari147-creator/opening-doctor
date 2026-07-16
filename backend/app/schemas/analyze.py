from __future__ import annotations

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    game_id: int | None = None


class AnalyzeResponse(BaseModel):
    games_analyzed: int
    game_ids: list[int]
    mistakes_found: int
