# API reference

Base URL: `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL` on
the frontend side). All endpoints are mounted under the `/api` prefix
except `/health`. Interactive Swagger docs are always available at
`/docs` when the backend is running.

All request/response bodies are JSON except `POST /api/upload`, which is
`multipart/form-data`.

---

## `POST /api/upload`

Uploads a PGN file and/or pasted PGN text, parses every game, and
immediately runs the full analysis pipeline (opening detection, theory-exit
detection, mistake detection) on each one.

**Form fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | no* | A `.pgn` or `.txt` file |
| `pgn_text` | string | no* | Raw PGN text (one or more games) |
| `player_name` | string | no | Matched case-insensitively against White/Black; scopes mistake detection to that side. Omit to analyze both sides. |

\* At least one of `file` / `pgn_text` is required.

**Response `200`:**
```json
{
  "games_added": 1,
  "game_ids": [1],
  "mistakes_found": 7,
  "parse_warnings": []
}
```

**Errors:** `400` if neither `file` nor `pgn_text` given; `422` if the PGN
text contains no parseable games; `413` if the file exceeds
`MAX_UPLOAD_SIZE_MB` (default 10MB).

---

## `POST /api/analyze`

Re-runs the analysis pipeline for an already-uploaded game (or every game),
replacing its moves/theory-exit/mistakes in place. Useful after an opening
book update or a mistake-detector fix.

**Body:**
```json
{ "game_id": 1 }
```
Omit or set `game_id: null` to re-analyze every stored game.

**Response `200`:**
```json
{ "games_analyzed": 1, "game_ids": [1], "mistakes_found": 7 }
```

**Errors:** `404` if `game_id` doesn't exist.

---

## `GET /api/mistakes`

Recurring mistakes grouped by `(mistake_type, san)` across every analyzed
game — e.g. *"You played h6 too early in 12 games. Average evaluation
loss: -0.8."*

**Query params:**

| Param | Type | Default | Description |
|---|---|---|---|
| `mistake_type` | string | — | Filter to one mistake type |
| `explain` | bool | `false` | Generate an AI coaching explanation (RAG, cites sources) per group. Slower — calls the LLM. Returns `503` if no LLM provider is configured. |
| `limit` | int | 20 | Max groups (1–100) |
| `offset` | int | 0 | Pagination offset |

**Response `200`:**
```json
{
  "groups": [
    {
      "mistake_type": "premature_pawn_push",
      "san": "h6",
      "occurrences": 12,
      "avg_eval_loss": -0.8,
      "example_description": "Played the flank pawn move h6 on move 3...",
      "game_ids": [1, 4, 9],
      "headline": "You played a premature pawn push, h6 in 12 games.",
      "explanation": null
    }
  ],
  "limit": 20,
  "offset": 0
}
```
When `explain=true`, `explanation` is populated:
```json
{
  "explanation_markdown": "### Why This Is Inaccurate\n...\n### A Better Move\n...",
  "citations": [{ "opening": "Italian Game", "theme": "common_mistakes", "source": "italian_game.md" }]
}
```

---

## `GET /api/study-plan`

Today's prioritized study plan, built from the weakest openings and most
common recurring mistakes — no LLM call, always available.

**Response `200`:**
```json
{
  "items": [
    { "activity": "Study Italian Game", "minutes": 15, "priority": "high", "reason": "Your weakest opening: ..." },
    { "activity": "Drill flank-pawn discipline...", "minutes": 10, "priority": "high", "reason": "Recurring in 12 games (you played h6)..." }
  ],
  "total_minutes": 45
}
```

---

## `POST /api/chat`

RAG-only chess Q&A ("Why is h6 bad?", "Explain the Italian Game", "How do I
beat the London?"). Answers are grounded strictly in the retrieved
knowledge base and cite their sources; the model is instructed not to
answer beyond the provided context plus basic chess rules.

**Body:**
```json
{ "question": "Why is h6 bad in the opening?" }
```

**Response `200`:**
```json
{
  "answer_markdown": "Playing h6 too early... [1]",
  "citations": [{ "opening": "Italian Game", "theme": "common_mistakes", "source": "italian_game.md" }]
}
```

**Errors:** `422` if `question` is empty; `503` if no LLM provider is
configured.

---

## `GET /api/dashboard`

Aggregate stats for the dashboard.

**Response `200`:**
```json
{
  "games_analyzed": 13,
  "opening_score": 91.7,
  "most_played_openings": [{ "opening_name": "Italian Game: ...", "count": 3 }],
  "weakest_openings": [{ "opening_name": "...", "games_played": 1, "mistake_count": 3, "avg_eval_loss": -0.43 }],
  "avg_move_leaving_theory": 5.7,
  "most_common_mistakes": [{ "mistake_type": "premature_pawn_push", "occurrences": 6, "avg_eval_loss": -0.4 }]
}
```

---

## `GET /api/games`

Paginated, searchable list of analyzed games.

**Query params:** `search` (matches opening name or event), `opening`
(exact match), `limit` (1–100, default 20), `offset` (default 0).

**Response `200`:** `{ "games": [...], "total": N, "limit": 20, "offset": 0 }`

## `GET /api/games/{id}`

Full detail for one game: every move (with `is_book_move` flag), theory-exit
info, and mistake count. `404` if not found.

---

## `GET /api/openings`

Per-opening stats aggregated from analyzed games: games played, win/draw/loss,
average move leaving theory, mistake count. Searchable and paginated
(`search`, `limit`, `offset`), same shape as `/api/games`.

---

## `GET /health`

Liveness check, no `/api` prefix. `{ "status": "ok" }`.
