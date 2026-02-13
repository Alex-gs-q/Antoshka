from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.text_norm import normalize_match_text


def resolve_known_path(text: str) -> Optional[str]:
    if not text:
        return None
    t = normalize_match_text(text)
    home = Path.home()
    mapping = {
        "zagruzki": home / "Downloads",
        "downloads": home / "Downloads",
        "dokumenty": home / "Documents",
        "documents": home / "Documents",
        "rabochiy stol": home / "Desktop",
        "desktop": home / "Desktop",
        "izobrazheniya": home / "Pictures",
        "pictures": home / "Pictures",
        "muzyka": home / "Music",
        "music": home / "Music",
        "video": home / "Videos",
        "videos": home / "Videos",
    }
    if t in mapping:
        return str(mapping[t])
    return None
