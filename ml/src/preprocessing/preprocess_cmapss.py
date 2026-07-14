"""
Preprocessing pipeline for NASA CMAPSS (FD001–FD004).
Steps:
  1. Load train/test/RUL for all 4 FD splits; attach column names.
  2. Drop near-constant sensors per-split (std < 0.01 across train).
  3. Min-max normalise sensors (fit on train engines).
  4. Piecewise-linear RUL labels (capped at RUL_MAX=125).
  5. Sliding window: window=30 cycles, stride=1 cycle.
  6. Engine-level train/val split (85/15) on train_FD; test_FD is test.
  7. Save cmapss_FD00{1-4}.npz + per-split scaler joblibs.

Run from ml/:  python src/preprocessing/preprocess_cmapss.py
"""

import os
import warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")


# Paths & constants

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATASET_ROOT = os.path.join(PROJECT_ROOT, "dataset", "CMaps")
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "ml", "data", "processed")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COL_NAMES = (
    ["unit", "cycle", "op_setting_1", "op_setting_2", "op_setting_3"]
    + [f"sensor_{i}" for i in range(1, 22)]
)
SENSOR_COLS  = [f"sensor_{i}" for i in range(1, 22)]
FD_SPLITS    = ["FD001", "FD002", "FD003", "FD004"]

WINDOW_SIZE  = 30
STRIDE       = 1
RUL_MAX      = 125
NC_THRESHOLD = 0.01   # sensors with std < this are dropped
VAL_FRAC     = 0.15
RANDOM_SEED  = 42


def load_fd(split: str):
    def read(path):
        df = pd.read_csv(path, sep=r"\s+", header=None, names=COL_NAMES)
        df.dropna(axis=1, how="all", inplace=True)
        return df
    train = read(os.path.join(DATASET_ROOT, f"train_{split}.txt"))
    test  = read(os.path.join(DATASET_ROOT, f"test_{split}.txt"))
    rul   = pd.read_csv(os.path.join(DATASET_ROOT, f"RUL_{split}.txt"),
                        header=None, names=["RUL"]).squeeze()
    return train, test, rul


def drop_near_constant(df: pd.DataFrame, nc_cols: list) -> pd.DataFrame:
    return df.drop(columns=[c for c in nc_cols if c in df.columns])


def add_rul_labels(train: pd.DataFrame, rul_max: int) -> pd.DataFrame:
    max_cycles = train.groupby("unit")["cycle"].max().rename("max_cycle")
    df = train.merge(max_cycles, on="unit")
    df["RUL"] = (df["max_cycle"] - df["cycle"]).clip(upper=rul_max)
    df.drop(columns="max_cycle", inplace=True)
    return df


def add_rul_test(test: pd.DataFrame, rul_file: pd.Series, rul_max: int) -> pd.DataFrame:
    # For each test engine, RUL at last cycle = rul_file value
    # RUL at earlier cycles = rul_file[unit-1] + (max_cycle - cycle)
    df = test.copy()
    max_cycles = df.groupby("unit")["cycle"].max().rename("max_cycle")
    df = df.merge(max_cycles, on="unit")
    # unit IDs are 1-indexed; rul_file is 0-indexed
    rul_at_end = df["unit"].map(lambda u: rul_file.iloc[u - 1])
    df["RUL"] = (rul_at_end + df["max_cycle"] - df["cycle"]).clip(upper=rul_max)
    df.drop(columns="max_cycle", inplace=True)
    return df


def make_windows(df: pd.DataFrame, sensor_cols: list, window: int, stride: int):
    X_list, y_list, unit_list = [], [], []
    for unit_id, grp in df.groupby("unit"):
        grp = grp.sort_values("cycle")
        vals = grp[sensor_cols].values.astype(np.float32)
        ruls = grp["RUL"].values.astype(np.float32)
        for start in range(0, len(grp) - window + 1, stride):
            end = start + window
            X_list.append(vals[start:end])
            y_list.append(ruls[end - 1])   # RUL at last step of window
            unit_list.append(unit_id)
    return (np.array(X_list, dtype=np.float32),
            np.array(y_list,  dtype=np.float32),
            np.array(unit_list, dtype=np.int32))


def run():
    print("=" * 60)
    print("  CMAPSS Preprocessing Pipeline")
    print("=" * 60)

    for split in FD_SPLITS:
        print(f"\n{'─'*50}")
        print(f"  Processing {split}")
        print(f"{'─'*50}")

        # 1. Load
        train_raw, test_raw, rul_file = load_fd(split)
        print(f"  [1] Loaded: train={len(train_raw):,} rows / "
              f"{train_raw['unit'].nunique()} engines | "
              f"test={len(test_raw):,} rows / {test_raw['unit'].nunique()} engines")

        # 2. Detect & drop near-constant sensors
        nc_cols = [c for c in SENSOR_COLS
                   if c in train_raw.columns and train_raw[c].std() < NC_THRESHOLD]
        informative = [c for c in SENSOR_COLS if c in train_raw.columns and c not in nc_cols]
        print(f"  [2] Dropping {len(nc_cols)} near-constant sensors: {nc_cols}")
        print(f"      Keeping {len(informative)} informative sensors: {informative}")

        train = drop_near_constant(train_raw, nc_cols)
        test  = drop_near_constant(test_raw,  nc_cols)

        # 3. RUL labels
        print(f"  [3] Adding piecewise RUL labels (cap={RUL_MAX})...")
        train = add_rul_labels(train, RUL_MAX)
        test  = add_rul_test(test, rul_file, RUL_MAX)
        print(f"      Train RUL: mean={train['RUL'].mean():.1f}  "
              f"min={train['RUL'].min()}  max={train['RUL'].max()}")
        print(f"      Test  RUL: mean={test['RUL'].mean():.1f}  "
              f"min={test['RUL'].min()}  max={test['RUL'].max()}")

        # 4. Min-max normalise (fit on train only)
        print(f"  [4] Min-max normalising {len(informative)} sensors...")
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaler.fit(train[informative].values)
        train[informative] = scaler.transform(train[informative].values)
        test[informative]  = scaler.transform(test[informative].values)

        # 5. Engine-level train/val split
        all_units  = train["unit"].unique()
        train_units, val_units = train_test_split(
            all_units, test_size=VAL_FRAC, random_state=RANDOM_SEED
        )
        tr_df  = train[train["unit"].isin(train_units)]
        val_df = train[train["unit"].isin(val_units)]
        print(f"  [5] Engine split: train={len(train_units)} engines / "
              f"val={len(val_units)} engines / test={test['unit'].nunique()} engines")

        # 6. Sliding windows
        print(f"  [6] Building sliding windows (w={WINDOW_SIZE}, stride={STRIDE})...")
        X_tr,  y_tr,  _  = make_windows(tr_df,  informative, WINDOW_SIZE, STRIDE)
        X_va,  y_va,  _  = make_windows(val_df, informative, WINDOW_SIZE, STRIDE)
        X_te,  y_te,  _  = make_windows(test,   informative, WINDOW_SIZE, STRIDE)

        for name, Xs, ys in [("Train", X_tr, y_tr), ("Val", X_va, y_va), ("Test", X_te, y_te)]:
            print(f"      {name:5s}: {len(Xs):6,} windows  shape={Xs.shape}  "
                  f"RUL mean={ys.mean():.1f}  std={ys.std():.1f}")

        # 7. Save
        out_npz    = os.path.join(OUTPUT_DIR, f"cmapss_{split}.npz")
        out_scaler = os.path.join(OUTPUT_DIR, f"cmapss_{split}_scaler.joblib")
        np.savez_compressed(
            out_npz,
            X_train=X_tr, y_train=y_tr,
            X_val=X_va,   y_val=y_va,
            X_test=X_te,  y_test=y_te,
            informative_sensors=np.array(informative),
            dropped_sensors=np.array(nc_cols),
        )
        joblib.dump(scaler, out_scaler)
        print(f"  [7] Saved: {out_npz}")
        print(f"             {out_scaler}")

    print("\n" + "="*60)
    print("  CMAPSS Preprocessing Complete")
    print("="*60)


if __name__ == "__main__":
    run()
