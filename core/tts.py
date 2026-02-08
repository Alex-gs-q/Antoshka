from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.logger import setup_logger

try:
    import pyttsx3
except Exception:  # noqa: BLE001
    pyttsx3 = None


@dataclass
class TTSConfig:
    enabled: bool = True
    rate: int = 180
    volume: float = 1.0
    voice_name_contains: Optional[str] = None


class TTS:
    def __init__(self, cfg: TTSConfig):
        self.logger = setup_logger()
        self.cfg = cfg
        self.engine = None

        if not cfg.enabled:
            self.logger.info("TTS disabled by config")
            return

        if pyttsx3 is None:
            self.logger.warning("TTS unavailable: pyttsx3 not installed")
            return

        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", int(cfg.rate))
            self.engine.setProperty("volume", float(cfg.volume))

            if cfg.voice_name_contains:
                self._select_voice(cfg.voice_name_contains)

            self.logger.info("TTS initialized (pyttsx3)")
        except Exception as e:  # noqa: BLE001
            self.engine = None
            self.logger.exception("TTS init failed: %s", e)

    def _select_voice(self, needle: str) -> None:
        if not self.engine:
            return
        needle = needle.lower().strip()
        try:
            for v in self.engine.getProperty("voices"):
                name = (getattr(v, "name", "") or "").lower()
                if needle in name:
                    self.engine.setProperty("voice", v.id)
                    self.logger.info("TTS voice selected: %s", getattr(v, "name", v.id))
                    return
            self.logger.info("TTS voice not found for needle=%s (using default)", needle)
        except Exception as e:  # noqa: BLE001
            self.logger.exception("TTS select voice failed: %s", e)

    def say(self, text: str) -> None:
        if not self.engine or not self.cfg.enabled:
            return
        text = (text or "").strip()
        if not text or text == "__EXIT__":
            return
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:  # noqa: BLE001
            self.logger.exception("TTS say failed: %s", e)
