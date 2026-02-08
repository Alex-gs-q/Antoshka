from __future__ import annotations

import re
import unicodedata


# Удаляем все "шумы", но оставляем буквы/цифры/пробелы.
# Важно: не ломаем русские буквы.
_PUNCT_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)
_SPACES_RE = re.compile(r"\s+", flags=re.UNICODE)


def normalize_ru(text: str) -> str:
    """
    Нормализация русского текста:
    - lower
    - ё -> е
    - убираем пунктуацию
    - схлопываем пробелы
    """
    if not text:
        return ""

    t = text.strip().lower()
    t = t.replace("ё", "е")
    t = unicodedata.normalize("NFKC", t)

    # Пунктуацию заменяем на пробел, чтобы слова не склеивались
    t = _PUNCT_RE.sub(" ", t)
    t = _SPACES_RE.sub(" ", t).strip()
    return t


def normalize_text(text: str) -> str:
    """
    СТАБИЛЬНЫЙ API для остальных модулей.
    Всегда импортируем normalize_text().
    """
    return normalize_ru(text)