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


def update_note(data_dir: Path, index: int, new_text: str) -> bool:
    notes = list_notes(data_dir)
    if index < 1 or index > len(notes):
        return False
    notes[index - 1]["text"] = new_text
    notes[index - 1]["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(data_dir / "notes.json", notes)
    return True


def replace_in_note(data_dir: Path, index: int, old: str, new: str) -> bool:
    notes = list_notes(data_dir)
    if index < 1 or index > len(notes):
        return False
    text = notes[index - 1].get("text", "")
    if old not in text:
        return False
    notes[index - 1]["text"] = text.replace(old, new, 1)
    notes[index - 1]["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(data_dir / "notes.json", notes)
    return True


def find_note_index(data_dir: Path, query: str) -> int | None:
    notes = list_notes(data_dir)
    q = (query or "").strip().lower()
    if not q:
        return None
    for idx, n in enumerate(notes, start=1):
        text = (n.get("text") or "").lower()
        if q in text:
            return idx
    return None
