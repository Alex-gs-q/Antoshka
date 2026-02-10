from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from services.storage import read_json, write_json


def append_chat(data_dir: Path, role: str, text: str) -> None:
    path = data_dir / "chat_history.json"
    history: List[Dict[str, str]] = read_json(path, default=[])
    history.append(
        {
            "role": role,
            "text": text,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
    )
    write_json(path, history)


def clear_chat_history(data_dir: Path) -> None:
    path = data_dir / "chat_history.json"
    write_json(path, [])
