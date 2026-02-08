from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.logger import setup_logger


logger = setup_logger()


@dataclass
class VolumeController:
    get_level: Optional[callable] = None
    set_level: Optional[callable] = None
    set_mute_fn: Optional[callable] = None

    def change_relative(self, delta: float) -> bool:
        if not self.get_level or not self.set_level:
            return False
        try:
            level = self.get_level()
            if level is None:
                return False
            level = max(0.0, min(1.0, level + delta))
            self.set_level(level)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("Volume change failed: %s", e)
            return False

    def set_mute(self, mute: bool) -> bool:
        if not self.set_mute_fn:
            return False
        try:
            self.set_mute_fn(mute)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("Volume mute failed: %s", e)
            return False
