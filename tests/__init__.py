"""Offline test package with the src-layout package made importable."""
from pathlib import Path
import sys

src = str(Path(__file__).resolve().parents[1] / "src")
if src not in sys.path:
    sys.path.insert(0, src)
