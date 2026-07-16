from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.game_repository import GameRepository
from backend.app.schemas.game import GameDetailOut, GameListResponse, GameSummaryOut, MoveOut, TheoryExitOut
from database.models import Game


def _to_summary(game: Game) -> GameSummaryOut:
    return GameSummaryOut(
        id=game.id,
        white=game.white_player.name,
        black=game.black_player.name,
        result=game.result.value,
        event=game.event,
        game_date=game.game_date,
        opening_name=game.opening_name,
        eco_code=game.eco_code,
        opening_variation=game.opening_variation,
        theory_exit_move=game.theory_exit.exit_move_number if game.theory_exit else None,
    )


async def list_games(
    session: AsyncSession, *, search: str | None, opening: str | None, limit: int, offset: int
) -> GameListResponse:
    repo = GameRepository(session)
    page = await repo.list_games(search=search, opening=opening, limit=limit, offset=offset)
    return GameListResponse(
        games=[_to_summary(g) for g in page.games],
        total=page.total,
        limit=limit,
        offset=offset,
    )


async def get_game_detail(session: AsyncSession, game_id: int) -> GameDetailOut | None:
    repo = GameRepository(session)
    game = await repo.get(game_id)
    if game is None:
        return None

    summary = _to_summary(game)
    return GameDetailOut(
        **summary.model_dump(),
        moves=[MoveOut.model_validate(m) for m in game.moves],
        theory_exit=(
            TheoryExitOut(
                exit_move_number=game.theory_exit.exit_move_number,
                color_to_move=game.theory_exit.color_to_move.value,
                expected_move_san=game.theory_exit.expected_move_san,
                played_move_san=game.theory_exit.played_move_san,
                opening_name=game.theory_exit.opening_name,
                eco_code=game.theory_exit.eco_code,
            )
            if game.theory_exit
            else None
        ),
        mistake_count=len(game.mistakes),
    )
