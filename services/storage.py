from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.logger import setup_logger


logger = setup_logger()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to read json: %s err=%s", path, e)
        return default


def write_json(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to write json: %s err=%s", path, e)
