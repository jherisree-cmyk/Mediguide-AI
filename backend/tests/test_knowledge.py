"""Phase 2 tests: the knowledge files are valid, and the validator catches mistakes."""
import copy
import re

import pytest

from mediguide.knowledge import Concept, Rule, load_knowledge, validate_knowledge

TELUGU = re.compile(r"[ఀ-౿]")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


@pytest.fixture(scope="module")
def kb():
    return load_knowledge()


def test_knowledge_files_are_valid(kb):
    assert validate_knowledge(kb) == []


def test_every_language_term_is_in_the_right_script(kb):
    for c in kb.concepts.values():
        for t in c.terms["te"]:
            assert TELUGU.search(t), f"{c.id}: Telugu term not in Telugu script: {t}"
        for t in c.terms["hi"]:
            assert DEVANAGARI.search(t), f"{c.id}: Hindi term not in Devanagari: {t}"
        for t in c.terms["en"]:
            assert not (TELUGU.search(t) or DEVANAGARI.search(t)), f"{c.id}: English term has Indic script: {t}"


def test_every_emergency_rule_has_an_external_source(kb):
    for r in kb.rules:
        if r.level == "EMERGENCY":
            assert any(s != "project_policy" for s in r.sources), r.id


def test_core_emergencies_are_covered(kb):
    """The warning signs named in the project brief must each be covered by an EMERGENCY rule."""
    emergency_concepts = {
        cid for r in kb.rules if r.level == "EMERGENCY"
        for clause in r.match for key in ("all", "any") for cid in clause.get(key, [])
    }
    for required in ["severe_breathing_distress", "chest_pain", "focal_weakness", "speech_difficulty",
                     "unconsciousness", "heavy_bleeding", "face_throat_swelling", "seizure", "suicidal_thoughts"]:
        assert required in emergency_concepts, f"no emergency rule mentions {required}"


def test_emergency_contacts_present(kb):
    numbers = {c["number"] for c in kb.emergency_contacts}
    assert {"112", "108", "14416"} <= numbers


# ---- negative tests: prove the validator actually catches errors ----------------------

def _broken(kb):
    return copy.deepcopy(kb)


def test_validator_catches_unknown_concept_in_rule(kb):
    bad = _broken(kb)
    bad.rules.append(Rule("X", "EMERGENCY", "t", [{"any": ["chest_pian"]}], ["nhs_sob"], "q"))
    assert any("unknown concept 'chest_pian'" in p for p in validate_knowledge(bad))


def test_validator_catches_duplicate_term(kb):
    bad = _broken(kb)
    bad.concepts["dup"] = Concept("dup", "sign", {"en": "a", "te": "అ", "hi": "अ"},
                                  {"en": ["headache"], "te": ["అ"], "hi": ["अ"]})
    assert any("'headache'" in p and "both" in p for p in validate_knowledge(bad))


def test_validator_catches_missing_source_and_bad_level(kb):
    bad = _broken(kb)
    bad.rules.append(Rule("Y", "PANIC", "t", [{"any": ["fever"]}], ["made_up"], "q"))
    problems = validate_knowledge(bad)
    assert any("invalid level" in p for p in problems)
    assert any("unknown source 'made_up'" in p for p in problems)


def test_validator_catches_match_everything_clause(kb):
    bad = _broken(kb)
    bad.rules.append(Rule("Z", "URGENT", "t", [{"onset": "sudden"}], ["nhs_sob"], "q"))
    assert any("would match every input" in p for p in validate_knowledge(bad))
