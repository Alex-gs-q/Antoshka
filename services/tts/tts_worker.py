from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Optional

from core.logger import setup_logger
from core.tts import TTS, TTSConfig


@dataclass(frozen=True)
class TTSItem:
    text: str
    lang: str


class TTSWorker:
    def __init__(self, settings: dict):
        self.log = setup_logger()
        self._queue: "queue.Queue[TTSItem]" = queue.Queue()
        self._stop = threading.Event()
        self._tts_ru: Optional[TTS] = None
        self._tts_en: Optional[TTS] = None
        self._last_error: Optional[str] = None
        self.update_settings(settings)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update_settings(self, settings: dict) -> None:
        tts_raw = settings.get("tts", {}) or {}
        self._tts_ru = TTS(_build_tts_config(tts_raw, "ru"))
        self._tts_en = TTS(_build_tts_config(tts_raw, "en"))
        self._last_error = None
        self.log.info("TTS settings updated: provider=%s", tts_raw.get("provider", "auto"))

    def stop(self) -> None:
        self._stop.set()
        self._queue.put(TTSItem(text="", lang="ru"))

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def is_available(self) -> bool:
        tts = self._tts_ru
        if not tts:
            return False
        if tts.provider == "edge":
            return tts.last_error is None
        return tts.engine is not None

    def say(self, text: str, lang: str = "ru") -> None:
        text = (text or "").strip()
        if not text:
            return
        self._queue.put(TTSItem(text=text, lang=lang))

    def get_volume(self) -> float | None:
        if self._tts_ru:
            return self._tts_ru.get_volume()
        return None

    def set_volume(self, level: float) -> bool:
        if self._tts_ru:
            return self._tts_ru.set_volume(level)
        return False

    def set_mute(self, mute: bool) -> bool:
        if self._tts_ru:
            return self._tts_ru.set_mute(mute)
        return False

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.3)
            except queue.Empty:
                continue
            if self._stop.is_set():
                break
            tts = self._tts_ru if item.lang == "ru" else self._tts_en
            if not tts:
                self.log.warning("TTS worker: no engine for lang=%s", item.lang)
                continue
            try:
                self.log.info("TTS start: lang=%s len=%s", item.lang, len(item.text))
                tts.say(item.text)
                self.log.info("TTS done: lang=%s", item.lang)
            except Exception as e:  # noqa: BLE001
                self._last_error = str(e)
                self.log.exception("TTS worker failed: %s", e)


def _build_tts_config(tts_raw: dict, lang: str) -> TTSConfig:
    voice_key = "voice_ru" if lang == "ru" else "voice_en"
    voice_name_key = "voice_name_contains_ru" if lang == "ru" else "voice_name_contains_en"
    voice = str(tts_raw.get(voice_key) or tts_raw.get("voice") or "")
    voice_name_contains = tts_raw.get(voice_name_key)
    return TTSConfig(
        enabled=bool(tts_raw.get("enabled", True)),
        provider=str(tts_raw.get("provider", "auto")),
        rate=int(tts_raw.get("rate", 180)),
        volume=float(tts_raw.get("volume", 1.0)),
        voice=voice or ("ru-RU-DmitryNeural" if lang == "ru" else "en-US-GuyNeural"),
        pitch=int(tts_raw.get("pitch", 0)),
        voice_name_contains=voice_name_contains,
    )
