from rag.generation.study_plan import OpeningWeakness, RecurringMistake, generate_study_plan


def test_prioritizes_worst_opening_first():
    weaknesses = [
        OpeningWeakness(opening="French Defense", games_played=5, mistake_count=3, avg_eval_loss=-0.3),
        OpeningWeakness(opening="Italian Game", games_played=12, mistake_count=10, avg_eval_loss=-0.9),
    ]
    plan = generate_study_plan(weaknesses, [])
    assert plan[0].activity == "Study Italian Game"
    assert plan[0].minutes == 15
    assert plan[0].priority == "high"
    assert plan[1].activity == "Study French Defense"
    assert plan[1].minutes == 10


def test_includes_recurring_mistake_drills_with_known_text():
    mistakes = [
        RecurringMistake(mistake_type="premature_pawn_push", san="h6", occurrences=12, avg_eval_loss=-0.8),
        RecurringMistake(mistake_type="delayed_castling", san=None, occurrences=6, avg_eval_loss=-0.5),
    ]
    plan = generate_study_plan([], mistakes)
    assert any("flank-pawn" in item.activity.lower() for item in plan)
    assert any("castling" in item.activity.lower() for item in plan)
    assert all(item.priority == "high" for item in plan)  # both >= 5 occurrences


def test_low_occurrence_mistake_is_medium_priority():
    mistakes = [RecurringMistake(mistake_type="lost_tempo", san="Bd3", occurrences=2, avg_eval_loss=-0.5)]
    plan = generate_study_plan([], mistakes)
    assert plan[0].priority == "medium"


def test_respects_max_items_cap():
    weaknesses = [
        OpeningWeakness(opening=f"Opening {i}", games_played=1, mistake_count=1, avg_eval_loss=-0.1 * i)
        for i in range(1, 4)
    ]
    mistakes = [
        RecurringMistake(mistake_type="lost_tempo", san=None, occurrences=i, avg_eval_loss=-0.1)
        for i in range(1, 4)
    ]
    plan = generate_study_plan(weaknesses, mistakes, max_items=4)
    assert len(plan) == 4


def test_unknown_mistake_type_gets_generic_drill_text():
    mistakes = [RecurringMistake(mistake_type="something_new", san=None, occurrences=3, avg_eval_loss=-0.2)]
    plan = generate_study_plan([], mistakes)
    assert plan[0].activity == "Review this recurring mistake pattern"
