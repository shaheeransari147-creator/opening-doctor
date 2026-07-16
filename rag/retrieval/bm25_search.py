"""Sparse lexical search over the knowledge base using BM25 (rank_bm25).

Qdrant holds the authoritative chunk payloads; this module pulls all points
for the collection once (cheap -- the KB is a few hundred chunks at most),
builds an in-memory BM25 index, and re-uses it for the lifetime of the
process. This keeps the sparse side of hybrid retrieval simple and fast
without needing a separate search engine (Elasticsearch/OpenSearch) as a
project dependency.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass(slots=True)
class BM25Document:
    point_id: str
    text: str
    payload: dict


class BM25Index:
    def __init__(self, documents: list[BM25Document]) -> None:
        self.documents = documents
        self._bm25 = BM25Okapi([_tokenize(doc.text) for doc in documents]) if documents else None

    def search(self, query: str, top_k: int) -> list[tuple[BM25Document, float]]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self.documents, scores), key=lambda pair: pair[1], reverse=True)
        return [(doc, score) for doc, score in ranked[:top_k] if score > 0]


def build_bm25_index(client: QdrantClient, collection_name: str) -> BM25Index:
    if not client.collection_exists(collection_name):
        return BM25Index([])

    documents: list[BM25Document] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection_name, limit=256, offset=offset, with_payload=True, with_vectors=False
        )
        for point in points:
            payload = point.payload or {}
            documents.append(BM25Document(point_id=str(point.id), text=payload.get("text", ""), payload=payload))
        if offset is None:
            break

    return BM25Index(documents)


@lru_cache
def get_cached_bm25_index(collection_name: str, qdrant_mode: str, qdrant_url: str, qdrant_local_path: str) -> BM25Index:
    from vector.qdrant_client import get_qdrant_client

    client = get_qdrant_client(qdrant_mode, qdrant_url, qdrant_local_path)
    return build_bm25_index(client, collection_name)
