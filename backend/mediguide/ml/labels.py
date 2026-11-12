"""Urgency label definitions and the NHAMCS -> MediGuide label mapping.

NHAMCS variable IMMEDR = "Immediacy with which patient should be seen", assigned by the
triage nurse at the emergency department (official CDC value labels, read from the
public-use Stata files):

    1 Immediate | 2 Emergent | 3 Urgent | 4 Semi-urgent | 5 Nonurgent
    0 No triage for this visit | 7 ED does not conduct nursing triage | -8 Unknown | -9 Blank

PROJECT DESIGN DECISION (not a clinical validation):
    Immediate, Emergent   -> EMERGENCY  (should not wait)
    Urgent                -> URGENT     (prompt medical assessment)
    Semi-urgent, Nonurgent-> ROUTINE    (non-emergency consultation)
    0, 7, -8, -9          -> excluded   (no triage label exists for these visits)

There is deliberately NO "self-care" class: every NHAMCS patient was already in an
emergency department, so the data cannot teach when self-care is appropriate.
"""
from enum import IntEnum


class Urgency(IntEnum):
    """Ordered so that a larger value is MORE urgent (used by the safety combiner)."""
    ROUTINE = 0
    URGENT = 1
    EMERGENCY = 2


IMMEDR_TO_URGENCY: dict[int, Urgency] = {
    1: Urgency.EMERGENCY,
    2: Urgency.EMERGENCY,
    3: Urgency.URGENT,
    4: Urgency.ROUTINE,
    5: Urgency.ROUTINE,
}

IMMEDR_NAMES: dict[int, str] = {
    -9: "Blank", -8: "Unknown", 0: "No triage for this visit",
    1: "Immediate", 2: "Emergent", 3: "Urgent", 4: "Semi-urgent", 5: "Nonurgent",
    7: "ED does not triage",
}


def map_immedr(code: int) -> Urgency | None:
    """Return the MediGuide urgency for an NHAMCS IMMEDR code, or None if unlabeled."""
    return IMMEDR_TO_URGENCY.get(int(code))
