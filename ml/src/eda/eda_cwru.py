"""
EDA for the CWRU (Case Western Reserve University) Bearing Dataset.
Pre-extracted time-domain features: max, min, mean, sd, rms,
skewness, kurtosis, crest, form — across 10 fault classes.

Run from ml/:  python src/eda/eda_cwru.py
"""

import os
import warnings
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import matplotlib
matplotlib.use("Agg")
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


# Paths

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATASET_PATH = os.path.join(PROJECT_ROOT, "dataset", "CWRU", "feature_time_48k_2048_load_1.csv")
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "ml", "data", "processed", "eda_plots", "cwru")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FEATURE_COLS = ["max", "min", "mean", "sd", "rms", "skewness", "kurtosis", "crest", "form"]

# Readable fault labels
FAULT_LABELS = {
    "Normal_1"    : "Normal",
    "Ball_007_1"  : "Ball 0.007\"",
    "Ball_014_1"  : "Ball 0.014\"",
    "Ball_021_1"  : "Ball 0.021\"",
    "IR_007_1"    : "Inner Race 0.007\"",
    "IR_014_1"    : "Inner Race 0.014\"",
    "IR_021_1"    : "Inner Race 0.021\"",
    "OR_007_6_1"  : "Outer Race 0.007\"",
    "OR_014_6_1"  : "Outer Race 0.014\"",
    "OR_021_6_1"  : "Outer Race 0.021\"",
}

FAULT_TYPE = {k: k.split("_")[0] for k in FAULT_LABELS}  # Ball / IR / OR / Normal


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def run_eda():
    print_section("CWRU EDA — PredictaGuard")

    df = pd.read_csv(DATASET_PATH)
    df.columns = df.columns.str.strip().str.replace('"', '')
    for col in FEATURE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["fault_label"] = df["fault"].map(FAULT_LABELS).fillna(df["fault"])
    df["fault_type"]  = df["fault"].map(FAULT_TYPE).fillna("Unknown")

    # ---- Basic info ----
    print_section("1. Dataset Shape & Types")
    print(f"  Rows     : {len(df):,}")
    print(f"  Columns  : {df.shape[1]}")
    print(f"\n  Dtypes:\n{df.dtypes.to_string()}")

    # ---- Missing values ----
    print_section("2. Missing Values")
    missing = df[FEATURE_COLS].isnull().sum()
    print(missing.to_string())
    if missing.sum() == 0:
        print("\n  No missing values.")

    # ---- Class distribution ----
    print_section("3. Fault Class Distribution")
    cls_dist = df["fault"].value_counts().reset_index()
    cls_dist.columns = ["fault_class", "count"]
    cls_dist["label"] = cls_dist["fault_class"].map(FAULT_LABELS)
    print(cls_dist.to_string(index=False))
    is_balanced = cls_dist["count"].std() < 1
    print(f"\n  Perfectly balanced: {is_balanced} (std={cls_dist['count'].std():.2f})")

    # class distribution bar
    fig, ax = plt.subplots(figsize=(12, 5))
    colors = sns.color_palette("tab10", len(cls_dist))
    ax.bar(cls_dist["label"], cls_dist["count"], color=colors, edgecolor="white")
    ax.set_title("CWRU — Fault Class Distribution (balanced)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Sample count")
    ax.set_xlabel("")
    plt.xticks(rotation=35, ha="right", fontsize=9)
    for bar, cnt in zip(ax.patches, cls_dist["count"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                str(cnt), ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "class_distribution.png"), dpi=150)
    plt.close()
    print("  Saved: class_distribution.png")

    # ---- Feature statistics per class ----
    print_section("4. Feature Statistics per Fault Class")
    feat_stats = df.groupby("fault")[FEATURE_COLS].mean().T
    print(feat_stats.round(4).to_string())

    # ---- Correlation heatmap ----
    print_section("5. Feature Correlation Heatmap")
    corr = df[FEATURE_COLS].corr()
    print(corr.round(3).to_string())

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, square=True, linewidths=0.5, ax=ax)
    ax.set_title("CWRU — Feature Correlation Heatmap", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "correlation_heatmap.png"), dpi=150)
    plt.close()
    print("  Saved: correlation_heatmap.png")

    # ---- Box plots per feature grouped by fault type ----
    fig, axes = plt.subplots(3, 3, figsize=(16, 13))
    axes = axes.flatten()
    palette = sns.color_palette("Set2", 4)
    for i, col in enumerate(FEATURE_COLS):
        order = sorted(df["fault_type"].unique())
        sns.boxplot(data=df, x="fault_type", y=col, order=order,
                    palette=palette, ax=axes[i], linewidth=0.8)
        axes[i].set_title(col, fontsize=10, fontweight="bold")
        axes[i].set_xlabel("")
        axes[i].tick_params(axis="x", rotation=20)
    fig.suptitle("CWRU — Feature Distributions by Fault Type", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "boxplots_by_fault_type.png"), dpi=150)
    plt.close()
    print("  Saved: boxplots_by_fault_type.png")

    # ---- Box plots per feature grouped by fault class ----
    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    axes = axes.flatten()
    palette10 = sns.color_palette("tab10", 10)
    order10 = [k for k in FAULT_LABELS if k in df["fault"].unique()]
    for i, col in enumerate(FEATURE_COLS):
        sns.boxplot(data=df, x="fault", y=col, order=order10,
                    palette=palette10, ax=axes[i], linewidth=0.7)
        axes[i].set_title(col, fontsize=9, fontweight="bold")
        axes[i].set_xlabel("")
        axes[i].tick_params(axis="x", rotation=60, labelsize=7)
    fig.suptitle("CWRU — Feature Distributions by Fault Class", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "boxplots_by_fault_class.png"), dpi=150)
    plt.close()
    print("  Saved: boxplots_by_fault_class.png")

    # ---- PCA biplot ----
    print_section("6. PCA — Fault Separability")
    X = df[FEATURE_COLS].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    pca = PCA(n_components=3)
    X_pca = pca.fit_transform(X_scaled)
    explained = pca.explained_variance_ratio_ * 100
    print(f"  PC1: {explained[0]:.1f}%  PC2: {explained[1]:.1f}%  PC3: {explained[2]:.1f}%")
    print(f"  Cumulative (PC1+PC2): {sum(explained[:2]):.1f}%")

    palette10 = sns.color_palette("tab10", 10)
    fault_classes = df["fault"].unique()
    class_to_color = {c: palette10[i % 10] for i, c in enumerate(sorted(fault_classes))}

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    # PC1 vs PC2
    for cls in sorted(fault_classes):
        mask = df["fault"].values == cls
        axes[0].scatter(X_pca[mask, 0], X_pca[mask, 1],
                        label=FAULT_LABELS.get(cls, cls),
                        color=class_to_color[cls], alpha=0.6, s=20)
    axes[0].set_xlabel(f"PC1 ({explained[0]:.1f}%)")
    axes[0].set_ylabel(f"PC2 ({explained[1]:.1f}%)")
    axes[0].set_title("PCA Biplot — PC1 vs PC2", fontsize=11, fontweight="bold")
    axes[0].legend(fontsize=7, markerscale=1.5)
    # PC1 vs PC3
    for cls in sorted(fault_classes):
        mask = df["fault"].values == cls
        axes[1].scatter(X_pca[mask, 0], X_pca[mask, 2],
                        color=class_to_color[cls], alpha=0.6, s=20)
    axes[1].set_xlabel(f"PC1 ({explained[0]:.1f}%)")
    axes[1].set_ylabel(f"PC3 ({explained[2]:.1f}%)")
    axes[1].set_title("PCA Biplot — PC1 vs PC3", fontsize=11, fontweight="bold")

    fig.suptitle("CWRU — PCA Fault Separability", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "pca_biplot.png"), dpi=150)
    plt.close()
    print("  Saved: pca_biplot.png")

    # ---- Feature loadings ----
    loadings = pd.DataFrame(pca.components_.T, index=FEATURE_COLS,
                            columns=["PC1", "PC2", "PC3"])
    print("\n  PCA Feature Loadings:")
    print(loadings.round(3).to_string())

    # ---- Feature distributions (histogram grid) ----
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    axes = axes.flatten()
    for i, col in enumerate(FEATURE_COLS):
        for cls in sorted(fault_classes):
            vals = df.loc[df["fault"] == cls, col]
            axes[i].hist(vals, bins=25, alpha=0.5, label=FAULT_LABELS.get(cls, cls), density=True)
        axes[i].set_title(col, fontsize=9, fontweight="bold")
        axes[i].set_xlabel("Value")
    axes[0].legend(fontsize=6, loc="upper right")
    fig.suptitle("CWRU — Feature Distributions by Fault Class (density)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "feature_distributions_by_class.png"), dpi=150)
    plt.close()
    print("  Saved: feature_distributions_by_class.png")

    print_section("CWRU EDA Complete")
    print(f"  Plots saved to: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    run_eda()
