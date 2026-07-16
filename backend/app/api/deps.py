from __future__ import annotations

from collections.abc import AsyncIterator

from backend.app.core.rag_context import RagContext, get_rag_context
from database.session import get_db as get_db  # re-exported for convenience

__all__ = ["get_db", "get_rag_ctx"]


async def get_rag_ctx() -> AsyncIterator[RagContext]:
    yield get_rag_context()
