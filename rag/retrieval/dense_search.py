"""Dense (semantic) vector search over the Qdrant knowledge-base collection."""
from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient

from vector.embeddings import embed_query


@dataclass(slots=True)
class DenseResult:
    point_id: str
    text: str
    payload: dict
    score: float


def dense_search(
    client: QdrantClient,
    collection_name: str,
    query: str,
    embedding_model: str,
    top_k: int,
) -> list[DenseResult]:
    if not client.collection_exists(collection_name):
        return []

    query_vector = embed_query(query, embedding_model)
    results = client.query_points(collection_name=collection_name, query=query_vector, limit=top_k)

    return [
        DenseResult(point_id=str(point.id), text=(point.payload or {}).get("text", ""), payload=point.payload or {}, score=point.score)
        for point in results.points
    ]
