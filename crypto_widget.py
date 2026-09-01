#!/usr/bin/env python3
"""Wrapper para ejecutar WidgetFinanzas desde la raíz del proyecto."""

import sys
from pathlib import Path

# Asegurar que src/ esté en el path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.main import main

if __name__ == "__main__":
    sys.exit(main())
