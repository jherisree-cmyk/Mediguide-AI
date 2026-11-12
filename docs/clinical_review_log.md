# Clinical & Translation Review Log

Until every safety-critical item below is signed off, the application displays:
"Safety rules and translations have NOT been clinically reviewed. Educational prototype only."

| Item | File | Reviewer (name, qualification) | Date | Outcome / changes |
|---|---|---|---|---|
| Red-flag emergency rules | knowledge/red_flags.yaml | | | |
| Telugu symptom terms | knowledge/symptoms.yaml | | | |
| Hindi symptom terms | knowledge/symptoms.yaml | | | |
| Telugu safety messages | knowledge/templates.yaml | | | |
| Hindi safety messages | knowledge/templates.yaml | | | |

## What reviewers should check (Phase 2 draft, 2026-11-10)

**Clinician (red_flags.yaml, 27 rules: 16 EMERGENCY, 11 URGENT floor)**
- Is each rule's trigger a fair encoding of the quoted guideline?
- Rules marked `note:` are deliberately MORE conservative than the source (EM_CHEST_PAIN, EM_SEIZURE, EM_SUDDEN_CONFUSION, EM_HEAD_INJURY, EM_GI_BLEED..., EM_INFANT_FEVER). Is the over-triage acceptable?
- Rules with source `project_policy` (UR_YOUNG_INFANT, UR_SEVERE_SYMPTOM, UR_MENTAL_HEALTH_CRISIS) have no external source. Should they be kept?
- Guidance is from UK (NHS/NICE), US (MedlinePlus) and WHO sources. Is anything different for Indian practice?

**Telugu reviewer (212 terms) / Hindi reviewer (262 terms) in symptoms.yaml**
- Is every term natural, everyday wording a patient would actually use?
- Is any term ambiguous, or does it mean something different in your region or dialect?
- Are there common words for these symptoms that are missing?
- Check the 8 warning-sign concepts (kind: sign) first. They trigger emergencies.

## Added in Phase 7 (2026-11-11)
| Item | File | Reviewer | Date | Outcome |
|---|---|---|---|---|
| Result texts, safety-netting list, disclaimer (EN/TE/HI) | knowledge/templates.yaml | | | |
| Follow-up question wording (EN/TE/HI) | knowledge/templates.yaml | | | |
| Self-care information text (must contain no treatment advice) | knowledge/templates.yaml | | | |
