import os
import sys

# Add project root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.main import get_weekly_report, get_cmms_report, get_downtime_report
from fastapi.responses import FileResponse

def test():
    print("Testing weekly report PDF generation...")
    res = get_weekly_report(format="pdf")
    assert isinstance(res, FileResponse), "Should return a FileResponse"
    print(f"Weekly PDF Path: {res.path}")
    with open(res.path, 'rb') as f:
        data = f.read()
        print(f"Weekly PDF Size: {len(data)} bytes")
        assert data.startswith(b'%PDF-'), "Should start with PDF signature"
    os.unlink(res.path)
    
    print("Testing CMMS report PDF generation...")
    res2 = get_cmms_report(motor_id="all", format="pdf")
    assert isinstance(res2, FileResponse), "Should return a FileResponse"
    print(f"CMMS PDF Path: {res2.path}")
    with open(res2.path, 'rb') as f:
        data = f.read()
        print(f"CMMS PDF Size: {len(data)} bytes")
        assert data.startswith(b'%PDF-'), "Should start with PDF signature"
    os.unlink(res2.path)
    
    print("Testing downtime report PDF generation...")
    res3 = get_downtime_report(format="pdf")
    assert isinstance(res3, FileResponse), "Should return a FileResponse"
    print(f"Downtime PDF Path: {res3.path}")
    with open(res3.path, 'rb') as f:
        data = f.read()
        print(f"Downtime PDF Size: {len(data)} bytes")
        assert data.startswith(b'%PDF-'), "Should start with PDF signature"
    os.unlink(res3.path)
    
    print("\nALL BACKEND PDF GENERATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    try:
        test()
    except Exception as e:
        print(f"Verification encountered an error: {e}")
