"""
EDA for the NASA CMAPSS (Commercial Modular Aero-Propulsion System Simulation) dataset.
Covers all 4 sub-datasets (FD001–FD004): engine count, cycle stats, near-constant sensor
detection, degradation trajectories, and RUL distributions.

Run from ml/:  python src/eda/eda_cmapss.py
"""

import os
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
DATASET_ROOT = os.path.join(PROJECT_ROOT, "dataset", "CMaps")
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "ml", "data", "processed", "eda_plots", "cmapss")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Column names per CMAPSS documentation
COL_NAMES = (
    ["unit", "cycle", "op_setting_1", "op_setting_2", "op_setting_3"]
    + [f"sensor_{i}" for i in range(1, 22)]
)

SENSOR_COLS   = [f"sensor_{i}" for i in range(1, 22)]
OP_COLS       = ["op_setting_1", "op_setting_2", "op_setting_3"]
FD_SPLITS     = ["FD001", "FD002", "FD003", "FD004"]


def load_fd(split: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    train_path = os.path.join(DATASET_ROOT, f"train_{split}.txt")
    test_path  = os.path.join(DATASET_ROOT, f"test_{split}.txt")
    rul_path   = os.path.join(DATASET_ROOT, f"RUL_{split}.txt")

    train = pd.read_csv(train_path, sep=r"\s+", header=None, names=COL_NAMES)
    test  = pd.read_csv(test_path,  sep=r"\s+", header=None, names=COL_NAMES)
    rul   = pd.read_csv(rul_path,   header=None, names=["RUL"]).squeeze()

    train.dropna(axis=1, how="all", inplace=True)
    test.dropna(axis=1, how="all", inplace=True)

    return train, test, rul


def compute_rul_labels(train: pd.DataFrame) -> pd.DataFrame:
    max_cycles = train.groupby("unit")["cycle"].max().rename("max_cycle")
    df = train.merge(max_cycles, on="unit")
    df["RUL"] = df["max_cycle"] - df["cycle"]
    df.drop(columns="max_cycle", inplace=True)
    return df


def near_constant_sensors(df: pd.DataFrame, threshold: float = 0.01) -> list:
    stds = df[SENSOR_COLS].std()
    return list(stds[stds < threshold].index)


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def run_eda():
    print_section("NASA CMAPSS EDA — PredictaGuard")

    all_data = {}
    near_const_per_fd = {}

    for split in FD_SPLITS:
        train, test, rul = load_fd(split)
        train_rul = compute_rul_labels(train)
        all_data[split] = (train, train_rul, test, rul)

        # ---- Per-split summary ----
        print_section(f"{split} — Summary")
        n_train_engines = train["unit"].nunique()
        n_test_engines  = test["unit"].nunique()
        total_train_cycles = len(train)
        max_cycle_per_engine = train.groupby("unit")["cycle"].max()

        print(f"  Train engines  : {n_train_engines}")
        print(f"  Test engines   : {n_test_engines}")
        print(f"  Train rows     : {total_train_cycles:,}")
        print(f"  Test rows      : {len(test):,}")
        print(f"  Cycle range    : {train['cycle'].min()} – {train['cycle'].max()}")
        print(f"  Avg cycles/engine: {max_cycle_per_engine.mean():.1f}  "
              f"(min={max_cycle_per_engine.min()}, max={max_cycle_per_engine.max()})")
        print(f"  RUL labels     : {len(rul)} engines, "
              f"mean={rul.mean():.1f}, min={rul.min()}, max={rul.max()}")

        # ---- Missing values ----
        mv = train[SENSOR_COLS + OP_COLS].isnull().sum()
        print(f"\n  Missing values : {mv.sum()} (across sensors + op settings)")

        # ---- Near-constant sensors ----
        nc = near_constant_sensors(train)
        near_const_per_fd[split] = nc
        print(f"\n  Near-constant sensors (std < 0.01): {nc if nc else 'None'}")

        # ---- Sensor statistics ----
        informative = [c for c in SENSOR_COLS if c not in nc]
        stats = train[informative].describe(percentiles=[0.05, 0.5, 0.95]).T
        stats["std"] = train[informative].std()
        print(f"\n  Informative sensor statistics ({len(informative)} sensors):")
        print(stats[["mean", "std", "min", "5%", "50%", "95%", "max"]].round(4).to_string())

    # ---- Cross-FD near-constant sensor summary ----
    print_section("Near-Constant Sensor Summary Across All FD Splits")
    all_nc = set()
    for split, nc in near_const_per_fd.items():
        print(f"  {split}: {nc}")
        all_nc.update(nc)
    print(f"\n  Recommend dropping from ALL splits: {sorted(all_nc)}")

    # ---- Plots ----
    # 1. Cycle length distributions per FD
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, split in zip(axes.flatten(), FD_SPLITS):
        train = all_data[split][0]
        cycle_lengths = train.groupby("unit")["cycle"].max()
        ax.hist(cycle_lengths, bins=30, color="#2196F3", edgecolor="white", linewidth=0.4)
        ax.set_title(f"{split} — Engine Lifetime Distribution", fontsize=11, fontweight="bold")
        ax.set_xlabel("Max cycle (lifetime)")
        ax.set_ylabel("# Engines")
        ax.axvline(cycle_lengths.mean(), color="red", linestyle="--",
                   linewidth=1.2, label=f"Mean={cycle_lengths.mean():.0f}")
        ax.legend(fontsize=9)
    fig.suptitle("CMAPSS — Engine Lifetime Distributions", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "engine_lifetime_distributions.png"), dpi=150)
    plt.close()
    print("  Saved: engine_lifetime_distributions.png")

    # 2. RUL distribution at test cutoff
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, split in zip(axes.flatten(), FD_SPLITS):
        rul = all_data[split][3]
        ax.hist(rul, bins=25, color="#FF5722", edgecolor="white", linewidth=0.4)
        ax.set_title(f"{split} — True RUL at Test Cutoff", fontsize=11, fontweight="bold")
        ax.set_xlabel("RUL (cycles)")
        ax.set_ylabel("# Engines")
        ax.axvline(rul.mean(), color="navy", linestyle="--",
                   linewidth=1.2, label=f"Mean={rul.mean():.0f}")
        ax.legend(fontsize=9)
    fig.suptitle("CMAPSS — RUL Distribution at Test Set Cutoff", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "rul_distribution_test_cutoff.png"), dpi=150)
    plt.close()
    print("  Saved: rul_distribution_test_cutoff.png")

    # 3. Degradation trajectories — FD001 (sample of engines)
    split = "FD001"
    train, train_rul, _, _ = all_data[split]
    nc = near_const_per_fd[split]
    informative = [c for c in SENSOR_COLS if c not in nc][:6]  # top-6 for clarity

    sample_units = sorted(train["unit"].unique())[:8]
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    axes = axes.flatten()
    colors = plt.cm.tab10(np.linspace(0, 1, len(sample_units)))
    for ax, col in zip(axes, informative):
        for uid, color in zip(sample_units, colors):
            subset = train[train["unit"] == uid].sort_values("cycle")
            rul_sub = train_rul[train_rul["unit"] == uid].sort_values("cycle")
            ax.plot(rul_sub["RUL"].values[::-1],   # x = RUL countdown
                    subset[col].values, color=color, alpha=0.6, linewidth=0.9)
        ax.set_xlabel("Remaining Useful Life (cycles)")
        ax.set_ylabel("Sensor value")
        ax.set_title(col, fontsize=10, fontweight="bold")
        ax.invert_xaxis()  # 0 = failure on right
    fig.suptitle(f"CMAPSS {split} — Sensor Degradation Trajectories (8 engines)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "degradation_trajectories_FD001.png"), dpi=150)
    plt.close()
    print("  Saved: degradation_trajectories_FD001.png")

    # 4. Correlation heatmap — FD001 informative sensors
    informative_all = [c for c in SENSOR_COLS if c not in near_const_per_fd["FD001"]]
    train_fd1 = all_data["FD001"][0]
    corr = train_fd1[informative_all].corr()
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, square=True, linewidths=0.4, annot_kws={"size": 7}, ax=ax)
    ax.set_title("CMAPSS FD001 — Sensor Correlation Heatmap", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "correlation_heatmap_FD001.png"), dpi=150)
    plt.close()
    print("  Saved: correlation_heatmap_FD001.png")

    # 5. Sensor standard deviations (to visualise near-constant sensors)
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    for ax, split in zip(axes.flatten(), FD_SPLITS):
        train = all_data[split][0]
        stds = train[SENSOR_COLS].std().sort_values()
        colors_bar = ["#F44336" if c in near_const_per_fd[split] else "#4CAF50"
                      for c in stds.index]
        ax.barh(stds.index, stds.values, color=colors_bar, edgecolor="white", linewidth=0.4)
        ax.axvline(0.01, color="navy", linestyle="--", linewidth=1.2, label="Threshold=0.01")
        ax.set_title(f"{split} — Sensor Standard Deviations", fontsize=11, fontweight="bold")
        ax.set_xlabel("Std Dev")
        ax.legend(fontsize=8)
    fig.suptitle("CMAPSS — Near-Constant Sensor Detection (red = drop candidate)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "sensor_std_near_constant_detection.png"), dpi=150)
    plt.close()
    print("  Saved: sensor_std_near_constant_detection.png")

    # 6. Operational setting distributions — FD002 (multi-condition)
    split = "FD002"
    train = all_data[split][0]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, col in zip(axes, OP_COLS):
        ax.hist(train[col], bins=30, color="#9C27B0", edgecolor="white", linewidth=0.4)
        ax.set_title(col, fontsize=10, fontweight="bold")
        ax.set_xlabel("Value")
        ax.set_ylabel("Count")
    fig.suptitle(f"CMAPSS {split} — Operational Setting Distributions (multi-condition)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "op_settings_FD002.png"), dpi=150)
    plt.close()
    print("  Saved: op_settings_FD002.png")

    print_section("CMAPSS EDA Complete")
    print(f"  Plots saved to: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    run_eda()
