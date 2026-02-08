import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from core.logger import setup_logger
from core.text_norm import normalize_ru


@dataclass
class NLUResult:
    intent: str
    slots: Dict[str, Any]
    confidence: float = 1.0


_PHRASES_CACHE: Optional[Dict[str, Any]] = None


def load_phrases(path: str = "config/phrases_ru.json") -> Dict[str, Any]:
    global _PHRASES_CACHE
    if _PHRASES_CACHE is not None:
        return _PHRASES_CACHE

    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    _PHRASES_CACHE = data
    return data


def _match_exact(norm: str, phrases: list[str]) -> bool:
    return any(norm == normalize_ru(x) for x in phrases)


def detect_intent(text: str) -> Optional[NLUResult]:
    logger = setup_logger()
    norm = normalize_ru(text)

    if not norm:
        return None

    cfg = load_phrases()
    intents = cfg.get("intents", {})
    sites = cfg.get("sites", {})

    # 1) точные интенты
    for intent_name in ("help", "time", "date", "greet", "exit"):
        phrases = intents.get(intent_name, [])
        if phrases and _match_exact(norm, phrases):
            logger.info("NLU matched intent=%s text=%s", intent_name, norm)
            return NLUResult(intent=intent_name, slots={})

    # 2) open_url: "открой ютуб" / "открой https://..."
    m = re.match(r"^(открой|открыть|запусти|запуск)\s+(?P<target>.+)$", norm)
    if m:
        target = m.group("target").strip()

        if target in sites:
            url = sites[target]
            logger.info("NLU matched intent=open_url target=%s url=%s", target, url)
            return NLUResult(intent="open_url", slots={"url": url})

        if target.startswith(("http://", "https://")) or re.search(r"\.(ru|com|net|org|ua|io|dev)(/|$)", target):
            url = target if target.startswith(("http://", "https://")) else f"https://{target}"
            logger.info("NLU matched intent=open_url url=%s", url)
            return NLUResult(intent="open_url", slots={"url": url})

    return None
