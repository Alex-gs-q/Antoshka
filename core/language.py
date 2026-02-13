from __future__ import annotations

import re

_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")


def detect_language(text: str) -> str:
    if _CYRILLIC_RE.search(text or ""):
        return "ru"
    return "en"


def normalize_language_mode(mode: str | None) -> str:
    mode = (mode or "auto").strip().lower()
    if mode in {"ru", "en", "auto"}:
        return mode
    return "auto"


def resolve_language(mode: str | None, text: str | None, fallback: str = "ru") -> str:
    mode = normalize_language_mode(mode)
    if mode == "auto":
        if text:
            return detect_language(text)
        return fallback
    return mode
