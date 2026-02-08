from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.logger import setup_logger


@dataclass
class STTConfig:
    mode: str = "text"  # future: "vosk"
    prompt: str = "Ты: "


class BaseSTT:
    def listen(self) -> Optional[str]:
        """
        Return:
          - None  -> user interrupted / EOF (need exit)
          - ""    -> empty input (skip)
          - text  -> normal user text
        """
        raise NotImplementedError


class TextSTT(BaseSTT):
    def __init__(self, config: STTConfig):
        self.config = config

    def listen(self) -> Optional[str]:
        try:
            text = input(self.config.prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not text:
            return ""
        return text


def create_stt(settings: dict) -> BaseSTT:
    """
    Factory: creates STT based on settings["stt"]["mode"].
    For now supports only text mode.
    """
    logger = setup_logger()
    stt_raw = settings.get("stt", {}) or {}
    mode = (stt_raw.get("mode") or "text").lower()

    if mode != "text":
        logger.warning("STT mode '%s' not implemented yet, fallback to text", mode)

    return TextSTT(STTConfig(mode="text", prompt="Ты: "))
