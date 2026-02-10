from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class Event:
    type: str
    due_time: datetime
    payload: dict
    duration_sec: int | None = None
    snooze_count: int = 0
    dismissed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    state: str = "scheduled"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
