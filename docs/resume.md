# MediGuide AI: resume and interview material

## Resume entry (pick 3–5 bullets)

**MediGuide AI: Multilingual Symptom Urgency Guidance (English, Telugu, Hindi)** · Python, spaCy, scikit-learn, FastAPI, React

- Built a full-stack triage-guidance prototype that turns free-text symptom descriptions in **English, Telugu, Hindi and code-mixed text** into Emergency / Urgent / Routine recommendations, with plain-language explanations in the user's language.
- Designed a **safety-first architecture**: 27 red-flag rules, each citing NHS/NICE/WHO guidance, decide emergencies independently of ML (enforced by an AST test). The ML model can only raise urgency; **34/34 emergency cases** were detected in a blind test across three languages.
- Built a rule-based NLP pipeline (spaCy Matcher, NegEx-style negation, Telugu suffix handling, Hindi normalisation) with **no machine translation in the safety path**. It reached **F1 0.932 (English) and 0.936 (Hindi)** on blind held-out sets.
- Trained and compared **Decision Tree vs Random Forest** on **84,148 real CDC emergency-department triage records** with a temporal hold-out (macro-F1 0.515 vs 0.538, against a 0.236 baseline). Deployed an explainable depth-6 tree whose decision path is shown to users.
- Added **voice input and read-aloud** in all three languages, **live symptom detection while typing** (stateless endpoint), a downloadable **summary for a doctor**, a nearby-care link and a dark mode.
- Generated follow-up questions **automatically from the safety rules**, so the app asks only what can change the outcome and never delays emergencies (28/28 test cases).
- Secured health data with **Argon2id, httpOnly JWT cookies, Fernet encryption at rest, owner-only access and anonymous admin statistics with small-count suppression**. Covered by **348 automated tests** (329 backend, 19 frontend) plus a **9-step real-browser walk-through** (Playwright + Edge).

## 30-second pitch
"MediGuide lets someone describe symptoms in English, Telugu or Hindi and tells them how urgently to get care, without
diagnosing. The interesting part is the safety design. Emergencies are decided by rules that each cite NHS or WHO
guidance, and the Decision Tree, trained on 84,000 real US emergency-department triage records, can only raise
urgency, never lower it. When I evaluated the model honestly, symptoms alone separated Routine from Urgent only
weakly, because nurses also use vital signs. So I kept the model capped and let the cited rules carry the emergency
decisions. Everything is tested: 348 automated tests plus a real-browser walk-through in three languages."

## Likely interview questions, with honest answers

**Why a Decision Tree and not deep learning or an LLM?**
Explainability and safety. A depth-6 tree gives at most six readable conditions per decision, which the user sees. There is
no labelled Telugu/Hindi triage corpus to fine-tune on, and a generative model could produce unsafe free-text advice. The Random
Forest was about 0.02 macro-F1 better; I reported it as a comparison but chose the explainable model.

**Your accuracy is only ~0.55. Isn't that bad?**
Accuracy is misleading here: always predicting "Urgent" also gets 0.548. Macro-F1 doubles from 0.236 to 0.538. The honest
conclusion is that self-reported symptoms carry limited triage signal without vital signs. That finding is why the
architecture puts cited safety rules first.

**What happens if the model is wrong?**
It can never lower a rule's level, and it can never say "Emergency". Every non-emergency result includes explicit
"call 112 if…" safety-netting. On the 2022 test set, 8.4% of nurse-triaged emergencies would still get "Routine" from
the model alone, and I document that as a residual risk rather than hiding it.

**How did you avoid fooling yourself in evaluation?**
I used a temporal split (2016–21 for training, 2022 locked for testing), chose thresholds on cross-validated
predictions, and evaluated the test set once. For the NLP I wrote held-out sentences after fixing the development
set and reported the blind run.

**How do you handle Telugu and Hindi without translation?**
Phrases in all three languages map to the same concept IDs (తలనొప్పి / सिरदर्द / headache → `headache`). Language-specific rules
handle negation that comes after the symptom (జ్వరం లేదు, बुखार नहीं), Telugu suffixes (జ్వరంతో) and Hindi
normalisation (nukta, chandrabindu). The result text comes from fixed templates, so no runtime machine translation can
mistranslate a safety instruction.

**What was the hardest bug?**
For example: unquoted commas in YAML silently truncated warning-sign labels ("Blue" instead of "Blue, grey or very
pale lips/skin"). Unit tests passed; I found it only by looking at browser screenshots. I then added a validator rule so
it cannot happen again.

**What would you do next?**
Get the rules reviewed by a clinician, and the Telugu/Hindi wording by native speakers. Collect an independent
native-speaker test set. Add support for romanised Hindi/Telugu. Run a usability study.

## Numbers you can quote (all verifiable in the repository)
| Item | Value |
|---|---|
| Real triage records used | 84,148 (CDC NHAMCS 2016–2022) |
| Training / test rows | 61,388 / 8,491 (temporal split) |
| Vocabulary | 71 concepts; ~520 English, ~220 Telugu, ~270 Hindi terms |
| Safety rules | 27 (16 Emergency, 11 Urgent), 23 cited sources |
| Automated tests | 329 backend + 19 frontend + 9 browser steps |
| Code | ~6,000 lines of Python/JavaScript |
