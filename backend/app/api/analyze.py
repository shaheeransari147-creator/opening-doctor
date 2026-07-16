from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db
from backend.app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from backend.app.services.analysis_service import reanalyze_all_games, reanalyze_game

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, session: AsyncSession = Depends(get_db)) -> AnalyzeResponse:
    """Re-runs opening/theory-exit/mistake detection for a single game
    (if `game_id` is given) or every stored game (if omitted). Useful after
    the opening book or mistake-detection rules are updated.
    """
    if request.game_id is not None:
        count = await reanalyze_game(session, request.game_id)
        if count is None:
            raise HTTPException(404, f"Game {request.game_id} not found")
        await session.commit()
        return AnalyzeResponse(games_analyzed=1, game_ids=[request.game_id], mistakes_found=count)

    summary = await reanalyze_all_games(session)
    await session.commit()
    return AnalyzeResponse(
        games_analyzed=summary.games_added, game_ids=summary.game_ids, mistakes_found=summary.mistakes_found
    )
