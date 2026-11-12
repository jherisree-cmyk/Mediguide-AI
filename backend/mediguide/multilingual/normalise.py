"""Script normalisation for Telugu and Hindi.

The same word can be typed in several Unicode forms. We normalise BOTH the user's text and
every vocabulary term with the same function, so they compare equal.

  * Indic NLP Library normaliser (canonical forms of vowel signs, invisible characters)
  * Native digits -> ASCII digits ("३ दिन" -> "3 दिन", "౩ రోజులు" -> "3 రోజులు")
  * Hindi: remove nukta (बुख़ार -> बुखार), chandrabindu -> anusvara (उल्टियाँ -> उल्टियां)
"""
from __future__ import annotations

from functools import lru_cache

from indicnlp.normalize.indic_normalize import IndicNormalizerFactory

_DIGITS = {**{chr(0x0966 + i): str(i) for i in range(10)},   # Devanagari ०-९
           **{chr(0x0C66 + i): str(i) for i in range(10)}}   # Telugu ౦-౯
_HINDI = {"़": "", "ँ": "ं"}                 # nukta removed, chandrabindu -> anusvara


@lru_cache(maxsize=None)
def _normaliser(lang: str):
    return IndicNormalizerFactory().get_normalizer(lang)


def normalise(text: str, lang: str) -> str:
    text = "".join(_DIGITS.get(ch, ch) for ch in text)
    if lang in ("te", "hi"):
        text = _normaliser(lang).normalize(text)
    if lang == "hi":
        text = "".join(_HINDI.get(ch, ch) for ch in text)
    return text
