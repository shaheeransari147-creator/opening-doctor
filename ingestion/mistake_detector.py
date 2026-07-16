"""Detects recurring opening-phase mistakes in a played game.

This module intentionally does NOT depend on a chess engine (none is part of
this project's stack). Instead it applies well-known opening principles as
deterministic heuristics, and produces a heuristic "severity" score (in a
pawn-like unit) so that mistakes can be ranked and averaged. This is a
teaching heuristic, not an engine centipawn evaluation -- see docs/ARCHITECTURE.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import chess

from ingestion.pgn_parser import ParsedMove

OPENING_PHASE_MOVE_LIMIT = 15  # full moves; mistakes are only scored within this window
QUEEN_DEV_DEADLINE = 6
CASTLING_DEADLINE = 10
CENTER_CONTROL_DEADLINE = 6
FLANK_PAWN_DEADLINE = 6

_HOME_SQUARES = {"white": {"queen": chess.D1}, "black": {"queen": chess.D8}}
_CENTER_PAWN_FILES = {"d", "e"}
_FLANK_PAWN_SQUARES = {"h3", "h6", "a3", "a6", "g4", "b4", "g5", "b5"}


@dataclass(slots=True)
class DetectedMistake:
    mistake_type: str
    color: str
    ply: int
    move_number: int
    san: str
    description: str
    eval_loss: float


def _is_center_pawn_move(san: str) -> bool:
    """True for any pawn move (push or capture) landing on the d- or e-file,
    e.g. "e4", "d4", "exd5", "dxe5" -- but not piece moves like "Be4".
    """
    core = san.rstrip("+#").split("=")[0]
    if not core or core[0] not in "abcdefgh":
        return False  # piece moves start with N/B/R/Q/K/O, not a file letter
    dest_square = core[-2:]
    return len(dest_square) == 2 and dest_square[0] in ("d", "e") and dest_square[1].isdigit()


def _attacks_enemy_piece(board_before: chess.Board, move: chess.Move, mover_is_white: bool) -> bool:
    """True if, after this move, the moved piece attacks at least one enemy piece
    (i.e. the move has a concrete tactical point rather than being "random").
    """
    temp = board_before.copy(stack=False)
    temp.push(move)
    attacked_squares = temp.attacks(move.to_square)
    opponent_pieces = temp.occupied_co[not mover_is_white]
    return bool(attacked_squares & opponent_pieces)


class _PieceTracker:
    """Tracks stable piece identities (keyed by their starting square) across a game,
    so that "the same piece moved again" can be detected reliably.
    """

    def __init__(self) -> None:
        board = chess.Board()
        self.square_to_id: dict[int, str] = {
            square: chess.square_name(square) for square in board.piece_map()
        }

    def apply(self, board_before: chess.Board, move: chess.Move) -> str:
        moving_id = self.square_to_id.get(move.from_square, f"unknown@{chess.square_name(move.from_square)}")

        if board_before.is_en_passant(move):
            captured_square = move.to_square + (-8 if board_before.turn == chess.WHITE else 8)
            self.square_to_id.pop(captured_square, None)
        elif board_before.is_capture(move):
            self.square_to_id.pop(move.to_square, None)

        self.square_to_id.pop(move.from_square, None)
        self.square_to_id[move.to_square] = moving_id

        if board_before.is_castling(move):
            white = board_before.turn == chess.WHITE
            kingside = board_before.is_kingside_castling(move)
            rook_from = chess.square(7 if kingside else 0, 0 if white else 7)
            rook_to = chess.square(5 if kingside else 3, 0 if white else 7)
            rook_id = self.square_to_id.pop(rook_from, None)
            if rook_id:
                self.square_to_id[rook_to] = rook_id

        return moving_id


def detect_mistakes(moves: list[ParsedMove], color: str) -> list[DetectedMistake]:
    """Runs all heuristic opening-mistake rules for one color's moves in a single game."""
    mistakes: list[DetectedMistake] = []

    board = chess.Board()
    tracker = _PieceTracker()
    # Seeded with each piece's own starting square, so that shuffling a piece
    # back to where it began also counts as a "revisit".
    piece_visited_squares: dict[str, set[int]] = {
        piece_id: {square} for square, piece_id in tracker.square_to_id.items()
    }
    has_castled = False
    center_pawn_moved = False

    own_move_index = 0  # index among this color's own moves only (0-indexed)
    mover_is_white = color == "white"

    for parsed_move in moves:
        move = chess.Move.from_uci(parsed_move.uci)
        is_own_move = parsed_move.color == color

        if is_own_move:
            own_move_index += 1
            piece_id = tracker.apply(board, move)
            visited = piece_visited_squares.setdefault(piece_id, set())

            # --- Rule: same piece shuffled back to a square it already occupied ---
            if move.to_square in visited and parsed_move.move_number <= OPENING_PHASE_MOVE_LIMIT:
                mistakes.append(
                    DetectedMistake(
                        mistake_type="repeated_piece_moves",
                        color=color,
                        ply=parsed_move.ply,
                        move_number=parsed_move.move_number,
                        san=parsed_move.san,
                        description=(
                            f"The piece originally on {piece_id} returned to {chess.square_name(move.to_square)} "
                            f"with {parsed_move.san}, a square it had already occupied earlier in the game. "
                            "Shuffling the same piece back and forth wastes tempi that should go toward "
                            "developing new pieces."
                        ),
                        eval_loss=-0.4,
                    )
                )
            visited.add(move.to_square)

            if parsed_move.san in ("O-O", "O-O-O"):
                has_castled = True

            if parsed_move.move_number <= CENTER_CONTROL_DEADLINE and _is_center_pawn_move(parsed_move.san):
                center_pawn_moved = True

            # --- Rule: early queen development ---
            queen_home = _HOME_SQUARES[color]["queen"]
            if parsed_move.san.startswith("Q") and move.from_square == queen_home and parsed_move.move_number <= QUEEN_DEV_DEADLINE:
                mistakes.append(
                    DetectedMistake(
                        mistake_type="early_queen_development",
                        color=color,
                        ply=parsed_move.ply,
                        move_number=parsed_move.move_number,
                        san=parsed_move.san,
                        description=(
                            f"Developed the queen with {parsed_move.san} on move {parsed_move.move_number}, "
                            "well before minor pieces and king safety are addressed. Early queen sorties "
                            "waste tempi once the opponent develops with gain of tempo (attacking the queen)."
                        ),
                        eval_loss=round(-0.3 - 0.1 * max(0, QUEEN_DEV_DEADLINE - parsed_move.move_number), 2),
                    )
                )

            # --- Rule: premature flank pawn push ---
            if (
                parsed_move.move_number <= FLANK_PAWN_DEADLINE
                and parsed_move.san in _FLANK_PAWN_SQUARES
                and "x" not in parsed_move.san
                and not _attacks_enemy_piece(board, move, mover_is_white)
            ):
                mistakes.append(
                    DetectedMistake(
                        mistake_type="premature_pawn_push",
                        color=color,
                        ply=parsed_move.ply,
                        move_number=parsed_move.move_number,
                        san=parsed_move.san,
                        description=(
                            f"Played the flank pawn move {parsed_move.san} on move {parsed_move.move_number} "
                            "without a concrete tactical reason. This weakens king-side/queen-side squares "
                            "before development is complete and rarely helps in the opening."
                        ),
                        eval_loss=-0.4,
                    )
                )

        board.push(move)

    # Lost-tempo detection needs the sequence of (piece_id per own move), which is
    # simplest to compute as its own dedicated pass over the game.
    mistakes.extend(_detect_lost_tempo(moves, color))

    # --- Rule: delayed castling (evaluated once, at the deadline) ---
    if not has_castled:
        deadline_move = next(
            (m for m in moves if m.color == color and m.move_number == CASTLING_DEADLINE),
            None,
        )
        last_move = next((m for m in reversed(moves) if m.color == color), None)
        anchor = deadline_move or last_move
        if anchor is not None and anchor.move_number >= CASTLING_DEADLINE - 2:
            mistakes.append(
                DetectedMistake(
                    mistake_type="delayed_castling",
                    color=color,
                    ply=anchor.ply,
                    move_number=anchor.move_number,
                    san=anchor.san,
                    description=(
                        f"King has not castled by move {anchor.move_number}. Delaying castling leaves the "
                        "king in the center and exposed to open lines and piece activity."
                    ),
                    eval_loss=-0.5,
                )
            )

    # --- Rule: ignoring center control ---
    if not center_pawn_moved:
        anchor = next(
            (m for m in moves if m.color == color and m.move_number == CENTER_CONTROL_DEADLINE),
            None,
        ) or next((m for m in reversed(moves) if m.color == color), None)
        if anchor is not None:
            mistakes.append(
                DetectedMistake(
                    mistake_type="ignored_center_control",
                    color=color,
                    ply=anchor.ply,
                    move_number=anchor.move_number,
                    san=anchor.san,
                    description=(
                        f"Neither central pawn (d- or e-file) has been advanced by move {anchor.move_number}. "
                        "Failing to contest the center allows the opponent a free hand to build a "
                        "space advantage."
                    ),
                    eval_loss=-0.6,
                )
            )

    return mistakes


def _detect_lost_tempo(moves: list[ParsedMove], color: str) -> list[DetectedMistake]:
    """Flags a piece moving twice in a row on the player's own two consecutive
    moves (i.e. no developing move in between), outside of check/capture/castling.
    """
    results: list[DetectedMistake] = []
    board = chess.Board()
    tracker = _PieceTracker()
    last_own_piece_id: str | None = None
    last_own_move_index_in_game = -10

    for idx, parsed_move in enumerate(moves):
        move = chess.Move.from_uci(parsed_move.uci)
        was_check_before = board.is_check()

        if parsed_move.color == color:
            is_capture = "x" in parsed_move.san
            is_castle = parsed_move.san in ("O-O", "O-O-O")
            consecutive = idx - last_own_move_index_in_game == 2  # no opponent move skipped, i.e. directly consecutive own moves
            opponent_color = chess.BLACK if color == "white" else chess.WHITE
            was_attacked = board.is_attacked_by(opponent_color, move.from_square)

            moved_id = tracker.apply(board, move)

            if (
                consecutive
                and moved_id == last_own_piece_id
                and not is_capture
                and not is_castle
                and not was_check_before
                and not was_attacked
                and parsed_move.move_number <= OPENING_PHASE_MOVE_LIMIT
            ):
                results.append(
                    DetectedMistake(
                        mistake_type="lost_tempo",
                        color=color,
                        ply=parsed_move.ply,
                        move_number=parsed_move.move_number,
                        san=parsed_move.san,
                        description=(
                            f"Moved the same piece again with {parsed_move.san} right after its previous move, "
                            "without being forced to. This loses a tempo that could have developed a new piece."
                        ),
                        eval_loss=-0.5,
                    )
                )

            last_own_piece_id = moved_id
            last_own_move_index_in_game = idx
        else:
            tracker.apply(board, move)

        board.push(move)

    return results
