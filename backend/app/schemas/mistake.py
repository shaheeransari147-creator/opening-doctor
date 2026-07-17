from __future__ import annotations

from pydantic import BaseModel


class CitationOut(BaseModel):
    opening: str
    theme: str
    source: str


class MistakeExplanationOut(BaseModel):
    explanation_markdown: str
    citations: list[CitationOut]


class MistakeGameRefOut(BaseModel):
    game_id: int
    opponent: str
    game_date: str | None
    move_number: int
    color: str
    result: str


class MistakeGroupOut(BaseModel):
    mistake_type: str
    san: str
    occurrences: int
    avg_eval_loss: float
    example_description: str
    games: list[MistakeGameRefOut]
    headline: str
    explanation: MistakeExplanationOut | None = None


class MistakeListResponse(BaseModel):
    groups: list[MistakeGroupOut]
    limit: int
    offset: int
