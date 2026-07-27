"""
Fault Classification — CWRU Bearing dataset.
Trains 3 models on (N, 9) feature vectors:
  1. RandomForestClassifier
  2. HistGradientBoostingClassifier
  3. MLPClassifier

10-class (fault type) and derived binary (normal vs fault) evaluation.
Run from ml/:  python -X utf8 src/models/train_fault_classification.py
"""

import os
import json
import warnings
import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.decomposition import PCA
from sklearn.metrics import (
    classification_report, confusion_matrix,
    f1_score, accuracy_score, roc_auc_score,
)

warnings.filterwarnings("ignore")


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR     = os.path.join(PROJECT_ROOT, "ml", "data", "processed")
MODEL_DIR    = os.path.join(PROJECT_ROOT, "ml", "models")
EVAL_DIR     = os.path.join(MODEL_DIR, "evaluation")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(EVAL_DIR,  exist_ok=True)

FEATURE_NAMES = ["max", "min", "mean", "sd", "rms", "skewness", "kurtosis", "crest", "form"]
FAULT_CLASSES  = [
    "Ball_007", "Ball_014", "Ball_021",
    "IR_007",   "IR_014",   "IR_021",
    "Normal",
    "OR_007",   "OR_014",   "OR_021",
]  # matches LabelEncoder order (alphabetical)


def print_section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def load_data():
    d  = np.load(os.path.join(DATA_DIR, "cwru_features.npz"))
    le = joblib.load(os.path.join(DATA_DIR, "cwru_label_encoder.joblib"))
    return (d["X_train"],       d["y_multi_train"], d["y_bin_train"],
            d["X_val"],         d["y_multi_val"],   d["y_bin_val"],
            d["X_test"],        d["y_multi_test"],  d["y_bin_test"],
            le)


def evaluate_multi(name, le, y_true, y_pred):
    acc    = accuracy_score(y_true, y_pred)
    f1_mac = f1_score(y_true, y_pred, average="macro")
    f1_wei = f1_score(y_true, y_pred, average="weighted")
    per_class_f1 = f1_score(y_true, y_pred, average=None)
    return {
        "model": name,
        "accuracy": round(acc, 4),
        "macro_f1": round(f1_mac, 4),
        "weighted_f1": round(f1_wei, 4),
        "per_class_f1": {cls: round(float(f), 4)
                         for cls, f in zip(le.classes_, per_class_f1)},
    }


def run():
    print_section("Fault Classification Training — CWRU")

    X_tr, y_tr_m, y_tr_b, X_va, y_va_m, y_va_b, X_te, y_te_m, y_te_b, le = load_data()
    print(f"  Train: {X_tr.shape}  classes={np.unique(y_tr_m).size}")
    print(f"  Val  : {X_va.shape}")
    print(f"  Test : {X_te.shape}")
    print(f"  Classes: {list(le.classes_)}")

    # Normal class index
    normal_idx = int(np.where(le.classes_ == "Normal_1")[0][0])
    print(f"  Normal class index: {normal_idx}")

    results_val  = {}
    results_test = {}
    models       = {}
    probs_val_all  = {}
    probs_test_all = {}

    # ------------------------------------------------------------------
    # Model 1: RandomForestClassifier
    # ------------------------------------------------------------------
    print_section("Model 1: RandomForestClassifier")
    rf = RandomForestClassifier(n_estimators=300, max_features="sqrt",
                                 class_weight="balanced", random_state=42, n_jobs=-1)
    rf.fit(X_tr, y_tr_m)

    y_pred_rf_va = rf.predict(X_va)
    y_pred_rf_te = rf.predict(X_te)
    y_prob_rf_va = rf.predict_proba(X_va)
    y_prob_rf_te = rf.predict_proba(X_te)

    r_val  = evaluate_multi("RandomForest", le, y_va_m, y_pred_rf_va)
    r_test = evaluate_multi("RandomForest", le, y_te_m, y_pred_rf_te)
    results_val["RandomForest"]    = r_val
    results_test["RandomForest"]   = r_test
    probs_val_all["RandomForest"]  = y_prob_rf_va
    probs_test_all["RandomForest"] = y_prob_rf_te
    models["RandomForest"] = rf
    joblib.dump(rf, os.path.join(MODEL_DIR, "cwru_random_forest.joblib"))

    print(f"  Val  — Accuracy={r_val['accuracy']:.4f}  MacroF1={r_val['macro_f1']:.4f}")
    print(f"  Test — Accuracy={r_test['accuracy']:.4f}  MacroF1={r_test['macro_f1']:.4f}")
    print(f"\n  Val classification report:\n"
          f"{classification_report(y_va_m, y_pred_rf_va, target_names=le.classes_)}")

    # ------------------------------------------------------------------
    # Model 2: HistGradientBoostingClassifier
    # ------------------------------------------------------------------
    print_section("Model 2: HistGradientBoostingClassifier")
    hgb = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_depth=6,
        early_stopping=True, n_iter_no_change=20,
        random_state=42
    )
    hgb.fit(X_tr, y_tr_m)
    print(f"  Stopped at iteration: {hgb.n_iter_}")

    y_pred_hgb_va = hgb.predict(X_va)
    y_pred_hgb_te = hgb.predict(X_te)
    y_prob_hgb_va = hgb.predict_proba(X_va)
    y_prob_hgb_te = hgb.predict_proba(X_te)

    r_val  = evaluate_multi("HGBClassifier", le, y_va_m, y_pred_hgb_va)
    r_test = evaluate_multi("HGBClassifier", le, y_te_m, y_pred_hgb_te)
    results_val["HGBClassifier"]    = r_val
    results_test["HGBClassifier"]   = r_test
    probs_val_all["HGBClassifier"]  = y_prob_hgb_va
    probs_test_all["HGBClassifier"] = y_prob_hgb_te
    models["HGBClassifier"] = hgb
    joblib.dump(hgb, os.path.join(MODEL_DIR, "cwru_hgb_classifier.joblib"))

    print(f"  Val  — Accuracy={r_val['accuracy']:.4f}  MacroF1={r_val['macro_f1']:.4f}")
    print(f"  Test — Accuracy={r_test['accuracy']:.4f}  MacroF1={r_test['macro_f1']:.4f}")
    print(f"\n  Val classification report:\n"
          f"{classification_report(y_va_m, y_pred_hgb_va, target_names=le.classes_)}")

    # ------------------------------------------------------------------
    # Model 3: MLPClassifier
    # ------------------------------------------------------------------
    print_section("Model 3: MLPClassifier")
    mlp = MLPClassifier(hidden_layer_sizes=(256, 128), activation="relu",
                         solver="adam", max_iter=300, early_stopping=True,
                         validation_fraction=0.1, n_iter_no_change=20,
                         random_state=42)
    mlp.fit(X_tr, y_tr_m)
    print(f"  Stopped at iteration: {mlp.n_iter_}")

    y_pred_mlp_va = mlp.predict(X_va)
    y_pred_mlp_te = mlp.predict(X_te)
    y_prob_mlp_va = mlp.predict_proba(X_va)
    y_prob_mlp_te = mlp.predict_proba(X_te)

    r_val  = evaluate_multi("MLP", le, y_va_m, y_pred_mlp_va)
    r_test = evaluate_multi("MLP", le, y_te_m, y_pred_mlp_te)
    results_val["MLP"]    = r_val
    results_test["MLP"]   = r_test
    probs_val_all["MLP"]  = y_prob_mlp_va
    probs_test_all["MLP"] = y_prob_mlp_te
    models["MLP"] = mlp
    joblib.dump(mlp, os.path.join(MODEL_DIR, "cwru_mlp.joblib"))

    print(f"  Val  — Accuracy={r_val['accuracy']:.4f}  MacroF1={r_val['macro_f1']:.4f}")
    print(f"  Test — Accuracy={r_test['accuracy']:.4f}  MacroF1={r_test['macro_f1']:.4f}")
    print(f"\n  Val classification report:\n"
          f"{classification_report(y_va_m, y_pred_mlp_va, target_names=le.classes_)}")

    # ------------------------------------------------------------------
    # Best model selection
    # ------------------------------------------------------------------
    best_name = max(results_val, key=lambda k: results_val[k]["macro_f1"])
    print_section(f"Best Model: {best_name}  (val MacroF1={results_val[best_name]['macro_f1']:.4f})")
    joblib.dump(models[best_name],
                os.path.join(MODEL_DIR, "cwru_best_model.joblib"))
    print("  Saved: cwru_best_model.joblib")
    for k, v in results_test.items():
        marker = " <-- BEST" if k == best_name else ""
        print(f"    {k:18s}  Accuracy={v['accuracy']:.4f}  MacroF1={v['macro_f1']:.4f}{marker}")

    # ------------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------------
    print_section("Generating Evaluation Plots")

    best_model   = models[best_name]
    best_pred_te = best_model.predict(X_te)
    short_labels = [c.replace("_1", "").replace("_6", "") for c in le.classes_]

    # 1. Confusion matrix (best model)
    cm = confusion_matrix(y_te_m, best_pred_te)
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                xticklabels=short_labels, yticklabels=short_labels,
                linewidths=0.5)
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("Actual",    fontsize=12)
    ax.set_title(f"CWRU Bearing — Confusion Matrix\n{best_name} (Test Set, Accuracy={results_test[best_name]['accuracy']:.4f})",
                 fontsize=12, fontweight="bold")
    plt.xticks(rotation=40, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "cwru_confusion_matrix.png"), dpi=150)
    plt.close()
    print("  Saved: cwru_confusion_matrix.png")

    # 2. RF Feature importance
    fi = rf.feature_importances_
    sorted_idx = np.argsort(fi)[::-1]
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#F44336" if i == sorted_idx[0] else "#2196F3" for i in range(len(fi))]
    ax.bar([FEATURE_NAMES[i] for i in sorted_idx], fi[sorted_idx], color=colors, edgecolor="white")
    ax.set_title("CWRU — Random Forest Feature Importances", fontweight="bold")
    ax.set_ylabel("Importance")
    ax.set_xlabel("Feature")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "cwru_feature_importance.png"), dpi=150)
    plt.close()
    print("  Saved: cwru_feature_importance.png")

    # 3. Per-class F1 comparison
    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(le.classes_))
    width = 0.28
    colors3 = ["#2196F3", "#4CAF50", "#FF5722"]
    for i, (name, color) in enumerate(zip(results_test.keys(), colors3)):
        f1s = [results_test[name]["per_class_f1"][c] for c in le.classes_]
        ax.bar(x + (i - 1) * width, f1s, width, label=name, color=color, alpha=0.85,
               edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(short_labels, rotation=35, ha="right")
    ax.set_ylabel("F1 Score")
    ax.set_ylim([0, 1.15])
    ax.set_title("CWRU — Per-Class F1 Score Comparison (Test Set)", fontweight="bold")
    ax.legend(fontsize=10)
    ax.axhline(1.0, color="k", linestyle="--", linewidth=0.8, alpha=0.5)
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "cwru_per_class_f1.png"), dpi=150)
    plt.close()
    print("  Saved: cwru_per_class_f1.png")

    # 4. PCA projection with predicted labels
    pca = PCA(n_components=2)
    X_all = np.vstack([X_tr, X_va, X_te])
    X_pca = pca.fit_transform(X_all)
    y_all = np.concatenate([y_tr_m, y_va_m, y_te_m])
    X_te_pca = X_pca[len(X_tr)+len(X_va):]

    palette = sns.color_palette("tab10", 10)
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    # True labels
    for cls_idx in range(10):
        mask = y_te_m == cls_idx
        axes[0].scatter(X_te_pca[mask, 0], X_te_pca[mask, 1],
                        color=palette[cls_idx], alpha=0.6, s=15,
                        label=short_labels[cls_idx])
    axes[0].set_title("True Labels", fontweight="bold")
    axes[0].legend(fontsize=7, markerscale=1.5, ncol=2)
    axes[0].set_xlabel("PC1"); axes[0].set_ylabel("PC2")
    # Predicted labels
    for cls_idx in range(10):
        mask = best_pred_te == cls_idx
        axes[1].scatter(X_te_pca[mask, 0], X_te_pca[mask, 1],
                        color=palette[cls_idx], alpha=0.6, s=15)
    axes[1].set_title(f"Predicted Labels ({best_name})", fontweight="bold")
    axes[1].set_xlabel("PC1"); axes[1].set_ylabel("PC2")
    fig.suptitle("CWRU — PCA Test Set: True vs Predicted", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "cwru_pca_decision_boundary.png"), dpi=150)
    plt.close()
    print("  Saved: cwru_pca_decision_boundary.png")

    # 5. Accuracy comparison bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    names = list(results_test.keys())
    accs_val  = [results_val[n]["accuracy"]  for n in names]
    accs_test = [results_test[n]["accuracy"] for n in names]
    x = np.arange(len(names))
    ax.bar(x - 0.2, accs_val,  0.35, label="Validation", color="#2196F3", alpha=0.85)
    ax.bar(x + 0.2, accs_test, 0.35, label="Test",       color="#4CAF50", alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=11)
    ax.set_ylabel("Accuracy")
    ax.set_ylim([0, 1.1])
    ax.set_title("CWRU Fault Classification — Model Comparison", fontweight="bold")
    ax.legend()
    for i, (av, at) in enumerate(zip(accs_val, accs_test)):
        ax.text(i - 0.2, av + 0.01, f"{av:.3f}", ha="center", va="bottom", fontsize=9)
        ax.text(i + 0.2, at + 0.01, f"{at:.3f}", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "cwru_model_comparison.png"), dpi=150)
    plt.close()
    print("  Saved: cwru_model_comparison.png")

    # ------------------------------------------------------------------
    # Save metrics JSON
    # ------------------------------------------------------------------
    metrics = {
        "task": "fault_classification",
        "dataset": "CWRU",
        "best_model": best_name,
        "validation": results_val,
        "test": results_test,
    }
    with open(os.path.join(EVAL_DIR, "cwru_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("  Saved: cwru_metrics.json")

    print_section("Fault Classification Training Complete")
    print(f"  Best model  : {best_name}")
    print(f"  Test Accuracy: {results_test[best_name]['accuracy']:.4f}")
    print(f"  Test MacroF1 : {results_test[best_name]['macro_f1']:.4f}\n")


if __name__ == "__main__":
    run()
