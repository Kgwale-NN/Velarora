"""Entry point — python run.py"""
import multiprocessing
import os
import sys
from pathlib import Path
multiprocessing.freeze_support()

if __name__ == "__main__":
    # Keep saved database/model paths stable, including when launched from VS Code.
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    os.chdir(root)
    import backend.main
