"""
Preprocessing pipeline for the CWRU Bearing dataset.
Steps:
  1. Load pre-extracted feature CSV.
  2. Encode fault labels (binary + multi-class integer).
  3. StandardScaler on 9 feature columns.
  4. Stratified train/val/test split (70/15/15).
  5. Save cwru_features.npz + cwru_scaler.joblib + cwru_label_encoder.joblib.

Run from ml/:  python src/preprocessing/preprocess_cwru.py
"""

import os
import warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")


# Paths

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATASET_PATH = os.path.join(PROJECT_ROOT, "dataset", "CWRU", "feature_time_48k_2048_load_1.csv")
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "ml", "data", "processed")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FEATURE_COLS = ["max", "min", "mean", "sd", "rms", "skewness", "kurtosis", "crest", "form"]
RANDOM_SEED  = 42
TRAIN_FRAC   = 0.70
VAL_FRAC     = 0.15   # of total; remainder = test


def run():
    print("=" * 60)
    print("  CWRU Preprocessing Pipeline")
    print("=" * 60)

    # 1. Load
    print("\n[1] Loading CWRU feature CSV...")
    df = pd.read_csv(DATASET_PATH)
    df.columns = df.columns.str.strip().str.replace('"', '')
    for col in FEATURE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    print(f"    Rows: {len(df):,}  |  Features: {len(FEATURE_COLS)}")
    print(f"    Classes: {sorted(df['fault'].unique())}")

    # 2. Missing values
    mv = df[FEATURE_COLS].isnull().sum().sum()
    print(f"\n[2] Missing values in features: {mv}")

    # 3. Encode labels
    print("\n[3] Encoding labels...")
    le_multi = LabelEncoder()
    y_multi  = le_multi.fit_transform(df["fault"])                           # 0-9 integer
    y_binary = (df["fault"] != "Normal_1").astype(int).values                # 0=normal, 1=fault

    print(f"    Multi-class mapping:")
    for cls, idx in zip(le_multi.classes_, range(len(le_multi.classes_))):
        print(f"      {idx:2d}  {cls}")
    print(f"    Binary: 0=Normal ({(y_binary==0).sum()}), 1=Fault ({(y_binary==1).sum()})")

    # 4. Scale features
    print("\n[4] Scaling features with StandardScaler...")
    X = df[FEATURE_COLS].values

    # First pass: full train split to fit scaler
    # We fit scaler only on training data
    X_temp, X_test_raw, y_multi_temp, y_multi_test, y_bin_temp, y_bin_test = train_test_split(
        X, y_multi, y_binary,
        test_size=(1 - TRAIN_FRAC - VAL_FRAC),
        stratify=y_multi,
        random_state=RANDOM_SEED
    )
    val_size_adjusted = VAL_FRAC / (TRAIN_FRAC + VAL_FRAC)
    X_train_raw, X_val_raw, y_multi_train, y_multi_val, y_bin_train, y_bin_val = train_test_split(
        X_temp, y_multi_temp, y_bin_temp,
        test_size=val_size_adjusted,
        stratify=y_multi_temp,
        random_state=RANDOM_SEED
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw).astype(np.float32)
    X_val   = scaler.transform(X_val_raw).astype(np.float32)
    X_test  = scaler.transform(X_test_raw).astype(np.float32)

    print(f"    Scaler mean (first 3): {scaler.mean_[:3].round(4)}")
    print(f"    Scaler std  (first 3): {scaler.scale_[:3].round(4)}")

    # 5. Report split sizes
    print(f"\n[5] Split sizes:")
    for name, Xs, ym, yb in [
        ("Train", X_train, y_multi_train, y_bin_train),
        ("Val",   X_val,   y_multi_val,   y_bin_val),
        ("Test",  X_test,  y_multi_test,  y_bin_test),
    ]:
        unique, counts = np.unique(ym, return_counts=True)
        print(f"    {name:5s}: {len(Xs):4d} samples  |  "
              f"binary fault rate: {yb.mean()*100:.1f}%  |  "
              f"class counts: {dict(zip(le_multi.classes_[unique], counts))}")

    # 6. Save
    out_npz     = os.path.join(OUTPUT_DIR, "cwru_features.npz")
    out_scaler  = os.path.join(OUTPUT_DIR, "cwru_scaler.joblib")
    out_encoder = os.path.join(OUTPUT_DIR, "cwru_label_encoder.joblib")

    np.savez_compressed(
        out_npz,
        X_train=X_train, y_multi_train=y_multi_train.astype(np.int32), y_bin_train=y_bin_train.astype(np.int32),
        X_val=X_val,     y_multi_val=y_multi_val.astype(np.int32),     y_bin_val=y_bin_val.astype(np.int32),
        X_test=X_test,   y_multi_test=y_multi_test.astype(np.int32),   y_bin_test=y_bin_test.astype(np.int32),
    )
    joblib.dump(scaler,   out_scaler)
    joblib.dump(le_multi, out_encoder)

    print(f"\n[6] Saved:")
    print(f"    {out_npz}")
    print(f"    {out_scaler}")
    print(f"    {out_encoder}")

    # Verify
    check = np.load(out_npz)
    print(f"\n    Verification — X_train: {check['X_train'].shape}  "
          f"y_multi_train: {check['y_multi_train'].shape}  "
          f"y_bin_train: {check['y_bin_train'].shape}")

    print("\n" + "="*60)
    print("  CWRU Preprocessing Complete")
    print("="*60)


if __name__ == "__main__":
    run()
