import pytest

from ingestion.pgn_parser import PgnParseError, parse_pgn_text

ITALIAN_GAME_PGN = """
[Event "Casual Game"]
[Site "?"]
[Date "2024.01.15"]
[Round "1"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 h6 4. d4 exd4 5. Nxd4 Bc5 6. Be3 Qf6 7. c3 Nge7
8. O-O O-O 9. Nb3 Bb6 10. Re1 d6 1-0
"""

TWO_GAME_PGN = ITALIAN_GAME_PGN + "\n" + ITALIAN_GAME_PGN.replace("Alice", "Carol").replace("Bob", "Dave")


def test_parses_single_game_headers_and_result():
    games = parse_pgn_text(ITALIAN_GAME_PGN)
    assert len(games) == 1
    game = games[0]
    assert game.white == "Alice"
    assert game.black == "Bob"
    assert game.result == "1-0"
    assert game.event == "Casual Game"


def test_parses_all_moves_with_fen_before_and_after():
    game = parse_pgn_text(ITALIAN_GAME_PGN)[0]
    assert game.ply_count == 20  # 10 full moves each side
    first = game.moves[0]
    assert first.san == "e4"
    assert first.color == "white"
    assert first.move_number == 1
    assert first.fen_before.startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w")
    assert "e4" not in first.fen_before  # sanity: piece placement field only, no move annotation
    assert first.fen_after.split(" ")[0] != first.fen_before.split(" ")[0]

    last = game.moves[-1]
    assert last.san == "d6"
    assert last.color == "black"
    assert last.move_number == 10


def test_ply_and_move_numbers_are_sequential():
    game = parse_pgn_text(ITALIAN_GAME_PGN)[0]
    for i, move in enumerate(game.moves, start=1):
        assert move.ply == i
        assert move.move_number == (i + 1) // 2
        assert move.color == ("white" if i % 2 == 1 else "black")


def test_parses_multiple_games_in_one_text():
    games = parse_pgn_text(TWO_GAME_PGN)
    assert len(games) == 2
    assert games[0].white == "Alice"
    assert games[1].white == "Carol"


def test_empty_text_raises():
    with pytest.raises(PgnParseError):
        parse_pgn_text("")


def test_garbage_text_raises():
    with pytest.raises(PgnParseError):
        parse_pgn_text("this is not a pgn file at all, just prose.")
