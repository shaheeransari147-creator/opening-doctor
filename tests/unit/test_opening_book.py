import pytest

from ingestion.opening_book import OpeningBook, get_default_book
from ingestion.opening_detector import detect_opening
from ingestion.pgn_parser import parse_pgn_text
from ingestion.theory_detector import detect_theory_exit

ITALIAN_WITH_EARLY_H6 = """
[Event "Casual Game"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 h6 4. d4 exd4 5. Nxd4 Bc5 6. Be3 Qf6 7. c3 Nge7
8. O-O O-O 9. Nb3 Bb6 10. Re1 d6 1-0
"""

RUY_LOPEZ_MAIN_LINE = """
[Event "Casual Game"]
[White "Carol"]
[Black "Dave"]
[Result "1/2-1/2"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 O-O
8. c3 d5 1/2-1/2
"""


@pytest.fixture(scope="module")
def book() -> OpeningBook:
    return get_default_book()


def test_book_loads_thousands_of_entries(book: OpeningBook):
    assert book.size > 3000


def test_detects_italian_game_before_deviation(book: OpeningBook):
    game = parse_pgn_text(ITALIAN_WITH_EARLY_H6)[0]
    san_moves = [m.san for m in game.moves[:4]]  # e4 e5 Nf3 Nc6 -- still book
    result = detect_opening(san_moves, book)
    assert result.eco is not None
    assert "Italian" in result.name or "King's Knight" in result.name or "Open Game" in result.name


def test_detects_ruy_lopez(book: OpeningBook):
    game = parse_pgn_text(RUY_LOPEZ_MAIN_LINE)[0]
    san_moves = [m.san for m in game.moves]
    result = detect_opening(san_moves, book)
    assert result.eco is not None
    assert result.eco.startswith("C")
    assert "Ruy Lopez" in result.name or "Spanish" in result.name


def test_theory_exit_at_clear_novelty(book: OpeningBook):
    game = parse_pgn_text(RUY_LOPEZ_MAIN_LINE)[0]
    # A sentinel token guarantees a trie miss regardless of how deep the ECO
    # dataset's coverage of this line happens to go.
    san_moves = [m.san for m in game.moves[:6]] + ["ZZ-NOT-A-REAL-MOVE"]
    exit_result = book.find_theory_exit(san_moves)
    assert exit_result is not None
    assert exit_result.exit_ply == 7
    assert exit_result.played_move_san == "ZZ-NOT-A-REAL-MOVE"
    assert exit_result.expected_move_san == "Ba4"  # the real Ruy Lopez main line reply to 3...a6


def test_theory_exit_via_detector_matches_book_directly(book: OpeningBook):
    game = parse_pgn_text(RUY_LOPEZ_MAIN_LINE)[0]
    moves = game.moves[:6]
    # Append a synthetic ParsedMove so detect_theory_exit's move-object bookkeeping
    # (exit_move_number, color_to_move) can be checked against a guaranteed deviation.
    from ingestion.pgn_parser import ParsedMove

    fake_move = ParsedMove(
        ply=7, move_number=4, color="white", san="ZZ-NOT-A-REAL-MOVE", uci="a1a1",
        fen_before="", fen_after="",
    )
    exit_result = detect_theory_exit(moves + [fake_move], book)
    assert exit_result is not None
    assert exit_result.exit_move_number == 4
    assert exit_result.color_to_move == "white"
    assert exit_result.played_move_san == "ZZ-NOT-A-REAL-MOVE"
    assert exit_result.expected_move_san == "Ba4"
    assert exit_result.opening.eco is not None  # opening was still identified from the matched prefix


def test_no_theory_exit_when_fully_in_book(book: OpeningBook):
    game = parse_pgn_text(RUY_LOPEZ_MAIN_LINE)[0]
    # Only the first 6 plies (1.e4 e5 2.Nf3 Nc6 3.Bb5 a6), a very well-known book line.
    exit_result = detect_theory_exit(game.moves[:6], book)
    assert exit_result is None


def test_no_theory_exit_when_reference_line_itself_is_shallow(book: OpeningBook):
    # 3...h6 here is catalogued only as a short, rare sideline ("Italian Game:
    # Anti-Fried Liver Defense") with no further recorded book continuation.
    # Once the game plays past the end of that short entry, there is no deeper
    # ECO line to compare against, so no specific "correct move" can be
    # reported -- this is a real limitation of a finite reference dataset,
    # not a bug in the matching algorithm.
    game = parse_pgn_text(ITALIAN_WITH_EARLY_H6)[0]
    exit_result = detect_theory_exit(game.moves, book)
    assert exit_result is None
