from ingestion.mistake_detector import detect_mistakes
from ingestion.pgn_parser import parse_pgn_text

# Black: plays h6 early (premature pawn push), moves the f8 bishop 3x (repeated
# piece moves impossible without more plies, so we focus on queen sortie +
# delayed castling + ignored center control instead), and never castles.
MISTAKE_RIDDEN_GAME = """
[Event "Casual Game"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. Nf3 h6 2. g3 h5 3. Bg2 c5 4. O-O Qb6 5. d4 Nc6 6. c3 Nb4 7. Na3 Nc6
8. e3 e6 1-0
"""

CLEAN_OPENING_GAME = """
[Event "Casual Game"]
[White "Carol"]
[Black "Dave"]
[Result "1/2-1/2"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 O-O
8. c3 d5 1/2-1/2
"""


def test_detects_early_queen_development():
    game = parse_pgn_text(MISTAKE_RIDDEN_GAME)[0]
    mistakes = detect_mistakes(game.moves, "black")
    queen_mistakes = [m for m in mistakes if m.mistake_type == "early_queen_development"]
    assert len(queen_mistakes) == 1
    assert queen_mistakes[0].san == "Qb6"
    assert queen_mistakes[0].move_number == 4
    assert queen_mistakes[0].eval_loss < 0


def test_detects_premature_pawn_push():
    game = parse_pgn_text(MISTAKE_RIDDEN_GAME)[0]
    mistakes = detect_mistakes(game.moves, "black")
    pawn_mistakes = [m for m in mistakes if m.mistake_type == "premature_pawn_push"]
    assert any(m.san == "h6" for m in pawn_mistakes)


def test_detects_delayed_castling():
    game = parse_pgn_text(MISTAKE_RIDDEN_GAME)[0]
    mistakes = detect_mistakes(game.moves, "black")
    assert any(m.mistake_type == "delayed_castling" for m in mistakes)


def test_detects_ignored_center_control():
    game = parse_pgn_text(MISTAKE_RIDDEN_GAME)[0]
    mistakes = detect_mistakes(game.moves, "black")
    # Black never pushed a d- or e- pawn until move 8 (e6) -- by the move-6 deadline
    # the center had been ignored.
    assert any(m.mistake_type == "ignored_center_control" for m in mistakes)


def test_detects_repeated_piece_moves_for_wandering_knight():
    game = parse_pgn_text(MISTAKE_RIDDEN_GAME)[0]
    mistakes = detect_mistakes(game.moves, "black")
    # The b8-knight goes Nc6-Nb4-Nc6: three moves of the same piece.
    repeated = [m for m in mistakes if m.mistake_type == "repeated_piece_moves"]
    assert any(m.san == "Nc6" for m in repeated)


def test_clean_game_has_no_major_opening_mistakes():
    game = parse_pgn_text(CLEAN_OPENING_GAME)[0]
    white_mistakes = detect_mistakes(game.moves, "white")
    black_mistakes = detect_mistakes(game.moves, "black")
    assert white_mistakes == []
    assert black_mistakes == []


def test_mistakes_are_grouped_by_type_and_move_for_aggregation():
    """Sanity check that the shape of a DetectedMistake supports the
    "you played h6 too early in N games" aggregation the API layer builds on top.
    """
    game = parse_pgn_text(MISTAKE_RIDDEN_GAME)[0]
    mistakes = detect_mistakes(game.moves, "black")
    for m in mistakes:
        assert m.color == "black"
        assert isinstance(m.eval_loss, float)
        assert m.description
