import os
import sys
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.main import get_downtime_report

try:
    print("Executing get_downtime_report...")
    res = get_downtime_report(format="pdf")
    print(f"Success! Path: {res.path}")
    os.unlink(res.path)
except Exception as e:
    print("Caught exception:")
    traceback.print_exc()
