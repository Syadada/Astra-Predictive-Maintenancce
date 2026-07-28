import os
import joblib
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "ml", "data", "processed")

def check():
    for f in sorted(os.listdir(PROCESSED_DIR)):
        if "scaler" in f and "cmapss" in f:
            p = os.path.join(PROCESSED_DIR, f)
            sc = joblib.load(p)
            print(f"\nScaler: {f}")
            print("  min_:", sc.min_[:5] if hasattr(sc, "min_") else "None")
            print("  scale_:", sc.scale_[:5] if hasattr(sc, "scale_") else "None")
            print("  data_min_:", sc.data_min_[:5] if hasattr(sc, "data_min_") else "None")
            print("  data_max_:", sc.data_max_[:5] if hasattr(sc, "data_max_") else "None")

if __name__ == "__main__":
    check()
