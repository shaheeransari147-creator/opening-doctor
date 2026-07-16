from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db
from backend.app.core.config import get_settings
from backend.app.schemas.game import UploadResponse
from backend.app.services.analysis_service import analyze_and_store_pgn
from ingestion.pgn_parser import PgnParseError

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_pgn(
    file: UploadFile | None = None,
    pgn_text: str | None = Form(None),
    player_name: str | None = Form(None),
    session: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """Accepts either an uploaded .pgn file or pasted PGN text (or both --
    contents are concatenated), parses every game, and immediately runs the
    full analysis pipeline (opening detection, theory-exit detection,
    mistake detection) on each one.
    """
    settings = get_settings()
    text_parts: list[str] = []

    if file is not None:
        raw = await file.read()
        if len(raw) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(413, f"File exceeds {settings.max_upload_size_mb}MB limit")
        text_parts.append(raw.decode("utf-8", errors="replace"))

    if pgn_text:
        text_parts.append(pgn_text)

    if not text_parts:
        raise HTTPException(400, "Provide either a PGN file upload or pasted PGN text")

    combined_text = "\n\n".join(text_parts)

    try:
        summary = await analyze_and_store_pgn(session, combined_text, player_name=player_name)
    except PgnParseError as exc:
        raise HTTPException(422, str(exc)) from exc

    await session.commit()

    return UploadResponse(
        games_added=summary.games_added,
        game_ids=summary.game_ids,
        mistakes_found=summary.mistakes_found,
    )
