"""
RUL Prediction — NASA CMAPSS (FD001–FD004, all 4 splits).
Trains 3 regression models per split on flattened (N, window×n_sensors) windows:
  1. RandomForestRegressor
  2. HistGradientBoostingRegressor
  3. MLPRegressor

Metrics: RMSE, MAE, R², NASA Score.
Saves per-split model files + cmapss_best_model.joblib (FD001 best, API compat).
Run from ml/:  python -X utf8 src/models/train_rul_prediction.py
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

from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

warnings.filterwarnings("ignore")


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR     = os.path.join(PROJECT_ROOT, "ml", "data", "processed")
MODEL_DIR    = os.path.join(PROJECT_ROOT, "ml", "models")
EVAL_DIR     = os.path.join(MODEL_DIR, "evaluation")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(EVAL_DIR,  exist_ok=True)

ALL_SPLITS = ["FD001", "FD002", "FD003", "FD004"]


def print_section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def nasa_score(y_true, y_pred):
    """NASA competition scoring — late predictions penalised more than early."""
    d = y_pred - y_true
    score = np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1)
    return float(np.sum(score))


def load_data(split: str):
    d = np.load(os.path.join(DATA_DIR, f"cmapss_{split}.npz"), allow_pickle=True)
    X_tr = d["X_train"].reshape(len(d["X_train"]), -1).astype(np.float32)
    X_va = d["X_val"].reshape(len(d["X_val"]),   -1).astype(np.float32)
    X_te = d["X_test"].reshape(len(d["X_test"]),  -1).astype(np.float32)
    return (X_tr, d["y_train"].astype(np.float32),
            X_va, d["y_val"].astype(np.float32),
            X_te, d["y_test"].astype(np.float32))


def evaluate(name, y_true, y_pred):
    rmse  = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae   = float(mean_absolute_error(y_true, y_pred))
    r2    = float(r2_score(y_true, y_pred))
    score = nasa_score(y_true, y_pred)
    return {"model": name,
            "rmse": round(rmse, 4), "mae": round(mae, 4),
            "r2":   round(r2, 4),   "nasa_score": round(score, 2)}


def generate_plots(split, y_te, preds_test, results_val, results_test, models, best_name):
    colors3 = ["#2196F3", "#4CAF50", "#FF5722"]
    best_pred_te = preds_test[best_name]
    best_model   = models[best_name]

    # 1. Predicted vs actual
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.scatter(y_te, best_pred_te, alpha=0.3, s=10, color="#2196F3")
    lim = (0, 130)
    ax.plot(lim, lim, "r--", linewidth=1.5, label="Perfect prediction")
    ax.set_xlabel("Actual RUL (cycles)")
    ax.set_ylabel("Predicted RUL (cycles)")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_title(f"CMAPSS {split} — Predicted vs Actual RUL\n"
                 f"{best_name}  RMSE={results_test[best_name]['rmse']:.3f}  "
                 f"R2={results_test[best_name]['r2']:.4f}",
                 fontweight="bold")
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, f"cmapss_{split}_predicted_vs_actual.png"), dpi=150)
    plt.close()

    # 2. Error distribution
    fig, ax = plt.subplots(figsize=(9, 5))
    for (name, pred), color in zip(preds_test.items(), colors3):
        errors = pred - y_te
        ax.hist(errors, bins=50, alpha=0.55, color=color, label=name, density=True)
    ax.axvline(0, color="k", linewidth=1.5, linestyle="--")
    ax.set_xlabel("Prediction Error (predicted − actual cycles)")
    ax.set_ylabel("Density")
    ax.set_title(f"CMAPSS {split} — RUL Prediction Error Distribution (Test Set)",
                 fontweight="bold")
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, f"cmapss_{split}_rul_error_distribution.png"), dpi=150)
    plt.close()

    # 3. Example engine degradation curves
    raw = np.load(os.path.join(DATA_DIR, f"cmapss_{split}.npz"), allow_pickle=True)
    X_te_raw = raw["X_test"]
    y_te_raw = raw["y_test"]
    all_preds = best_model.predict(X_te_raw.reshape(len(X_te_raw), -1))

    breakpoints = [0]
    for i in range(1, len(y_te_raw)):
        if y_te_raw[i] > y_te_raw[i - 1] + 5:
            breakpoints.append(i)
    breakpoints.append(len(y_te_raw))

    segs = [(breakpoints[i], breakpoints[i + 1]) for i in range(len(breakpoints) - 1)]
    segs_sorted = sorted(segs, key=lambda s: s[1] - s[0], reverse=True)[:3]

    if segs_sorted:
        n_eng = len(segs_sorted)
        fig, axes = plt.subplots(1, n_eng, figsize=(6 * n_eng, 5))
        if n_eng == 1:
            axes = [axes]
        eng_colors = ["#2196F3", "#4CAF50", "#FF5722"]
        for ax, (start, end), color in zip(axes, segs_sorted, eng_colors):
            true_rul = y_te_raw[start:end]
            pred_rul = all_preds[start:end]
            cycles   = np.arange(len(true_rul))
            ax.plot(cycles, true_rul, color="black",  linewidth=1.5, label="Actual RUL")
            ax.plot(cycles, pred_rul, color=color,    linewidth=1.5, linestyle="--",
                    label=f"Predicted ({best_name})")
            ax.fill_between(cycles, true_rul, pred_rul, alpha=0.15, color=color)
            rmse_eng = np.sqrt(np.mean((pred_rul - true_rul) ** 2))
            ax.set_title(f"Engine ({end - start} windows)\nRMSE={rmse_eng:.2f}", fontweight="bold")
            ax.set_xlabel("Window index")
            ax.set_ylabel("RUL (cycles)")
            ax.legend(fontsize=8)
            ax.axhline(0, color="red", linestyle=":", linewidth=1, alpha=0.6)
        fig.suptitle(f"CMAPSS {split} — RUL Degradation Curves (Sample Engines)",
                     fontsize=13, fontweight="bold")
        plt.tight_layout()
        fig.savefig(os.path.join(EVAL_DIR, f"cmapss_{split}_example_engine_rul.png"), dpi=150)
        plt.close()

    # 4. RMSE comparison bar chart
    fig, ax = plt.subplots(figsize=(9, 5))
    names = list(results_test.keys())
    rmses_val  = [results_val[n]["rmse"]  for n in names]
    rmses_test = [results_test[n]["rmse"] for n in names]
    x = np.arange(len(names))
    ax.bar(x - 0.2, rmses_val,  0.35, label="Validation", color="#2196F3", alpha=0.85)
    ax.bar(x + 0.2, rmses_test, 0.35, label="Test",       color="#4CAF50", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=11)
    ax.set_ylabel("RMSE (cycles)")
    ax.set_title(f"CMAPSS {split} RUL Prediction — Model Comparison", fontweight="bold")
    ax.legend()
    for i, (rv, rt) in enumerate(zip(rmses_val, rmses_test)):
        ax.text(i - 0.2, rv + 0.3, f"{rv:.2f}", ha="center", va="bottom", fontsize=9)
        ax.text(i + 0.2, rt + 0.3, f"{rt:.2f}", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, f"cmapss_{split}_model_comparison.png"), dpi=150)
    plt.close()

    print(f"  Plots: {split}_predicted_vs_actual, _rul_error_distribution, "
          f"_example_engine_rul, _model_comparison")


def train_split(split: str):
    """Train 3 models on one CMAPSS split. Returns (best_name, results_val, results_test)."""
    print_section(f"RUL Prediction — CMAPSS {split}")

    X_tr, y_tr, X_va, y_va, X_te, y_te = load_data(split)
    print(f"  Train: {X_tr.shape}  RUL mean={y_tr.mean():.1f}  std={y_tr.std():.1f}")
    print(f"  Val  : {X_va.shape}  RUL mean={y_va.mean():.1f}  std={y_va.std():.1f}")
    print(f"  Test : {X_te.shape}  RUL mean={y_te.mean():.1f}  std={y_te.std():.1f}")

    results_val  = {}
    results_test = {}
    preds_test   = {}
    models       = {}

    # ------------------------------------------------------------------
    # Model 1: RandomForestRegressor
    # ------------------------------------------------------------------
    print(f"\n  [1] RandomForestRegressor")
    rf = RandomForestRegressor(n_estimators=200, max_depth=20,
                                min_samples_leaf=5, random_state=42, n_jobs=-1)
    rf.fit(X_tr, y_tr)
    r_val  = evaluate("RandomForest", y_va, rf.predict(X_va))
    r_test = evaluate("RandomForest", y_te, rf.predict(X_te))
    print(f"      Val  RMSE={r_val['rmse']:.3f}  MAE={r_val['mae']:.3f}  "
          f"R2={r_val['r2']:.4f}  NASA={r_val['nasa_score']:.0f}")
    print(f"      Test RMSE={r_test['rmse']:.3f}  MAE={r_test['mae']:.3f}  "
          f"R2={r_test['r2']:.4f}  NASA={r_test['nasa_score']:.0f}")
    results_val["RandomForest"]  = r_val
    results_test["RandomForest"] = r_test
    preds_test["RandomForest"]   = rf.predict(X_te)
    models["RandomForest"] = rf
    joblib.dump(rf, os.path.join(MODEL_DIR, f"cmapss_{split}_random_forest.joblib"))

    # ------------------------------------------------------------------
    # Model 2: HistGradientBoostingRegressor
    # ------------------------------------------------------------------
    print(f"\n  [2] HistGradientBoostingRegressor")
    hgb = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, max_depth=8,
        early_stopping=True, n_iter_no_change=20, random_state=42
    )
    hgb.fit(X_tr, y_tr)
    print(f"      Stopped at iteration: {hgb.n_iter_}")
    r_val  = evaluate("HGBRegressor", y_va, hgb.predict(X_va))
    r_test = evaluate("HGBRegressor", y_te, hgb.predict(X_te))
    print(f"      Val  RMSE={r_val['rmse']:.3f}  MAE={r_val['mae']:.3f}  "
          f"R2={r_val['r2']:.4f}  NASA={r_val['nasa_score']:.0f}")
    print(f"      Test RMSE={r_test['rmse']:.3f}  MAE={r_test['mae']:.3f}  "
          f"R2={r_test['r2']:.4f}  NASA={r_test['nasa_score']:.0f}")
    results_val["HGBRegressor"]  = r_val
    results_test["HGBRegressor"] = r_test
    preds_test["HGBRegressor"]   = hgb.predict(X_te)
    models["HGBRegressor"] = hgb
    joblib.dump(hgb, os.path.join(MODEL_DIR, f"cmapss_{split}_hgb_regressor.joblib"))

    # ------------------------------------------------------------------
    # Model 3: MLPRegressor
    # ------------------------------------------------------------------
    print(f"\n  [3] MLPRegressor (512-256-128)")
    mlp = MLPRegressor(hidden_layer_sizes=(512, 256, 128), activation="relu",
                        solver="adam", max_iter=300, early_stopping=True,
                        validation_fraction=0.1, n_iter_no_change=20,
                        random_state=42)
    mlp.fit(X_tr, y_tr)
    print(f"      Stopped at iteration: {mlp.n_iter_}")
    r_val  = evaluate("MLP", y_va, mlp.predict(X_va))
    r_test = evaluate("MLP", y_te, mlp.predict(X_te))
    print(f"      Val  RMSE={r_val['rmse']:.3f}  MAE={r_val['mae']:.3f}  "
          f"R2={r_val['r2']:.4f}  NASA={r_val['nasa_score']:.0f}")
    print(f"      Test RMSE={r_test['rmse']:.3f}  MAE={r_test['mae']:.3f}  "
          f"R2={r_test['r2']:.4f}  NASA={r_test['nasa_score']:.0f}")
    results_val["MLP"]  = r_val
    results_test["MLP"] = r_test
    preds_test["MLP"]   = mlp.predict(X_te)
    models["MLP"] = mlp
    joblib.dump(mlp, os.path.join(MODEL_DIR, f"cmapss_{split}_mlp.joblib"))

    # ------------------------------------------------------------------
    # Best model (lowest val RMSE)
    # ------------------------------------------------------------------
    best_name = min(results_val, key=lambda k: results_val[k]["rmse"])
    print_section(f"{split} Best: {best_name}  val RMSE={results_val[best_name]['rmse']:.3f}")
    joblib.dump(models[best_name],
                os.path.join(MODEL_DIR, f"cmapss_{split}_best_model.joblib"))
    print(f"  Saved: cmapss_{split}_best_model.joblib")
    for k, v in results_test.items():
        marker = " <-- BEST" if k == best_name else ""
        print(f"    {k:18s}  Test RMSE={v['rmse']:.3f}  MAE={v['mae']:.3f}  "
              f"R2={v['r2']:.4f}  NASA={v['nasa_score']:.0f}{marker}")

    generate_plots(split, y_te, preds_test, results_val, results_test, models, best_name)

    return best_name, results_val, results_test


def run():
    all_results = {}
    overall_best = {"rmse": float("inf"), "split": None, "model": None}

    for split in ALL_SPLITS:
        best_name, results_val, results_test = train_split(split)
        all_results[split] = {
            "best_model": best_name,
            "validation": results_val,
            "test": results_test,
        }
        test_rmse = results_test[best_name]["rmse"]
        if test_rmse < overall_best["rmse"]:
            overall_best = {"rmse": test_rmse, "split": split, "model": best_name}

    # ------------------------------------------------------------------
    # Cross-split comparison plot
    # ------------------------------------------------------------------
    print_section("Cross-Split Summary")
    best_vals  = [all_results[s]["validation"][all_results[s]["best_model"]]["rmse"] for s in ALL_SPLITS]
    best_tests = [all_results[s]["test"][all_results[s]["best_model"]]["rmse"]       for s in ALL_SPLITS]
    x = np.arange(len(ALL_SPLITS))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - 0.2, best_vals,  0.35, label="Val RMSE",  color="#2196F3", alpha=0.85)
    ax.bar(x + 0.2, best_tests, 0.35, label="Test RMSE", color="#4CAF50", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(ALL_SPLITS, fontsize=12)
    ax.set_ylabel("RMSE (cycles)")
    ax.set_title("CMAPSS Multi-Split RUL Prediction — Best Model per Split", fontweight="bold")
    ax.legend()
    for i, (rv, rt) in enumerate(zip(best_vals, best_tests)):
        ax.text(i - 0.2, rv + 0.3, f"{rv:.2f}", ha="center", va="bottom", fontsize=9)
        ax.text(i + 0.2, rt + 0.3, f"{rt:.2f}", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    fig.savefig(os.path.join(EVAL_DIR, "cmapss_multi_split_comparison.png"), dpi=150)
    plt.close()
    print("  Saved: cmapss_multi_split_comparison.png")

    # ------------------------------------------------------------------
    # Save combined metrics JSON
    # ------------------------------------------------------------------
    metrics = {
        "task": "rul_prediction",
        "dataset": "CMAPSS_FD001-FD004",
        "rul_cap": 125,
        "window_size": 30,
        "splits": all_results,
        "overall_best": overall_best,
    }
    with open(os.path.join(EVAL_DIR, "cmapss_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("  Saved: cmapss_metrics.json")

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    print_section("Multi-Split Training Complete")
    for split in ALL_SPLITS:
        bn = all_results[split]["best_model"]
        rt = all_results[split]["test"][bn]
        marker = " <-- OVERALL BEST" if split == overall_best["split"] else ""
        print(f"  {split}  best={bn:15s}  "
              f"RMSE={rt['rmse']:.3f}  MAE={rt['mae']:.3f}  "
              f"R2={rt['r2']:.4f}  NASA={rt['nasa_score']:.0f}{marker}")

    # Keep cmapss_best_model.joblib pointing to FD001 best for API backward-compat.
    # The API predictor uses cmapss_FD001_scaler.joblib (14 features), so the model
    # must expect 30×14=420 input features.
    fd001_best_name = all_results["FD001"]["best_model"]
    fd001_best = joblib.load(os.path.join(MODEL_DIR, "cmapss_FD001_best_model.joblib"))
    joblib.dump(fd001_best, os.path.join(MODEL_DIR, "cmapss_best_model.joblib"))
    print(f"\n  cmapss_best_model.joblib → FD001/{fd001_best_name} (API backward-compat)\n")


if __name__ == "__main__":
    run()
