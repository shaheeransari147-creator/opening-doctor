"""Shared helpers for turning retrieved chunks into LLM prompt context and
into citation records returned to the client -- used by both the mistake
explainer and the RAG chat endpoint so citations are always derived from
what was actually retrieved, never from the LLM's own claims.
"""
from __future__ import annotations

from dataclasses import dataclass

from rag.retrieval.reranker import RerankedChunk


@dataclass(slots=True)
class Citation:
    opening: str
    theme: str
    source: str


def format_context_block(chunks: list[RerankedChunk]) -> str:
    if not chunks:
        return "(No relevant reference material was found in the knowledge base.)"

    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        payload = chunk.payload
        header = f"[{i}] {payload.get('opening', 'Unknown opening')} -- {payload.get('theme', '')}"
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n".join(blocks)


def citations_from_chunks(chunks: list[RerankedChunk]) -> list[Citation]:
    seen: set[tuple[str, str]] = set()
    citations: list[Citation] = []
    for chunk in chunks:
        payload = chunk.payload
        key = (payload.get("opening", ""), payload.get("theme", ""))
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(
                opening=payload.get("opening", "Unknown"),
                theme=payload.get("theme", ""),
                source=payload.get("source", payload.get("doc_id", "unknown")),
            )
        )
    return citations
