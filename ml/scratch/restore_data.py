import os
import zipfile
import numpy as np

def check_labels():
    rb_dir = r"C:\$Recycle.Bin\S-1-5-21-3066796454-542909024-2799650001-1002"
    zip_path = os.path.join(rb_dir, "$RUZLR2L.zip")
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(".")
        
    npz_path = "CWRU_48k_load_1_CNN_data.npz"
    d = np.load(npz_path, allow_pickle=True)
    labels = d["labels"]
    
    unique, counts = np.unique(labels, return_counts=True)
    print("Unique labels and counts:")
    for u, c in zip(unique, counts):
        print(f"  {u}: {c}")

if __name__ == "__main__":
    check_labels()
