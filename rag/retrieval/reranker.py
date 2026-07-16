"""Cross-encoder reranking: scores each (query, candidate) pair jointly,
which is far more accurate than either BM25 or dense cosine similarity alone
but too slow to run over an entire corpus -- hence it only runs on the small
merged candidate set produced by rag.retrieval.hybrid.
"""
from __future__ import annotations

from dataclasses import dataclass

from vector.embeddings import rerank as rerank_scores


@dataclass(slots=True)
class RerankedChunk:
    text: str
    payload: dict
    rerank_score: float


def rerank_candidates(
    query: str,
    candidates: list[tuple[str, dict]],
    reranker_model: str,
    top_k: int,
) -> list[RerankedChunk]:
    if not candidates:
        return []

    texts = [text for text, _payload in candidates]
    scores = rerank_scores(query, texts, reranker_model)

    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    return [
        RerankedChunk(text=text, payload=payload, rerank_score=float(score))
        for (text, payload), score in ranked[:top_k]
    ]
