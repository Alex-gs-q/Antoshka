from __future__ import annotations


def get_voice_timeout_seconds(settings: dict, default: int = 12) -> int:
    ui = (settings or {}).get("ui", {}) or {}
    raw = ui.get("voice_response_timeout_sec", ui.get("voice_response_timeout", default))
    try:
        value = int(raw)
    except Exception:
        value = default
    return max(1, min(30, value))


def apply_timeout_ms(seconds: int) -> int:
    value = int(seconds)
    if value < 1:
        value = 1
    return value * 1000
