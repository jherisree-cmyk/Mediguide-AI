# Testing and evaluation

**Software test results are not clinical safety or effectiveness results.**
All text-based experiments use synthetic, developer-written sentences. Only Experiment 3 uses real patient data
(CDC NHAMCS emergency-department triage decisions).

## Method used throughout
For each NLP experiment there are two sets:
- **Development set:** used to find errors and fix them, so its scores after fixing are inflated.
- **Held-out set:** written *after* the fixes and scored **once**. **That blind run is the reported result.**

Re-runs after later fixes are shown for transparency, but are labelled "not blind".

## Summary

| # | Experiment | Data | Blind result | After fixes (not blind) | Report |
|---|---|---|---|---|---|
| 1 | English symptom extraction | dev 47 / held-out 30 sentences | P 0.953, R 0.911, **F1 0.932**; negation 5/6; 86.7% exact | F1 0.989; 29/30 | [phase3](../reports/phase3_experiment1_extraction.md) |
| 2 | Telugu / Hindi extraction | dev 36+36 / held-out 20+20 | TE **F1 1.000** (20/20) · HI **F1 0.936** (15/20) | HI 20/20 | [phase4](../reports/phase4_experiment2_multilingual.md) |
| 3 | Decision Tree vs Random Forest | NHAMCS dev 61,388 / test 8,491 | DT **0.515**, RF **0.538**, depth-6 DT 0.486 macro-F1 (baseline 0.236) | n/a (test used once) | [phase6](../reports/phase6_experiment3_ml.md) |
| 3b | App policy (rules + depth-6 DT, capped at URGENT) | NHAMCS 2022 test | **91.6%** of emergencies ≥ Urgent; under-triage 19.0% | n/a | same |
| 4 | Emergency warning detection | 68 cases (36 EN, 16 TE, 16 HI) | Emergency recall **34/34**; 2 under-triaged URGENT (HI) | 68/68 | [phase5](../reports/phase5_experiment4_safety.md) |
| 5 | Follow-up questions + end-to-end | 18 + 10 cases | **28/28** | n/a | [phase7](../reports/phase7_experiment5_followup.md) |
| 6 | Application testing | automated | **329** pytest · **19** Vitest · **9/9** browser steps (browser run before Phase 12) | n/a | [backend](backend.md) · [frontend](frontend.md) |

## Experiment 6 coverage (application)

| Area | Where it is tested |
|---|---|
| Registration, login, logout, cookie flags, password hashing, rate limiting | `backend/tests/test_api.py`, browser step 7 |
| Symptom submission, follow-up, results (EN/TE/HI, desktop + mobile) | `test_api.py`, `components.test.jsx`, browser steps 3–6 |
| Language selection | `components.test.jsx`, browser step 2 |
| History, deletion of item / all / account | `test_api.py`, browser step 7 |
| Access control (other users, admin escalation, admin page) | `test_api.py`, browser step 8 |
| Privacy (encryption at rest, purge of pending data, no text for admins, no health data in browser storage) | `test_api.py`, `components.test.jsx`, browser step 8 |
| Accessibility (icon + text urgency, skip link, labels) | `components.test.jsx`, browser step 9 |

## Bugs found by testing (all fixed)

| Phase | Bug | How it was found | Why it mattered |
|---|---|---|---|
| 1 | `Urgency.ROUTINE == 0` is falsy, so `u and u.name` mislabelled routine visits | Code review + unit test | Silent label corruption |
| 1 | pandas 3 `stack()` keeps NaN, so the symptom share was reported as 37.5% instead of 74.1% | Implausible number | Wrong data analysis |
| 3 | Inserted words ("can't move my **left** arm") broke phrase matching | Held-out set | **Missed stroke sign** |
| 3 | Duplicate YAML key silently dropped a setting | Debugging a test | Could silently delete a safety rule. YAML loader now rejects duplicates |
| 4 | Hindi inflections (दिख**ने**) and inserted particles (ठंड **भी**) not matched | Held-out set | Missed symptoms |
| 5 | Two inserted words (कमर में **बहुत तेज** दर्द) not matched | Blind safety run | **Under-triage** |
| 6 | Reported "97%" emergencies ≥ Urgent belonged to a different model setup; the correct figure is 91.6% | Re-checking results before reporting | A design decision was based on the wrong number; corrected with the user |
| 8 | Expired pending assessments not purged (transaction rolled back by the 404) | API test written for the privacy promise | Encrypted text kept longer than promised |
| 9 | After answering the questions, users were sent back to the start page | Component test | Broken main flow |
| 9 | Five labels truncated by unquoted YAML commas (cyanosis shown as "Blue") | Browser screenshot | Incomplete warning-sign names in emergency checklists |
| 9 | First Tab skipped the skip link (focus moved on first load; React StrictMode double effect) | Browser test | Keyboard accessibility |
| 12 | Telugu "ఊపిరి ఆడటం లేదు" ("I can't breathe") was mapped to *unconscious* instead of *severe breathing difficulty* | Live symptom detection showed the wrong chip | Wrong warning sign shown (level was still Emergency) |

## Known limitations of the testing
- One person wrote the vocabulary, the rules and the test sentences. Independent native-speaker test sets are the most important next step.
- The test sets are small (20–68 cases), so one error moves a percentage by several points.
- No usability testing with real patients has been done.
- The NHAMCS labels are US nurse triage decisions made with information the app does not have (vital signs, the patient's appearance).
