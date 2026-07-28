import os

def check_files():
    rb_dir = r"C:\$Recycle.Bin\S-1-5-21-3066796454-542909024-2799650001-1002"
    if not os.path.exists(rb_dir):
        print("Recycle Bin directory not found!")
        return
        
    print(f"Listing files in {rb_dir}:")
    for f in os.listdir(rb_dir):
        p = os.path.join(rb_dir, f)
        size = os.path.getsize(p)
        print(f"  {f:25s} | Size: {size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    check_files()
