import os
import numpy as np
import pandas as pd
import scipy.stats as stats

print("Extracting CWRU features from raw data...")

# Paths
ml_dir = os.path.dirname(os.path.abspath(__file__))
dataset_dir = os.path.join(ml_dir, "..", "dataset", "CWRU")
npz_path = os.path.join(dataset_dir, "cwru.npz")
csv_path = os.path.join(dataset_dir, "feature_time_48k_2048_load_1.csv")

if not os.path.exists(npz_path):
    print(f"[ERROR] cwru.npz not found at {npz_path}")
    exit(1)

# Load NPZ
npz = np.load(npz_path)
data = npz["data"]
labels = npz["labels"]

# Label mapping
label_map = {
    "Normal": "Normal_1",
    "Ball_007": "Ball_007_1",
    "Ball_014": "Ball_014_1",
    "Ball_021": "Ball_021_1",
    "IR_007": "IR_007_1",
    "IR_014": "IR_014_1",
    "IR_021": "IR_021_1",
    "OR_007": "OR_007_6_1",
    "OR_014": "OR_014_6_1",
    "OR_021": "OR_021_6_1",
}

features = []
for i in range(len(data)):
    sample = data[i].flatten()
    lbl = labels[i]
    mapped_lbl = label_map.get(lbl, lbl)
    
    # Calculate time domain features
    v_max = np.max(sample)
    v_min = np.min(sample)
    v_mean = np.mean(sample)
    v_sd = np.std(sample)
    v_rms = np.sqrt(np.mean(sample**2))
    v_skew = stats.skew(sample)
    v_kurt = stats.kurtosis(sample)
    v_crest = np.max(np.abs(sample)) / (v_rms + 1e-9)
    v_form = v_rms / (np.mean(np.abs(sample)) + 1e-9)
    
    features.append({
        "max": v_max,
        "min": v_min,
        "mean": v_mean,
        "sd": v_sd,
        "rms": v_rms,
        "skewness": v_skew,
        "kurtosis": v_kurt,
        "crest": v_crest,
        "form": v_form,
        "fault": mapped_lbl
    })

df = pd.DataFrame(features)

# Write to CSV
df.to_csv(csv_path, index=False)
print(f"Features extracted successfully! CSV saved at: {csv_path}")
