"""Seed script: loads seed_data/pgns/seed_games.pgn (13 sample games across
all 8 supported openings, all played by "Student") through the full
analysis pipeline, so a fresh install has meaningful dashboard/mistakes/
study-plan data out of the box.

Usage (from repo root, with the backend venv active):
    python -m database.seed.seed_games
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging, get_logger
from backend.app.services.analysis_service import analyze_and_store_pgn
from database.models import GameSource
from database.session import init_engine, session_scope

logger = get_logger(__name__)

PGN_PATH = Path(__file__).resolve().parents[2] / "seed_data" / "pgns" / "seed_games.pgn"


async def seed_games() -> None:
    pgn_text = PGN_PATH.read_text(encoding="utf-8")

    async with session_scope() as session:
        summary = await analyze_and_store_pgn(
            session, pgn_text, player_name="Student", source=GameSource.SEED
        )

    logger.info(
        "Seeded %d games (%d mistakes found) from %s", summary.games_added, summary.mistakes_found, PGN_PATH.name
    )


async def main() -> None:
    configure_logging(get_settings().log_level)
    init_engine(get_settings().database_url)
    await seed_games()


if __name__ == "__main__":
    asyncio.run(main())
