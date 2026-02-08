from typing import Dict, Any

from adapters.windows import open_path


def handle(slots: Dict[str, Any]) -> str:
    path = slots.get("path")
    if not path:
        return "Не понял, какой путь открыть."

    ok = open_path(path)
    return "Открываю." if ok else "Не смог открыть путь."
