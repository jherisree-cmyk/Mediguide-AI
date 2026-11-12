"""Phase 6 / Experiment 3: Decision Tree vs Random Forest urgency classifier on NHAMCS.

Steps
  1. Build features with mediguide.ml.features (the SAME code the app uses at prediction time).
  2. Keep visits with >= 1 recognised symptom (the app never runs the model without one).
  3. Tune each model with stratified 5-fold cross-validation on the DEV split (2016-2021) only.
  4. Choose decision thresholds on out-of-fold DEV predictions (never on the test set):
       predict EMERGENCY if P(emergency) >= t_E
       else URGENT       if P(emergency) + P(urgent) >= t_U
       else ROUTINE
     t_E gives >= 80% emergency recall; t_U gives >= 90% recall for "urgent or higher".
  5. Evaluate ONCE on the locked TEST split (2022): ML alone, rules alone, rules + ML.
  6. Save models, metadata, metrics and figures.

APP POLICY (decided 2026-11-10, see reports/phase6_experiment3_ml.md):
  * Only the red-flag RULES may output EMERGENCY. The ML output is capped at URGENT, because
    the model's emergency precision is ~0.2 (both in dev out-of-fold predictions and on test).
  * The app uses a depth-6 Decision Tree (explainable in <= 6 conditions). Depth 6 was chosen
    on DEV cross-validation only (macro-F1 0.481 vs 0.519 for the unrestricted tree).

Usage: python scripts/train_models.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix, f1_score,
                             make_scorer, recall_score)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict
from sklearn.tree import DecisionTreeClassifier, plot_tree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from mediguide.knowledge import load_knowledge  # noqa: E402
from mediguide.ml.features import feature_names, from_nhamcs  # noqa: E402
from mediguide.ml.labels import Urgency  # noqa: E402
from mediguide.nlp.schema import Extraction, Finding  # noqa: E402
from mediguide.safety.engine import SafetyEngine  # noqa: E402

SEED = 42
CLASSES = [u.name for u in Urgency]            # ROUTINE, URGENT, EMERGENCY (index = Urgency value)
EM, UR = int(Urgency.EMERGENCY), int(Urgency.URGENT)
TARGET_EM_RECALL, TARGET_URGENT_PLUS_RECALL = 0.80, 0.90
FIG, MODELS, REPORTS = ROOT / "reports/figures", ROOT / "models", ROOT / "reports"
# dataviz palette (validated): categorical slots 1-2, sequential blue ramp, chart chrome
C1, C2 = "#2a78d6", "#eb6834"
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "xtick.color": MUTED,
                     "ytick.color": MUTED, "text.color": INK, "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True,
                     "grid.color": GRID, "grid.linewidth": 0.6})


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def em_recall(y, p):
    return recall_score(y, p, labels=[EM], average="macro", zero_division=0)


def decide(proba: np.ndarray, t_e: float, t_u: float) -> np.ndarray:
    pred = np.full(len(proba), int(Urgency.ROUTINE))
    pred[proba[:, EM] + proba[:, UR] >= t_u] = UR
    pred[proba[:, EM] >= t_e] = EM
    return pred


def pick_thresholds(y: np.ndarray, proba: np.ndarray) -> tuple[float, float]:
    """Largest thresholds that still meet the recall targets on out-of-fold DEV predictions."""
    grid = np.round(np.arange(0.02, 0.99, 0.01), 2)
    t_e = max(t for t in grid if (proba[y == EM, EM] >= t).mean() >= TARGET_EM_RECALL)
    hi = y >= UR
    t_u = max(t for t in grid if ((proba[hi, EM] + proba[hi, UR]) >= t).mean() >= TARGET_URGENT_PLUS_RECALL)
    return float(t_e), float(t_u)


def app_ml_level(proba: np.ndarray, t_u: float) -> np.ndarray:
    """App policy: ML may say URGENT or ROUTINE, never EMERGENCY."""
    return np.where(proba[:, EM] + proba[:, UR] >= t_u, UR, int(Urgency.ROUTINE))


def metrics(y: np.ndarray, pred: np.ndarray) -> dict:
    rep = classification_report(y, pred, labels=[0, 1, 2], target_names=CLASSES, output_dict=True, zero_division=0)
    return {
        "accuracy": accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, average="macro"),
        "emergency_recall": em_recall(y, pred),
        "under_triage_rate": float((pred < y).mean()),
        "over_triage_rate": float((pred > y).mean()),
        "emergency_to_at_least_urgent": float((pred[y == EM] >= UR).mean()),
        "urgent_plus_recall": float((pred[y >= UR] >= UR).mean()),
        "per_class": {c: {k: rep[c][k] for k in ("precision", "recall", "f1-score", "support")} for c in CLASSES},
        "confusion": confusion_matrix(y, pred, labels=[0, 1, 2]).tolist(),
    }


def rules_on_nhamcs(X: pd.DataFrame, engine: SafetyEngine) -> np.ndarray:
    """Run the red-flag rules on NHAMCS visits. Approximation: only symptom concepts exist
    (no warning-sign phrases, onset or duration); pain >= 7 marks symptoms as severe."""
    sym_cols = [c for c in X.columns if c.startswith("sym_")]
    out = np.zeros(len(X), dtype=int)
    for i, (_, row) in enumerate(X.iterrows()):
        ext = Extraction(language="en", original_text="", normalised_text="", age_years=row["age_years"])
        sev = "severe" if row["pain_known"] and row["pain_score"] >= 7 else None
        for c in sym_cols:
            if row[c]:
                ext.findings[c[4:]] = Finding(concept_id=c[4:], kind="symptom", severity=sev)
        level = engine.evaluate(ext).level
        out[i] = {"EMERGENCY": EM, "URGENT": UR}.get(level, int(Urgency.ROUTINE))
    return out


# ------------------------------------------------------------------------------------- plots
def plot_confusions(results: dict, path: Path) -> None:
    names = list(results)
    fig, axes = plt.subplots(1, len(names), figsize=(4.2 * len(names), 4))
    for ax, name in zip(np.atleast_1d(axes), names):
        cm = np.array(results[name]["confusion"])
        share = cm / cm.sum(axis=1, keepdims=True)
        ax.imshow(share, cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
            "blues", ["#f2f7fd", "#9ec5f4", "#2a78d6", "#104281"]), vmin=0, vmax=1)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{share[i, j]:.0%}\n({cm[i, j]:,})", ha="center", va="center", fontsize=8,
                        color="#ffffff" if share[i, j] > 0.45 else INK)
        ax.set_xticks(range(3), [c.title() for c in CLASSES])
        ax.set_yticks(range(3), [c.title() for c in CLASSES])
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Nurse triage (2022 test)")
        ax.set_title(name, loc="left", fontsize=10)
        ax.grid(False)
    fig.suptitle("Confusion matrices on the 2022 test set (row-normalised)", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_thresholds(y: np.ndarray, proba: dict, chosen: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    grid = np.linspace(0.02, 0.8, 79)
    for (name, p), color in zip(proba.items(), (C1, C2)):
        rec = [(p[y == EM, EM] >= t).mean() for t in grid]
        prec = [((p[:, EM] >= t) & (y == EM)).sum() / max((p[:, EM] >= t).sum(), 1) for t in grid]
        ax.plot(grid, rec, color=color, lw=2, label=f"{name}: emergency recall")
        ax.plot(grid, prec, color=color, lw=2, ls="--", label=f"{name}: emergency precision")
        ax.axvline(chosen[name][0], color=color, lw=1, ls=":")
    ax.axhline(TARGET_EM_RECALL, color=MUTED, lw=1)
    ax.text(0.79, TARGET_EM_RECALL + 0.02, "recall target 0.80", ha="right", fontsize=8, color=INK2)
    ax.set_xlabel("Threshold on P(emergency)")
    ax.set_ylabel("Out-of-fold value (dev split)")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(0, 0.8)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    fig.suptitle("Emergency threshold trade-off (chosen on dev, dotted lines)", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_importance(imp: pd.Series, title: str, path: Path) -> None:
    top = imp.sort_values().tail(15)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.barh([n.replace("sym_", "") for n in top.index], top.values, color=C1, height=0.6)
    ax.set_xlabel("Importance")
    ax.grid(axis="y", visible=False)
    fig.suptitle(title, x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# -------------------------------------------------------------------------------------- main
def main() -> None:
    t0 = time.time()
    FIG.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(exist_ok=True)
    kb = load_knowledge()
    df = pd.read_csv(ROOT / "data/processed/nhamcs_ed.csv.gz")
    X_all = from_nhamcs(df, kb)
    y_all = df["URGENCY"].map({u.name: int(u) for u in Urgency}).to_numpy()
    keep = (X_all["n_symptoms"] > 0).to_numpy()
    dropped = {s: int(((df["SPLIT"] == s).to_numpy() & ~keep).sum()) for s in ("dev", "test")}
    dev = keep & (df["SPLIT"] == "dev").to_numpy()
    test = keep & (df["SPLIT"] == "test").to_numpy()
    X_dev, y_dev, X_test, y_test = X_all[dev], y_all[dev], X_all[test], y_all[test]
    assert list(X_dev.columns) == feature_names(kb)
    log(f"dev {len(X_dev):,} rows, test {len(X_test):,} rows, {X_dev.shape[1]} features; "
        f"dropped (no recognised symptom): {dropped}")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    scoring = {"macro_f1": "f1_macro", "em_recall": make_scorer(em_recall), "accuracy": "accuracy"}

    log("Decision Tree grid search ...")
    dt = GridSearchCV(DecisionTreeClassifier(random_state=SEED), {
        "max_depth": [4, 6, 8, 10, 12, 16, None], "min_samples_leaf": [10, 50, 100, 200],
        "class_weight": [None, "balanced"], "criterion": ["gini", "entropy"]},
        scoring=scoring, refit="macro_f1", cv=cv, n_jobs=-1).fit(X_dev, y_dev)
    log(f"  best {dt.best_params_}  cv macro-F1 {dt.best_score_:.3f}")

    log("Random Forest grid search ...")
    rf = GridSearchCV(RandomForestClassifier(n_estimators=200, max_features="sqrt", random_state=SEED, n_jobs=-1), {
        "max_depth": [12, 20, None], "min_samples_leaf": [5, 20, 50], "class_weight": [None, "balanced"]},
        scoring=scoring, refit="macro_f1", cv=cv, n_jobs=1).fit(X_dev, y_dev)
    log(f"  best {rf.best_params_}  cv macro-F1 {rf.best_score_:.3f}")

    log("Depth-6 app Decision Tree grid search ...")
    dt6 = GridSearchCV(DecisionTreeClassifier(max_depth=6, random_state=SEED), {
        "min_samples_leaf": [20, 50, 100, 200], "class_weight": [None, "balanced"], "criterion": ["gini", "entropy"]},
        scoring=scoring, refit="macro_f1", cv=cv, n_jobs=-1).fit(X_dev, y_dev)
    log(f"  best {dt6.best_params_}  cv macro-F1 {dt6.best_score_:.3f}")

    cv_table = []
    for name, gs in (("Decision Tree", dt), ("Random Forest", rf), ("Decision Tree depth-6 (app)", dt6)):
        r = gs.cv_results_
        i = gs.best_index_
        cv_table.append({"model": name, "params": gs.best_params_,
                         "cv_macro_f1": (r["mean_test_macro_f1"][i], r["std_test_macro_f1"][i]),
                         "cv_em_recall": (r["mean_test_em_recall"][i], r["std_test_em_recall"][i]),
                         "cv_accuracy": (r["mean_test_accuracy"][i], r["std_test_accuracy"][i])})

    log("Out-of-fold probabilities for threshold selection ...")
    oof = {name: cross_val_predict(gs.best_estimator_, X_dev, y_dev, cv=cv, method="predict_proba", n_jobs=-1)
           for name, gs in (("Decision Tree", dt), ("Random Forest", rf), ("Decision Tree depth-6 (app)", dt6))}
    thresholds = {name: pick_thresholds(y_dev, p) for name, p in oof.items()}
    log(f"  thresholds (t_E, t_U): {thresholds}")

    log("Evaluating ONCE on the 2022 test split ...")
    models = {"Decision Tree": dt.best_estimator_, "Random Forest": rf.best_estimator_,
              "Decision Tree depth-6 (app)": dt6.best_estimator_}
    results, preds = {}, {}
    dummy = DummyClassifier(strategy="most_frequent").fit(X_dev, y_dev)
    results["Majority class"] = metrics(y_test, dummy.predict(X_test))
    for name, m in models.items():
        proba = m.predict_proba(X_test)
        results[f"{name} (argmax)"] = metrics(y_test, proba.argmax(axis=1))
        preds[name] = decide(proba, *thresholds[name])
        results[f"{name} (thresholds)"] = metrics(y_test, preds[name])
    engine = SafetyEngine(kb)
    rules_pred = rules_on_nhamcs(X_test, engine)
    results["Rules only"] = metrics(y_test, rules_pred)
    results["Rules + Decision Tree"] = metrics(y_test, np.maximum(rules_pred, preds["Decision Tree"]))
    results["Rules + Random Forest"] = metrics(y_test, np.maximum(rules_pred, preds["Random Forest"]))
    app_t_u = thresholds["Decision Tree depth-6 (app)"][1]
    app_ml = app_ml_level(dt6.best_estimator_.predict_proba(X_test), app_t_u)
    results["APP: Rules + depth-6 DT (ML capped at URGENT)"] = metrics(y_test, np.maximum(rules_pred, app_ml))

    log("Feature importance ...")
    dt_imp = pd.Series(dt.best_estimator_.feature_importances_, index=X_dev.columns)
    perm = permutation_importance(rf.best_estimator_, X_test, y_test, scoring="f1_macro", n_repeats=5,
                                  random_state=SEED, n_jobs=-1)
    rf_perm = pd.Series(perm.importances_mean, index=X_dev.columns)

    # ---- figures
    plot_confusions({k: results[k] for k in ("Random Forest (argmax)", "Rules + Random Forest",
                                             "APP: Rules + depth-6 DT (ML capped at URGENT)")},
                    FIG / "p6_confusion_matrices.png")
    plot_thresholds(y_dev, {k: oof[k] for k in ("Decision Tree", "Random Forest")}, thresholds,
                    FIG / "p6_threshold_tradeoff.png")
    plot_importance(dt_imp, "Decision Tree: impurity-based feature importance", FIG / "p6_dt_importance.png")
    plot_importance(rf_perm, "Random Forest: permutation importance on 2022 test (macro-F1 drop)",
                    FIG / "p6_rf_permutation_importance.png")
    fig, ax = plt.subplots(figsize=(18, 8))
    plot_tree(dt6.best_estimator_, max_depth=3, feature_names=list(X_dev.columns), class_names=CLASSES,
              filled=False, impurity=False, proportion=True, fontsize=7, ax=ax)
    fig.suptitle("App Decision Tree (depth 6), top 4 levels (proportions of training visits)", x=0.01, ha="left", fontsize=11)
    fig.savefig(FIG / "p6_decision_tree_top.png", dpi=130)
    plt.close(fig)

    # ---- save models + metadata
    data_hash = hashlib.sha256((ROOT / "data/processed/nhamcs_ed.csv.gz").read_bytes()).hexdigest()[:16]
    for key, name in (("dt", "Decision Tree"), ("rf", "Random Forest"), ("dt_app", "Decision Tree depth-6 (app)")):
        joblib.dump(models[name], MODELS / f"{key}_v1.joblib", compress=3)
        meta = {"model": name, "version": "v1", "trained": str(date.today()), "sklearn": sklearn.__version__,
                "features": list(X_dev.columns), "classes": CLASSES, "params": models[name].get_params(),
                "thresholds": {"t_emergency": thresholds[name][0], "t_urgent_or_higher": thresholds[name][1]},
                "train_data": {"source": "NHAMCS ED 2016-2021", "rows": int(len(X_dev)), "sha256_16": data_hash},
                "test_metrics_2022": results[f"{name} (thresholds)"],
                "app_policy": ("ML output capped at URGENT; EMERGENCY only from red-flag rules"
                               if key == "dt_app" else "comparison model, not used by the app"),
                "status": "EDUCATIONAL PROTOTYPE - not clinically validated"}
        (MODELS / f"{key}_v1.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    (REPORTS / "phase6_results.json").write_text(json.dumps(
        {"dropped_rows": dropped, "cv": cv_table, "thresholds": thresholds, "test": results,
         "dt_importance_top": dt_imp.sort_values(ascending=False).head(15).round(4).to_dict(),
         "rf_permutation_top": rf_perm.sort_values(ascending=False).head(15).round(4).to_dict(),
         "dt_depth": int(dt.best_estimator_.get_depth()), "dt_leaves": int(dt.best_estimator_.get_n_leaves()),
         "dt_app_leaves": int(dt6.best_estimator_.get_n_leaves()),
         "dt_app_importance_top": pd.Series(dt6.best_estimator_.feature_importances_, index=X_dev.columns)
             .sort_values(ascending=False).head(15).round(4).to_dict()},
        indent=2, default=lambda o: float(o) if isinstance(o, np.floating) else str(o)), encoding="utf-8")

    print("\nCross-validation on DEV (mean ± sd over 5 folds)")
    for r in cv_table:
        print(f"  {r['model']:14} macro-F1 {r['cv_macro_f1'][0]:.3f}±{r['cv_macro_f1'][1]:.3f}  "
              f"em-recall {r['cv_em_recall'][0]:.3f}±{r['cv_em_recall'][1]:.3f}  "
              f"acc {r['cv_accuracy'][0]:.3f}±{r['cv_accuracy'][1]:.3f}  {r['params']}")
    print("\nTEST 2022 (evaluated once)")
    print(f"  {'system':46} {'acc':>6} {'macroF1':>8} {'EM rec':>7} {'EM>=U':>6} {'U+rec':>6} {'under':>6} {'over':>6}")
    for k, v in results.items():
        print(f"  {k:46} {v['accuracy']:6.3f} {v['macro_f1']:8.3f} {v['emergency_recall']:7.3f} "
              f"{v['emergency_to_at_least_urgent']:6.3f} {v['urgent_plus_recall']:6.3f} "
              f"{v['under_triage_rate']:6.3f} {v['over_triage_rate']:6.3f}")
    log(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
