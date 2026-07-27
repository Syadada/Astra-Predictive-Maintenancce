import os
import sys
import asyncio

# Set path relative to ml/
PROJECT_ROOT = r"c:\Users\rasyaad\Downloads\PredictaGuard-main\PredictaGuard-main"
sys.path.append(os.path.join(PROJECT_ROOT, "ml"))

from src.api.scheduler import run_inference

async def main():
    print("[Manual Runner] Triggering model inference and decision pipeline...")
    await run_inference()
    print("[Manual Runner] Inference execution completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
