from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.config import save_settings
from core.language import resolve_language
from core.logger import setup_logger
from core.resources import resource_path


@dataclass
class STTConfig:
    mode: str = "text"
    prompt: str = "Ты: "


@dataclass
class STTStatus:
    available: bool
    code: str
    requested_mode: str
    resolved_model_path: Path | None = None
    detail: str = ""


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


def validate_vosk_model_dir(path: Path | str) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return False
    if not (p / "conf").is_dir():
        return False
    marker_dirs = ((p / "graph").is_dir(), (p / "am").is_dir(), (p / "ivector").is_dir())
    marker_files = (
        (p / "HCLG.fst").is_file(),
        (p / "final.mdl").is_file(),
        (p / "conf" / "model.conf").is_file(),
    )
    return any(marker_dirs) or any(marker_files)


def is_valid_vosk_model_dir(path: Path | str) -> bool:
    return validate_vosk_model_dir(path)


def _glob_dirs(base: Path, pattern: str) -> list[Path]:
    if not base.exists() or not base.is_dir():
        return []
    try:
        return [p for p in base.glob(pattern) if p.is_dir()]
    except Exception:
        return []


def _frozen_bases() -> list[Path]:
    bases: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bases.append(Path(str(meipass)))
    bases.append(Path(sys.executable).resolve().parent)
    return bases


def _candidate_model_paths(settings: dict, lang: str) -> list[Path]:
    stt_raw = settings.get("stt", {}) or {}
    configured = [
        stt_raw.get(f"vosk_model_path_{lang}"),
        stt_raw.get("vosk_model_path"),
    ]
    candidates: list[Path] = []
    for item in configured:
        if item:
            candidates.append(Path(str(item)))

    bases = [Path("."), Path.cwd(), resource_path(Path(".")), resource_path(Path("_internal"))]
    bases.extend(_frozen_bases())
    for base in bases:
        candidates.append(base / "models" / "vosk")
        candidates.extend(_glob_dirs(base / "models", "vosk-model*"))
        candidates.append(base / "_internal" / "models" / "vosk")
        candidates.extend(_glob_dirs(base / "_internal" / "models", "vosk-model*"))

    out: list[Path] = []
    seen: set[str] = set()
    for p in candidates:
        variants = [p]
        if not p.is_absolute():
            variants.append(resource_path(p))
        for v in variants:
            key = str(v.resolve()) if v.exists() else os.path.normcase(str(v))
            if key in seen:
                continue
            seen.add(key)
            out.append(v)
    return out


def resolve_vosk_model_path(settings: dict, lang: str = "ru") -> Path | None:
    for candidate in _candidate_model_paths(settings, lang):
        if validate_vosk_model_dir(candidate):
            return candidate
    return None


def get_stt_status(settings: dict) -> STTStatus:
    logger = setup_logger()
    stt_raw = settings.get("stt", {}) or {}
    mode = (stt_raw.get("mode") or "text").lower()
    lang_mode = stt_raw.get("language") or (settings.get("app", {}) or {}).get("language", "auto")
    lang = resolve_language(lang_mode, None, fallback="ru")
    if lang_mode == "auto":
        logger.info("STT language auto -> using %s model", lang)
    else:
        logger.info("STT language: %s", lang)

    if mode not in {"vosk", "auto"}:
        return STTStatus(available=False, code="not_requested", requested_mode=mode)

    model_path = resolve_vosk_model_path(settings, lang=lang)
    if model_path is not None:
        return STTStatus(available=True, code="ready", requested_mode=mode, resolved_model_path=model_path)

    if lang != "ru":
        ru_path = resolve_vosk_model_path(settings, lang="ru")
        if ru_path is not None:
            return STTStatus(
                available=True,
                code="ready_fallback_lang",
                requested_mode=mode,
                resolved_model_path=ru_path,
                detail=lang,
            )
    return STTStatus(available=False, code="missing_model", requested_mode=mode)


def _attach_status(stt: BaseSTT, status: STTStatus) -> BaseSTT:
    setattr(stt, "_stt_available", bool(status.available))
    setattr(stt, "_stt_status_code", str(status.code))
    setattr(stt, "_stt_requested_mode", str(status.requested_mode))
    setattr(stt, "_stt_model_path", str(status.resolved_model_path) if status.resolved_model_path else "")
    return stt


def create_stt(settings: dict) -> BaseSTT:
    logger = setup_logger()
    stt_raw = settings.get("stt", {}) or {}
    mode = (stt_raw.get("mode") or "text").lower()
    status = get_stt_status(settings)

    if mode in {"vosk", "auto"}:
        try:
            # Lazy import to avoid crash if vosk deps not installed in text mode
            from core.stt_vosk import VoskConfig, VoskSTT
            import sounddevice as sd

            model_path = status.resolved_model_path
            lang = resolve_language(
                stt_raw.get("language") or (settings.get("app", {}) or {}).get("language", "auto"),
                None,
                fallback="ru",
            )
            fallback_from = status.detail if status.code == "ready_fallback_lang" else None
            if fallback_from:
                lang = "ru"
                logger.warning("Vosk model for %s missing, fallback to %s", fallback_from, lang)
            if model_path is None:
                raise FileNotFoundError("Vosk model not found")

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
            return _attach_status(stt, status)
        except Exception as e:  # noqa: BLE001
            if mode == "vosk":
                logger.warning("Vosk STT unavailable, falling back to text: %s", e)
            else:
                logger.info("STT auto fallback to text: %s", e)
            fail_status = status
            if fail_status.code.startswith("ready"):
                fail_status = STTStatus(
                    available=False,
                    code="runtime_unavailable",
                    requested_mode=mode,
                    resolved_model_path=status.resolved_model_path,
                    detail=str(e),
                )
            return _attach_status(TextSTT(STTConfig(mode="text", prompt="Ты: ")), fail_status)

    logger.info("STT mode: text")
    return _attach_status(TextSTT(STTConfig(mode="text", prompt="Ты: ")), status)
