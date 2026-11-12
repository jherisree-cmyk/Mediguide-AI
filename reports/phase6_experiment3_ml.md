# Experiment 3: Decision Tree vs Random Forest urgency classifier (Phase 6)

## Setup
- **Data:** CDC NHAMCS ED 2016–2022. Label = nurse triage (Immediate/Emergent → EMERGENCY, Urgent → URGENT, Semi/Non-urgent → ROUTINE).
- **Rows used:** visits with ≥1 recognised symptom. Dev (2016–21) **61,388** rows; test (2022) **8,491** rows. Dropped because no recognised symptom: 12,553 dev and 1,716 test.
- **Features (66):** 62 symptom flags, age, pain known, pain score (0–10), number of symptoms. **No vital signs and no sex**: only what a patient can report at home. Training and the app share one feature module, and a test checks that they produce identical vectors.
- **Protocol:** stratified 5-fold CV on dev for tuning; thresholds chosen on out-of-fold dev predictions; the 2022 test split was evaluated once per final model; temporal split (no patient IDs exist).

## Cross-validation (dev, mean ± sd, 5 folds)
| Model | Best params | Macro-F1 | Emergency recall | Accuracy |
|---|---|---|---|---|
| Decision Tree (unrestricted) | depth None (36 reached), leaf 50, balanced | 0.519 ± 0.006 | 0.586 ± 0.009 | 0.539 ± 0.007 |
| **Decision Tree depth-6 (app)** | leaf 100, balanced, 49 leaves | **0.483 ± 0.005** | 0.558 ± 0.015 | 0.502 ± 0.006 |
| Random Forest (200 trees) | depth None, leaf 5, balanced | 0.543 ± 0.003 | 0.599 ± 0.006 | 0.564 ± 0.004 |

## 2022 test set
"EM≥U" = share of nurse-EMERGENCY visits given at least URGENT. "Under" = share of visits given a lower level than the nurse gave.

| System | Acc | Macro-F1 | EM recall | EM≥U | Under | Over |
|---|---|---|---|---|---|---|
| Majority class (always URGENT) | 0.548 | 0.236 | 0.000 | 1.000 | 0.162 | 0.290 |
| Decision Tree (argmax) | 0.526 | 0.515 | 0.601 | 0.853 | 0.209 | 0.265 |
| Random Forest (argmax) | 0.550 | 0.538 | 0.615 | 0.846 | 0.213 | 0.237 |
| Decision Tree depth-6 (argmax) | 0.495 | 0.486 | 0.595 | 0.786 | 0.247 | 0.258 |
| Rules + Random Forest (ML may say EMERGENCY) | 0.387 | 0.383 | 0.851 | 0.976 | 0.059 | 0.553 |
| **APP: rules + depth-6 DT, ML capped at URGENT** | **0.546** | **0.466** | **0.286** | **0.916** | **0.190** | **0.264** |

## Findings
1. **Accuracy is misleading here.** "Always URGENT" scores 0.548 accuracy, the same as the Random Forest. Macro-F1 shows the real gain: 0.236 → 0.538.
2. **Random Forest beats the Decision Tree** by about 0.02–0.06 macro-F1. Decision Tree depth 6 vs unrestricted costs about 0.04, in exchange for an explanation with at most 6 conditions.
3. **Self-reported features separate Routine from Urgent only weakly.** Catching more emergencies quickly sends almost everyone to URGENT (dev: threshold 0.45 → 93% of emergencies caught but 75% of routine visits sent to URGENT; 0.40 → 97% / 86%). The nurses' labels depend on information the app cannot collect, such as vital signs and how the patient looks.
4. **Most important features** (both models): age, then abdominal pain, shortness of breath, chest pain and limb/joint pain.
5. **Rules on NHAMCS find only 29% of emergencies.** This does NOT contradict Experiment 4 (34/34). NHAMCS has only coded reasons for visit: no warning-sign phrases ("pain spreading to arm", "blue lips"), no onset and no duration. So most rules cannot fire on this data.

## Design decisions (made with the project owner, 2026-11-10)
- **EMERGENCY only from the cited rules.** ML emergency precision is about 0.2–0.25 (dev out-of-fold and test). Telling users "call 112" on that basis would be wrong about 3 times in 4. The ML can raise a case to URGENT only, and flags a high emergency probability as "get seen today".
- **Depth-6 Decision Tree in the app**, chosen on dev CV for explainability.
- **URGENT threshold 0.45**, chosen on dev (target 90% recall for URGENT-or-higher). It was **kept after seeing the test result** to avoid tuning on the test set.

## Residual risk (must be stated in the report and the app)
On the 2022 test, the app policy gives **ROUTINE to 115 of 1,374 (8.4%) nurse-triaged emergencies**, and its URGENT-or-higher recall is 0.876 (dev target 0.90). Mitigations:
- every ROUTINE result shows explicit safety-netting ("go to A&E / call 112 if any of these appear");
- users confirm their symptoms, and an emergency checklist is asked;
- red-flag phrases that real users type (absent from NHAMCS) trigger the rules directly.

**None of this is clinical validation.** It is an educational prototype.

## Files
`scripts/train_models.py` · `models/dt_app_v1.joblib/.json` (app) · `models/dt_v1.*`, `models/rf_v1.*` (comparison) ·
`reports/phase6_results.json` · figures `reports/figures/p6_*.png`
