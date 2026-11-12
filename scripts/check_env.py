"""Phase 0 environment check: verifies every core library imports and works
on a tiny example, including Telugu and Hindi text."""
import sys
import importlib
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

REQUIRED = ["spacy", "indicnlp", "numpy", "pandas", "sklearn", "joblib", "yaml",
            "matplotlib", "seaborn", "fastapi", "uvicorn", "sqlalchemy",
            "pydantic", "argon2", "jwt", "cryptography", "pytest", "httpx"]


def check_imports() -> bool:
    ok = True
    for name in REQUIRED:
        try:
            mod = importlib.import_module(name)
            print(f"  [OK]   {name:<12} {getattr(mod, '__version__', '')}")
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"  [FAIL] {name:<12} {exc}")
    return ok


def check_spacy_matcher() -> bool:
    import spacy
    from spacy.matcher import PhraseMatcher
    nlp = spacy.blank("xx")  # multi-language tokeniser, no model download needed
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("HEADACHE", [nlp("headache"), nlp("తలనొప్పి"), nlp("सिरदर्द")])
    tests = ["I have a Headache", "నాకు తలనొప్పి ఉంది", "मुझे सिरदर्द है"]
    ok = True
    for text in tests:
        found = len(matcher(nlp(text))) > 0
        ok &= found
        print(f"  [{'OK' if found else 'FAIL'}]   matched HEADACHE in: {text}")
    return ok


def check_indic_normaliser() -> bool:
    from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
    from indicnlp.tokenize import indic_tokenize
    factory = IndicNormalizerFactory()
    ok = True
    for lang, text in [("te", "నాకు జ్వరం మరియు తలనొప్పి ఉన్నాయి."),
                       ("hi", "मुझे बुखार और सिरदर्द है।")]:
        norm = factory.get_normalizer(lang).normalize(text)
        tokens = indic_tokenize.trivial_tokenize(norm, lang)
        ok &= len(tokens) > 3
        print(f"  [OK]   {lang} tokens: {tokens}")
    return ok


def check_ml() -> bool:
    from sklearn.datasets import load_iris
    from sklearn.tree import DecisionTreeClassifier
    X, y = load_iris(return_X_y=True)
    acc = DecisionTreeClassifier(random_state=0).fit(X, y).score(X, y)
    print(f"  [OK]   DecisionTree fit on toy data (train acc {acc:.2f}; sanity check only)")
    return True


if __name__ == "__main__":
    print(f"Python {sys.version.split()[0]}")
    results = {}
    for title, fn in [("Imports", check_imports), ("spaCy PhraseMatcher (EN/TE/HI)", check_spacy_matcher),
                      ("Indic NLP normaliser", check_indic_normaliser), ("scikit-learn", check_ml)]:
        print(f"\n== {title} ==")
        results[title] = fn()
    print("\nRESULT:", "ALL CHECKS PASSED" if all(results.values()) else "SOME CHECKS FAILED")
    sys.exit(0 if all(results.values()) else 1)
