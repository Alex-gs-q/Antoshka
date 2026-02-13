from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from services.storage import read_json, write_json


def add_reminder(data_dir: Path, text: str, when: Optional[datetime]) -> None:
    path = data_dir / "reminders.json"
    reminders: List[Dict[str, str]] = read_json(path, default=[])
    reminders.append(
        {
            "text": text,
            "when": when.isoformat(timespec="seconds") if when else "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    write_json(path, reminders)
