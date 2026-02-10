from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

import unicodedata

from core.text_norm import normalize_text

_DURATION_RE = re.compile(
    r"(?P<num>\d+)\s*(?P<unit>"
    r"секунд[ауы]?|сек|"
    r"минут[ауы]?|мин|"
    r"час(?:а|ов)?|ч|"
    r"sekund[ay]?|sek|"
    r"minut[ay]?|min|"
    r"chas|chasov|ch"
    r")",
    flags=re.IGNORECASE | re.UNICODE,
)


def parse_duration_seconds(text: str) -> Optional[int]:
    raw = (text or "").strip()
    if not raw:
        return None

    raw_norm = unicodedata.normalize("NFKC", raw.lower())
    total = 0

    def apply_matches(target: str) -> int:
        seconds = 0
        for m in _DURATION_RE.finditer(target):
            num = int(m.group("num"))
            unit = m.group("unit")
            if unit.startswith(("сек", "sek")):
                seconds += num
            elif unit.startswith(("мин", "min")):
                seconds += num * 60
            elif unit.startswith(("час", "chas")) or unit == "ч" or unit == "ch":
                seconds += num * 3600
        return seconds

    total = apply_matches(raw_norm)
    if total == 0:
        # fallback to translit normalization for noisy STT
        t = normalize_text(raw)
        total = apply_matches(t)

    return total if total > 0 else None


def parse_time_of_day(text: str) -> Optional[datetime]:
    raw = (text or "").strip()
    m = re.search(r"(?P<h>\d{1,2}):(?P<m>\d{2})", raw)
    if not m:
        t = normalize_text(text)
        m = re.search(r"(?P<h>\d{1,2})[:\s](?P<m>\d{2})", t)
    if not m:
        return None
    h = int(m.group("h"))
    mnt = int(m.group("m"))
    if h > 23 or mnt > 59:
        return None
    now = datetime.now()
    target = now.replace(hour=h, minute=mnt, second=0, microsecond=0)
    if target < now:
        target = target + timedelta(days=1)
    return target


def parse_date(text: str) -> Optional[datetime]:
    raw = (text or "").strip()
    m = re.search(r"(?P<y>\d{4})[-./](?P<mo>\d{1,2})[-./](?P<d>\d{1,2})", raw)
    if not m:
        m = re.search(r"(?P<d>\d{1,2})[./](?P<mo>\d{1,2})[./](?P<y>\d{4})", raw)
    if not m:
        return None
    y = int(m.group("y"))
    mo = int(m.group("mo"))
    d = int(m.group("d"))
    if y < 1900 or mo < 1 or mo > 12 or d < 1 or d > 31:
        return None
    try:
        return datetime(year=y, month=mo, day=d)
    except Exception:
        return None


def parse_date_time(date_text: str, time_text: str) -> Optional[datetime]:
    date = parse_date(date_text)
    if date is None:
        return None
    time_dt = parse_time_of_day(time_text)
    if time_dt is None:
        return None
    return date.replace(hour=time_dt.hour, minute=time_dt.minute, second=0, microsecond=0)
