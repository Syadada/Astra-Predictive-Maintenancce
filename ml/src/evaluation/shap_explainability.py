"""
SHAP Explainability — PredictaGuard
Menghasilkan penjelasan konkret untuk setiap prediksi model:
  1. CWRU Bearing Fault (RF TreeExplainer) — 9 fitur, exact SHAP
  2. SKAB Anomaly Detection (RF TreeExplainer) — 480 fitur, agregasi per sensor

Run dari ml/:  python -X utf8 src/evaluation/shap_explainability.py
"""

import os, warnings
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import shap

warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MODEL_DIR    = os.path.join(PROJECT_ROOT, "ml", "models")
PROC_DIR     = os.path.join(PROJECT_ROOT, "ml", "data", "processed")
EVAL_DIR     = os.path.join(MODEL_DIR, "evaluation")
os.makedirs(EVAL_DIR, exist_ok=True)

# ── Nama fitur per dataset ────────────────────────────────────────────────────
CWRU_FEATURES = ["max", "min", "mean", "sd", "rms", "skewness", "kurtosis", "crest", "form"]
CWRU_FEATURE_LABELS = {
    "max":       "Nilai Puncak",
    "min":       "Nilai Lembah",
    "mean":      "Rata-rata Sinyal",
    "sd":        "Standar Deviasi",
    "rms":       "RMS (Getaran Efektif)",
    "skewness":  "Kemiringan Distribusi",
    "kurtosis":  "Ketajaman Impak",
    "crest":     "Faktor Puncak",
    "form":      "Faktor Bentuk",
}
SKAB_SENSORS = [
    "Accelerometer1RMS", "Accelerometer2RMS", "Current",
    "Pressure", "Temperature", "Thermocouple", "Voltage", "Volume Flow RateRMS"
]
SKAB_SENSOR_LABELS = {
    "Accelerometer1RMS":    "Getaran Akselerometer 1",
    "Accelerometer2RMS":    "Getaran Akselerometer 2",
    "Current":              "Arus Listrik",
    "Pressure":             "Tekanan",
    "Temperature":          "Suhu",
    "Thermocouple":         "Termokopel",
    "Voltage":              "Tegangan",
    "Volume Flow RateRMS":  "Laju Aliran",
}

# Warna severity untuk bar chart
SEVERITY_COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#F44336"]


def pct(v):
    return f"{v:.1f}%"


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAS: terjemahkan SHAP ke teks bahasa manusia
# ═══════════════════════════════════════════════════════════════════════════════

def shap_to_text(contributions: dict, prediction: str, confidence: float,
                 context: str = "bearing") -> str:
    """
    contributions = {"RMS (Getaran)": 0.52, "Kurtosis": 0.28, ...}  (nilai 0-1)
    Menghasilkan paragraf penjelasan untuk teknisi.
    """
    sorted_c = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
    top3 = sorted_c[:3]

    if context == "bearing":
        action_map = {
            "OR_021_6_1": "segera hentikan mesin dan ganti bearing outer race",
            "OR_014_6_1": "jadwalkan penggantian bearing outer race dalam 36 jam",
            "OR_007_6_1": "lakukan inspeksi visual bearing outer race",
            "IR_021_1":   "hentikan mesin darurat — inner race rusak parah",
            "IR_014_1":   "rencanakan penggantian inner race dalam 36 jam",
            "IR_007_1":   "jadwalkan pelumasan dan inspeksi inner race",
            "Ball_021_1": "ganti elemen bola bearing segera",
            "Ball_014_1": "jadwalkan penggantian bola bearing",
            "Ball_007_1": "lakukan pelumasan ulang dan pantau getaran",
            "Normal_1":   "tidak ada tindakan diperlukan, lanjutkan operasi",
        }
        action = action_map.get(prediction, "periksa kondisi bearing")
        tipe = prediction.replace("_", " ").replace("1", "").strip()

        lines = [
            f"DIAGNOSIS: {tipe} (keyakinan model {confidence*100:.0f}%)",
            "",
            "FAKTOR PENYEBAB:",
        ]
        for name, pct_val in top3:
            bar = "█" * int(pct_val * 20)
            lines.append(f"  {name:<28s} {pct_val*100:5.1f}%  |{bar}")
        lines += [
            "",
            f"REKOMENDASI: {action.capitalize()}.",
            "",
            "PENJELASAN TEKNIS:",
        ]
        for name, pct_val in top3:
            if pct_val > 0.30:
                lines.append(f"  - {name} menyimpang jauh dari kondisi normal ({pct_val*100:.0f}% kontribusi).")
        return "\n".join(lines)

    elif context == "anomaly":
        lines = [
            f"ANOMALI TERDETEKSI (keyakinan {confidence*100:.0f}%)",
            "",
            "SENSOR YANG MENYIMPANG:",
        ]
        for name, pct_val in top3:
            bar = "█" * int(pct_val * 20)
            lines.append(f"  {name:<30s} {pct_val*100:5.1f}%  |{bar}")
        dominant = top3[0][0]
        lines += [
            "",
            f"KESIMPULAN: Anomali didominasi oleh penyimpangan pada {dominant}.",
            "Periksa kondisi fisik sensor tersebut dan area sekitarnya.",
        ]
        return "\n".join(lines)

    return str(contributions)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 1: CWRU Bearing Fault — TreeExplainer
# ═══════════════════════════════════════════════════════════════════════════════

def demo_cwru_shap():
    print("\n" + "="*60)
    print("  SHAP Demo 1: CWRU Bearing Fault Classification")
    print("="*60)

    # Load model + scaler + label encoder
    rf_model = joblib.load(os.path.join(MODEL_DIR, "cwru_random_forest.joblib"))
    scaler   = joblib.load(os.path.join(PROC_DIR,  "cwru_scaler.joblib"))
    le       = joblib.load(os.path.join(PROC_DIR,  "cwru_label_encoder.joblib"))

    # Load test data
    d       = np.load(os.path.join(PROC_DIR, "cwru_features.npz"), allow_pickle=True)
    X_test  = d["X_test"].astype(np.float64)
    y_test  = d["y_multi_test"]

    # Normalisasi (model ditraining pada data yang sudah di-scale)
    X_test_sc = scaler.transform(X_test)

    # ── Buat SHAP explainer dari data train (background) ──────────────────────
    X_train_sc = scaler.transform(d["X_train"].astype(np.float64))
    explainer  = shap.TreeExplainer(rf_model, data=X_train_sc[:200],
                                    feature_perturbation="interventional")

    # ── Pilih dua contoh konkret ───────────────────────────────────────────────
    # Contoh A: OR_021_6_1 (outer race fault, berat)
    target_class = "OR_021_6_1"
    target_idx   = le.transform([target_class])[0]
    mask_A       = y_test == target_idx
    idx_A        = np.where(mask_A)[0][0]

    # Contoh B: Normal
    normal_idx = le.transform(["Normal_1"])[0]
    mask_B     = y_test == normal_idx
    idx_B      = np.where(mask_B)[0][0]

    samples = {"OR_021_6_1 (Outer Race Berat)": idx_A, "Normal_1": idx_B}

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    all_shap_results = {}
    for ax, (label, idx) in zip(axes, samples.items()):
        x        = X_test_sc[idx:idx+1]
        sv       = explainer.shap_values(x)          # (1, 9, n_classes) di SHAP>=0.46

        pred_idx  = rf_model.predict(x)[0]
        pred_cls  = le.classes_[pred_idx]
        pred_prob = rf_model.predict_proba(x)[0][pred_idx]

        # SHAP 0.52+ mengembalikan ndarray (n_samples, n_features, n_classes)
        if isinstance(sv, np.ndarray) and sv.ndim == 3:
            shap_for_pred = sv[0, :, pred_idx]       # (9,)
        else:
            shap_for_pred = sv[pred_idx][0]           # fallback list format
        abs_shap      = np.abs(shap_for_pred)
        pct_contrib   = abs_shap / (abs_shap.sum() + 1e-9)

        print(f"\n  Sampel: {label}")
        print(f"    Prediksi : {pred_cls}  (keyakinan {pred_prob*100:.1f}%)")
        print(f"    True     : {le.classes_[y_test[idx]]}")
        print(f"    SHAP kontribusi per fitur:")

        contrib_dict = {}
        for fname, sv_val, pct_v in sorted(
                zip(CWRU_FEATURES, shap_for_pred, pct_contrib),
                key=lambda x: abs(x[1]), reverse=True):
            direction = "naik" if sv_val > 0 else "turun"
            label_id  = CWRU_FEATURE_LABELS[fname]
            print(f"      {label_id:28s}  {sv_val:+.4f}  ({pct_v*100:5.1f}%)  [{direction}]")
            contrib_dict[label_id] = float(pct_v)

        all_shap_results[label] = (pred_cls, pred_prob, contrib_dict, shap_for_pred)

        # Plot bar chart per sampel
        sorted_items = sorted(zip(CWRU_FEATURES, shap_for_pred, pct_contrib),
                              key=lambda x: abs(x[1]), reverse=True)
        feat_labels  = [CWRU_FEATURE_LABELS[f] for f, _, _ in sorted_items]
        shap_vals    = [v for _, v, _ in sorted_items]
        colors       = ["#F44336" if v > 0 else "#2196F3" for v in shap_vals]

        bars = ax.barh(feat_labels[::-1], shap_vals[::-1], color=colors[::-1], alpha=0.85)
        ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
        ax.set_xlabel("Nilai SHAP (+ = mendorong ke kelas ini, - = menolak)")
        ax.set_title(f"{label}\nPrediksi: {pred_cls}  ({pred_prob*100:.0f}%)", fontweight="bold", fontsize=10)
        ax.tick_params(axis="y", labelsize=8)

        patch_pos = mpatches.Patch(color="#F44336", alpha=0.85, label="Mendorong prediksi")
        patch_neg = mpatches.Patch(color="#2196F3", alpha=0.85, label="Menolak prediksi")
        ax.legend(handles=[patch_pos, patch_neg], fontsize=8)

    plt.suptitle("CWRU Bearing — SHAP Feature Contributions per Prediksi", fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(EVAL_DIR, "shap_cwru_comparison.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Plot tersimpan: {path}")

    # ── Teks penjelasan bahasa manusia ────────────────────────────────────────
    pred_cls, pred_prob, contrib_dict, _ = all_shap_results["OR_021_6_1 (Outer Race Berat)"]
    print("\n" + "-"*60)
    print("  PENJELASAN UNTUK TEKNISI:")
    print("-"*60)
    print(shap_to_text(contrib_dict, pred_cls, pred_prob, context="bearing"))

    return all_shap_results


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 2: SKAB Anomaly Detection — TreeExplainer + agregasi per sensor
# ═══════════════════════════════════════════════════════════════════════════════

def demo_skab_shap():
    print("\n" + "="*60)
    print("  SHAP Demo 2: SKAB Anomaly Detection")
    print("="*60)

    rf_model = joblib.load(os.path.join(MODEL_DIR, "skab_best_model.joblib"))
    d        = np.load(os.path.join(PROC_DIR, "skab_windows.npz"), allow_pickle=True)
    X_test   = d["X_test"]            # (N, 60, 8)
    y_test   = d["y_test"]            # (N,)

    # Flatten untuk model: (N, 480)
    X_flat_test  = X_test.reshape(len(X_test), -1).astype(np.float32)
    X_flat_train = d["X_train"].reshape(len(d["X_train"]), -1).astype(np.float32)

    # SHAP TreeExplainer — background = subset train
    background = X_flat_train[:100]
    explainer  = shap.TreeExplainer(rf_model, data=background,
                                    feature_perturbation="interventional")

    # Pilih satu window anomali dan satu window normal
    anomaly_idxs = np.where(y_test == 1)[0]
    normal_idxs  = np.where(y_test == 0)[0]

    # Pilih anomali dengan confidence tertinggi
    probs = rf_model.predict_proba(X_flat_test[anomaly_idxs[:20]])[:, 1]
    best_anomaly_local = np.argmax(probs)
    idx_anomaly = anomaly_idxs[best_anomaly_local]
    idx_normal  = normal_idxs[5]

    samples = {"Anomali Terdeteksi": idx_anomaly, "Kondisi Normal": idx_normal}

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    all_results = {}

    for ax, (label, idx) in zip(axes, samples.items()):
        x_flat   = X_flat_test[idx:idx+1]
        pred     = rf_model.predict(x_flat)[0]
        prob     = rf_model.predict_proba(x_flat)[0][pred]
        label_str = "ANOMALI" if pred == 1 else "NORMAL"

        # SHAP untuk kelas anomali (index 1)
        sv_raw   = explainer.shap_values(x_flat)    # (1, 480, 2) atau list
        if isinstance(sv_raw, np.ndarray) and sv_raw.ndim == 3:
            sv_anom = sv_raw[0, :, 1]               # (480,) kelas anomali
        else:
            sv_anom = sv_raw[1][0]                  # fallback

        # Agregasi per sensor: sum |shap| untuk 60 timestep tiap sensor
        n_sensors  = len(SKAB_SENSORS)
        window_len = 60
        sv_2d      = sv_anom.reshape(window_len, n_sensors)  # (60, 8)
        sensor_importance = np.abs(sv_2d).sum(axis=0)        # (8,) — sum waktu
        total             = sensor_importance.sum() + 1e-9
        sensor_pct        = sensor_importance / total

        print(f"\n  Sampel: {label}")
        print(f"    Prediksi: {label_str}  (prob anomali: {rf_model.predict_proba(x_flat)[0][1]*100:.1f}%)")
        print(f"    Kontribusi per sensor:")
        contrib_dict = {}
        for sname, imp, pct_v in sorted(
                zip(SKAB_SENSORS, sensor_importance, sensor_pct),
                key=lambda x: x[1], reverse=True):
            lbl = SKAB_SENSOR_LABELS[sname]
            print(f"      {lbl:30s}  {pct_v*100:5.1f}%")
            contrib_dict[lbl] = float(pct_v)

        all_results[label] = (label_str, prob, contrib_dict)

        # Plot donut / bar horizontal
        sorted_items = sorted(zip(SKAB_SENSORS, sensor_pct),
                              key=lambda x: x[1], reverse=True)
        feat_labels  = [SKAB_SENSOR_LABELS[s] for s, _ in sorted_items]
        pct_vals     = [p for _, p in sorted_items]
        bar_colors   = [SEVERITY_COLORS[min(i, len(SEVERITY_COLORS)-1)] for i in range(len(pct_vals))]

        bars = ax.barh(feat_labels[::-1], [p*100 for p in pct_vals[::-1]],
                       color=bar_colors[::-1], alpha=0.85)
        for bar, pv in zip(bars, pct_vals[::-1]):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                    f"{pv*100:.1f}%", va="center", fontsize=8)
        ax.set_xlabel("Kontribusi SHAP (%)")
        ax.set_xlim(0, max(p*100 for p in pct_vals) * 1.25)
        title_color = "#F44336" if pred == 1 else "#4CAF50"
        ax.set_title(f"{label}\nPrediksi: {label_str}  (prob={prob*100:.0f}%)",
                     fontweight="bold", fontsize=10, color=title_color)
        ax.tick_params(axis="y", labelsize=8)

    plt.suptitle("SKAB Pump — SHAP Sensor Contributions per Window", fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(EVAL_DIR, "shap_skab_comparison.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Plot tersimpan: {path}")

    # ── Teks penjelasan ───────────────────────────────────────────────────────
    label_str, prob, contrib_dict = all_results["Anomali Terdeteksi"]
    print("\n" + "-"*60)
    print("  PENJELASAN UNTUK TEKNISI (ANOMALI PUMP):")
    print("-"*60)
    print(shap_to_text(contrib_dict, "anomaly", prob, context="anomaly"))

    return all_results


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 3: Global Feature Importance — 100 sampel agregat
# ═══════════════════════════════════════════════════════════════════════════════

def demo_global_importance():
    print("\n" + "="*60)
    print("  SHAP Demo 3: Global Importance (100 sampel CWRU)")
    print("="*60)

    rf_model  = joblib.load(os.path.join(MODEL_DIR, "cwru_random_forest.joblib"))
    scaler    = joblib.load(os.path.join(PROC_DIR,  "cwru_scaler.joblib"))
    le        = joblib.load(os.path.join(PROC_DIR,  "cwru_label_encoder.joblib"))
    d         = np.load(os.path.join(PROC_DIR, "cwru_features.npz"), allow_pickle=True)

    X_train_sc = scaler.transform(d["X_train"].astype(np.float64))
    X_test_sc  = scaler.transform(d["X_test"].astype(np.float64))

    explainer  = shap.TreeExplainer(rf_model, data=X_train_sc[:200],
                                    feature_perturbation="interventional")
    sv_all     = explainer.shap_values(X_test_sc[:100])   # (100, 9, n_classes) atau list

    # Mean |SHAP| per fitur, dirata-rata semua kelas
    if isinstance(sv_all, np.ndarray) and sv_all.ndim == 3:
        mean_abs = np.abs(sv_all).mean(axis=(0, 2))        # (9,)
    else:
        mean_abs = np.mean([np.abs(sv_all[k]).mean(axis=0)
                            for k in range(len(le.classes_))], axis=0)
    total    = mean_abs.sum()
    pct_arr  = mean_abs / total

    print("  Global SHAP importance (rata-rata 100 sampel, semua kelas):")
    for fname, imp, pct_v in sorted(zip(CWRU_FEATURES, mean_abs, pct_arr),
                                    key=lambda x: x[1], reverse=True):
        bar = "#" * int(pct_v * 50)
        print(f"    {CWRU_FEATURE_LABELS[fname]:28s}  {pct_v*100:5.1f}%  |{bar}")

    # Plot
    sorted_items  = sorted(zip(CWRU_FEATURES, pct_arr), key=lambda x: x[1], reverse=True)
    feat_labels   = [CWRU_FEATURE_LABELS[f] for f, _ in sorted_items]
    pct_vals      = [p*100 for _, p in sorted_items]
    bar_colors    = ["#F44336" if p > 20 else "#FF9800" if p > 10 else "#2196F3" for p in pct_vals]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(feat_labels[::-1], pct_vals[::-1], color=bar_colors[::-1], alpha=0.85)
    for bar, pv in zip(bars, pct_vals[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f"{pv:.1f}%", va="center", fontsize=9)
    ax.set_xlabel("Kontribusi SHAP rata-rata (%)")
    ax.set_title("CWRU — Global SHAP Feature Importance\n(rata-rata absolut dari 100 sampel test, semua kelas)",
                 fontweight="bold")
    ax.set_xlim(0, max(pct_vals) * 1.2)
    plt.tight_layout()
    path = os.path.join(EVAL_DIR, "shap_cwru_global.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Plot tersimpan: {path}")

    return dict(zip(CWRU_FEATURES, pct_arr))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("PredictaGuard — SHAP Explainability Demo")

    cwru_results   = demo_cwru_shap()
    skab_results   = demo_skab_shap()
    global_imp     = demo_global_importance()

    print("\n" + "="*60)
    print("  Output files tersimpan di ml/models/evaluation/:")
    print("    shap_cwru_comparison.png  — SHAP per prediksi bearing fault")
    print("    shap_skab_comparison.png  — SHAP per sensor anomali pump")
    print("    shap_cwru_global.png      — global importance semua sampel")
    print("="*60)
