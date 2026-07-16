"""Splits knowledge-base markdown documents into overlapping, metadata-tagged
chunks suitable for embedding and indexing into Qdrant.

Each source document (seed_data/openings/*.md) has YAML frontmatter with
document-level metadata (opening, eco, color, difficulty, source) and a body
organized into "## Heading" sections (Overview, Strategic Plans, Common
Mistakes, Opening Traps, Model Game, ...). We chunk *within* each section so
that every chunk keeps a single, accurate "theme" tag, then further split
long sections into overlapping token windows to respect the target chunk
size.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import tiktoken
import yaml

_ENCODING = tiktoken.get_encoding("cl100k_base")
_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

DEFAULT_CHUNK_SIZE_TOKENS = 650
DEFAULT_CHUNK_OVERLAP_TOKENS = 100


@dataclass(slots=True)
class ChunkMetadata:
    opening: str
    eco: str | None
    color: str | None
    difficulty: str | None
    theme: str
    source: str
    doc_id: str  # the source filename, e.g. "italian_game.md" -- always unique
    # per document, unlike `source` (an editorial/citation label that authors
    # may reuse across files), so it is safe to use for point-ID generation.
    variation: str | None = None


@dataclass(slots=True)
class Chunk:
    text: str
    chunk_index: int
    token_count: int
    metadata: ChunkMetadata


def _theme_slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", heading.strip().lower()).strip("_")


def _split_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    _, fm, body = raw.split("---", 2)
    metadata = yaml.safe_load(fm) or {}
    return metadata, body.strip()


def _split_into_sections(body: str) -> list[tuple[str, str]]:
    """Returns [(heading, section_text), ...] for every '## Heading' block."""
    matches = list(_SECTION_RE.finditer(body))
    sections: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections.append((heading, body[start:end].strip()))
    return sections


def _windowed_token_chunks(
    text: str, chunk_size: int, overlap: int
) -> list[str]:
    tokens = _ENCODING.encode(text)
    if len(tokens) <= chunk_size:
        return [text]

    chunks: list[str] = []
    step = chunk_size - overlap
    for start in range(0, len(tokens), step):
        window = tokens[start : start + chunk_size]
        if not window:
            break
        chunks.append(_ENCODING.decode(window))
        if start + chunk_size >= len(tokens):
            break
    return chunks


def chunk_document(
    path: Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
    overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Chunks a single seed_data/openings/*.md file into metadata-tagged Chunks."""
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(raw)

    opening = frontmatter.get("opening", path.stem)
    eco = frontmatter.get("eco")
    color = frontmatter.get("primary_color")
    difficulty = frontmatter.get("difficulty")
    source = frontmatter.get("source", path.name)

    chunks: list[Chunk] = []
    chunk_index = 0

    for heading, section_text in _split_into_sections(body):
        if not section_text:
            continue
        theme = _theme_slug(heading)
        for window_text in _windowed_token_chunks(section_text, chunk_size, overlap):
            chunks.append(
                Chunk(
                    text=f"## {heading}\n\n{window_text}",
                    chunk_index=chunk_index,
                    token_count=len(_ENCODING.encode(window_text)),
                    metadata=ChunkMetadata(
                        opening=opening,
                        eco=eco,
                        color=color,
                        difficulty=difficulty,
                        theme=theme,
                        source=source,
                        doc_id=path.name,
                    ),
                )
            )
            chunk_index += 1

    return chunks


def chunk_directory(
    directory: Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
    overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
) -> dict[str, list[Chunk]]:
    """Chunks every *.md file in a directory. Returns {filename: [Chunk, ...]}."""
    result: dict[str, list[Chunk]] = {}
    for path in sorted(directory.glob("*.md")):
        result[path.name] = chunk_document(path, chunk_size=chunk_size, overlap=overlap)
    return result
