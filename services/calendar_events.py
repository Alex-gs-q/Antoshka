from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from services.storage import read_json, write_json


def add_event(data_dir: Path, title: str, when: Optional[datetime]) -> None:
    path = data_dir / "calendar.json"
    events: List[Dict[str, str]] = read_json(path, default=[])
    events.append(
        {
            "title": title,
            "when": when.isoformat(timespec="minutes") if when else "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    write_json(path, events)


def list_events(data_dir: Path) -> list[dict]:
    data = read_json(data_dir / "calendar.json", default=[])
    if isinstance(data, list):
        return data
    return []
