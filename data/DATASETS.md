# Datasets used by MediGuide AI

All counts below were **measured by our scripts on 2026-11-10**, not copied from elsewhere.

## 1. NHAMCS Emergency Department public-use files, 2016-2022 (PRIMARY: training + test)

| Item | Value |
|---|---|
| Publisher | CDC, National Center for Health Statistics (NCHS) |
| Landing page | https://www.cdc.gov/nchs/ahcd/datasets_documentation_related.htm |
| Direct files | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/NHAMCS/stata/ (`ED2016-stata.zip` ... `ed2022-stata.zip`) |
| Codebooks | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/NHAMCS/ (`doc16_ed.pdf` ... `doc22-ed-508.pdf`) |
| License | US Government work, public domain. Cite NCHS. |
| Records | 123,040 ED visits. **84,148 (68.4%) have a nurse triage level.** |
| Features used | `AGE`, `SEX`, `PAINSCALE` (0-10), `RFV1`-`RFV5` (coded reasons for visit, 837 codes), `PATWT` (survey weight) |
| Label | `IMMEDR`: nurse-assigned immediacy (1 Immediate, 2 Emergent, 3 Urgent, 4 Semi-urgent, 5 Nonurgent) |
| Real triage labels? | **Yes**, assigned by ED triage nurses at real visits. |
| Our mapping | 1-2 -> EMERGENCY, 3 -> URGENT, 4-5 -> ROUTINE. Codes 0/7/-8/-9 (no triage) excluded. See `backend/mediguide/ml/labels.py`. |
| Split | dev = 2016-2021 (73,941), test = 2022 (10,207, temporal hold-out) |

**Limitations**
- Nurses saw vital signs and the patient in person. Our users self-report text only, so the model cannot match nurse performance.
- Every patient was already in an ED, so there is no self-care class, and the population is sicker than app users in general.
- Reasons for visit are **codes**, not free text. Our NLP extracts symptoms and maps them to these codes.
- Pain score is missing in 24% of dev visits; RFV2 is missing in 31%.
- Triage practice is US-specific. Use in India is not validated.
- NHAMCS is a weighted sample survey. Unweighted ML metrics describe the sample, not national rates.
- Records are visits, not patients. No patient ID exists, so a person could appear in several years. The temporal split limits but cannot exclude overlap.

## 2. Semigran et al. (2015) symptom-checker vignettes (EXTERNAL TEST)

| Item | Value |
|---|---|
| Paper | Semigran HL et al. "Evaluation of symptom checkers for self diagnosis and triage: audit study." BMJ 2015;351:h3480. doi:10.1136/bmj.h3480 |
| Gold labels (downloaded) | Zenodo 10.5281/zenodo.6054093 (Schmieding et al. 2022, CC BY 4.0): `Triage_Accuracy_Symptom_Checker_Apps_2020.xlsx` |
| Records | 45 vignettes: 15 emergency (Em), 15 non-emergency (NE), 15 self-care (Sc). Verified that every vignette has one consistent gold label. |
| Real triage labels? | **Yes**, assigned by physicians to written case descriptions. |
| Vignette text | **Manual download needed** (the PMC site blocks scripts): open https://pmc.ncbi.nlm.nih.gov/articles/PMC4496786/ and download the web appendix PDF into `data/raw/vignettes/` |
| Use | External sanity test of the *whole pipeline* (text -> urgency). 45 cases is too few for confident metrics; report counts, not just percentages. |

## 3. Not used for labels
- **Disease-prediction datasets (e.g. Kaggle Symptom2Disease, Disease-Symptom Prediction):** disease labels only. We may use their sentences to test symptom extraction. Their labels are never turned into urgency labels.
- **MIMIC-IV-ED:** optional future upgrade. Needs PhysioNet credentialing.

## 4. Synthetic data
`data/synthetic/` holds hand-written test sentences for **software testing only**. They are not clinical data and are never used to train or report model accuracy.
