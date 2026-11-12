# Experiment 1: English symptom extraction (Phase 3)

**Setup.** A rule-based extractor (spaCy token matcher + NegEx-style negation + regex attributes)
was scored on hand-written synthetic sentences. This measures *software behaviour*, not clinical accuracy.

| Set | Cases | Purpose |
|---|---|---|
| `data/synthetic/en_extraction_dev.yaml` | 47 | Error analysis and fixing (the system was tuned on it) |
| `data/synthetic/en_extraction_heldout.yaml` | 30 | Written after the fixes and scored **once** |

## Results

| Run | Precision | Recall | F1 | Negation | Attributes | Exact cases |
|---|---|---|---|---|---|---|
| Dev, baseline | 0.966 | 0.851 | 0.905 | 15/15 | 17/24 | 32/47 (68.1%) |
| Dev, after fixes | 1.000 | 1.000 | 1.000 | 15/15 | 24/24 | 47/47 (tuned, so not a fair estimate) |
| **Held-out, first and only blind run** | **0.953** | **0.911** | **0.932** | **5/6** | **9/11** | **26/30 (86.7%)** |
| Held-out after a 2nd fix round | 0.978 | 1.000 | 0.989 | 5/6 | 11/11 | 29/30 (no longer blind) |

**Report the bold row as the result.** The later rows are shown for transparency only.

## Error analysis

| Error type | Example | Fix |
|---|---|---|
| Vocabulary gaps / word order | "my speech is slurred", "lips are swollen", "killing myself" | Added variants to `symptoms.yaml` |
| Inserted words break exact phrases | "can't move my **left** arm", "lower stomach" | Phrases allow an optional side/position word between their words |
| Negation reaching too far | "no headache…, **only** a cough" | Added "only"/"just" as negation terminators |
| Negated severity | "**not** severe" counted as severe | A severity word right after a negation word is ignored |
| Duration phrasing | "it has been 3 days", "for the last week" | Two new regex patterns |
| Durations stated in their own sentence | "Headache. Dizzy. Since this morning." | Applied to all earlier symptoms without a duration |
| **Silent config bug** | Duplicate `en:` key in YAML deleted the modifier list without any error | YAML loader now **rejects duplicate keys** (protects `red_flags.yaml` too) |

## Known limitations
- Raised negation: in "I **don't think** I have a fever" the fever is kept as present. It is flagged as uncertain, so the user is asked to confirm. This errs on the safe side.
- Matching is lexicon-based. Phrasings that are not in the vocabulary are missed. The user-confirmation step and the fallback rule ("not understood → seek assessment", Phase 7) cover this.
- The test sentences were written by the developer, not by patients. Real patient language is messier, so expect lower real-world performance.
