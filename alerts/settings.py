from __future__ import annotations

from typing import Any, Dict, List


DEFAULT_ALERT_SETTINGS: Dict[str, Any] = {
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
    "notify_tray_fallback_dup": True,
    "debug_ui": False,
    "alert_popup_enabled": True,
    "alert_popup_auto_close_sec": 20,
    "timer_restart_enabled": True,
}


def _uniq_ints(values: List[int]) -> List[int]:
    seen = set()
    out: List[int] = []
    for v in values:
        iv = int(v)
        if iv not in seen:
            seen.add(iv)
            out.append(iv)
    return out


def get_alert_settings(settings: dict) -> Dict[str, Any]:
    ui = (settings or {}).get("ui", {}) or {}
    merged = dict(DEFAULT_ALERT_SETTINGS)
    merged.update(ui)
    merged["alerts_volume"] = int(merged.get("alerts_volume", 80))
    merged["snooze_default_minutes"] = int(merged.get("snooze_default_minutes", 5))
    merged["snooze_quick_buttons"] = _uniq_ints(merged.get("snooze_quick_buttons", [1, 3, 5, 10, 15]))
    merged["snooze_dropdown_options"] = _uniq_ints(merged.get("snooze_dropdown_options", [1, 3, 5, 10, 15, 30]))
    if not isinstance(merged.get("alerts_custom_sounds"), list):
        merged["alerts_custom_sounds"] = []
    return merged
