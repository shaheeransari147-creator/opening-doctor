from pathlib import Path

from rag.chunking.chunker import chunk_directory, chunk_document

OPENINGS_DIR = Path(__file__).resolve().parents[2] / "seed_data" / "openings"


def test_chunks_italian_game_with_expected_metadata():
    chunks = chunk_document(OPENINGS_DIR / "italian_game.md")
    assert len(chunks) >= 5  # one per "## Heading" section, at least

    first = chunks[0]
    assert first.metadata.opening == "Italian Game"
    assert first.metadata.eco == "C50-C54"
    assert first.metadata.color == "white"
    assert first.metadata.difficulty == "beginner"
    assert first.metadata.doc_id == "italian_game.md"
    assert first.metadata.theme  # non-empty theme slug


def test_chunk_indices_are_sequential_and_unique():
    chunks = chunk_document(OPENINGS_DIR / "italian_game.md")
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_each_chunk_is_within_a_reasonable_token_budget():
    chunks = chunk_document(OPENINGS_DIR / "sicilian_defense.md", chunk_size=650, overlap=100)
    for chunk in chunks:
        # Small tolerance for the "## Heading" prefix we prepend after windowing.
        assert chunk.token_count <= 650 + 20


def test_themes_reflect_document_sections():
    chunks = chunk_document(OPENINGS_DIR / "ruy_lopez.md")
    themes = {c.metadata.theme for c in chunks}
    assert "overview" in themes
    assert "common_mistakes" in themes
    assert "opening_traps" in themes
    assert "model_game" in themes


def test_chunk_directory_covers_all_eight_openings():
    result = chunk_directory(OPENINGS_DIR)
    assert len(result) == 8
    expected_files = {
        "italian_game.md",
        "sicilian_defense.md",
        "french_defense.md",
        "london_system.md",
        "caro_kann_defense.md",
        "queens_gambit.md",
        "kings_indian_defense.md",
        "ruy_lopez.md",
    }
    assert set(result.keys()) == expected_files
    for chunks in result.values():
        assert len(chunks) > 0


def test_doc_ids_are_unique_per_source_file_even_with_same_editorial_source():
    """Regression test: point IDs are derived from doc_id, not the editorial
    `source` metadata tag, so two documents must never collide even if a
    future author reuses the same `source:` frontmatter value.
    """
    all_chunks = []
    for chunks in chunk_directory(OPENINGS_DIR).values():
        all_chunks.extend(chunks)

    ids = {(c.metadata.doc_id, c.chunk_index) for c in all_chunks}
    assert len(ids) == len(all_chunks)
