"""Phase 1 tests: NHAMCS triage code -> MediGuide urgency mapping."""
from mediguide.ml.labels import Urgency, map_immedr


def test_emergency_codes():
    assert map_immedr(1) is Urgency.EMERGENCY  # Immediate
    assert map_immedr(2) is Urgency.EMERGENCY  # Emergent


def test_urgent_and_routine_codes():
    assert map_immedr(3) is Urgency.URGENT
    assert map_immedr(4) is Urgency.ROUTINE
    assert map_immedr(5) is Urgency.ROUTINE


def test_unlabeled_codes_are_excluded():
    for code in (-9, -8, 0, 7):
        assert map_immedr(code) is None


def test_routine_is_not_confused_with_missing():
    # ROUTINE has value 0 (falsy) - it must still be distinguishable from None.
    assert map_immedr(4) is not None


def test_ordering_supports_most_urgent_wins():
    assert max(Urgency.ROUTINE, Urgency.EMERGENCY) is Urgency.EMERGENCY
    assert Urgency.ROUTINE < Urgency.URGENT < Urgency.EMERGENCY
