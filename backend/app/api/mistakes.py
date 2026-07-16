from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db, get_rag_ctx
from backend.app.core.rag_context import RagContext
from backend.app.schemas.mistake import MistakeListResponse
from backend.app.services.mistake_service import get_grouped_mistakes

router = APIRouter(tags=["mistakes"])


@router.get("/mistakes", response_model=MistakeListResponse)
async def list_mistakes(
    mistake_type: str | None = None,
    explain: bool = Query(False, description="Generate an AI coaching explanation for each group (slower, calls the LLM)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    rag_context: RagContext = Depends(get_rag_ctx),
) -> MistakeListResponse:
    """Recurring mistakes grouped by type + move, e.g. "You played h6 too
    early in 12 games. Average evaluation loss: -0.8". Pass `explain=true`
    to also generate a grounded AI coaching explanation per group (RAG-only,
    citing sources).
    """
    groups = await get_grouped_mistakes(
        session,
        limit=limit,
        offset=offset,
        mistake_type=mistake_type,
        explain=explain,
        rag_context=rag_context if explain else None,
    )
    return MistakeListResponse(groups=groups, limit=limit, offset=offset)
