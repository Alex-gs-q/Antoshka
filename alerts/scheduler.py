from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

from alerts.models import Event
from core.logger import setup_logger


class AlertScheduler:
    def __init__(self, on_event_fired: Callable[[Event], None]):
        self.log = setup_logger()
        self._on_event_fired = on_event_fired
        self._lock = threading.Lock()
        self._events: Dict[str, Event] = {}
        self._timers: Dict[str, threading.Timer] = {}

    def schedule_event(self, event: Event) -> str:
        with self._lock:
            self._events[event.id] = event
            self._schedule_timer(event)
        self.log.info("ALERT schedule id=%s type=%s due=%s", event.id, event.type, event.due_time)
        return event.id

    def reschedule_event(self, event_id: str, new_due_time: datetime) -> bool:
        with self._lock:
            event = self._events.get(event_id)
            if not event or event.dismissed:
                return False
            event.due_time = new_due_time
            event.state = "scheduled"
            self._cancel_timer(event_id)
            self._schedule_timer(event)
        self.log.info("ALERT reschedule id=%s due=%s", event_id, new_due_time)
        return True

    def dismiss_event(self, event_id: str) -> bool:
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                return False
            event.dismissed = True
            event.state = "dismissed"
            self._cancel_timer(event_id)
        self.log.info("ALERT dismiss id=%s", event_id)
        return True

    def dismiss_all(self) -> int:
        with self._lock:
            ids = list(self._events.keys())
        count = 0
        for event_id in ids:
            if self.dismiss_event(event_id):
                count += 1
        self.log.info("ALERT dismiss_all count=%s", count)
        return count

    def restart_timer(self, event_id: str) -> Optional[str]:
        with self._lock:
            event = self._events.get(event_id)
            if not event or event.type != "timer" or not event.duration_sec:
                return None
            duration = int(event.duration_sec)
        new_event = Event(
            type="timer",
            due_time=datetime.now() + timedelta(seconds=duration),
            payload=dict(event.payload),
            duration_sec=duration,
        )
        return self.schedule_event(new_event)

    def get_event(self, event_id: str) -> Optional[Event]:
        with self._lock:
            return self._events.get(event_id)

    def _schedule_timer(self, event: Event) -> None:
        delay = max(0.0, (event.due_time - datetime.now()).total_seconds())

        def _fire() -> None:
            with self._lock:
                current = self._events.get(event.id)
                if not current or current.dismissed:
                    return
                current.state = "alerting"
            self.log.info("ALERT fire id=%s type=%s due=%s", event.id, event.type, event.due_time)
            try:
                self._on_event_fired(current)
            except Exception as e:  # noqa: BLE001
                self.log.exception("ALERT fire failed: %s", e)

        timer = threading.Timer(delay, _fire)
        timer.daemon = True
        timer.start()
        self._timers[event.id] = timer

    def _cancel_timer(self, event_id: str) -> None:
        timer = self._timers.pop(event_id, None)
        if timer:
            try:
                timer.cancel()
            except Exception as e:  # noqa: BLE001
                self.log.exception("ALERT cancel timer failed: %s", e)
