from __future__ import annotations

from typing import List

from core.logger import setup_logger

try:
    import pyttsx3
except Exception:  # noqa: BLE001
    pyttsx3 = None


EDGE_VOICES_PRESET = [
    "ru-RU-DmitryNeural",
    "ru-RU-SvetlanaNeural",
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-GB-RyanNeural",
    "en-GB-SoniaNeural",
]


def list_pyttsx3_voices() -> List[str]:
    logger = setup_logger()
    if pyttsx3 is None:
        return []
    try:
        engine = pyttsx3.init()
        voices = []
        for v in engine.getProperty("voices"):
            name = str(getattr(v, "name", "") or "").strip()
            if name:
                voices.append(name)
        return sorted(set(voices))
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to list pyttsx3 voices: %s", e)
        return []


def list_edge_voices() -> List[str]:
    return list(EDGE_VOICES_PRESET)
