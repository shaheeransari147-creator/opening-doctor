"""Generates a prioritized daily study plan from a player's aggregated
opening statistics. This is deliberately rule-based (not LLM-generated):
the plan must always be available, even with no LLM API key configured, and
its inputs (weakest openings, most common mistakes) are already precise,
structured data -- there is nothing an LLM would add except phrasing.
"""
from __future__ import annotations

from dataclasses import dataclass

MISTAKE_DRILL_TEXT: dict[str, str] = {
    "early_queen_development": "Practice developing minor pieces before bringing the queen out",
    "delayed_castling": "Practice castling timing -- aim to castle by move 8-10",
    "premature_pawn_push": "Drill flank-pawn discipline: only push h/a/g/b pawns with a concrete reason",
    "ignored_center_control": "Practice central pawn breaks (d4/d5, e4/e5) in your main openings",
    "lost_tempo": "Review tempo-efficient development -- avoid moving the same piece twice early",
    "repeated_piece_moves": "One-move-per-piece drill: develop a new piece every move in the opening",
    "theory_deviation": "Review the theory exit points in your most-played openings",
}

MINUTES_FOR_RANK = [15, 10, 10]  # minutes allocated to the 1st, 2nd, 3rd weakest opening


@dataclass(slots=True)
class OpeningWeakness:
    opening: str
    games_played: int
    mistake_count: int
    avg_eval_loss: float


@dataclass(slots=True)
class RecurringMistake:
    mistake_type: str
    san: str | None
    occurrences: int
    avg_eval_loss: float


@dataclass(slots=True)
class StudyPlanItem:
    activity: str
    minutes: int
    priority: str  # "high" | "medium" | "low"
    reason: str


def generate_study_plan(
    weakest_openings: list[OpeningWeakness],
    recurring_mistakes: list[RecurringMistake],
    *,
    max_items: int = 6,
) -> list[StudyPlanItem]:
    items: list[StudyPlanItem] = []

    ranked_openings = sorted(weakest_openings, key=lambda w: (w.avg_eval_loss, -w.mistake_count))[:3]
    for i, weakness in enumerate(ranked_openings):
        minutes = MINUTES_FOR_RANK[i] if i < len(MINUTES_FOR_RANK) else 5
        items.append(
            StudyPlanItem(
                activity=f"Study {weakness.opening}",
                minutes=minutes,
                priority="high" if i == 0 else "medium",
                reason=(
                    f"Your weakest opening: {weakness.mistake_count} mistakes across "
                    f"{weakness.games_played} games, averaging {weakness.avg_eval_loss:+.2f} pawns lost."
                ),
            )
        )

    ranked_mistakes = sorted(recurring_mistakes, key=lambda m: m.occurrences, reverse=True)[:3]
    for mistake in ranked_mistakes:
        drill = MISTAKE_DRILL_TEXT.get(mistake.mistake_type, "Review this recurring mistake pattern")
        san_note = f" (you played {mistake.san})" if mistake.san else ""
        items.append(
            StudyPlanItem(
                activity=drill,
                minutes=10,
                priority="high" if mistake.occurrences >= 5 else "medium",
                reason=f"Recurring in {mistake.occurrences} games{san_note}, "
                f"averaging {mistake.avg_eval_loss:+.2f} pawns lost.",
            )
        )

    return items[:max_items]
