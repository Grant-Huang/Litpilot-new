"""Vercel Serverless entry point — re-exports FastAPI app."""
import sys
import os

# Ensure project root is in path for imports
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.main import app  # noqa: F401, E402
