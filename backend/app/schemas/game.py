from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class UploadRequest(BaseModel):
    pgn_text: str = Field(..., min_length=1, description="Raw PGN text, one or more games")
    player_name: str | None = Field(
        None, description="If given, matched against White/Black to set the tracked color for mistake analysis"
    )


class MoveOut(BaseModel):
    ply: int
    move_number: int
    color: str
    san: str
    fen_after: str
    is_book_move: bool

    model_config = {"from_attributes": True}


class TheoryExitOut(BaseModel):
    exit_move_number: int
    color_to_move: str
    expected_move_san: str | None
    played_move_san: str | None
    opening_name: str | None
    eco_code: str | None

    model_config = {"from_attributes": True}


class GameSummaryOut(BaseModel):
    id: int
    white: str
    black: str
    result: str
    event: str | None
    game_date: dt.date | None
    opening_name: str | None
    eco_code: str | None
    opening_variation: str | None
    theory_exit_move: int | None = None

    model_config = {"from_attributes": True}


class GameDetailOut(GameSummaryOut):
    moves: list[MoveOut]
    theory_exit: TheoryExitOut | None
    mistake_count: int


class GameListResponse(BaseModel):
    games: list[GameSummaryOut]
    total: int
    limit: int
    offset: int


class UploadResponse(BaseModel):
    games_added: int
    game_ids: list[int]
    mistakes_found: int
    parse_warnings: list[str] = []
