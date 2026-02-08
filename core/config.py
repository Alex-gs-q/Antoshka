import json
from pathlib import Path
from typing import Any, Dict

from core.logger import setup_logger


DEFAULT_SETTINGS: Dict[str, Any] = {
    "app": {"name": "Антошка", "language": "ru", "log_level": "INFO"},
    "stt": {"mode": "text", "vosk_model_path": "models/vosk"},
    "tts": {"enabled": True, "voice": "default", "rate": 180},
    "safety": {
        "dangerous_mode": False,
        "confirm_phrase": "подтверждаю",
        "confirm_ttl_seconds": 10,
    },
    "llm": {"provider": "dummy", "model": "default", "history_max_messages": 10},
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Рекурсивно объединяет словари: override перекрывает base."""
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_settings(path: str = "config/settings.json") -> Dict[str, Any]:
    logger = setup_logger(level=DEFAULT_SETTINGS["app"]["log_level"])
    p = Path(path)

    if not p.exists():
        logger.warning("Settings file not found: %s. Using defaults.", p)
        return dict(DEFAULT_SETTINGS)

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings.json must contain a JSON object")
        settings = deep_merge(DEFAULT_SETTINGS, data)
        logger.info("Settings loaded from %s", p)
        return settings
    except Exception as e:
        logger.exception("Failed to load settings from %s. Using defaults. Error: %s", p, e)
        return dict(DEFAULT_SETTINGS)
