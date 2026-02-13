from __future__ import annotations

import os
import sys
from pathlib import Path


def _app_base_dir() -> Path:
    override = os.environ.get("ANTOSHKA_DATA_DIR")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Antoshka"
    return Path.cwd()


def data_dir() -> Path:
    return _app_base_dir() / "data"


def config_dir() -> Path:
    return _app_base_dir() / "config"


def logs_dir() -> Path:
    return _app_base_dir() / "logs"
