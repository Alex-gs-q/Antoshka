from __future__ import annotations

import re

# всё, что НЕ буква/цифра/пробел — выкидываем
_RE_NON_ALNUM = re.compile(r"[^0-9a-zа-яё\s]+", flags=re.IGNORECASE)
_RE_SPACES = re.compile(r"\s+", flags=re.IGNORECASE)


def normalize_ru(text: str) -> str:
    """
    Нормализация русского текста для NLU/STT:
    - lower
    - ё -> е
    - выкинуть пунктуацию
    - схлопнуть пробелы
    """
    if text is None:
        return ""

    t = str(text).strip().lower()
    if not t:
        return ""

    t = t.replace("ё", "е")
    t = _RE_NON_ALNUM.sub(" ", t)
    t = _RE_SPACES.sub(" ", t).strip()
    return t


def normalize_text(text: str) -> str:
    """
    Stable alias for normalization used across modules.
    """
    return normalize_ru(text)