"""Application configuration loaded from environment variables / .env file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000"

    # --- Postgres ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "opening_doctor"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # --- Qdrant ---
    qdrant_mode: str = "local"  # "local" (embedded, file-backed) or "server"
    qdrant_url: str = "http://localhost:6333"
    qdrant_local_path: str = str(REPO_ROOT / "vector" / ".qdrant_data")
    qdrant_collection: str = "opening_knowledge"

    # --- Embeddings / Reranking (free, CPU-friendly via fastembed/ONNX) ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"

    # --- Chunking ---
    chunk_size_tokens: int = 650
    chunk_overlap_tokens: int = 100

    # --- Retrieval ---
    retrieval_top_k_bm25: int = 20
    retrieval_top_k_dense: int = 20
    retrieval_top_k_final: int = 5

    # --- LLM provider (configurable) ---
    llm_provider: str = "openrouter"  # "openrouter" | "ollama" | "groq" | "openai"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2:3b"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5"

    llm_temperature: float = 0.3
    llm_max_tokens: int = 1200

    # --- Uploads ---
    max_upload_size_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
