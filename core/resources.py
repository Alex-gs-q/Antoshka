from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str | Path) -> Path:
    """
    Resolve resource path for dev and PyInstaller.
    """
    rel = Path(relative)
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return (base / rel).resolve()
