# Experiment 5: Follow-up questions and the complete assessment (Phase 7)

## Design
**Questions are derived from the safety rules**, not hand-written per symptom. For every rule that is
more urgent than the current result *and* already partly matches the case, the app asks only for what
that rule still needs:

| Rule needs | Question |
|---|---|
| a missing concept (e.g. `radiating_pain`) | one checklist: "Do you also have any of these?" |
| `onset: sudden` | "Did the chest pain start suddenly or gradually?" |
| `severity: severe` | 0–10 pain/discomfort score |
| `min_duration_days` | "How long have you had the fever?" |
| `context: pregnant` | "Is the person pregnant?" (only if plausible: not male, age 10–55) |
| `max_age_months`, model input | age (if unknown) |

So when a rule changes, the questions change with it. Clauses already ruled out by the user's answers
(e.g. pain 3/10 → a "severe" clause cannot match) produce no question.

**Final level = the more urgent of (red-flag rules, depth-6 Decision Tree capped at URGENT).**

| Situation | Behaviour |
|---|---|
| Emergency found | Result immediately: no questions, no ML, emergency numbers shown |
| Nothing understood | Emergency-sign checklist. If still nothing → URGENT + "we could not understand" |
| Age unknown after questions | Model cannot run → at least URGENT, with an explanation |
| URGENT / ROUTINE | Safety-netting list ("call 112/108 if…"); ROUTINE also gets self-care information (no treatment advice) |
| Suicidal thoughts / hallucinations / low mood | Tele-MANAS 14416 support text |

All user-facing text comes from `knowledge/templates.yaml` (EN/TE/HI). It is never machine-translated
at runtime.

## Results (first run, synthetic cases in `data/synthetic/followup_cases.yaml`)

| Part | Cases | Correct |
|---|---|---|
| A. Right questions asked / unnecessary questions avoided | 18 (EN 14, TE 1, HI 3) | **18/18** |
| B. End-to-end assessment after answers | 10 | **10/10** |

The checks include: no questions on emergencies (F02, F03, F07, F15, F17); no duration question when
the duration is known (F05); no pregnancy question for a 70-year-old (F12); no onset or pain question
when the pain is already 3/10 (F16); Telugu and Hindi questions in the right script.

## Tested safety guarantees
- ML cannot lower a rule level (chest pain, age 19, pain 2/10 → still URGENT).
- An emergency never waits for questions or ML.
- Unclear input is never reassuring.
- Every non-emergency result has safety-netting. Emergency results have no self-care text.
- The disclaimer is always present. Every rule title is translated.

## Limitations
- Only one round of questions (simple, predictable). Answers do not trigger a second round.
- Pain answers are applied to all reported symptoms (conservative simplification).
- The cases test software behaviour, not whether patients understand the questions. That needs user testing.
