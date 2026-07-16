"""Hybrid retrieval pipeline:

    query -> BM25 (sparse) ----\
                                 +--> merge (dedup by point id) --> rerank --> top K
    query -> dense (Qdrant) ---/

BM25 catches exact keyword/terminology matches (opening names, move
notation like "h6", ECO codes) that embeddings can under-weight; dense
search catches semantic/paraphrased matches BM25 would miss entirely.
Merging both candidate pools before the final cross-encoder rerank gives the
best of both without ever trusting either single-signal ranking directly.
"""
from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient

from rag.retrieval.bm25_search import BM25Index
from rag.retrieval.dense_search import dense_search
from rag.retrieval.reranker import RerankedChunk, rerank_candidates


@dataclass(slots=True)
class RetrievalFilters:
    opening: str | None = None
    color: str | None = None
    difficulty: str | None = None
    theme: str | None = None


def _passes_filters(payload: dict, filters: RetrievalFilters | None) -> bool:
    if filters is None:
        return True
    if filters.opening and payload.get("opening") != filters.opening:
        return False
    if filters.color and payload.get("color") not in (filters.color, None):
        return False
    if filters.difficulty and payload.get("difficulty") != filters.difficulty:
        return False
    if filters.theme and payload.get("theme") != filters.theme:
        return False
    return True


def hybrid_retrieve(
    client: QdrantClient,
    bm25_index: BM25Index,
    collection_name: str,
    query: str,
    *,
    embedding_model: str,
    reranker_model: str,
    top_k_bm25: int,
    top_k_dense: int,
    top_k_final: int,
    filters: RetrievalFilters | None = None,
) -> list[RerankedChunk]:
    bm25_hits = bm25_index.search(query, top_k_bm25)
    dense_hits = dense_search(client, collection_name, query, embedding_model, top_k_dense)

    merged: dict[str, tuple[str, dict]] = {}
    for doc, _score in bm25_hits:
        if _passes_filters(doc.payload, filters):
            merged[doc.point_id] = (doc.text, doc.payload)
    for hit in dense_hits:
        if _passes_filters(hit.payload, filters):
            merged.setdefault(hit.point_id, (hit.text, hit.payload))

    candidates = list(merged.values())
    return rerank_candidates(query, candidates, reranker_model, top_k_final)
