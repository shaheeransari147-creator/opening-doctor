"""FastAPI application entrypoint for Opening Doctor."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import analyze, chat, dashboard, games, mistakes, openings, study_plan, upload
from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging, get_logger
from database.session import init_engine
from ingestion.pgn_parser import PgnParseError
from rag.generation.llm_client import LLMNotConfiguredError

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_engine(settings.database_url)
    logger.info("Opening Doctor API starting up (environment=%s, llm_provider=%s)", settings.environment, settings.llm_provider)
    yield
    logger.info("Opening Doctor API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Opening Doctor API",
        description="RAG-powered chess opening coach",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (upload.router, analyze.router, mistakes.router, study_plan.router, chat.router, dashboard.router, games.router, openings.router):
        app.include_router(router, prefix=settings.api_prefix)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(LLMNotConfiguredError)
    async def llm_not_configured_handler(request: Request, exc: LLMNotConfiguredError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(PgnParseError)
    async def pgn_parse_error_handler(request: Request, exc: PgnParseError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    return app


app = create_app()
