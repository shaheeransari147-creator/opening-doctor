"""Loads the ECO opening reference database (lichess-org/chess-openings dataset,
MIT licensed) into an in-memory trie for fast prefix matching against played games.

Each row of the TSV files looks like:
    eco   name                              pgn
    C50   Italian Game                      1. e4 e5 2. Nf3 Nc6 3. Bc4

We index every book line by its SAN move sequence so that, given a played
game's moves, we can find the longest known book continuation in O(number of
played moves) time, regardless of how many thousand reference lines exist.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

_MOVE_NUMBER_RE = re.compile(r"^\d+\.(\.\.)?$")

DEFAULT_ECO_DIR = Path(__file__).resolve().parents[1] / "database" / "seed" / "eco"


@dataclass(slots=True)
class OpeningEntry:
    eco: str
    name: str
    moves: tuple[str, ...]

    @property
    def family(self) -> str:
        return self.name.split(":", 1)[0].strip()

    @property
    def variation(self) -> str | None:
        parts = self.name.split(":", 1)
        return parts[1].strip() if len(parts) > 1 else None


@dataclass(slots=True)
class _TrieNode:
    children: dict[str, "_TrieNode"] = field(default_factory=dict)
    entry: OpeningEntry | None = None
    descendant_leaves: int = 0


def _tokenize_pgn_moves(pgn_moves: str) -> tuple[str, ...]:
    """Turns '1. e4 e5 2. Nf3 Nc6' into ('e4', 'e5', 'Nf3', 'Nc6')."""
    tokens = pgn_moves.replace("...", " ").split()
    return tuple(tok for tok in tokens if not _MOVE_NUMBER_RE.match(tok))


@dataclass(slots=True)
class OpeningMatch:
    entry: OpeningEntry | None
    matched_ply: int  # how many played moves matched this entry's line (0 if no match at all)


@dataclass(slots=True)
class TheoryExitResult:
    exit_ply: int  # 1-indexed ply of the first move that deviates from all book lines
    expected_move_san: str | None  # main-line continuation the book suggests (None if book is exhausted)
    played_move_san: str


class OpeningBook:
    """An in-memory trie of known opening lines, for O(depth) prefix matching."""

    def __init__(self) -> None:
        self._root = _TrieNode()
        self._entries: list[OpeningEntry] = []

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> tuple[OpeningEntry, ...]:
        return tuple(self._entries)

    def add_entry(self, entry: OpeningEntry) -> None:
        node = self._root
        for move in entry.moves:
            node = node.children.setdefault(move, _TrieNode())
        node.entry = entry
        self._entries.append(entry)

    def _finalize_leaf_counts(self) -> None:
        def visit(node: _TrieNode) -> int:
            count = 1 if node.entry is not None else 0
            for child in node.children.values():
                count += visit(child)
            node.descendant_leaves = count
            return count

        visit(self._root)

    @classmethod
    def load_from_tsv_dir(cls, directory: Path = DEFAULT_ECO_DIR) -> "OpeningBook":
        book = cls()
        tsv_files = sorted(directory.glob("*.tsv"))
        if not tsv_files:
            raise FileNotFoundError(f"No ECO .tsv files found in {directory}")

        for path in tsv_files:
            with path.open(encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                for row in reader:
                    moves = _tokenize_pgn_moves(row["pgn"])
                    if not moves:
                        continue
                    book.add_entry(OpeningEntry(eco=row["eco"], name=row["name"], moves=moves))

        book._finalize_leaf_counts()
        return book

    def match(self, played_san_moves: list[str] | tuple[str, ...]) -> OpeningMatch:
        """Finds the deepest named book entry reached by following `played_san_moves`."""
        node = self._root
        best_entry: OpeningEntry | None = None
        matched_ply = 0

        for i, move in enumerate(played_san_moves):
            child = node.children.get(move)
            if child is None:
                break
            node = child
            if node.entry is not None:
                best_entry = node.entry
                matched_ply = i + 1

        return OpeningMatch(entry=best_entry, matched_ply=matched_ply)

    def find_theory_exit(self, played_san_moves: list[str] | tuple[str, ...]) -> TheoryExitResult | None:
        """Finds the first ply where the played game deviates from every known book line.

        Returns None if the entire game stayed within the reference book (e.g. a very
        short game), or if the first move itself isn't in the book at all (also None,
        since there is nothing to "exit" from).
        """
        node = self._root

        for i, move in enumerate(played_san_moves):
            if not node.children:
                # Ran past the deepest known continuation for this exact line.
                return None

            child = node.children.get(move)
            if child is not None:
                node = child
                continue

            # `move` deviates from every known continuation at this point.
            expected = self._main_line_continuation(node)
            return TheoryExitResult(exit_ply=i + 1, expected_move_san=expected, played_move_san=move)

        return None

    @staticmethod
    def _main_line_continuation(node: "_TrieNode") -> str | None:
        """Picks the most heavily represented next move at a trie node (a proxy for 'main line')."""
        if not node.children:
            return None
        return max(node.children.items(), key=lambda kv: kv[1].descendant_leaves)[0]


_default_book: OpeningBook | None = None


def get_default_book() -> OpeningBook:
    global _default_book
    if _default_book is None:
        _default_book = OpeningBook.load_from_tsv_dir()
    return _default_book
