"""Dense embedding and reranking models, served locally via fastembed (ONNX
runtime) so the whole RAG pipeline runs free and fast on CPU, with no GPU
and no external embedding API required.
"""
from __future__ import annotations

from functools import lru_cache

from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder


@lru_cache
def get_embedding_model(model_name: str) -> TextEmbedding:
    """Loads (and caches) the dense embedding model. First call downloads
    the ONNX weights (~130MB for bge-small-en-v1.5) to a local cache dir.
    """
    return TextEmbedding(model_name=model_name)


@lru_cache
def get_reranker_model(model_name: str) -> TextCrossEncoder:
    return TextCrossEncoder(model_name=model_name)


def embed_texts(texts: list[str], model_name: str) -> list[list[float]]:
    model = get_embedding_model(model_name)
    return [vec.tolist() for vec in model.embed(texts)]


def embed_query(text: str, model_name: str) -> list[float]:
    return embed_texts([text], model_name)[0]


def rerank(query: str, documents: list[str], model_name: str) -> list[float]:
    """Returns a relevance score per document, in the same order as `documents`."""
    model = get_reranker_model(model_name)
    return list(model.rerank(query, documents))
