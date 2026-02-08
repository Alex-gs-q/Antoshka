from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import os
import sys
import tempfile
import threading
import asyncio

from core.logger import setup_logger

try:
    import pyttsx3
except Exception:  # noqa: BLE001
    pyttsx3 = None
try:
    import edge_tts
except Exception:  # noqa: BLE001
    edge_tts = None
try:
    import winsound
except Exception:  # noqa: BLE001
    winsound = None


@dataclass
class TTSConfig:
    enabled: bool = True
    provider: str = "auto"  # auto | pyttsx3 | edge
    rate: int = 180
    volume: float = 1.0
    voice: str = "ru-RU-DmitryNeural"
    pitch: int = 0  # edge-tts: -50..+50
    voice_name_contains: Optional[str] = None


class TTS:
    def __init__(self, cfg: TTSConfig):
        self.logger = setup_logger()
        self.cfg = cfg
        self.engine = None
        self._last_volume = float(cfg.volume)
        self.last_error: Optional[str] = None
        self.last_info: Optional[str] = None
        self._lock = threading.Lock()
        self.provider = (cfg.provider or "auto").lower().strip()

        if not cfg.enabled:
            self.logger.info("TTS disabled by config")
            self.last_info = "disabled_by_config"
            return

        provider = self.provider
        if provider == "auto":
            provider = (
                "edge"
                if (edge_tts is not None and sys.platform == "win32")
                else "pyttsx3"
            )
        self.provider = provider

        if provider == "edge":
            if edge_tts is None:
                self.last_error = "edge_tts_not_installed"
                self.logger.warning("TTS unavailable: edge-tts not installed")
                return
            if sys.platform != "win32":
                self.last_error = "edge_tts_windows_only"
                self.logger.warning(
                    "TTS unavailable: edge-tts playback only wired for Windows"
                )
                return
            if winsound is None:
                self.last_error = "winsound_unavailable"
                self.logger.warning("TTS unavailable: winsound not available")
                return
            self.last_info = "edge_tts_ready"
            self.logger.info("TTS initialized (edge-tts), voice=%s", cfg.voice)
            return

        if pyttsx3 is None:
            self.last_error = "pyttsx3_not_installed"
            self.logger.warning("TTS unavailable: pyttsx3 not installed")
            return

        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", int(cfg.rate))
            self.engine.setProperty("volume", float(cfg.volume))

            if cfg.voice_name_contains:
                self._select_voice(cfg.voice_name_contains)

            self.last_info = "pyttsx3_ready"
            self.logger.info("TTS initialized (pyttsx3)")
        except Exception as e:  # noqa: BLE001
            self.engine = None
            self.last_error = str(e)
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
            self.logger.info(
                "TTS voice not found for needle=%s (using default)", needle
            )
        except Exception as e:  # noqa: BLE001
            self.logger.exception("TTS select voice failed: %s", e)

    def say(self, text: str) -> None:
        self.logger.info("TTS say start")
        if not self.cfg.enabled:
            return
        text = (text or "").strip()
        if not text or text == "__EXIT__":
            return
        try:
            if self.provider == "edge":
                self._say_edge(text)
                return
            if not self.engine:
                return
            self.engine.say(text)
            self.engine.runAndWait()
            self.logger.info("TTS say done")
        except Exception as e:  # noqa: BLE001
            self.last_error = str(e)
            self.logger.exception("TTS say failed: %s", e)

    def _say_edge(self, text: str) -> None:
        if edge_tts is None or winsound is None:
            return
        rate_pct = max(-90, min(200, int((self.cfg.rate - 180) / 2)))
        rate = f"{rate_pct:+d}%"
        pitch = max(-50, min(50, int(self.cfg.pitch)))

        async def _run() -> str:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.cfg.voice,
                rate=rate,
                pitch=f"{pitch:+d}Hz",
                volume="+0%",
            )
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                await communicate.save(f.name)
                return f.name

        with self._lock:
            tmp = None
            try:
                tmp = asyncio.run(_run())
                winsound.PlaySound(tmp, winsound.SND_FILENAME)
                self.logger.info("TTS edge playback done")
            finally:
                if tmp and os.path.exists(tmp):
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass

    def get_volume(self) -> float | None:
        if not self.engine or self.provider == "edge":
            return None
        try:
            return float(self.engine.getProperty("volume"))
        except Exception as e:  # noqa: BLE001
            self.logger.exception("TTS get_volume failed: %s", e)
            return None

    def set_volume(self, level: float) -> bool:
        if not self.engine or self.provider == "edge":
            return False
        level = max(0.0, min(1.0, float(level)))
        try:
            self.engine.setProperty("volume", level)
            self._last_volume = level
            return True
        except Exception as e:  # noqa: BLE001
            self.logger.exception("TTS set_volume failed: %s", e)
            return False

    def set_mute(self, mute: bool) -> bool:
        if not self.engine or self.provider == "edge":
            return False
        try:
            if mute:
                current = self.get_volume()
                if current is not None:
                    self._last_volume = current
                return self.set_volume(0.0)
            return self.set_volume(self._last_volume or 1.0)
        except Exception as e:  # noqa: BLE001
            self.logger.exception("TTS set_mute failed: %s", e)
            return False
