# Model card: MediGuide urgency Decision Tree (dt_app_v1)

| | |
|---|---|
| Purpose | Secondary urgency signal (ROUTINE vs URGENT) behind independent red-flag rules. **Never outputs EMERGENCY.** |
| Status | **Educational prototype. Not clinically validated. Not a medical device.** |
| Algorithm | scikit-learn DecisionTreeClassifier, max_depth 6, min_samples_leaf 100, class_weight balanced (49 leaves) |
| Training data | CDC NHAMCS ED public-use files 2016–2021 (61,388 visits with ≥1 recognised symptom) |
| Labels | Nurse triage: Immediate/Emergent → EMERGENCY, Urgent → URGENT, Semi/Non-urgent → ROUTINE |
| Inputs | 62 symptom flags, age, pain score (or "unknown"), number of symptoms |
| Decision rule | URGENT if P(urgent) + P(emergency) ≥ 0.45, else ROUTINE; flag "high emergency probability" if P(emergency) ≥ 0.20 |
| Test (2022, 8,491 visits) | Combined with rules: macro-F1 0.466; 91.6% of nurse emergencies get ≥ URGENT; 8.4% get ROUTINE |
| Known limits | No vital signs; US emergency-department population (no self-care cases); not validated for India; coded reasons for visit, not free text; severity words mapped to approximate pain scores (mild 2 / moderate 5 / severe 8) by project assumption |
| Fairness | Not evaluated by sex, ethnicity or region. Age is the strongest feature. |
