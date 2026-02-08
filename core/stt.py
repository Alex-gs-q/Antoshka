from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.logger import setup_logger
from core.config import save_settings


@dataclass
class STTConfig:
    mode: str = "text"
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

    def stop(self) -> None:
        """Optional: request stop for listening."""
        return


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
    logger = setup_logger()
    stt_raw = settings.get("stt", {}) or {}
    mode = (stt_raw.get("mode") or "text").lower()

    if mode in {"vosk", "auto"}:
        try:
            # Lazy import to avoid crash if vosk deps not installed in text mode
            from core.stt_vosk import VoskSTT, VoskConfig
            import sounddevice as sd

            model_path = stt_raw.get("vosk_model_path") or "models/vosk"
            device = stt_raw.get("device")
            if device is None:
                try:
                    default_in = sd.default.device[0]
                    if default_in is not None and default_in >= 0:
                        device = int(default_in)
                    else:
                        for idx, info in enumerate(sd.query_devices()):
                            if info.get("max_input_channels", 0) > 0:
                                device = idx
                                break
                    if device is not None:
                        stt_raw["device"] = device
                        settings["stt"] = stt_raw
                        save_settings(settings)
                except Exception:
                    device = None
            return VoskSTT(VoskConfig(model_path=str(model_path), device=device))
        except Exception as e:  # noqa: BLE001
            if mode == "vosk":
                logger.warning("Vosk STT unavailable, falling back to text: %s", e)
            else:
                logger.info("STT auto fallback to text: %s", e)

    logger.info("STT mode: text")
    return TextSTT(STTConfig(mode="text", prompt="Ты: "))
