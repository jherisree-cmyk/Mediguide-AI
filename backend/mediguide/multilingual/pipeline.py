"""Single entry point: detect the language (unless the user chose one) and extract symptoms.

The output uses language-neutral concept ids (e.g. "headache"). These ids are the common
internal representation: "తలనొప్పి", "सिरदर्द" and "headache" all become the same id, so
the safety rules and the ML model never need machine translation.
"""
from __future__ import annotations

from mediguide.multilingual.langdetect import Detection, detect_language
from mediguide.nlp.extractor import get_extractor
from mediguide.nlp.schema import Extraction

SUPPORTED = ("en", "te", "hi")


def analyse(text: str, lang: str | None = None) -> tuple[Detection, Extraction]:
    detection = detect_language(text)
    use = lang if lang in SUPPORTED else detection.lang
    return detection, get_extractor(use).extract(text)
