"""
Preprocessing pipeline for the SKAB dataset.
Steps:
  1. Load and concatenate all 35 SCAB CSV files with category tags.
  2. Parse datetime, forward-fill missing values.
  3. StandardScaler fitted on anomaly-free data only.
  4. Sliding window segmentation (window=60s, stride=30s).
  5. Chronological train/val/test split (70/15/15).
  6. Save skab_windows.npz + skab_scaler.joblib.

Run from ml/:  python src/preprocessing/preprocess_skab.py
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


# Paths

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATASET_ROOT = os.path.join(PROJECT_ROOT, "dataset", "SCAB")
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "ml", "data", "processed")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SENSOR_COLS = [
    "Accelerometer1RMS", "Accelerometer2RMS", "Current",
    "Pressure", "Temperature", "Thermocouple", "Voltage", "Volume Flow RateRMS"
]

WINDOW_SIZE = 60   # seconds (1 Hz sampling → 60 rows)
STRIDE      = 30   # rows between window starts

TRAIN_FRAC  = 0.70
VAL_FRAC    = 0.15


def load_all() -> pd.DataFrame:
    frames = []
    # anomaly-free has no anomaly/changepoint columns
    af_path = os.path.join(DATASET_ROOT, "anomaly-free", "anomaly-free.csv")
    af = pd.read_csv(af_path, sep=";", parse_dates=["datetime"])
    af["anomaly"]    = 0.0
    af["changepoint"] = 0.0
    af["source_category"] = "anomaly-free"
    frames.append(af)

    for cat in ["other", "valve1", "valve2"]:
        for f in sorted(glob.glob(os.path.join(DATASET_ROOT, cat, "*.csv"))):
            df = pd.read_csv(f, sep=";", parse_dates=["datetime"])
            df["source_category"] = cat
            frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("datetime").reset_index(drop=True)
    return combined


def sliding_windows(data: np.ndarray, labels: np.ndarray,
                    window: int, stride: int):
    X, y = [], []
    for start in range(0, len(data) - window + 1, stride):
        end = start + window
        X.append(data[start:end])
        # label = 1 if any anomaly in window
        y.append(1 if labels[start:end].max() > 0 else 0)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def chronological_split(X, y, train_frac, val_frac):
    n = len(X)
    t = int(n * train_frac)
    v = int(n * (train_frac + val_frac))
    return (X[:t], y[:t],
            X[t:v], y[t:v],
            X[v:],  y[v:])


def run():
    print("=" * 60)
    print("  SKAB Preprocessing Pipeline")
    print("=" * 60)

    # 1. Load
    print("\n[1] Loading all SCAB files...")
    df = load_all()
    print(f"    Total rows: {len(df):,}  |  Columns: {df.shape[1]}")

    # 2. Missing value check + forward-fill
    mv = df[SENSOR_COLS].isnull().sum().sum()
    print(f"\n[2] Missing sensor values: {mv}")
    if mv > 0:
        df[SENSOR_COLS] = df[SENSOR_COLS].fillna(method="ffill").fillna(method="bfill")
        print(f"    After fill: {df[SENSOR_COLS].isnull().sum().sum()} missing")

    # 3. Fit scaler on anomaly-free only, transform all
    print("\n[3] Fitting StandardScaler on anomaly-free segment...")
    af_mask = df["source_category"] == "anomaly-free"
    scaler = StandardScaler()
    scaler.fit(df.loc[af_mask, SENSOR_COLS].values)
    scaled = scaler.transform(df[SENSOR_COLS].values)
    print(f"    Scaler mean (first 3): {scaler.mean_[:3].round(4)}")
    print(f"    Scaler std  (first 3): {scaler.scale_[:3].round(4)}")

    # 4. Sliding windows
    print(f"\n[4] Sliding window segmentation (window={WINDOW_SIZE}, stride={STRIDE})...")
    labels = df["anomaly"].values
    X, y = sliding_windows(scaled, labels, WINDOW_SIZE, STRIDE)
    print(f"    Windows created: {len(X):,}  |  Shape: {X.shape}")
    print(f"    Anomaly windows: {y.sum():,} ({y.mean()*100:.1f}%)")
    print(f"    Normal  windows: {(y==0).sum():,} ({(y==0).mean()*100:.1f}%)")

    # 5. Chronological split
    print(f"\n[5] Chronological split  (train={TRAIN_FRAC*100:.0f}% / "
          f"val={VAL_FRAC*100:.0f}% / test={(1-TRAIN_FRAC-VAL_FRAC)*100:.0f}%)...")
    X_tr, y_tr, X_va, y_va, X_te, y_te = chronological_split(X, y, TRAIN_FRAC, VAL_FRAC)
    for name, Xs, ys in [("Train", X_tr, y_tr), ("Val", X_va, y_va), ("Test", X_te, y_te)]:
        print(f"    {name:5s}: {len(Xs):5,} windows  |  anomaly rate: {ys.mean()*100:.1f}%")

    # 6. Save
    out_npz    = os.path.join(OUTPUT_DIR, "skab_windows.npz")
    out_scaler = os.path.join(OUTPUT_DIR, "skab_scaler.joblib")
    np.savez_compressed(
        out_npz,
        X_train=X_tr, y_train=y_tr,
        X_val=X_va,   y_val=y_va,
        X_test=X_te,  y_test=y_te,
    )
    joblib.dump(scaler, out_scaler)
    print(f"\n[6] Saved:")
    print(f"    {out_npz}")
    print(f"    {out_scaler}")

    # Verify
    check = np.load(out_npz)
    print(f"\n    Verification — keys in npz: {list(check.keys())}")
    print(f"    X_train shape: {check['X_train'].shape}  dtype: {check['X_train'].dtype}")
    print(f"    y_train shape: {check['y_train'].shape}  dtype: {check['y_train'].dtype}")

    print("\n" + "="*60)
    print("  SKAB Preprocessing Complete")
    print("="*60)


if __name__ == "__main__":
    run()
