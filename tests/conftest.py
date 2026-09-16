import os
import sys
import types
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import yfinance  # noqa: F401
except ImportError:
    sys.modules["yfinance"] = types.SimpleNamespace(download=None)
