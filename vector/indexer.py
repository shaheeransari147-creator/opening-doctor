"""Embeds chunks and upserts them into a Qdrant collection as points with
full metadata payloads (opening, variation, eco, color, difficulty, theme,
source), so the retrieval layer can both similarity-search and filter on
these fields.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from rag.chunking.chunker import Chunk
from vector.embeddings import embed_texts
from vector.qdrant_client import ensure_collection


def _point_id(doc_id: str, chunk_index: int) -> str:
    digest = hashlib.sha256(f"{doc_id}:{chunk_index}".encode()).hexdigest()
    return digest[:32]


def upsert_chunks(
    client: QdrantClient,
    collection_name: str,
    chunks: list[Chunk],
    embedding_model_name: str,
    embedding_dim: int,
) -> int:
    if not chunks:
        return 0

    ensure_collection(client, collection_name, embedding_dim)

    vectors = embed_texts([c.text for c in chunks], embedding_model_name)

    points = [
        PointStruct(
            id=_point_id(chunk.metadata.doc_id, chunk.chunk_index),
            vector=vector,
            payload={"text": chunk.text, "token_count": chunk.token_count, **asdict(chunk.metadata)},
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]

    client.upsert(collection_name=collection_name, points=points)
    return len(points)
