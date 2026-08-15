"""
Anomaly Detection — SKAB dataset.
Trains 3 models on flattened (N, 60x8=480) windows:
  1. IsolationForest   (unsupervised, fit on normal only)
  2. RandomForestClassifier  (supervised)
  3. MLPClassifier           (supervised neural net)

Selects best by val F1, evaluates on test, saves all models + metrics + plots.
Run from ml/:  python -X utf8 src/models/train_anomaly_detection.py
"""

import os
import json
import warnings
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import joblib
# pyrefly: ignore [missing-import]
import matplotlib
matplotlib.use("Agg")
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix,
    f1_score, roc_auc_score, roc_curve,
    precision_recall_curve, average_precision_score,
)

warnings.filterwarnings("ignore")


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR     = os.path.join(PROJECT_ROOT, "ml", "data", "processed")
MODEL_DIR    = os.path.join(PROJECT_ROOT, "ml", "models")
EVAL_DIR     = os.path.join(MODEL_DIR, "evaluation")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(EVAL_DIR,  exist_ok=True)


def print_section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def load_data():
    d = np.load(os.path.join(DATA_DIR, "skab_windows.npz"))
    X_tr = d["X_train"].reshape(len(d["X_train"]), -1)   # (1091, 480)
    X_va = d["X_val"].reshape(len(d["X_val"]),   -1)
    X_te = d["X_test"].reshape(len(d["X_test"]),  -1)
    return (X_tr, d["y_train"].astype(int),
            X_va, d["y_val"].astype(int),
            X_te, d["y_test"].astype(int))


def evaluate(name, y_true, y_pred, y_prob=None):
    f1  = f1_score(y_true, y_pred, average="weighted")
    auc = roc_auc_score(y_true, y_prob) if y_prob is not None else float("nan")
    rep = classification_report(y_true, y_pred, target_names=["Normal", "Anomaly"],
                                 output_dict=True)
    return {"model": name, "weighted_f1": round(f1, 4), "roc_auc": round(auc, 4),
            "precision_anomaly": round(rep["Anomaly"]["precision"], 4),
            "recall_anomaly":    round(rep["Anomaly"]["recall"],    4),
            "f1_anomaly":        round(rep["Anomaly"]["f1-score"],  4),
            "accuracy":          round(rep["accuracy"],             4)}


def run():
    print_section("Anomaly Detection Training — SKAB")

    X_tr, y_tr, X_va, y_va, X_te, y_te = load_data()
    print(f"  Train: {X_tr.shape}  anomaly={y_tr.mean()*100:.1f}%")
    print(f"  Val  : {X_va.shape}  anomaly={y_va.mean()*100:.1f}%")
    print(f"  Test : {X_te.shape}  anomaly={y_te.mean()*100:.1f}%")

    results_val  = {}
    results_test = {}
    models       = {}
    probs_val    = {}
    probs_test   = {}

    # ------------------------------------------------------------------
    # Model 1: IsolationForest (unsupervised — fit on normal only)

    print_section("Model 1: IsolationForest (unsupervised)")
    X_normal = X_tr[y_tr == 0]
    isoforest = IsolationForest(n_estimators=300, contamination="auto",
                                random_state=42, n_jobs=-1)
    isoforest.fit(X_normal)

    # IF returns -1 (anomaly) / +1 (normal) → convert to 0/1
    def if_predict(model, X):
        raw = model.predict(X)
        return (raw == -1).astype(int)

    def if_score(model, X):
        # decision_function: lower = more anomalous; negate for probability proxy
        return -model.decision_function(X)

    y_pred_if_val  = if_predict(isoforest, X_va)
    y_pred_if_test = if_predict(isoforest, X_te)
    y_prob_if_val  = if_score(isoforest, X_va)
    y_prob_if_test = if_score(isoforest, X_te)

    # Normalise scores to [0,1]
    lo, hi = y_prob_if_val.min(), y_prob_if_val.max()
    y_prob_if_val_n  = (y_prob_if_val  - lo) / (hi - lo + 1e-9)
    y_prob_if_test_n = (y_prob_if_test - lo) / (hi - lo + 1e-9)

    r_val  = evaluate("IsolationForest", y_va, y_pred_if_val,  y_prob_if_val_n)
    r_test = evaluate("IsolationForest", y_te, y_pred_if_test, y_prob_if_test_n)
    print(f"  Val  — F1={r_val['weighted_f1']:.4f}  AUC={r_val['roc_auc']:.4f}  "
          f"Recall(anomaly)={r_val['recall_anomaly']:.4f}")
    print(f"  Test — F1={r_test['weighted_f1']:.4f}  AUC={r_test['roc_auc']:.4f}  "
          f"Recall(anomaly)={r_test['recall_anomaly']:.4f}")
    print(f"\n  Val classification report:\n"
          f"{classification_report(y_va, y_pred_if_val, target_names=['Normal','Anomaly'])}")

    results_val["IsolationForest"]  = r_val
    results_test["IsolationForest"] = r_test
    probs_val["IsolationForest"]    = y_prob_if_val_n
    probs_test["IsolationForest"]   = y_prob_if_test_n
    models["IsolationForest"]       = isoforest
    joblib.dump(isoforest, os.path.join(MODEL_DIR, "skab_isolation_forest.joblib"))

    # ------------------------------------------------------------------
    # Model 2: RandomForestClassifier
    # ------------------------------------------------------------------
    print_section("Model 2: RandomForestClassifier (supervised)")
    rf = RandomForestClassifier(n_estimators=200, max_depth=15,
                                 class_weight="balanced", random_state=42, n_jobs=-1)
    rf.fit(X_tr, y_tr)

    y_pred_rf_val  = rf.predict(X_va)
    y_pred_rf_test = rf.predict(X_te)
    y_prob_rf_val  = rf.predict_proba(X_va)[:, 1]
    y_prob_rf_test = rf.predict_proba(X_te)[:, 1]

    r_val  = evaluate("RandomForest", y_va, y_pred_rf_val,  y_prob_rf_val)
    r_test = evaluate("RandomForest", y_te, y_pred_rf_test, y_prob_rf_test)
    print(f"  Val  — F1={r_val['weighted_f1']:.4f}  AUC={r_val['roc_auc']:.4f}  "
          f"Recall(anomaly)={r_val['recall_anomaly']:.4f}")
    print(f"  Test — F1={r_test['weighted_f1']:.4f}  AUC={r_test['roc_auc']:.4f}  "
          f"Recall(anomaly)={r_test['recall_anomaly']:.4f}")
    print(f"\n  Val classification report:\n"
          f"{classification_report(y_va, y_pred_rf_val, target_names=['Normal','Anomaly'])}")

    results_val["RandomForest"]  = r_val
    results_test["RandomForest"] = r_test
    probs_val["RandomForest"]    = y_prob_rf_val
    probs_test["RandomForest"]   = y_prob_rf_test
    models["RandomForest"]       = rf
    joblib.dump(rf, os.path.join(MODEL_DIR, "skab_random_forest.joblib"))

    # ------------------------------------------------------------------
    # Model 3: MLPClassifier
    # ------------------------------------------------------------------
    print_section("Model 3: MLPClassifier (neural net)")
    mlp = MLPClassifier(hidden_layer_sizes=(256, 128, 64), activation="relu",
                         solver="adam", max_iter=300, early_stopping=True,
                         validation_fraction=0.1, n_iter_no_change=15,
                         random_state=42)
    mlp.fit(X_tr, y_tr)
    print(f"  Stopped at iteration: {mlp.n_iter_}")

    y_pred_mlp_val  = mlp.predict(X_va)
    y_pred_mlp_test = mlp.predict(X_te)
    y_prob_mlp_val  = mlp.predict_proba(X_va)[:, 1]
    y_prob_mlp_test = mlp.predict_proba(X_te)[:, 1]

    r_val  = evaluate("MLP", y_va, y_pred_mlp_val,  y_prob_mlp_val)
    r_test = evaluate("MLP", y_te, y_pred_mlp_test, y_prob_mlp_test)
    print(f"  Val  — F1={r_val['weighted_f1']:.4f}  AUC={r_val['roc_auc']:.4f}  "
          f"Recall(anomaly)={r_val['recall_anomaly']:.4f}")
    print(f"  Test — F1={r_test['weighted_f1']:.4f}  AUC={r_test['roc_auc']:.4f}  "
          f"Recall(anomaly)={r_test['recall_anomaly']:.4f}")
    print(f"\n  Val classification report:\n"
          f"{classification_report(y_va, y_pred_mlp_val, target_names=['Normal','Anomaly'])}")

    results_val["MLP"]  = r_val
    results_test["MLP"] = r_test
    probs_val["MLP"]    = y_prob_mlp_val
    probs_test["MLP"]   = y_prob_mlp_test
    models["MLP"]       = mlp
    joblib.dump(mlp, os.path.join(MODEL_DIR, "skab_mlp.joblib"))

    # ------------------------------------------------------------------
    # Select best model by val weighted F1
    # ------------------------------------------------------------------
    best_name = max(results_val, key=lambda k: results_val[k]["weighted_f1"])
    print_section(f"Best Model: {best_name}  (val F1={results_val[best_name]['weighted_f1']:.4f})")
    joblib.dump(models[best_name],
                os.path.join(MODEL_DIR, "skab_best_model.joblib"))
    print(f"  Saved best model: skab_best_model.joblib")
    print(f"\n  Test results:")
    for k, v in results_test.items():
        marker = " <-- BEST" if k == best_name else ""
        print(f"    {k:18s}  F1={v['weighted_f1']:.4f}  AUC={v['roc_auc']:.4f}"
              f"  Recall(A)={v['recall_anomaly']:.4f}{marker}")

    # ------------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------------
    print_section("Generating Evaluation Plots")

    # 1. ROC curves
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["#2196F3", "#4CAF50", "#FF5722"]
    for (name, prob), color in zip(probs_test.items(), colors):
        fpr, tpr, _ = roc_curve(y_te, prob)
        auc = results_test[name]["roc_auc"]
        ax.plot(fpr, tpr, color=color, linewidth=2,
                label=f"{name} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], "k--", linewidth=1)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("SKAB Anomaly Detection — ROC Curves (Test Set)", fontweight="bold")
    ax.legend(fontsize=10)
    ax.set_xlim([0, 1]); ax.set_ylim([0, 1.02])
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "skab_roc_curves.png"), dpi=150)
    plt.close()
    print("  Saved: skab_roc_curves.png")

    # 2. Confusion matrices (all 3 models)
    preds_test = {
        "IsolationForest": if_predict(isoforest, X_te),
        "RandomForest":    rf.predict(X_te),
        "MLP":             mlp.predict(X_te),
    }
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, (name, y_pred) in zip(axes, preds_test.items()):
        cm = confusion_matrix(y_te, y_pred)
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                    xticklabels=["Normal", "Anomaly"],
                    yticklabels=["Normal", "Anomaly"])
        f1_w = results_test[name]["weighted_f1"]
        ax.set_title(f"{name}\nTest F1={f1_w:.4f}", fontsize=10, fontweight="bold")
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    fig.suptitle("SKAB — Confusion Matrices (Test Set)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "skab_confusion_matrices.png"), dpi=150)
    plt.close()
    print("  Saved: skab_confusion_matrices.png")

    # 3. Precision-Recall curves
    fig, ax = plt.subplots(figsize=(8, 6))
    for (name, prob), color in zip(probs_test.items(), colors):
        prec, rec, _ = precision_recall_curve(y_te, prob)
        ap = average_precision_score(y_te, prob)
        ax.plot(rec, prec, color=color, linewidth=2,
                label=f"{name} (AP={ap:.3f})")
    baseline = y_te.mean()
    ax.axhline(baseline, color="k", linestyle="--", linewidth=1,
               label=f"Baseline (prevalence={baseline:.2f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("SKAB Anomaly Detection — Precision-Recall Curves (Test Set)",
                 fontweight="bold")
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "skab_pr_curves.png"), dpi=150)
    plt.close()
    print("  Saved: skab_pr_curves.png")

    # 4. F1 comparison bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    names   = list(results_test.keys())
    f1s_val  = [results_val[n]["weighted_f1"]  for n in names]
    f1s_test = [results_test[n]["weighted_f1"] for n in names]
    x = np.arange(len(names))
    ax.bar(x - 0.2, f1s_val,  0.35, label="Validation", color="#2196F3", alpha=0.85)
    ax.bar(x + 0.2, f1s_test, 0.35, label="Test",       color="#4CAF50", alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=11)
    ax.set_ylabel("Weighted F1")
    ax.set_ylim([0, 1.05])
    ax.set_title("SKAB Anomaly Detection — Model Comparison", fontweight="bold")
    ax.legend()
    for i, (fv, ft) in enumerate(zip(f1s_val, f1s_test)):
        ax.text(i - 0.2, fv + 0.01, f"{fv:.3f}", ha="center", va="bottom", fontsize=9)
        ax.text(i + 0.2, ft + 0.01, f"{ft:.3f}", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "skab_model_comparison.png"), dpi=150)
    plt.close()
    print("  Saved: skab_model_comparison.png")

    # ------------------------------------------------------------------
    # Save metrics JSON
    # ------------------------------------------------------------------
    metrics = {
        "task": "anomaly_detection",
        "dataset": "SKAB",
        "best_model": best_name,
        "validation": results_val,
        "test": results_test,
    }
    with open(os.path.join(EVAL_DIR, "skab_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("  Saved: skab_metrics.json")

    print_section("Anomaly Detection Training Complete")
    print(f"  Best model: {best_name}")
    print(f"  Test F1   : {results_test[best_name]['weighted_f1']:.4f}")
    print(f"  Test AUC  : {results_test[best_name]['roc_auc']:.4f}")
    print(f"  Test Recall(Anomaly): {results_test[best_name]['recall_anomaly']:.4f}\n")


if __name__ == "__main__":
    run()
