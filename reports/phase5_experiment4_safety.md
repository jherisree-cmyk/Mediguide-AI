# Experiment 4: Emergency warning detection (Phase 5)

**Pipeline tested:** free text (EN/TE/HI) → NLP extraction → red-flag rule engine.
**Data:** `data/synthetic/safety_cases.yaml`, 68 developer-written cases (36 EN, 16 TE, 16 HI):
34 emergency, 18 urgent, 12 routine and 4 not-understood. The routine and not-understood cases both expect "no rule".

## Results

| Run | Emergency recall | Emergency precision | Under-triaged | Over-triaged | Fully correct |
|---|---|---|---|---|---|
| **Blind run** | **34/34 (1.000)** | **34/34 (1.000)** | **2** | **0** | **66/68** |
| After fix | 34/34 | 34/34 | 0 | 0 | 68/68 (no longer blind) |

Blind-run confusion matrix (rows = expected):

|            | EMERGENCY | URGENT | NONE |
|---|---|---|---|
| EMERGENCY  | 34 | 0 | 0 |
| URGENT     | 0 | 16 | **2** |
| NONE       | 0 | 0 | 16 |

**The 2 under-triaged cases were both Hindi URGENT cases**, missed by text matching rather than by the rules:
- "सांस फूल**ती** है": a verb form missing from the vocabulary.
- "कमर में **बहुत तेज** दर्द": two inserted words, but the matcher allowed only one.

Fix: vocabulary variants, and up to two optional modifier words between phrase words (all languages).

## Safety properties verified by tests
- The `safety` package never imports ML code. An AST scan of every file enforces this.
- An unknown age never satisfies an age rule. An age from the user profile overrides one found in the text.
- Uncertain ("maybe") findings still count. Unknown onset of confusion is treated as sudden.
- Negated symptoms never fire a rule. The most urgent fired rule is listed first.
- Every emergency result carries the emergency numbers (112, 108, 14416), the source URLs and the quoted guidance.
- Unrecognised text is flagged (`understood = false`), so Phase 7 can route it to "seek assessment".

## What this does and does not show
- It shows that the rule engine **faithfully encodes the quoted NHS/WHO/NICE guidance** for these phrasings in three languages.
- It does **not** show clinical safety. The same developer wrote the rules, the vocabulary and the test cases, so the 100% recall is an upper bound. Real patient messages will contain phrasings that the vocabulary misses. That is why Phase 7 adds:
  1. user confirmation of the extracted symptoms;
  2. an explicit emergency checklist question when the text is not understood;
  3. a fallback that never gives a reassuring answer to unrecognised text.
