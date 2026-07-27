"""
EDA for the SKAB (Skoltech Anomaly Benchmark) dataset.
Covers: shape, missing values, class distribution, sensor statistics,
correlation, time-series plots, anomaly prevalence per experiment.

Run from ml/:  python src/eda/eda_skab.py
"""

import os
import glob
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")


# Paths

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATASET_ROOT = os.path.join(PROJECT_ROOT, "dataset", "SCAB")
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "ml", "data", "processed", "eda_plots", "skab")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SENSOR_COLS = [
    "Accelerometer1RMS", "Accelerometer2RMS", "Current",
    "Pressure", "Temperature", "Thermocouple", "Voltage", "Volume Flow RateRMS"
]


# Load all SKAB files

def load_skab() -> pd.DataFrame:
    frames = []
    categories = {
        "anomaly-free": os.path.join(DATASET_ROOT, "anomaly-free", "anomaly-free.csv"),
    }
    for cat in ["other", "valve1", "valve2"]:
        for f in sorted(glob.glob(os.path.join(DATASET_ROOT, cat, "*.csv"))):
            key = f"{cat}/{os.path.basename(f)}"
            categories[key] = f

    for cat_name, path in categories.items():
        df = pd.read_csv(path, sep=";", parse_dates=["datetime"])
        df["source_category"] = cat_name.split("/")[0]
        df["source_file"] = cat_name
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("datetime").reset_index(drop=True)
    return combined



# Report helpers

def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def run_eda():
    print_section("SKAB EDA — PredictaGuard")

    df = load_skab()

    # ---- Basic info ----
    print_section("1. Dataset Shape & Types")
    print(f"  Total rows    : {len(df):,}")
    print(f"  Total columns : {df.shape[1]}")
    print(f"  Date range    : {df['datetime'].min()}  to  {df['datetime'].max()}")
    print(f"\n  Dtypes:\n{df.dtypes.to_string()}")

    # ---- Missing values ----
    print_section("2. Missing Values")
    missing = df[SENSOR_COLS].isnull().sum()
    missing_pct = (missing / len(df) * 100).round(3)
    mv = pd.DataFrame({"missing_count": missing, "missing_%": missing_pct})
    print(mv.to_string())
    if missing.sum() == 0:
        print("\n  No missing values detected.")

    # ---- File & category inventory ----
    print_section("3. File Inventory")
    inv = (df.groupby(["source_category", "source_file"])
             .size().rename("rows").reset_index())
    print(inv.to_string(index=False))

    # ---- Anomaly / changepoint distribution ----
    print_section("4. Anomaly & Changepoint Distribution")
    labelled = df.dropna(subset=["anomaly", "changepoint"])
    if len(labelled) == 0:
        print("  No labelled rows (anomaly-free files have no labels).")
    else:
        a_counts = labelled["anomaly"].value_counts().sort_index()
        cp_counts = labelled["changepoint"].value_counts().sort_index()
        print(f"  Labelled rows : {len(labelled):,}")
        print(f"\n  anomaly distribution:\n{a_counts.to_string()}")
        print(f"\n  changepoint distribution:\n{cp_counts.to_string()}")
        a_rate = (labelled["anomaly"].sum() / len(labelled) * 100)
        print(f"\n  Anomaly rate  : {a_rate:.2f}%")

        # Per-file anomaly rate
        per_file = (labelled.groupby("source_file")
                    .apply(lambda g: pd.Series({
                        "rows": len(g),
                        "anomaly_rows": int(g["anomaly"].sum()),
                        "anomaly_%": round(g["anomaly"].mean() * 100, 2)
                    })).reset_index())
        print(f"\n  Per-file anomaly rates:\n{per_file.to_string(index=False)}")

    # ---- Sensor statistics ----
    print_section("5. Sensor Descriptive Statistics")
    stats = df[SENSOR_COLS].describe(percentiles=[0.25, 0.5, 0.75, 0.95]).T
    stats["skewness"] = df[SENSOR_COLS].skew()
    stats["kurtosis"] = df[SENSOR_COLS].kurtosis()
    print(stats.round(4).to_string())

    # ---- Sensor stats: normal vs anomaly ----
    if "anomaly" in df.columns and labelled is not None and len(labelled) > 0:
        print_section("5b. Sensor Means: Normal vs Anomaly (labelled rows only)")
        grp = labelled.groupby("anomaly")[SENSOR_COLS].mean().T
        grp.columns = ["Normal (anomaly=0)", "Anomaly (anomaly=1)"]
        grp["delta_%"] = ((grp["Anomaly (anomaly=1)"] - grp["Normal (anomaly=0)"])
                          / grp["Normal (anomaly=0)"].abs() * 100).round(2)
        print(grp.round(4).to_string())

    # ---- Correlation heatmap ----
    print_section("6. Correlation Analysis")
    corr = df[SENSOR_COLS].corr()
    print(corr.round(3).to_string())

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, square=True, linewidths=0.5, ax=ax)
    ax.set_title("SKAB — Sensor Correlation Heatmap", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "correlation_heatmap.png"), dpi=150)
    plt.close()
    print("  Saved: correlation_heatmap.png")

    # ---- Sensor distributions ----
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))
    axes = axes.flatten()
    for i, col in enumerate(SENSOR_COLS):
        axes[i].hist(df[col].dropna(), bins=60, color="#2196F3", edgecolor="white", linewidth=0.3)
        axes[i].set_title(col, fontsize=9, fontweight="bold")
        axes[i].set_xlabel("Value")
        axes[i].set_ylabel("Count")
    fig.suptitle("SKAB — Sensor Feature Distributions", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "sensor_distributions.png"), dpi=150)
    plt.close()
    print("  Saved: sensor_distributions.png")

    # ---- Time-series sample: anomaly-free vs anomalous ----
    af_df = df[df["source_category"] == "anomaly-free"].head(600)
    an_df = df[(df["source_category"] != "anomaly-free") &
               (df.get("anomaly", pd.Series(0, index=df.index)) == 1)].head(600)

    fig, axes = plt.subplots(4, 2, figsize=(18, 14))
    axes = axes.flatten()
    for i, col in enumerate(SENSOR_COLS):
        if len(af_df):
            axes[i].plot(range(len(af_df)), af_df[col].values,
                         label="Normal", color="#4CAF50", alpha=0.7, linewidth=0.8)
        if len(an_df):
            axes[i].plot(range(len(an_df)), an_df[col].values,
                         label="Anomaly", color="#F44336", alpha=0.7, linewidth=0.8)
        axes[i].set_title(col, fontsize=9, fontweight="bold")
        axes[i].legend(fontsize=7)
    fig.suptitle("SKAB — Normal vs Anomaly Sensor Traces (600-sample excerpt)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "normal_vs_anomaly_traces.png"), dpi=150)
    plt.close()
    print("  Saved: normal_vs_anomaly_traces.png")

    # ---- Anomaly prevalence bar chart per file ----
    if "anomaly" in df.columns and len(labelled) > 0:
        per_file_sorted = per_file.sort_values("anomaly_%", ascending=False)
        fig, ax = plt.subplots(figsize=(16, 6))
        bars = ax.bar(range(len(per_file_sorted)), per_file_sorted["anomaly_%"],
                      color="#FF5722", edgecolor="white", linewidth=0.5)
        ax.set_xticks(range(len(per_file_sorted)))
        ax.set_xticklabels(per_file_sorted["source_file"], rotation=75, ha="right", fontsize=7)
        ax.set_ylabel("Anomaly %")
        ax.set_title("SKAB — Anomaly Prevalence per Experiment File", fontsize=13, fontweight="bold")
        ax.axhline(per_file_sorted["anomaly_%"].mean(), color="navy",
                   linestyle="--", linewidth=1.2, label=f"Mean: {per_file_sorted['anomaly_%'].mean():.1f}%")
        ax.legend()
        plt.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "anomaly_prevalence_per_file.png"), dpi=150)
        plt.close()
        print("  Saved: anomaly_prevalence_per_file.png")

    # ---- Category-level anomaly rate ----
    if "anomaly" in df.columns and len(labelled) > 0:
        cat_stats = (labelled.groupby("source_category")
                     .agg(rows=("anomaly", "count"),
                          anomaly_pct=("anomaly", lambda x: x.mean() * 100))
                     .reset_index())
        print_section("7. Category-Level Anomaly Rates")
        print(cat_stats.round(2).to_string(index=False))

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.bar(cat_stats["source_category"], cat_stats["anomaly_pct"],
               color=["#2196F3", "#FF9800", "#9C27B0"], edgecolor="white")
        ax.set_ylabel("Anomaly %")
        ax.set_title("SKAB — Anomaly Rate by Category", fontsize=12, fontweight="bold")
        for bar, pct in zip(ax.patches, cat_stats["anomaly_pct"]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    f"{pct:.1f}%", ha="center", va="bottom", fontsize=9)
        plt.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "anomaly_rate_by_category.png"), dpi=150)
        plt.close()
        print("  Saved: anomaly_rate_by_category.png")

    print_section("SKAB EDA Complete")
    print(f"  Plots saved to: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    run_eda()
