from typing import Dict, Any

from adapters.windows import open_url


def handle(slots: Dict[str, Any]) -> str:
    url = slots.get("url")
    if not url:
        return "Не понял, какой сайт открыть."

    ok = open_url(url)
    return "Открываю сайт." if ok else "Не смог открыть сайт."
