from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from services.storage import read_json, write_json


def add_note(data_dir: Path, text: str) -> None:
    path = data_dir / "notes.json"
    notes: List[Dict[str, str]] = read_json(path, default=[])
    notes.append(
        {"text": text, "created_at": datetime.now().isoformat(timespec="seconds")}
    )
    write_json(path, notes)



def list_notes(data_dir: Path) -> list[dict]:
    path = data_dir / "notes.json"
    data = read_json(path, default=[])
    if isinstance(data, list):
        return data
    return []


def delete_note(data_dir: Path, index: int) -> bool:
    notes = list_notes(data_dir)
    if index < 1 or index > len(notes):
        return False
    notes.pop(index - 1)
    write_json(data_dir / "notes.json", notes)
    return True
