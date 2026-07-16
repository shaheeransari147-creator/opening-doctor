"""Orchestrates the full ingestion + analysis pipeline: parse PGN -> detect
opening -> detect theory exit -> detect mistakes -> persist everything.

This is the service the /upload and /analyze API routes call into; it is the
one place that wires together the standalone `ingestion.*` modules with the
database repositories.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.repositories.game_repository import GameRepository
from backend.app.repositories.mistake_repository import MistakeRepository
from backend.app.repositories.player_repository import PlayerRepository
from database.models import Color, Game, GameResult, GameSource, Mistake, Move, TheoryExit
from ingestion.mistake_detector import detect_mistakes
from ingestion.opening_book import OpeningBook, get_default_book
from ingestion.opening_detector import detect_opening
from ingestion.pgn_parser import ParsedGame, parse_pgn_text
from ingestion.theory_detector import detect_theory_exit

logger = get_logger(__name__)

_RESULT_MAP = {"1-0": GameResult.WHITE_WIN, "0-1": GameResult.BLACK_WIN, "1/2-1/2": GameResult.DRAW}


@dataclass(slots=True)
class AnalysisSummary:
    games_added: int
    game_ids: list[int]
    mistakes_found: int


def _resolve_tracked_color(parsed: ParsedGame, player_name: str | None) -> Color | None:
    if not player_name:
        return None
    needle = player_name.strip().lower()
    if needle and needle in parsed.white.lower():
        return Color.WHITE
    if needle and needle in parsed.black.lower():
        return Color.BLACK
    return None


async def _persist_analysis(
    session: AsyncSession,
    game: Game,
    parsed: ParsedGame,
    book: OpeningBook,
    tracked_color: Color | None,
) -> int:
    """Detects opening/theory-exit/mistakes for `parsed` and writes moves,
    theory exit, and mistakes for the (already-created, already-flushed)
    `game` row. Returns the number of mistakes found. Also updates the
    game's own opening fields in place.
    """
    game_repo = GameRepository(session)
    mistake_repo = MistakeRepository(session)

    san_moves = [m.san for m in parsed.moves]
    opening = detect_opening(san_moves, book)
    game.eco_code = opening.eco
    game.opening_name = opening.name
    game.opening_variation = opening.variation
    game.tracked_player_color = tracked_color

    moves = [
        Move(
            game_id=game.id,
            ply=m.ply,
            move_number=m.move_number,
            color=Color(m.color),
            san=m.san,
            uci=m.uci,
            fen_before=m.fen_before,
            fen_after=m.fen_after,
            is_book_move=(m.ply <= opening.matched_ply),
        )
        for m in parsed.moves
    ]
    await game_repo.add_moves(moves)

    exit_detection = detect_theory_exit(parsed.moves, book)
    if exit_detection is not None:
        await game_repo.set_theory_exit(
            TheoryExit(
                game_id=game.id,
                exit_ply=exit_detection.exit_ply,
                exit_move_number=exit_detection.exit_move_number,
                color_to_move=Color(exit_detection.color_to_move),
                eco_code=exit_detection.opening.eco,
                opening_name=exit_detection.opening.name,
                opening_variation=exit_detection.opening.variation,
                expected_move_san=exit_detection.expected_move_san,
                played_move_san=exit_detection.played_move_san,
            )
        )

    colors_to_analyze = [tracked_color.value] if tracked_color else ["white", "black"]
    move_by_ply = {m.ply: mv for m, mv in zip(parsed.moves, moves, strict=True)}
    mistakes: list[Mistake] = []
    for color in colors_to_analyze:
        for detected in detect_mistakes(parsed.moves, color):
            mistakes.append(
                Mistake(
                    game_id=game.id,
                    move_id=move_by_ply[detected.ply].id,
                    mistake_type=detected.mistake_type,
                    color=Color(detected.color),
                    move_number=detected.move_number,
                    ply=detected.ply,
                    san=detected.san,
                    description=detected.description,
                    eval_loss=detected.eval_loss,
                )
            )
    if mistakes:
        await mistake_repo.bulk_create(mistakes)

    return len(mistakes)


async def analyze_and_store_pgn(
    session: AsyncSession,
    pgn_text: str,
    *,
    player_name: str | None = None,
    source: GameSource = GameSource.UPLOAD,
    book: OpeningBook | None = None,
) -> AnalysisSummary:
    book = book or get_default_book()
    parsed_games = parse_pgn_text(pgn_text)

    player_repo = PlayerRepository(session)
    game_repo = GameRepository(session)

    game_ids: list[int] = []
    total_mistakes = 0

    for parsed in parsed_games:
        white = await player_repo.get_or_create(parsed.white)
        black = await player_repo.get_or_create(parsed.black)
        tracked_color = _resolve_tracked_color(parsed, player_name)

        game = Game(
            white_player_id=white.id,
            black_player_id=black.id,
            event=parsed.event,
            site=parsed.site,
            round=parsed.round,
            game_date=parsed.game_date,
            result=_RESULT_MAP.get(parsed.result, GameResult.UNKNOWN),
            pgn_raw=parsed.raw_pgn,
            source=source,
        )
        await game_repo.create(game)

        total_mistakes += await _persist_analysis(session, game, parsed, book, tracked_color)
        game_ids.append(game.id)

    logger.info("Analyzed %d games, found %d mistakes", len(game_ids), total_mistakes)
    return AnalysisSummary(games_added=len(game_ids), game_ids=game_ids, mistakes_found=total_mistakes)


async def reanalyze_game(session: AsyncSession, game_id: int, *, book: OpeningBook | None = None) -> int | None:
    """Re-runs the full analysis pipeline for an already-stored game (e.g.
    after an opening-book update or a mistake-detector fix), replacing its
    moves/theory-exit/mistakes in place. Returns the new mistake count, or
    None if the game does not exist.
    """
    book = book or get_default_book()
    game_repo = GameRepository(session)
    game = await game_repo.get(game_id)
    if game is None:
        return None

    parsed_games = parse_pgn_text(game.pgn_raw)
    parsed = parsed_games[0]

    await session.execute(delete(Mistake).where(Mistake.game_id == game_id))
    await session.execute(delete(TheoryExit).where(TheoryExit.game_id == game_id))
    await session.execute(delete(Move).where(Move.game_id == game_id))
    await session.flush()

    mistake_count = await _persist_analysis(session, game, parsed, book, game.tracked_player_color)
    logger.info("Re-analyzed game %d, found %d mistakes", game_id, mistake_count)
    return mistake_count


async def reanalyze_all_games(session: AsyncSession, *, book: OpeningBook | None = None) -> AnalysisSummary:
    book = book or get_default_book()
    game_repo = GameRepository(session)

    game_ids: list[int] = []
    total_mistakes = 0
    page = await game_repo.list_games(limit=1_000_000, offset=0)
    for game_summary in page.games:
        count = await reanalyze_game(session, game_summary.id, book=book)
        if count is not None:
            game_ids.append(game_summary.id)
            total_mistakes += count

    return AnalysisSummary(games_added=len(game_ids), game_ids=game_ids, mistakes_found=total_mistakes)
