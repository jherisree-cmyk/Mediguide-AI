"""Text cleaning for symptom extraction.

What we DO:   Unicode NFC normalisation, unify apostrophes/quotes, collapse whitespace,
              fix common misspellings (dictionary + conservative fuzzy matching).
What we DON'T: remove stop words, lower-case the stored text or strip punctuation.
              Words like "no", "not", "without" carry medical meaning (negation), and
              punctuation marks sentence/clause boundaries, so both must survive.
"""
from __future__ import annotations

import difflib
import re
import unicodedata

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "`": "'",
                              "“": '"', "”": '"'})
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text).translate(_APOSTROPHES)
    text = re.sub(r"\bcan not\b", "cannot", text, flags=re.IGNORECASE)
    return " ".join(text.split())


class SpellingCorrector:
    """Two-stage correction for English.

    1. Exact dictionary of known misspellings (knowledge/nlp_cues.yaml: spelling_en).
    2. Fuzzy match (difflib ratio >= cutoff) for words of >= min_len letters that are NOT
       already in our vocabulary, against single words used in symptom terms. Every
       correction is reported so the user can confirm the extracted symptoms.
    """

    def __init__(self, dictionary: dict[str, str], vocabulary: set[str],
                 cutoff: float = 0.88, min_len: int = 6):
        self.dictionary = {k.lower(): v for k, v in dictionary.items()}
        self.vocabulary = {w.lower() for w in vocabulary}
        self.targets = sorted(w for w in self.vocabulary if len(w) >= min_len - 1 and w.isalpha())
        self.cutoff = cutoff
        self.min_len = min_len

    def correct(self, text: str) -> tuple[str, list[tuple[str, str]]]:
        corrections: list[tuple[str, str]] = []

        def fix(m: re.Match) -> str:
            word = m.group(0)
            low = word.lower()
            if low in self.dictionary:
                new = self.dictionary[low]
                if new != low:
                    corrections.append((word, new))
                return new
            if len(low) >= self.min_len and low.isalpha() and low not in self.vocabulary:
                best = difflib.get_close_matches(low, self.targets, n=1, cutoff=self.cutoff)
                if best:
                    corrections.append((word, best[0]))
                    return best[0]
            return word

        return _WORD.sub(fix, text), corrections
