"""Seed script: chunks every seed_data/openings/*.md document and indexes it
into Qdrant, recording each source file's ingestion status in the
`kb_sources` Postgres table (keyed by content checksum, so re-running this
script is a cheap no-op unless a document actually changed).

Usage (from repo root, with the backend venv active):
    python -m database.seed.index_knowledge_base
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging, get_logger
from database.models import KbSource
from database.session import init_engine, session_scope
from rag.chunking.chunker import chunk_document
from vector.indexer import upsert_chunks
from vector.qdrant_client import get_qdrant_client

logger = get_logger(__name__)

OPENINGS_DIR = Path(__file__).resolve().parents[2] / "seed_data" / "openings"


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def index_knowledge_base() -> int:
    settings = get_settings()
    client = get_qdrant_client(settings.qdrant_mode, settings.qdrant_url, settings.qdrant_local_path)

    total_chunks = 0
    async with session_scope() as session:
        for path in sorted(OPENINGS_DIR.glob("*.md")):
            checksum = _checksum(path)

            existing = await session.scalar(select(KbSource).where(KbSource.filename == path.name))
            if existing is not None and existing.checksum == checksum:
                logger.info("Skipping unchanged document: %s", path.name)
                continue

            chunks = chunk_document(path, chunk_size=settings.chunk_size_tokens, overlap=settings.chunk_overlap_tokens)
            count = upsert_chunks(
                client,
                settings.qdrant_collection,
                chunks,
                settings.embedding_model,
                settings.embedding_dim,
            )
            total_chunks += count
            logger.info("Indexed %d chunks from %s", count, path.name)

            opening = chunks[0].metadata.opening if chunks else path.stem
            eco = chunks[0].metadata.eco if chunks else None

            stmt = (
                pg_insert(KbSource)
                .values(filename=path.name, opening=opening, eco=eco, checksum=checksum, chunk_count=count)
                .on_conflict_do_update(
                    index_elements=[KbSource.filename],
                    set_={"checksum": checksum, "chunk_count": count, "opening": opening, "eco": eco},
                )
            )
            await session.execute(stmt)

    logger.info("Knowledge base indexing complete: %d total chunks", total_chunks)
    return total_chunks


async def main() -> None:
    configure_logging(get_settings().log_level)
    init_engine(get_settings().database_url)
    await index_knowledge_base()


if __name__ == "__main__":
    asyncio.run(main())
