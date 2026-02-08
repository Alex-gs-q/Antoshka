from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, List

from core.logger import setup_logger


@dataclass
class ScheduledItem:
    timer: threading.Timer
    message: str


class Scheduler:
    def __init__(self, notify: Callable[[str], None]):
        self.logger = setup_logger()
        self.notify = notify
        self._items: List[ScheduledItem] = []

    def schedule_in(self, seconds: int, message: str) -> None:
        def _fire():
            try:
                self.notify(message)
            except Exception as e:  # noqa: BLE001
                self.logger.error("Scheduler notify failed: %s", e)

        timer = threading.Timer(seconds, _fire)
        timer.daemon = True
        timer.start()
        self._items.append(ScheduledItem(timer=timer, message=message))
        self.logger.info("Scheduled in %ss: %s", seconds, message)
