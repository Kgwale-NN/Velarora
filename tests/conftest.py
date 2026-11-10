"""
conftest.py — repo root
Adds the repo root to sys.path so `import backend.* / frontend.*` works when pytest is run
from any working directory, and sets a dummy STORAGE_SECRET so importing
backend.config (which now refuses to load without one) succeeds in tests.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# backend.config raises at import time if STORAGE_SECRET is missing/placeholder.
# Tests don't go through .env loading, so set a dummy value before any test
# transitively imports the config module.
os.environ.setdefault("STORAGE_SECRET", "test-storage-secret-not-used-for-real-signing")
