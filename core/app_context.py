from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Any

from services.scheduler import Scheduler
from services.volume import VolumeController


@dataclass
class AppContext:
    notify: Callable[[str], None]
    data_dir: Path
    scheduler: Scheduler
    volume: Optional[VolumeController] = None
    llm_client: Optional[Any] = None
    registry: Optional[Any] = None
    on_settings_changed: Optional[Callable[[dict], None]] = None
    language_mode: str = "auto"
    language: str = "ru"
