"""Language detection by Unicode script (Module 2).

Telugu and Hindi use their own scripts, so counting letters per Unicode block is a very
reliable signal and needs no extra library or model:

    Telugu      U+0C00 - U+0C7F
    Devanagari  U+0900 - U+097F   (Hindi)
    Latin       A-Z, a-z          (English)

Code-mixed messages are common ("నాకు fever ఉంది"). The language with the most Indic
letters wins; `mixed` is True when Latin words also appear, and the extractor then
matches English terms as well.

Limitation: romanised Hindi/Telugu ("mujhe bukhar hai") is Latin script and is detected
as English. The user can still choose their language manually in the app.
"""
from __future__ import annotations

from dataclasses import dataclass

RANGES = {"te": (0x0C00, 0x0C7F), "hi": (0x0900, 0x097F)}


@dataclass
class Detection:
    lang: str            # en | te | hi
    counts: dict         # letters per script
    mixed: bool          # Latin letters present alongside an Indic script
    confident: bool      # at least 3 letters of the winning script


def detect_language(text: str) -> Detection:
    counts = {"te": 0, "hi": 0, "latin": 0}
    for ch in text:
        cp = ord(ch)
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            counts["latin"] += 1
            continue
        for lang, (lo, hi) in RANGES.items():
            if lo <= cp <= hi:
                counts[lang] += 1
                break
    indic = max(("te", "hi"), key=lambda k: counts[k])
    if counts[indic] > 0:
        return Detection(indic, counts, counts["latin"] > 0, counts[indic] >= 3)
    return Detection("en", counts, False, counts["latin"] >= 3)
