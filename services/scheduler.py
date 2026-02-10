from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from alerts.models import Event
from alerts.scheduler import AlertScheduler
from core.logger import setup_logger


class Scheduler:
    def __init__(self, notify: Callable[[Event], None]):
        self.logger = setup_logger()
        self.notify = notify
        self._scheduler = AlertScheduler(on_event_fired=notify)

    def schedule_in(self, seconds: int, message: str, meta: dict | None = None) -> str:
        payload = dict(meta or {})
        payload.setdefault("message", message)
        event = Event(
            type=str(payload.get("type", "message")),
            due_time=datetime.now() + timedelta(seconds=int(seconds)),
            payload=payload,
            duration_sec=int(payload.get("duration_sec") or seconds),
        )
        event_id = self._scheduler.schedule_event(event)
        self.logger.info("Scheduled in %ss: %s id=%s", seconds, message, event_id)
        return event_id

    def reschedule_event(self, event_id: str, new_due_time: datetime) -> bool:
        return self._scheduler.reschedule_event(event_id, new_due_time)

    def dismiss_event(self, event_id: str) -> bool:
        return self._scheduler.dismiss_event(event_id)

    def get_event(self, event_id: str) -> Event | None:
        return self._scheduler.get_event(event_id)

    def restart_timer(self, event_id: str) -> str | None:
        return self._scheduler.restart_timer(event_id)
