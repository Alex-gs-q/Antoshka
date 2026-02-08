from __future__ import annotations

from typing import Dict, Optional

from core.text_norm import normalize_text


APP_ALIASES: Dict[str, str] = {
    "brauzer": "msedge",
    "edge": "msedge",
    "hrom": "chrome",
    "chrome": "chrome",
    "provodnik": "explorer",
    "explorer": "explorer",
    "bloknot": "notepad",
    "notepad": "notepad",
    "kalkulyator": "calc",
    "calc": "calc",
    "dispetcher zadach": "taskmgr",
    "task manager": "taskmgr",
    "powershell": "powershell",
    "terminal": "wt",
    "cmd": "cmd",
    "steam": "steam",
    "telegram": "telegram",
    "discord": "discord",
}


def resolve_app(text: str, custom: Optional[Dict[str, str]] = None) -> Optional[str]:
    if not text:
        return None
    t = normalize_text(text)
    custom = custom or {}
    custom_norm = {normalize_text(k): v for k, v in custom.items()}
    if t in custom_norm:
        return custom_norm[t]
    if t in APP_ALIASES:
        return APP_ALIASES[t]
    return None
