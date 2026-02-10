from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.language import normalize_language_mode
from core.logger import setup_logger
from core.text_norm import normalize_text

_WARNED_PHRASES: set[str] = set()


def _looks_like_mojibake(text: str) -> bool:
    if not text:
        return False
    # Common UTF-8->cp1251/latin1 mojibake markers for Cyrillic.
    bad_markers = ("Ð", "Ñ", "Ã", "Â")
    return any(m in text for m in bad_markers)


@dataclass(frozen=True)
class NLUResult:
    intent: str
    slots: Dict[str, Any]
    confidence: float = 1.0


_PHRASES_PATHS = {
    "ru": Path("config") / "phrases_ru.json",
    "en": Path("config") / "phrases_en.json",
}

# Кэшируем фразы, чтобы не читать JSON каждый раз
_CACHED_PAIRS: dict[str, List[Tuple[str, str]]] = {}


def _load_pairs(lang: str) -> List[Tuple[str, str]]:
    """
    Возвращает список (phrase, intent), где phrase уже нормализована.
    Сортируем по длине фразы: длинные матчится первыми.
    """
    lang = normalize_language_mode(lang)
    if lang == "auto":
        lang = "ru"

    if lang in _CACHED_PAIRS:
        return _CACHED_PAIRS[lang]

    path = _PHRASES_PATHS.get(lang, _PHRASES_PATHS["ru"])
    if not path.exists():
        from core.resources import resource_path

        path = resource_path(path)
    raw_text = path.read_text(encoding="utf-8")
    if lang == "ru":
        if _looks_like_mojibake(raw_text) and str(path) not in _WARNED_PHRASES:
            logger = setup_logger()
            logger.warning(
                "phrases_ru.json looks like mojibake. Re-save as UTF-8 or run: python tools/fix_phrases.py"
            )
            _WARNED_PHRASES.add(str(path))
    data = json.loads(raw_text)
    pairs: List[Tuple[str, str]] = []

    for intent, phrases in data.items():
        for p in phrases:
            pn = normalize_text(p)
            if pn:
                pairs.append((pn, intent))

    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    _CACHED_PAIRS[lang] = pairs
    return pairs


def _phrase_as_words_in_text(phrase: str, text: str) -> bool:
    """
    Проверяем, что phrase встречается в text как "слова", а не внутри других слов.
    Пример: phrase="час" НЕ должен матчиться в "сейчас".
    """
    pattern = r"(?:^|\s)" + re.escape(phrase) + r"(?:$|\s)"
    return re.search(pattern, text) is not None


def detect_intent(text: str, lang: str = "ru") -> NLUResult:
    logger = setup_logger()

    t = normalize_text(text)
    if not t:
        return NLUResult(intent="unknown", slots={}, confidence=0.0)

    for phrase, intent in _load_pairs(lang):
        # 1) точное совпадение
        if t == phrase:
            logger.info("NLU matched intent=%s text=%s", intent, t)
            return NLUResult(intent=intent, slots={}, confidence=1.0)

        # 2) совпадение по словам (без "час" внутри "сейчас")
        if _phrase_as_words_in_text(phrase, t):
            logger.info("NLU matched intent=%s text=%s", intent, t)
            return NLUResult(intent=intent, slots={}, confidence=0.9)

    return NLUResult(intent="unknown", slots={}, confidence=0.0)
