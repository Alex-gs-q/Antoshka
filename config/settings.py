from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from core.logger import setup_logger
from core.paths import config_dir
from core.resources import resource_path
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SETTINGS: Dict[str, Any] = {
    "app": {"name": "Антошка", "language": "auto", "log_level": "INFO", "debug": False},
    "stt": {
        "mode": "text",
        "vosk_model_path": "models/vosk",
        "vosk_model_path_ru": "models/vosk",
        "vosk_model_path_en": "models/vosk_en",
        "device": None,
        "language": "auto",
        "min_listen_seconds": 0.0,
        "max_listen_seconds": 20,
        "silence_seconds_to_stop": 1.0,
    },
    "tts": {
        "enabled": True,
        "provider": "auto",
        "rate": 180,
        "volume": 1.0,
        "pitch": 0,
        "voice_ru": "ru-RU-DmitryNeural",
        "voice_en": "en-US-GuyNeural",
        "voice_name_contains_ru": None,
        "voice_name_contains_en": None,
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
        "ai_mode_autostart": True,
        "voice_filter_lang": "All",
        "voice_filter_gender": "All",
        "theme_preset": "dark",
        "accent_color": "#7dd3fc",
        "background_intensity": 0.7,
        "show_start_screen": True,
        "voice_response_timeout_sec": 12,
        "alerts_enabled": True,
        "alerts_sound": "Music/Kioko - The Phantom Traveler.mp3",
        "alerts_sound_name": "default",
        "alerts_sound_path": "",
        "alerts_custom_sounds": [],
        "alerts_volume": 80,
        "alerts_loop": True,
        "snooze_default_minutes": 5,
        "snooze_quick_enabled": True,
        "snooze_quick_buttons": [1, 3, 5, 10, 15],
        "snooze_dropdown_enabled": True,
        "snooze_dropdown_options": [1, 3, 5, 10, 15, 30],
        "timer_restart_enabled": True,
        "system_notifications": True,
        "notify_show_text": True,
        "notify_show_icon": True,
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


def load_settings(path: str | None = None) -> Dict[str, Any]:
    logger = setup_logger(level=DEFAULT_SETTINGS["app"]["log_level"])
    p = Path(path) if path else (config_dir() / "settings.json")
    bundled_rel = Path(path) if path else Path("config/settings.json")

    if not p.exists():
        bundled = resource_path(bundled_rel)
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
        ui = settings.setdefault("ui", {})
        if "voice_response_timeout_sec" not in ui and "voice_response_timeout" in ui:
            ui["voice_response_timeout_sec"] = ui.get("voice_response_timeout", 12)
        logger.info("Settings loaded from %s", p)
        return settings
    except Exception as e:
        logger.exception(
            "Failed to load settings from %s. Using defaults. Error: %s", p, e
        )
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: Dict[str, Any], path: str | None = None) -> None:
    logger = setup_logger(level=DEFAULT_SETTINGS["app"]["log_level"])
    p = Path(path) if path else (config_dir() / "settings.json")
    try:
        ui = settings.get("ui")
        if isinstance(ui, dict) and "voice_response_timeout" in ui:
            ui.pop("voice_response_timeout", None)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Settings saved to %s", p)
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to save settings to %s. Error: %s", p, e)
