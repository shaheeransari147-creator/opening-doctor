# Entity-relationship diagram

Generated from `database/models.py` (SQLAlchemy models) / the applied
Alembic migration `database/migrations/versions/7bf3e71785b6_initial_schema.py`.

```mermaid
erDiagram
    PLAYERS ||--o{ GAMES : "white_player_id"
    PLAYERS ||--o{ GAMES : "black_player_id"
    GAMES ||--o{ MOVES : "game_id"
    GAMES ||--o| THEORY_EXITS : "game_id"
    GAMES ||--o{ MISTAKES : "game_id"
    MOVES ||--o| MISTAKES : "move_id"

    PLAYERS {
        int id PK
        string name
        string fide_id "nullable"
    }

    GAMES {
        int id PK
        int white_player_id FK
        int black_player_id FK
        string event "nullable"
        string site "nullable"
        string round "nullable"
        date game_date "nullable"
        enum result "1-0 | 0-1 | 1/2-1/2 | *"
        string eco_code "nullable, indexed"
        string opening_name "nullable, indexed"
        string opening_variation "nullable"
        enum tracked_player_color "white|black, nullable"
        text pgn_raw
        enum source "upload | seed"
        datetime created_at
    }

    MOVES {
        int id PK
        int game_id FK
        int ply "1-indexed half-move"
        int move_number "full move number, as in PGN"
        enum color "white | black"
        string san
        string uci
        string fen_before
        string fen_after
        bool is_book_move
    }

    THEORY_EXITS {
        int id PK
        int game_id FK "unique"
        int exit_ply
        int exit_move_number
        enum color_to_move "white | black"
        string eco_code "nullable"
        string opening_name "nullable"
        string opening_variation "nullable"
        string expected_move_san "nullable"
        string played_move_san "nullable"
    }

    MISTAKES {
        int id PK
        int game_id FK
        int move_id FK "nullable"
        enum mistake_type "early_queen_development | delayed_castling |
                            premature_pawn_push | ignored_center_control |
                            lost_tempo | repeated_piece_moves | theory_deviation"
        enum color "white | black"
        int move_number
        int ply
        string san
        text description
        float eval_loss "heuristic severity, pawn-like unit"
        datetime created_at
    }

    OPENING_BOOK_ENTRIES {
        int id PK
        string eco "indexed"
        string name "indexed"
        text pgn_moves "e.g. '1. e4 e5 2. Nf3 Nc6'"
        text san_moves_json "JSON list of SAN moves"
        int ply_count
        string final_fen "indexed"
    }

    KB_SOURCES {
        int id PK
        string filename "unique"
        string opening
        string eco "nullable"
        string checksum "sha256, for incremental re-indexing"
        int chunk_count
        datetime ingested_at
    }
```

## Notes

- `OPENING_BOOK_ENTRIES` and `KB_SOURCES` have no foreign keys to the game
  data — they're reference/tracking tables. `OPENING_BOOK_ENTRIES` mirrors
  the in-memory trie built from `database/seed/eco/*.tsv` (the lichess ECO
  dataset) so it can also be browsed/queried directly via SQL. `KB_SOURCES`
  tracks which `seed_data/openings/*.md` files have been chunked and indexed
  into Qdrant, keyed by content checksum, so re-running the indexing script
  is a no-op unless a document actually changed.
- The actual vector embeddings live in **Qdrant**, not Postgres — each
  point's payload carries the same metadata dimensions the spec requires
  (opening, variation, eco, color, difficulty, theme, source), plus the
  chunk text itself.
- `Mistake.eval_loss` and `TheoryExit` are populated by the ingestion
  pipeline (`ingestion/opening_detector.py`, `theory_detector.py`,
  `mistake_detector.py`) at upload/analyze time — see
  [ARCHITECTURE.md](ARCHITECTURE.md).
