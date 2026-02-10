from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.config import save_settings
from core.language import resolve_language
from core.logger import setup_logger


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
    lang_mode = stt_raw.get("language") or (settings.get("app", {}) or {}).get(
        "language", "auto"
    )
    lang = resolve_language(lang_mode, None, fallback="ru")
    if lang_mode == "auto":
        logger.info("STT language auto -> using %s model", lang)
    else:
        logger.info("STT language: %s", lang)

    if mode in {"vosk", "auto"}:
        try:
            # Lazy import to avoid crash if vosk deps not installed in text mode
            from core.stt_vosk import VoskSTT, VoskConfig
            import sounddevice as sd

            fallback_from = None
            model_path = Path(
                stt_raw.get(f"vosk_model_path_{lang}")
                or stt_raw.get("vosk_model_path")
                or "models/vosk"
            )
            if not model_path.exists() and lang != "ru":
                ru_path = Path(
                    stt_raw.get("vosk_model_path_ru")
                    or stt_raw.get("vosk_model_path")
                    or "models/vosk"
                )
                if ru_path.exists():
                    fallback_from = lang
                    lang = "ru"
                    model_path = ru_path
                    logger.warning("Vosk model for %s missing, fallback to %s", fallback_from, lang)
            if not model_path.exists():
                raise FileNotFoundError(f"Vosk model not found at {model_path}")
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
                except Exception as e:  # noqa: BLE001
                    logger.exception("Failed to resolve default input device: %s", e)
                    device = None
            stt = VoskSTT(
                VoskConfig(
                    model_path=str(model_path),
                    device=device,
                    max_listen_seconds=int(stt_raw.get("max_listen_seconds", 20)),
                    min_listen_seconds=float(stt_raw.get("min_listen_seconds", 0.0)),
                    silence_seconds_to_stop=float(stt_raw.get("silence_seconds_to_stop", 1.0)),
                )
            )
            setattr(stt, "_lang", lang)
            if fallback_from:
                setattr(stt, "_fallback_from", fallback_from)
            return stt
        except Exception as e:  # noqa: BLE001
            if mode == "vosk":
                logger.warning("Vosk STT unavailable, falling back to text: %s", e)
            else:
                logger.info("STT auto fallback to text: %s", e)

    logger.info("STT mode: text")
    return TextSTT(STTConfig(mode="text", prompt="Ты: "))
