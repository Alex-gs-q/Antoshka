from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from services.storage import read_json, write_json


def add_note(data_dir: Path, text: str) -> None:
    path = data_dir / "notes.json"
    notes: List[Dict[str, str]] = read_json(path, default=[])
    notes.append({"text": text, "created_at": datetime.now().isoformat(timespec="seconds")})
    write_json(path, notes)
