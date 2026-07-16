"""Parses PGN text (one or many games) into structured, typed data using python-chess.

This module has no database or web-framework dependencies: it is a pure
transformation from PGN text -> in-memory dataclasses, so it can be unit
tested in isolation and reused by both the API upload endpoint and seed
scripts.
"""
from __future__ import annotations

import datetime as dt
import io
import logging
from dataclasses import dataclass, field

import chess
import chess.pgn

logger = logging.getLogger(__name__)


class PgnParseError(ValueError):
    """Raised when PGN text cannot be parsed into at least one valid game."""


@dataclass(slots=True)
class ParsedMove:
    ply: int  # 1-indexed half-move counter
    move_number: int  # full move number, as printed in PGN (1, 1, 2, 2, ...)
    color: str  # "white" | "black"
    san: str
    uci: str
    fen_before: str
    fen_after: str


@dataclass(slots=True)
class ParsedGame:
    white: str
    black: str
    event: str | None
    site: str | None
    round: str | None
    game_date: dt.date | None
    result: str
    moves: list[ParsedMove] = field(default_factory=list)
    raw_pgn: str = ""

    @property
    def ply_count(self) -> int:
        return len(self.moves)


def _parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        year, month, day = value.split(".")
        return dt.date(int(year), int(month.replace("?", "1") or 1), int(day.replace("?", "1") or 1))
    except (ValueError, AttributeError):
        return None


def _game_to_pgn_text(game: chess.pgn.Game) -> str:
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    return game.accept(exporter)


def _extract_moves(game: chess.pgn.Game) -> list[ParsedMove]:
    moves: list[ParsedMove] = []
    board = game.board()
    ply = 0
    for node in game.mainline():
        move = node.move
        fen_before = board.fen()
        san = board.san(move)
        uci = move.uci()
        color = "white" if board.turn == chess.WHITE else "black"
        board.push(move)
        fen_after = board.fen()
        ply += 1
        move_number = (ply + 1) // 2
        moves.append(
            ParsedMove(
                ply=ply,
                move_number=move_number,
                color=color,
                san=san,
                uci=uci,
                fen_before=fen_before,
                fen_after=fen_after,
            )
        )
    return moves


def parse_pgn_text(pgn_text: str) -> list[ParsedGame]:
    """Parses PGN text that may contain one or more games.

    Raises:
        PgnParseError: if the text contains no valid games at all.
    """
    if not pgn_text or not pgn_text.strip():
        raise PgnParseError("PGN text is empty.")

    stream = io.StringIO(pgn_text)
    parsed_games: list[ParsedGame] = []

    while True:
        try:
            game = chess.pgn.read_game(stream)
        except Exception as exc:  # python-chess raises bare Exception on malformed input
            logger.warning("Skipping malformed game during PGN parse: %s", exc)
            continue
        if game is None:
            break

        headers = game.headers
        try:
            moves = _extract_moves(game)
        except Exception as exc:
            logger.warning("Skipping game with illegal move sequence: %s", exc)
            continue

        if not moves:
            # Empty games (headers only, no moves) are not useful for analysis.
            continue

        parsed_games.append(
            ParsedGame(
                white=headers.get("White", "Unknown"),
                black=headers.get("Black", "Unknown"),
                event=headers.get("Event") or None,
                site=headers.get("Site") or None,
                round=headers.get("Round") or None,
                game_date=_parse_date(headers.get("Date")),
                result=headers.get("Result", "*"),
                moves=moves,
                raw_pgn=_game_to_pgn_text(game),
            )
        )

    if not parsed_games:
        raise PgnParseError("No valid games could be parsed from the provided PGN text.")

    return parsed_games
