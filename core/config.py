import json
from pathlib import Path
from typing import Any, Dict

from core.logger import setup_logger
from core.resources import resource_path

DEFAULT_SETTINGS: Dict[str, Any] = {
    "app": {"name": "Антошка", "language": "ru", "log_level": "INFO"},
    "stt": {"mode": "text", "vosk_model_path": "models/vosk"},
    "tts": {
        "enabled": True,
        "provider": "auto",
        "voice": "ru-RU-DmitryNeural",
        "rate": 180,
        "volume": 1.0,
        "pitch": 0,
        "voice_name_contains": None,
    },
    "safety": {
        "dangerous_mode": False,
        "confirm_phrase": "подтверждаю",
        "confirm_ttl_seconds": 10,
    },
    "llm": {"provider": "dummy", "model": "gpt-4o-mini", "history_max_messages": 10},
    "custom_sites": {},
    "custom_apps": {},
    "ui": {
        "wake_word": False,
        "continuous_dialogue": True,
        "hands_free": False,
        "ai_mode": False,
        "voice_filter_lang": "All",
        "voice_filter_gender": "All",
    },
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
        bundled = resource_path(path)
        if bundled.exists():
            p = bundled
        else:
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
        logger.exception(
            "Failed to load settings from %s. Using defaults. Error: %s", p, e
        )
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: Dict[str, Any], path: str = "config/settings.json") -> None:
    logger = setup_logger(level=DEFAULT_SETTINGS["app"]["log_level"])
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Settings saved to %s", p)
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to save settings to %s. Error: %s", p, e)
