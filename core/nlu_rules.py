from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List, Tuple

from core.logger import setup_logger
from core.text_norm import normalize_text


@dataclass(frozen=True)
class NLUResult:
    intent: str
    slots: Dict[str, Any]
    confidence: float = 1.0


_PHRASES_PATH = Path("config") / "phrases_ru.json"


@lru_cache(maxsize=1)
def _load_phrases_normalized() -> Dict[str, List[str]]:
    """
    Load phrases and normalize them once.
    Cached to avoid re-reading file every request.
    """
    data = json.loads(_PHRASES_PATH.read_text(encoding="utf-8"))
    out: Dict[str, List[str]] = {}
    for intent, phrases in data.items():
        out[intent] = [normalize_text(p) for p in phrases]
    return out


def detect_intent(text: str) -> NLUResult:
    logger = setup_logger()

    t = normalize_text(text)
    if not t:
        return NLUResult(intent="unknown", slots={}, confidence=0.0)

    phrases = _load_phrases_normalized()

    # (phrase, intent) pairs sorted by phrase length desc
    pairs: List[Tuple[str, str]] = []
    for intent, items in phrases.items():
        for p in items:
            if p:
                pairs.append((p, intent))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)

    for phrase, intent in pairs:
        # exact OR substring
        if t == phrase or phrase in t:
            logger.info("NLU matched intent=%s text=%s", intent, t)
            return NLUResult(intent=intent, slots={}, confidence=1.0)

    return NLUResult(intent="unknown", slots={}, confidence=0.0)