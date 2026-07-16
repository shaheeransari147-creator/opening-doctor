"""Thin wrapper around the Qdrant client that supports two modes:

- "local":  an embedded, file-backed Qdrant instance (no server process
            needed) -- ideal for development or any environment without
            Docker.
- "server": a real Qdrant server reachable over HTTP, e.g. the `qdrant`
            service in docker-compose.yml for production deployments.

Both modes expose the exact same QdrantClient API, so the rest of the RAG
pipeline (vector/indexer.py, rag/retrieval/*) doesn't need to care which
mode is active.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


@lru_cache
def get_qdrant_client(mode: str, url: str, local_path: str) -> QdrantClient:
    if mode == "server":
        return QdrantClient(url=url)

    Path(local_path).mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=local_path)


def ensure_collection(client: QdrantClient, collection_name: str, vector_size: int) -> None:
    if client.collection_exists(collection_name):
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
