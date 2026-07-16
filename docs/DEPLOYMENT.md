# Deployment guide (Docker Compose)

## Services

`docker-compose.yml` at the repo root defines five services:

| Service | Image / build | Purpose |
|---|---|---|
| `postgres` | `postgres:16-alpine` | Primary database |
| `qdrant` | `qdrant/qdrant:latest` | Vector store (server mode) |
| `ollama` | `ollama/ollama:latest` | Local LLM inference (default provider) |
| `backend` | `docker/Dockerfile.backend` | FastAPI app |
| `frontend` | `docker/Dockerfile.frontend` | Next.js production build |

`backend` waits for Postgres to be healthy, then runs Alembic migrations
automatically on every boot (`docker/backend-entrypoint.sh`) before starting
uvicorn — no manual migration step needed in this path. It talks to `qdrant`
and `ollama` over the Docker network (`QDRANT_MODE=server`,
`OLLAMA_BASE_URL=http://ollama:11434/v1`, both overridden in the compose
file regardless of what `.env` says, since those hostnames only resolve
inside the Docker network).

## Deploy

```bash
cp .env.example .env
docker compose up --build -d
```

Pull an Ollama model into the running container (one-time — the model is
cached in the `ollama_data` volume):

```bash
docker compose exec ollama ollama pull llama3.2:1b
```

Seed the reference opening database and knowledge base (one-time, or
whenever `seed_data/` changes):

```bash
docker compose exec backend python -m database.seed.load_opening_book
docker compose exec backend python -m database.seed.index_knowledge_base
docker compose exec backend python -m database.seed.seed_games   # optional demo data
```

Open http://localhost:3000. The API is at http://localhost:8000
(`/docs` for Swagger).

## Configuration

All backend configuration flows through `.env` (see `.env.example` for every
variable) via `env_file: .env` in `docker-compose.yml`, with a few
values force-overridden in the compose file itself because they must point
at Docker service names rather than `localhost`:

```yaml
environment:
  POSTGRES_HOST: postgres
  QDRANT_MODE: server
  QDRANT_URL: http://qdrant:6333
  OLLAMA_BASE_URL: http://ollama:11434/v1
```

To use Groq or OpenAI instead of the bundled Ollama container, set
`LLM_PROVIDER=groq` (+ `GROQ_API_KEY`) or `LLM_PROVIDER=openai` (+
`OPENAI_API_KEY`) in `.env` — the `ollama` service can then be removed from
`docker-compose.yml` (or just left running unused).

## Data persistence

Named volumes persist across `docker compose down` (but not `down -v`):

- `postgres_data` — the database
- `qdrant_data` — the vector index (server mode)
- `ollama_data` — downloaded Ollama models
- `qdrant_index_cache` — mount point for the backend container's local Qdrant
  path (unused when `QDRANT_MODE=server`, kept for parity with local dev)

## Updating

```bash
git pull
docker compose up --build -d
```

Migrations run automatically on the next `backend` container start. If
`seed_data/openings/*.md` changed, re-run
`docker compose exec backend python -m database.seed.index_knowledge_base`
— it's checksum-gated, so unchanged files are skipped automatically.

## Production hardening (beyond MVP scope)

This compose file is sized for a self-hosted/personal deployment. Before
exposing it publicly, consider: a reverse proxy with TLS (Caddy/Traefik/nginx),
non-default Postgres credentials, restricting exposed ports (only 3000/8000
need to be public; 5432/6333/11434 should stay internal), resource limits on
the `backend`/`ollama` services, and adding authentication (see
[ARCHITECTURE.md](ARCHITECTURE.md#single-tenant-scope) — this MVP is
single-tenant with no auth by design).
