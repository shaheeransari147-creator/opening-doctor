"""SQLAlchemy ORM models shared by the backend, ingestion, and seed scripts.

This module is intentionally framework-agnostic (no FastAPI imports) so it can
be reused by `ingestion/`, `database/seed/`, and `backend/app` alike.
"""
from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GameResult(str, enum.Enum):
    WHITE_WIN = "1-0"
    BLACK_WIN = "0-1"
    DRAW = "1/2-1/2"
    UNKNOWN = "*"


class Color(str, enum.Enum):
    WHITE = "white"
    BLACK = "black"


class GameSource(str, enum.Enum):
    UPLOAD = "upload"
    SEED = "seed"


class MistakeType(str, enum.Enum):
    EARLY_QUEEN_DEVELOPMENT = "early_queen_development"
    DELAYED_CASTLING = "delayed_castling"
    PREMATURE_PAWN_PUSH = "premature_pawn_push"
    IGNORED_CENTER_CONTROL = "ignored_center_control"
    LOST_TEMPO = "lost_tempo"
    REPEATED_PIECE_MOVES = "repeated_piece_moves"
    THEORY_DEVIATION = "theory_deviation"


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    fide_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (UniqueConstraint("name", "fide_id", name="uq_player_name_fide"),)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    white_player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    black_player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))

    event: Mapped[str | None] = mapped_column(String(255), nullable=True)
    site: Mapped[str | None] = mapped_column(String(255), nullable=True)
    round: Mapped[str | None] = mapped_column(String(32), nullable=True)
    game_date: Mapped[dt.date | None] = mapped_column(nullable=True)
    result: Mapped[GameResult] = mapped_column(Enum(GameResult), default=GameResult.UNKNOWN)

    eco_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    opening_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    opening_variation: Mapped[str | None] = mapped_column(String(255), nullable=True)

    tracked_player_color: Mapped[Color | None] = mapped_column(Enum(Color), nullable=True)

    pgn_raw: Mapped[str] = mapped_column(Text)
    source: Mapped[GameSource] = mapped_column(Enum(GameSource), default=GameSource.UPLOAD)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))

    white_player: Mapped[Player] = relationship(foreign_keys=[white_player_id])
    black_player: Mapped[Player] = relationship(foreign_keys=[black_player_id])
    moves: Mapped[list["Move"]] = relationship(back_populates="game", cascade="all, delete-orphan", order_by="Move.ply")
    mistakes: Mapped[list["Mistake"]] = relationship(back_populates="game", cascade="all, delete-orphan")
    theory_exit: Mapped["TheoryExit | None"] = relationship(back_populates="game", cascade="all, delete-orphan", uselist=False)


class Move(Base):
    __tablename__ = "moves"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)

    ply: Mapped[int] = mapped_column(Integer)  # 1-indexed half-move count
    move_number: Mapped[int] = mapped_column(Integer)  # full move number, as in PGN
    color: Mapped[Color] = mapped_column(Enum(Color))

    san: Mapped[str] = mapped_column(String(16))
    uci: Mapped[str] = mapped_column(String(8))
    fen_before: Mapped[str] = mapped_column(String(100))
    fen_after: Mapped[str] = mapped_column(String(100))

    is_book_move: Mapped[bool] = mapped_column(Boolean, default=False)

    game: Mapped[Game] = relationship(back_populates="moves")

    __table_args__ = (UniqueConstraint("game_id", "ply", name="uq_move_game_ply"),)


class TheoryExit(Base):
    """Records where a game first left known opening theory."""

    __tablename__ = "theory_exits"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), unique=True)

    exit_ply: Mapped[int] = mapped_column(Integer)
    exit_move_number: Mapped[int] = mapped_column(Integer)
    color_to_move: Mapped[Color] = mapped_column(Enum(Color))

    eco_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    opening_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_variation: Mapped[str | None] = mapped_column(String(255), nullable=True)

    expected_move_san: Mapped[str | None] = mapped_column(String(16), nullable=True)
    played_move_san: Mapped[str | None] = mapped_column(String(16), nullable=True)

    game: Mapped[Game] = relationship(back_populates="theory_exit")


class Mistake(Base):
    __tablename__ = "mistakes"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    move_id: Mapped[int | None] = mapped_column(ForeignKey("moves.id", ondelete="SET NULL"), nullable=True)

    mistake_type: Mapped[MistakeType] = mapped_column(Enum(MistakeType), index=True)
    color: Mapped[Color] = mapped_column(Enum(Color))
    move_number: Mapped[int] = mapped_column(Integer)
    ply: Mapped[int] = mapped_column(Integer)
    san: Mapped[str] = mapped_column(String(16))

    description: Mapped[str] = mapped_column(Text)
    eval_loss: Mapped[float] = mapped_column(Float)  # heuristic severity, in "pawns"

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))

    game: Mapped[Game] = relationship(back_populates="mistakes")


class OpeningBookEntry(Base):
    """Reference opening theory database (imported from the lichess ECO dataset)."""

    __tablename__ = "opening_book_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    eco: Mapped[str] = mapped_column(String(8), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    pgn_moves: Mapped[str] = mapped_column(Text)  # e.g. "1. e4 e5 2. Nf3 Nc6"
    san_moves_json: Mapped[str] = mapped_column(Text)  # JSON list of SAN moves, e.g. ["e4","e5","Nf3","Nc6"]
    ply_count: Mapped[int] = mapped_column(Integer)
    final_fen: Mapped[str] = mapped_column(String(100), index=True)

    __table_args__ = (UniqueConstraint("eco", "name", name="uq_opening_book_eco_name"),)


class KbSource(Base):
    """Tracks knowledge-base documents that have been chunked and ingested into Qdrant."""

    __tablename__ = "kb_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True)
    opening: Mapped[str] = mapped_column(String(255))
    eco: Mapped[str | None] = mapped_column(String(8), nullable=True)
    checksum: Mapped[str] = mapped_column(String(64))
    chunk_count: Mapped[int] = mapped_column(Integer)
    ingested_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))
