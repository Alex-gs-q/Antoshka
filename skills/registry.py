from typing import Callable, Dict, Any, Optional

from skills import help as skill_help
from skills import greet as skill_greet
from skills import open_url as skill_open_url
from skills import open_path as skill_open_path
from skills import exit as skill_exit
from skills.time_date import handle_time, handle_date


Handler = Callable[[Dict[str, Any]], str]


def get_handler(intent: str) -> Optional[Handler]:
    mapping: Dict[str, Handler] = {
        "help": skill_help.handle,
        "greet": skill_greet.handle,
        "time": handle_time,
        "date": handle_date,
        "open_url": skill_open_url.handle,
        "open_path": skill_open_path.handle,
        "exit": skill_exit.handle,
    }
    return mapping.get(intent)


def run_intent(intent: str, slots: Dict[str, Any]) -> str:
    handler = get_handler(intent)
    if handler is None:
        return f"Неизвестная команда: {intent}"
    return handler(slots or {})
