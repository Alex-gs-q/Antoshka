from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.logger import setup_logger
from core.text_norm import normalize_text


@dataclass(frozen=True)
class NLUResult:
    intent: str
    slots: Dict[str, Any]
    confidence: float = 1.0


_PHRASES_PATH = Path("config") / "phrases_ru.json"

# Кэшируем фразы, чтобы не читать JSON каждый раз
_CACHED_PAIRS: List[Tuple[str, str]] | None = None


def _load_pairs() -> List[Tuple[str, str]]:
    """
    Возвращает список (phrase, intent), где phrase уже нормализована.
    Сортируем по длине фразы: длинные матчится первыми.
    """
    global _CACHED_PAIRS

    if _CACHED_PAIRS is not None:
        return _CACHED_PAIRS

    data = json.loads(_PHRASES_PATH.read_text(encoding="utf-8"))
    pairs: List[Tuple[str, str]] = []

    for intent, phrases in data.items():
        for p in phrases:
            pn = normalize_text(p)
            if pn:
                pairs.append((pn, intent))

    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    _CACHED_PAIRS = pairs
    return pairs


def _phrase_as_words_in_text(phrase: str, text: str) -> bool:
    """
    Проверяем, что phrase встречается в text как "слова", а не внутри других слов.
    Пример: phrase="час" НЕ должен матчиться в "сейчас".
    """
    pattern = r"(?:^|\s)" + re.escape(phrase) + r"(?:$|\s)"
    return re.search(pattern, text) is not None


def detect_intent(text: str) -> NLUResult:
    logger = setup_logger()

    t = normalize_text(text)
    if not t:
        return NLUResult(intent="unknown", slots={}, confidence=0.0)

    for phrase, intent in _load_pairs():
        # 1) точное совпадение
        if t == phrase:
            logger.info("NLU matched intent=%s text=%s", intent, t)
            return NLUResult(intent=intent, slots={}, confidence=1.0)

        # 2) совпадение по словам (без "час" внутри "сейчас")
        if _phrase_as_words_in_text(phrase, t):
            logger.info("NLU matched intent=%s text=%s", intent, t)
            return NLUResult(intent=intent, slots={}, confidence=0.9)

    return NLUResult(intent="unknown", slots={}, confidence=0.0)
