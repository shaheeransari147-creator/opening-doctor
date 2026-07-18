# Deploying for free: Netlify + Render + Neon

Three services, all genuinely free (no credit card required anywhere), no
Docker needed on your machine — Render builds the existing
`docker/Dockerfile.backend` for you.

| Piece | Host | Why |
|---|---|---|
| Frontend (Next.js) | [Netlify](https://netlify.com) | First-class Next.js support (SSR, API routes) via `@netlify/plugin-nextjs` |
| Backend (FastAPI) | [Render](https://render.com) | Free web service that runs a long-lived process (Netlify Functions can't — see below) |
| Database | [Neon](https://neon.tech) | Free serverless Postgres |
| Vector DB | *(none needed)* | Qdrant stays in local/embedded mode on the backend; no separate service |
| LLM | OpenRouter (already configured) | Already an external API call, no hosting needed |

**Why not put everything on Netlify?** Netlify Functions are serverless
(stateless, short timeouts — 10s free / 26s paid). This app needs a
long-running process: a warm in-memory BM25 index, an embedding model loaded
once and reused, and LLM calls that can take longer than a function timeout
allows. Render's free web service is a normal always-running container
(with one tradeoff — see **Cold starts** below).

## 1. Database — Neon

1. Sign up at [neon.tech](https://neon.tech) (free, no card).
2. Create a project, e.g. `opening-doctor`.
3. Copy the connection string it gives you — it looks like:
   ```
   postgresql://user:password@ep-xxx-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```
   Keep this; you'll paste it into Render as `DATABASE_URL` in step 2.

## 2. Backend — Render

1. Sign up at [render.com](https://render.com) (free, no card) and connect
   your GitHub account.
2. Push this repo to GitHub if you haven't already (see the main README).
3. In Render: **New → Blueprint**, select this repo. Render reads
   `render.yaml` at the repo root automatically and proposes the
   `opening-doctor-backend` web service (Docker runtime, free plan).
4. Before the first deploy, fill in the env vars marked as secrets:
   - `DATABASE_URL` — the Neon connection string from step 1
   - `OPENROUTER_API_KEY` — a free key from [openrouter.ai/keys](https://openrouter.ai/keys)
   - `CORS_ORIGINS` — set to `http://localhost:3000` for now; you'll update
     this to your real Netlify URL in step 4
   - *(optional)* `SEED_DEMO_DATA` = `true` — loads the 13 sample games on
     this boot only. **Remove this env var right after the first successful
     deploy** (it's not idempotent — leaving it set re-inserts duplicate
     games on every restart).
5. Deploy. On first boot, the entrypoint automatically runs Alembic
   migrations, loads the ~3,800-line ECO opening reference, and indexes the
   8 opening guides into a local Qdrant index — no manual seed step needed
   (see `docker/backend-entrypoint.sh`).
6. Once live, note the backend URL Render gives you, e.g.
   `https://opening-doctor-backend.onrender.com`. Confirm it works:
   ```bash
   curl https://opening-doctor-backend.onrender.com/health
   ```

## 3. Frontend — Netlify

1. Sign up at [netlify.com](https://netlify.com) (free, no card).
2. **Add new site → Import an existing project**, pick this repo. Netlify
   reads `netlify.toml` at the repo root automatically (`base = "frontend"`,
   the Next.js plugin).
3. **Before the first build**, add an environment variable:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL from step 2 (e.g.
     `https://opening-doctor-backend.onrender.com`, no trailing slash)

   This matters because `NEXT_PUBLIC_*` variables are baked into the
   JavaScript bundle **at build time**, not read at runtime. If you set it
   after the first build, trigger a new deploy (Netlify → Deploys → Trigger
   deploy) for it to take effect.
4. Deploy. Netlify gives you a URL like `https://your-site.netlify.app`.

## 4. Close the loop: update CORS

Go back to Render → your backend service → Environment, and set
`CORS_ORIGINS` to your real Netlify URL (comma-separate if you want to keep
`http://localhost:3000` too for local testing against the deployed backend):

```
CORS_ORIGINS=https://your-site.netlify.app,http://localhost:3000
```

Save — Render redeploys automatically. Visit your Netlify URL; the
dashboard, upload, chat, etc. should now all work against the live backend.

## Known limitations of the free tier

- **Cold starts.** Render's free web services spin down after 15 minutes of
  no traffic and take ~30–60 seconds to wake on the next request. The first
  request after idle time will be slow; everything after that is normal
  speed until it idles out again.
- **512MB RAM.** The embedding model (`bge-small-en-v1.5`, ~130MB) and
  reranker (~90MB) both load into memory alongside FastAPI. This generally
  fits, but it's a real constraint on the free plan — if you see the
  service crash-loop or OOM in Render's logs, that's the likely cause; the
  paid Starter plan (512MB → more, still cheap) removes this ceiling.
- **Ephemeral disk.** Local Qdrant data doesn't survive a redeploy on
  Render's free tier — this is why the entrypoint re-indexes the knowledge
  base on every boot. It's small (8 documents, ~48 chunks) so this adds a
  few seconds to startup, not minutes.
- **Neon free tier** auto-suspends after inactivity too (a few seconds to
  wake, much faster than Render's cold start) and caps storage at 0.5GB —
  more than enough for this app's schema.

## Updating after a deploy

Push to `master` (or your default branch) — both Render and Netlify
auto-deploy on push once connected. Alembic migrations and knowledge-base
re-indexing run automatically on every Render boot, so schema/seed-data
changes in `seed_data/openings/*.md` or new Alembic revisions just work on
the next push.
