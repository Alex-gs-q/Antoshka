from datetime import datetime
from typing import Dict, Any


def handle_time(_: Dict[str, Any]) -> str:
    now = datetime.now()
    return f"Сейчас {now:%H:%M}."


def handle_date(_: Dict[str, Any]) -> str:
    now = datetime.now()
    return f"Сегодня {now:%d.%m.%Y}."
