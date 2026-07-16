"""Integration test fixtures: a dedicated Postgres test database (never the
dev/demo database), a fresh schema per test, and an in-process ASGI client
against the real FastAPI app (no live server / network hop needed).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import get_settings
from backend.app.core.rag_context import get_shared_qdrant_client
from database.models import Base
from database.session import get_engine, init_engine

_ENV_OVERRIDES = {
    "POSTGRES_DB": "opening_doctor_test",
    "LLM_PROVIDER": "groq",
    "GROQ_API_KEY": "",
    "QDRANT_MODE": "local",
    "QDRANT_LOCAL_PATH": str(Path(tempfile.gettempdir()) / "opening_doctor_test_qdrant"),
}


# All integration tests and their fixtures share one event loop for the
# whole session. Postgres async connections (asyncpg) are bound to the loop
# they were opened on; mixing per-test loops with a session-scoped engine
# causes "Event loop is closed" errors when the pool tries to reuse or
# close a connection from a different (already-closed) loop.
@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def _setup_schema():
    # Apply the test overrides just long enough to populate the process-wide
    # get_settings()/get_shared_qdrant_client() caches with test values, then
    # immediately restore the real environment. Everything downstream reads
    # those cached singletons (not raw os.environ), so this doesn't leak into
    # unit tests that build their own fresh Settings() later in the same
    # pytest session (the whole suite runs as one process).
    original_env = {key: os.environ.get(key) for key in _ENV_OVERRIDES}
    os.environ.update(_ENV_OVERRIDES)
    get_settings.cache_clear()
    get_shared_qdrant_client.cache_clear()

    settings = get_settings()
    get_shared_qdrant_client()

    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    from backend.app.main import app  # import after the cache is warmed with test settings

    init_engine(settings.database_url)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield app

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _clean_tables():
    """Truncates all tables between tests so each test starts from a blank slate."""
    yield
    engine = get_engine()
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture(loop_scope="session")
async def client(_setup_schema):
    transport = ASGITransport(app=_setup_schema)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
