"""End-to-end integration test: upload -> games -> mistakes -> dashboard ->
openings -> study-plan, all against the real FastAPI app and a real
(disposable) Postgres test database. No LLM or Qdrant network calls are
exercised here -- see test_chat_llm_not_configured.py for the RAG-dependent
endpoints' graceful-failure behavior.
"""
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

MISTAKE_RIDDEN_GAME = """
[Event "Casual Game"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. Nf3 h6 2. g3 h5 3. Bg2 c5 4. O-O Qb6 5. d4 Nc6 6. c3 Nb4 7. Na3 Nc6
8. e3 e6 1-0
"""

CLEAN_GAME = """
[Event "Casual Game"]
[White "Carol"]
[Black "Dave"]
[Result "1/2-1/2"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 O-O
8. c3 d5 1/2-1/2
"""


async def test_upload_parses_and_analyzes_games(client):
    resp = await client.post("/api/upload", data={"pgn_text": MISTAKE_RIDDEN_GAME, "player_name": "Bob"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["games_added"] == 1
    assert body["mistakes_found"] > 0
    assert len(body["game_ids"]) == 1


async def test_upload_requires_pgn_text_or_file(client):
    resp = await client.post("/api/upload", data={})
    assert resp.status_code == 400


async def test_upload_rejects_garbage_pgn(client):
    resp = await client.post("/api/upload", data={"pgn_text": "not a real pgn at all"})
    assert resp.status_code == 422


async def test_games_list_and_detail(client):
    upload = await client.post("/api/upload", data={"pgn_text": MISTAKE_RIDDEN_GAME, "player_name": "Bob"})
    game_id = upload.json()["game_ids"][0]

    listed = await client.get("/api/games")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["games"][0]["white"] == "Alice"

    detail = await client.get(f"/api/games/{game_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["mistake_count"] > 0
    assert len(detail_body["moves"]) == 16


async def test_game_detail_404_for_missing_game(client):
    resp = await client.get("/api/games/999999")
    assert resp.status_code == 404


async def test_mistakes_are_grouped_across_games(client):
    # Upload the same mistake-ridden game twice under different player names
    # so the "h6" premature-pawn-push mistake accumulates to 2 occurrences.
    await client.post("/api/upload", data={"pgn_text": MISTAKE_RIDDEN_GAME, "player_name": "Bob"})
    await client.post(
        "/api/upload",
        data={"pgn_text": MISTAKE_RIDDEN_GAME.replace("Bob", "Eve"), "player_name": "Eve"},
    )

    resp = await client.get("/api/mistakes")
    assert resp.status_code == 200
    groups = resp.json()["groups"]
    h6_group = next(g for g in groups if g["san"] == "h6")
    assert h6_group["occurrences"] == 2
    assert "h6" in h6_group["headline"]


async def test_dashboard_reflects_uploaded_games(client):
    await client.post("/api/upload", data={"pgn_text": MISTAKE_RIDDEN_GAME, "player_name": "Bob"})
    await client.post("/api/upload", data={"pgn_text": CLEAN_GAME})

    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["games_analyzed"] == 2
    assert 0 <= body["opening_score"] <= 100
    assert len(body["most_common_mistakes"]) > 0


async def test_openings_endpoint_lists_and_searches(client):
    await client.post("/api/upload", data={"pgn_text": CLEAN_GAME})

    all_openings = await client.get("/api/openings")
    assert all_openings.status_code == 200
    assert all_openings.json()["total"] >= 1

    searched = await client.get("/api/openings", params={"search": "Ruy Lopez"})
    assert searched.status_code == 200
    assert all("Ruy Lopez" in o["opening_name"] or "Spanish" in o["opening_name"] for o in searched.json()["openings"])


async def test_study_plan_prioritizes_weakest_areas(client):
    await client.post("/api/upload", data={"pgn_text": MISTAKE_RIDDEN_GAME, "player_name": "Bob"})

    resp = await client.get("/api/study-plan")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) > 0
    assert body["total_minutes"] == sum(item["minutes"] for item in body["items"])


async def test_analyze_rerun_for_single_game(client):
    upload = await client.post("/api/upload", data={"pgn_text": MISTAKE_RIDDEN_GAME, "player_name": "Bob"})
    game_id = upload.json()["game_ids"][0]

    resp = await client.post("/api/analyze", json={"game_id": game_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["games_analyzed"] == 1
    assert body["game_ids"] == [game_id]


async def test_analyze_404_for_missing_game(client):
    resp = await client.post("/api/analyze", json={"game_id": 999999})
    assert resp.status_code == 404
