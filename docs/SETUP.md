# Local development setup

This is the exact sequence used to build and verify this project without
Docker (Windows, but the steps are the same on macOS/Linux with the obvious
package-manager substitutions).

## Prerequisites

- **Python 3.12** — `winget install Python.Python.3.12` / `brew install python@3.12` / your distro's package manager
- **Node.js LTS** (Next.js 15 needs Node 18.18+) — `winget install OpenJS.NodeJS.LTS` / `brew install node`
- **PostgreSQL 16 or 17** — native install, or `docker compose up postgres` if you have Docker
- **An LLM provider** — default is [OpenRouter](https://openrouter.ai/keys) (free key, hosted); for a fully offline/keyless setup instead, install [Ollama](https://ollama.com) and `ollama pull llama3.2:3b`

## 1. Database

Create the database and user (adjust to match whatever Postgres you have
running):

```sql
CREATE DATABASE opening_doctor;
```

Copy `.env.example` to `.env` at the repo root and fill in your Postgres
connection details:

```bash
cp .env.example .env
```

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=opening_doctor
```

## 2. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements-dev.txt
```

Run migrations and seed data from the **repo root** (the modules are
structured as siblings — `ingestion`, `rag`, `vector`, `database`,
`backend` — so imports resolve relative to the root):

```bash
cd ..   # repo root
python -m alembic upgrade head
python -m database.seed.load_opening_book      # loads the ~3,800-line ECO reference dataset
python -m database.seed.index_knowledge_base   # chunks + embeds the 8 opening guides into Qdrant
python -m database.seed.seed_games             # optional: 13 demo games for a populated dashboard
```

The first run of `index_knowledge_base` downloads the embedding
(`BAAI/bge-small-en-v1.5`, ~130MB) and reranker (`Xenova/ms-marco-MiniLM-L-6-v2`,
~90MB) ONNX models via `fastembed` — cached locally afterward.

Qdrant runs in **embedded/local mode** by default (`QDRANT_MODE=local` in
`.env`) — no separate server needed for local dev; it persists to
`vector/.qdrant_data/`.

Start the API:

```bash
cd backend
python run.py
```

http://localhost:8000/docs has interactive Swagger docs.

## 3. LLM provider

Default is OpenRouter, using a free-tier model. Get a free key at
https://openrouter.ai/keys (required even for `:free` models) and set it in
`.env`:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
```

For a fully offline/keyless setup instead, switch to local Ollama:

```bash
ollama pull llama3.2:3b
```

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
```

Or Groq (also free, very fast, needs a key from https://console.groq.com/keys):

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your-key-here
```

## 4. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # or create .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

http://localhost:3000.

## 5. Tests

```bash
cd backend
python -m pytest ../tests/ -v
```

This runs all 54 tests: 39 unit tests (`tests/unit/`) plus 15 integration
tests (`tests/integration/`) that spin up the real FastAPI app against a
disposable `opening_doctor_test` Postgres database, created and dropped
automatically per test session — see `tests/integration/conftest.py`. Your
dev/demo database is never touched, and the LLM provider is force-set to an
unconfigured state so the suite never depends on any provider being reachable.

## Troubleshooting

- **`alembic upgrade head` can't connect** — check `.env`'s `POSTGRES_*`
  values match your running Postgres instance and the database exists.
- **fastembed model download fails / hangs** — it needs outbound HTTPS to
  Hugging Face; check your network/proxy. Models are cached after the
  first successful download.
- **`/api/chat` or `/api/mistakes?explain=true` return `503`** — no LLM
  provider is configured or reachable. If using OpenRouter, check
  `OPENROUTER_API_KEY` is set. If using Ollama, confirm `ollama list` shows
  a pulled model and `ollama serve` is running (the installer usually starts
  it as a background service automatically).
- **Windows: PostgreSQL GUI installer hangs** — if you hit this, the NSIS
  installer payload can be extracted directly with 7-Zip and run via
  `initdb`/`pg_ctl` without the wizard; see the git history of this
  project's setup for the exact commands, or just use
  `docker compose up postgres` instead.
