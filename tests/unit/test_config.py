from backend.app.core.config import Settings


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_database_url_falls_back_to_postgres_components_when_no_database_url_env():
    settings = _settings(postgres_host="db.local", postgres_port=5433, postgres_user="u", postgres_password="p", postgres_db="d")
    assert settings.database_url == "postgresql+asyncpg://u:p@db.local:5433/d"
    assert settings.sync_database_url == "postgresql+psycopg2://u:p@db.local:5433/d"


def test_database_url_env_takes_precedence_and_translates_sslmode_for_asyncpg():
    settings = _settings(DATABASE_URL="postgresql://u:p@ep-cool-1234.neon.tech/opening_doctor?sslmode=require")
    assert settings.database_url == "postgresql+asyncpg://u:p@ep-cool-1234.neon.tech/opening_doctor?ssl=require"


def test_database_url_env_drops_channel_binding_for_asyncpg():
    settings = _settings(
        DATABASE_URL="postgresql://u:p@ep-cool-1234.neon.tech/opening_doctor?sslmode=require&channel_binding=require"
    )
    assert "channel_binding" not in settings.database_url
    assert "ssl=require" in settings.database_url


def test_sync_database_url_keeps_sslmode_natively_for_psycopg2():
    settings = _settings(DATABASE_URL="postgresql://u:p@ep-cool-1234.neon.tech/opening_doctor?sslmode=require")
    assert settings.sync_database_url == "postgresql+psycopg2://u:p@ep-cool-1234.neon.tech/opening_doctor?sslmode=require"


def test_database_url_env_accepts_short_postgres_scheme():
    settings = _settings(DATABASE_URL="postgres://u:p@host/db")
    assert settings.database_url == "postgresql+asyncpg://u:p@host/db"
