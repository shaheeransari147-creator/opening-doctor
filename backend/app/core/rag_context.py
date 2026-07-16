"""Process-wide singletons for the RAG pipeline (Qdrant client, BM25 index,
LLM client), so each API request doesn't pay the cost of re-loading the
embedding model or re-scrolling the whole Qdrant collection.
"""
from __future__ import annotations

from functools import lru_cache

from qdrant_client import QdrantClient

from backend.app.core.config import Settings, get_settings
from rag.generation.llm_client import LLMClient
from rag.retrieval.bm25_search import BM25Index, build_bm25_index
from vector.qdrant_client import get_qdrant_client


@lru_cache
def get_shared_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return get_qdrant_client(settings.qdrant_mode, settings.qdrant_url, settings.qdrant_local_path)


def build_shared_bm25_index() -> BM25Index:
    settings = get_settings()
    return build_bm25_index(get_shared_qdrant_client(), settings.qdrant_collection)


class RagContext:
    """Lazily builds and caches the pieces needed for hybrid retrieval + generation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._bm25_index: BM25Index | None = None
        self._llm_client: LLMClient | None = None

    @property
    def qdrant_client(self) -> QdrantClient:
        return get_shared_qdrant_client()

    @property
    def bm25_index(self) -> BM25Index:
        if self._bm25_index is None:
            self._bm25_index = build_shared_bm25_index()
        return self._bm25_index

    def refresh_bm25_index(self) -> None:
        self._bm25_index = build_shared_bm25_index()

    @property
    def llm_client(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = LLMClient(self.settings)
        return self._llm_client


@lru_cache
def get_rag_context() -> RagContext:
    return RagContext(get_settings())
