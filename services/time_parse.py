from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

from core.text_norm import normalize_text


_DURATION_RE = re.compile(
    r"(?P<num>\d+)\s*(?P<unit>секунд|секунду|сек|минут|минуту|мин|час|часов|ч)",
    flags=re.IGNORECASE | re.UNICODE,
)


def parse_duration_seconds(text: str) -> Optional[int]:
    t = normalize_text(text)
    if not t:
        return None
    m = _DURATION_RE.search(t)
    if not m:
        return None
    num = int(m.group("num"))
    unit = m.group("unit")
    if unit.startswith("сек"):
        return num
    if unit.startswith("мин"):
        return num * 60
    if unit.startswith("час") or unit == "ч":
        return num * 3600
    return None


def parse_time_of_day(text: str) -> Optional[datetime]:
    t = normalize_text(text)
    m = re.search(r"(?P<h>\d{1,2}):(?P<m>\d{2})", t)
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
