from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QFontDatabase


@dataclass(frozen=True)
class Theme:
    name: str
    bg_top: QColor
    bg_bottom: QColor
    text_primary: QColor
    text_muted: QColor
    input_bg: QColor
    input_border: QColor
    button_bg: QColor
    button_border: QColor
    user_bubble_bg: QColor
    user_bubble_border: QColor
    bot_bubble_bg: QColor
    card_bg: QColor
    card_border: QColor
    accent: QColor
    accent_2: QColor


def _hex(color: str) -> QColor:
    return QColor(color)


def _mix(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, float(t)))
    r = int(c1.red() + (c2.red() - c1.red()) * t)
    g = int(c1.green() + (c2.green() - c1.green()) * t)
    b = int(c1.blue() + (c2.blue() - c1.blue()) * t)
    a = int(c1.alpha() + (c2.alpha() - c1.alpha()) * t)
    return QColor(r, g, b, a)


def _apply_intensity(color: QColor, intensity: float) -> QColor:
    intensity = max(0.2, min(1.0, float(intensity)))
    return QColor(
        int(color.red() * intensity),
        int(color.green() * intensity),
        int(color.blue() * intensity),
        color.alpha(),
    )


def _accent_pair(accent_hex: str) -> tuple[QColor, QColor]:
    accent = _hex(accent_hex or "#7dd3fc")
    accent_2 = _mix(accent, QColor("#ffffff"), 0.25)
    return accent, accent_2


def build_theme(settings: dict) -> Theme:
    ui = settings.get("ui", {}) or {}
    preset = str(ui.get("theme_preset", "dark")).lower()
    accent_hex = str(ui.get("accent_color", "#7dd3fc"))
    intensity = float(ui.get("background_intensity", 0.7))
    accent, accent_2 = _accent_pair(accent_hex)

    if preset == "midnight":
        bg_top = _apply_intensity(_hex("#070b12"), intensity)
        bg_bottom = _apply_intensity(_hex("#0b1220"), intensity)
        base = Theme(
            name="midnight",
            bg_top=bg_top,
            bg_bottom=bg_bottom,
            text_primary=_hex("#e8ecff"),
            text_muted=_hex("#8ea0c8"),
            input_bg=_hex("#0b111f"),
            input_border=_hex("#1b263d"),
            button_bg=_hex("#10182b"),
            button_border=_hex("#1b263d"),
            user_bubble_bg=_hex("#182338"),
            user_bubble_border=_hex("#26324a"),
            bot_bubble_bg=_hex("#0d1524"),
            card_bg=_hex("#0c1426"),
            card_border=_hex("#22314d"),
            accent=accent,
            accent_2=accent_2,
        )
    elif preset == "neon":
        bg_top = _apply_intensity(_hex("#0a0f1f"), intensity)
        bg_bottom = _apply_intensity(_hex("#0b1428"), intensity)
        base = Theme(
            name="neon",
            bg_top=bg_top,
            bg_bottom=bg_bottom,
            text_primary=_hex("#eef4ff"),
            text_muted=_hex("#9db2d7"),
            input_bg=_hex("#0f1730"),
            input_border=_hex("#23314a"),
            button_bg=_hex("#132036"),
            button_border=_hex("#23314a"),
            user_bubble_bg=_hex("#1b2842"),
            user_bubble_border=_hex("#2a3b5a"),
            bot_bubble_bg=_hex("#111a32"),
            card_bg=_hex("#0f1a30"),
            card_border=_hex("#243452"),
            accent=accent,
            accent_2=accent_2,
        )
    else:
        bg_top = _apply_intensity(_hex("#0b0f18"), intensity)
        bg_bottom = _apply_intensity(_hex("#111827"), intensity)
        base = Theme(
            name="dark",
            bg_top=bg_top,
            bg_bottom=bg_bottom,
            text_primary=_hex("#e5e7ff"),
            text_muted=_hex("#9aa6c8"),
            input_bg=_hex("#0f1524"),
            input_border=_hex("#20283a"),
            button_bg=_hex("#151b2b"),
            button_border=_hex("#222a40"),
            user_bubble_bg=_hex("#1a2338"),
            user_bubble_border=_hex("#28324a"),
            bot_bubble_bg=_hex("#121a2b"),
            card_bg=_hex("#0f172a"),
            card_border=_hex("#26304a"),
            accent=accent,
            accent_2=accent_2,
        )
    return base


def choose_font() -> str:
    for candidate in ["Segoe UI", "Noto Sans", "Ubuntu", "Roboto", "Arial"]:
        if QFontDatabase.hasFamily(candidate):
            return candidate
    return "Segoe UI"
