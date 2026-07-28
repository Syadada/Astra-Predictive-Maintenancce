import os
import zipfile
import numpy as np
import pandas as pd
import scipy.stats
import shutil

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")
RB_DIR = r"C:\$Recycle.Bin\S-1-5-21-3066796454-542909024-2799650001-1002"

# 1. Map label suffixes for CWRU
_LABEL_MAPPING = {
    "Normal": "Normal_1",
    "Ball_007": "Ball_007_1",
    "Ball_014": "Ball_014_1",
    "Ball_021": "Ball_021_1",
    "IR_007": "IR_007_1",
    "IR_014": "IR_014_1",
    "IR_021": "IR_021_1",
    "OR_007": "OR_007_6_1",
    "OR_014": "OR_014_6_1",
    "OR_021": "OR_021_6_1"
}

def restore_cmapss():
    print("Restoring CMAPSS dataset...")
    zip_path = os.path.join(RB_DIR, "$REA7J1N.zip")
    if not os.path.exists(zip_path):
        print("  Error: CMAPSS zip not found in Recycle Bin!")
        return False
        
    # Extract to dataset/
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(DATASET_DIR)
    print("  CMAPSS restored successfully to dataset/CMaps")
    return True

def restore_skab():
    print("Restoring SKAB dataset...")
    skab_zips = {
        "$RL4VDQJ.zip": "anomaly-free",
        "$RB4XSUE.zip": "valve1",
        "$R0RDYXQ.zip": "valve2",
        "$RIOV3H6.zip": "other"
    }
    
    scab_dir = os.path.join(DATASET_DIR, "SCAB")
    os.makedirs(scab_dir, exist_ok=True)
    
    for zip_name, label in skab_zips.items():
        zip_path = os.path.join(RB_DIR, zip_name)
        if not os.path.exists(zip_path):
            print(f"  Error: {label} zip not found in Recycle Bin!")
            return False
            
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(scab_dir)
            
    print("  SKAB restored successfully to dataset/SCAB")
    return True

def restore_cwru():
    print("Reconstructing CWRU feature CSV...")
    zip_path = os.path.join(RB_DIR, "$RUZLR2L.zip")
    if not os.path.exists(zip_path):
        print("  Error: CWRU npz zip not found in Recycle Bin!")
        return False
        
    # Extract CWRU npz to scratch
    temp_dir = os.path.dirname(__file__)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(temp_dir)
        
    npz_path = os.path.join(temp_dir, "CWRU_48k_load_1_CNN_data.npz")
    if not os.path.exists(npz_path):
        print("  Error: Extracted CWRU npz not found!")
        return False
        
    d = np.load(npz_path, allow_pickle=True)
    data = d["data"]
    labels = d["labels"]
    
    # Compute the 9 features
    rows = []
    for i in range(len(data)):
        x = data[i].flatten()
        
        mx = np.max(x)
        mn = np.min(x)
        mean = np.mean(x)
        sd = np.std(x)
        rms = np.sqrt(np.mean(x**2))
        skew = scipy.stats.skew(x)
        kurt = scipy.stats.kurtosis(x, fisher=True)
        crest = np.max(np.abs(x)) / (rms + 1e-9)
        form = rms / (np.mean(x) + 1e-9)
        
        # Map label
        raw_lbl = labels[i]
        mapped_lbl = _LABEL_MAPPING.get(raw_lbl, raw_lbl)
        
        rows.append({
            "max": mx,
            "min": mn,
            "mean": mean,
            "sd": sd,
            "rms": rms,
            "skewness": skew,
            "kurtosis": kurt,
            "crest": crest,
            "form": form,
            "fault": mapped_lbl
        })
        
    # Save as CSV
    df = pd.DataFrame(rows)
    cwru_dir = os.path.join(DATASET_DIR, "CWRU")
    os.makedirs(cwru_dir, exist_ok=True)
    csv_path = os.path.join(cwru_dir, "feature_time_48k_2048_load_1.csv")
    df.to_csv(csv_path, index=False)
    
    # Close and remove temp npz
    d.close()
    os.remove(npz_path)
    
    print(f"  CWRU feature CSV reconstructed and saved to {csv_path} ({len(df)} rows)")
    return True

def main():
    os.makedirs(DATASET_DIR, exist_ok=True)
    success = restore_cmapss() and restore_skab() and restore_cwru()
    if success:
        print("\nAll datasets restored successfully!")
    else:
        print("\nRestoration failed!")

if __name__ == "__main__":
    main()
