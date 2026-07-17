# Opening Doctor

A RAG-powered chess coach. Upload your games, and it identifies recurring
opening mistakes, retrieves relevant opening theory from a curated knowledge
base, and explains what to do better — like a coach, not an engine printout.

![status](https://img.shields.io/badge/status-MVP-informational)

## What it does

1. **Parses your PGN games** (upload a file or paste text) with `python-chess`.
2. **Detects the opening** (name, ECO code, variation) by matching your moves
   against a ~3,800-line reference database (the lichess-org `chess-openings`
   ECO dataset).
3. **Finds where you left known theory** — the exact move, what the book
   recommends instead, and what you played.
4. **Detects recurring opening mistakes** — early queen sorties, delayed
   castling, premature flank pawn pushes, ignoring the center, lost tempi,
   and shuffling the same piece back and forth — using deterministic chess
   heuristics (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for why this
   isn't an engine-evaluation product).
5. **Explains mistakes like a coach**, grounded in a hybrid-retrieval RAG
   pipeline (BM25 + dense vector search + cross-encoder rerank) over eight
   annotated opening guides, always citing its sources.
6. **Answers chess questions in a chat**, RAG-only — it won't answer from
   ungrounded model knowledge, and every answer cites what it retrieved.
7. **Builds a daily study plan** prioritized by your weakest openings and
   most common recurring mistakes.
8. **Dashboards** your opening score, most/least played openings, average
   move you leave theory, and most common mistakes, with charts.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15, TypeScript, TailwindCSS, shadcn/ui, Recharts |
| Backend | FastAPI, Python 3.12, async SQLAlchemy |
| Database | PostgreSQL 16/17 |
| Vector DB | Qdrant (embedded/local mode for dev, server mode in Docker) |
| Chess | python-chess |
| Embeddings | BAAI/bge-small-en-v1.5 via [fastembed](https://github.com/qdrant/fastembed) (ONNX, CPU, free) |
| Reranker | Xenova/ms-marco-MiniLM-L-6-v2 via fastembed (CPU, free) |
| LLM | Configurable — **OpenRouter by default** (free-tier model, needs a free key), or local Ollama (fully keyless) / Groq / OpenAI GPT-5 |
| Sparse search | BM25 (`rank_bm25`) |

The embedding model and reranker are always free and run locally with no API
key. The LLM defaults to OpenRouter's free tier (needs a free key from
[openrouter.ai/keys](https://openrouter.ai/keys)); swap in fully local/keyless
Ollama, Groq, or GPT-5 instead — see
[Configuring the LLM provider](#configuring-the-llm-provider).

## Project structure

```
/frontend       Next.js 15 app (App Router)
/backend        FastAPI app: routers, schemas, repositories, services
/ingestion      PGN parsing, opening/theory-exit detection, mistake detection
/rag            Chunking, hybrid retrieval, LLM generation (explain/chat/study-plan)
/vector         Qdrant client wrapper, embeddings, indexer
/database       SQLAlchemy models, Alembic migrations, seed scripts
/docker         Dockerfiles + entrypoint
/docs           Architecture, ER diagram, API reference, setup & deploy guides
/tests          Unit tests (ingestion/rag logic) + integration tests (full API)
/seed_data      8 annotated opening guides (RAG knowledge base) + sample PGNs
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how these modules fit
together and the reasoning behind key design decisions.

## Quick start

Two paths: Docker Compose (production-like, one command) or local dev
(no Docker, faster iteration). Both are fully supported.

### Option A — Docker Compose

Requires Docker Desktop.

```bash
cp .env.example .env
# Edit .env: set OPENROUTER_API_KEY (free at https://openrouter.ai/keys),
# or switch LLM_PROVIDER=ollama for a fully offline/keyless setup instead.
docker compose up --build
```

This starts Postgres, Qdrant, Ollama (only used if `LLM_PROVIDER=ollama`),
the backend (migrations run automatically on boot), and the frontend.

If using Ollama, pull a model into its container once, the first time:

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

Then seed the knowledge base and sample games:

```bash
docker compose exec backend python -m database.seed.load_opening_book
docker compose exec backend python -m database.seed.index_knowledge_base
docker compose exec backend python -m database.seed.seed_games
```

Open http://localhost:3000.

### Option B — Local dev (no Docker)

See [docs/SETUP.md](docs/SETUP.md) for the full walkthrough (this is exactly
how this project was built and verified). Short version:

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate   # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt

# Postgres + Qdrant: run natively or via `docker compose up postgres qdrant`
# LLM: get a free key at https://openrouter.ai/keys (default provider), or
# install Ollama from ollama.com + `ollama pull llama3.2:3b` for a fully
# offline/keyless setup instead.

cp ../.env.example ../.env   # edit POSTGRES_* and OPENROUTER_API_KEY

cd ..
python -m alembic upgrade head
python -m database.seed.load_opening_book
python -m database.seed.index_knowledge_base
python -m database.seed.seed_games      # optional: demo data

cd backend
python run.py    # http://localhost:8000, docs at /docs

# Frontend, in a second terminal
cd frontend
npm install
npm run dev      # http://localhost:3000
```

## Configuring the LLM provider

Set `LLM_PROVIDER` in `.env` to `openrouter` (default), `ollama`, `groq`, or `openai`:

```bash
# Free-tier model, hosted — needs a free key from https://openrouter.ai/keys (default)
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free

# Fully local, no API key at all
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b        # or llama3.2:1b for faster/lower quality

# Free, hosted, very fast — needs a key from https://console.groq.com/keys
LLM_PROVIDER=groq
GROQ_API_KEY=...

# GPT-5 — needs an OpenAI API key
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5
```

All three are OpenAI-compatible under the hood (`rag/generation/llm_client.py`),
so switching providers never touches the explanation/chat/RAG logic. If no
provider is configured, `/api/chat` and `/api/mistakes?explain=true` return a
clean `503` explaining what to set — never a crash or a hallucinated answer.

## API

See [docs/API.md](docs/API.md) for the full reference, or run the backend and
open http://localhost:8000/docs for interactive Swagger docs.

| Endpoint | Purpose |
|---|---|
| `POST /api/upload` | Upload a PGN file or pasted text; parses + fully analyzes every game |
| `POST /api/analyze` | Re-run analysis for one game or all games |
| `GET /api/mistakes` | Recurring mistakes grouped across games (`?explain=true` for AI coaching) |
| `GET /api/study-plan` | Today's prioritized study plan |
| `POST /api/chat` | RAG-only chess Q&A, with citations |
| `GET /api/dashboard` | Aggregate stats for the dashboard |
| `GET /api/games`, `GET /api/games/{id}` | List / inspect analyzed games |
| `GET /api/openings` | Per-opening stats, searchable and paginated |

## Testing

```bash
cd backend
python -m pytest ../tests/ -v
```

54 tests: 39 unit tests (PGN parsing, opening/theory-exit detection, mistake
heuristics, chunking, LLM provider abstraction) plus 15 integration tests
that exercise the full FastAPI app end-to-end (upload → games → mistakes →
dashboard → openings → study-plan → analyze) against a disposable
`opening_doctor_test` Postgres database, created and torn down automatically
— never your dev/demo data. The LLM provider is force-unconfigured for
these, so the suite never depends on OpenRouter/Ollama/Groq being reachable.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — module boundaries, the hybrid
  RAG pipeline, and why mistake detection is heuristic rather than engine-based
- [docs/ER_DIAGRAM.md](docs/ER_DIAGRAM.md) — database schema
- [docs/API.md](docs/API.md) — endpoint reference
- [docs/SETUP.md](docs/SETUP.md) — local development setup
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Docker Compose deployment

## Known limitations (MVP scope)

- Single-tenant: no user accounts/auth. Mistake analysis is scoped by an
  optional `player_name` matched against PGN headers, not a login.
- Mistake "evaluation loss" is a heuristic severity score calibrated to chess
  principles, not a chess-engine centipawn evaluation — no engine is part of
  this stack by design (see docs/ARCHITECTURE.md).
- The default OpenRouter free-tier model is rate-limited and its latency
  varies with OpenRouter's own load; Groq is faster and also free if you'd
  rather use that key. Local Ollama inference latency depends heavily on your
  CPU, and the first request after a period of inactivity pays a model-load
  cost — but it needs no API key and no internet access at all.
