# Experiment 2: Telugu and Hindi symptom extraction (Phase 4)

## Approach: shared concept IDs, no machine translation
Telugu, Hindi and English phrases map directly to the same concept IDs (e.g. `headache`).
Safety rules and the ML model only ever see these IDs. So **no machine translation sits in
the safety-critical path**, and there is no risk of a mistranslated symptom. IndicTrans2 is not
used. It could be added later as an optional fallback for unrecognised text, with its output
flagged for user confirmation.

Language-specific handling:
- **Language detection** by Unicode script (Telugu / Devanagari / Latin). Code-mixed text ("నాకు fever ఉంది") also matches English terms.
- **Normalisation**: native digits → ASCII; Hindi nukta and chandrabindu unified; Indic NLP normaliser.
- **Telugu endings**: a list of endings plus the anusvara alternation (జ్వరం / జ్వరముంది / జ్వరంతో).
- **Hindi endings**: a list of verb and noun endings (दिख → दिखने, सूज → सूजन).
- **Negation after the noun** (జ్వరం లేదు, बुखार नहीं) with clause terminators (ఉంది / है, కానీ / लेकिन).
- **Negated severity**: "తలనొప్పి ఎక్కువగా లేదు" means "the headache is not severe". The headache stays present.

## Results (synthetic, developer-written sentences)

| Set | Cases | Precision | Recall | F1 | Negation | Exact |
|---|---|---|---|---|---|---|
| Telugu dev, baseline | 36 | 1.000 | 0.933 | 0.966 | 10/10 | 32/36 |
| Hindi dev, baseline | 36 | 1.000 | 0.956 | 0.977 | 10/10 | 33/36 |
| **Telugu held-out, blind run** | 20 | **1.000** | **1.000** | **1.000** | 3/3 | **20/20** |
| **Hindi held-out, blind run** | 20 | **1.000** | **0.880** | **0.936** | 3/3 | **15/20** |
| Hindi held-out after Hindi-ending fix | 20 | 1.000 | 1.000 | 1.000 | 3/3 | 20/20 (no longer blind) |

Report the bold rows. Both false-positive traps passed ("చలికాలం" = winter is not chills;
"कोई परेशानी नहीं" = no problem).

## Error analysis
| Error | Example | Fix |
|---|---|---|
| Ending merged with the verb (Telugu) | జ్వరము**ంది** | Added the "ంది" ending |
| Spelling variant | ఛా**తి** / ఛా**తీ** | Added variants |
| Hindi inflection | धुंधला दिख**ने**, कम हो रह**े** | Hindi ending list; inflected cue variants |
| Inserted words | पेट में **अचानक** दर्द, ठंड **भी** लग रही | Intensity/onset adverbs and the particles भी/కూడా allowed inside phrases |
| Infant is the patient | "2 నెలల పాపకి జ్వరం" | Age under 1 year → subject is someone else |

## Threats to validity (important)
- **Same author.** One person wrote the vocabulary *and* the test sentences, so their phrasing habits appear in both. This inflates the scores, which is the most likely explanation of the Telugu 100%. Real patient messages, typed by native speakers, will score lower.
- **Small sets** (20 held-out cases per language). One error changes recall by about 4 points.
- **Romanised Hindi/Telugu** ("mujhe bukhar hai", "naaku jwaram undi") is very common in India and is **not supported**. It is detected as English and mostly not matched.
- **Dialects.** Telangana vs coastal Andhra Telugu, and regional Hindi variants, are not covered.

**Next step for validity:** ask 3–5 native speakers per language to describe given symptoms in
their own words, then score that set once, unchanged.
