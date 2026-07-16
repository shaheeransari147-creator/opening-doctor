"""Theory-exit detection: determines when a player left known opening theory.

Answers: "at which move did the player stop following the reference opening
book, what did the book recommend, and what did they play instead?"
"""
from __future__ import annotations

from dataclasses import dataclass

from ingestion.opening_book import OpeningBook
from ingestion.opening_detector import OpeningDetectionResult, detect_opening
from ingestion.pgn_parser import ParsedMove


@dataclass(slots=True)
class TheoryExitDetection:
    exit_ply: int
    exit_move_number: int
    color_to_move: str
    expected_move_san: str | None
    played_move_san: str
    opening: OpeningDetectionResult


def detect_theory_exit(moves: list[ParsedMove], book: OpeningBook) -> TheoryExitDetection | None:
    """Returns the theory-exit point for a game, or None if the game never left the book."""
    san_moves = [m.san for m in moves]
    exit_result = book.find_theory_exit(san_moves)
    if exit_result is None:
        return None

    opening = detect_opening(san_moves, book)
    exiting_move = moves[exit_result.exit_ply - 1]

    return TheoryExitDetection(
        exit_ply=exit_result.exit_ply,
        exit_move_number=exiting_move.move_number,
        color_to_move=exiting_move.color,
        expected_move_san=exit_result.expected_move_san,
        played_move_san=exit_result.played_move_san,
        opening=opening,
    )
