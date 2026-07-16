"""Opening detection: given a game's moves, determines the opening name,
ECO code, and main variation by matching against the reference OpeningBook.
"""
from __future__ import annotations

from dataclasses import dataclass

from ingestion.opening_book import OpeningBook


@dataclass(slots=True)
class OpeningDetectionResult:
    eco: str | None
    name: str | None
    family: str | None
    variation: str | None
    matched_ply: int


def detect_opening(played_san_moves: list[str], book: OpeningBook) -> OpeningDetectionResult:
    """Returns the deepest (most specific) known opening line reached by the game."""
    match = book.match(played_san_moves)

    if match.entry is None:
        return OpeningDetectionResult(eco=None, name=None, family=None, variation=None, matched_ply=0)

    return OpeningDetectionResult(
        eco=match.entry.eco,
        name=match.entry.name,
        family=match.entry.family,
        variation=match.entry.variation,
        matched_ply=match.matched_ply,
    )
