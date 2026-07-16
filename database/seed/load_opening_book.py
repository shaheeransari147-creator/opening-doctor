"""Seed script: loads the lichess ECO opening dataset (database/seed/eco/*.tsv)
into the `opening_book_entries` Postgres table, so the reference book used by
ingestion.opening_book can also be browsed/queried directly via SQL and the API.

Usage (from repo root, with the backend venv active):
    python -m database.seed.load_opening_book
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import chess
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging, get_logger
from database.models import OpeningBookEntry
from database.session import init_engine, session_scope
from ingestion.opening_book import OpeningBook

logger = get_logger(__name__)


async def load_opening_book() -> int:
    book = OpeningBook.load_from_tsv_dir()
    logger.info("Loaded %d entries from ECO tsv files into in-memory trie", book.size)

    inserted = 0
    async with session_scope() as session:
        for entry in book.entries:
            board = chess.Board()
            for san in entry.moves:
                board.push_san(san)

            stmt = (
                pg_insert(OpeningBookEntry)
                .values(
                    eco=entry.eco,
                    name=entry.name,
                    pgn_moves=" ".join(entry.moves),
                    san_moves_json=json.dumps(list(entry.moves)),
                    ply_count=len(entry.moves),
                    final_fen=board.fen(),
                )
                .on_conflict_do_nothing(constraint="uq_opening_book_eco_name")
            )
            result = await session.execute(stmt)
            inserted += result.rowcount or 0

    logger.info("Inserted %d new opening_book_entries rows", inserted)
    return inserted


async def main() -> None:
    configure_logging(get_settings().log_level)
    init_engine(get_settings().database_url)
    await load_opening_book()


if __name__ == "__main__":
    asyncio.run(main())
