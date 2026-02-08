from __future__ import annotations

import re
import unicodedata

_PUNCT_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)
_SPACES_RE = re.compile(r"\s+", flags=re.UNICODE)

# Transliteration map (Cyrillic -> Latin)
_CYR_MAP = {
    0x0430: "a", 0x0410: "a",
    0x0431: "b", 0x0411: "b",
    0x0432: "v", 0x0412: "v",
    0x0433: "g", 0x0413: "g",
    0x0434: "d", 0x0414: "d",
    0x0435: "e", 0x0415: "e",
    0x0451: "e", 0x0401: "e",
    0x0436: "zh", 0x0416: "zh",
    0x0437: "z", 0x0417: "z",
    0x0438: "i", 0x0418: "i",
    0x0439: "y", 0x0419: "y",
    0x043a: "k", 0x041a: "k",
    0x043b: "l", 0x041b: "l",
    0x043c: "m", 0x041c: "m",
    0x043d: "n", 0x041d: "n",
    0x043e: "o", 0x041e: "o",
    0x043f: "p", 0x041f: "p",
    0x0440: "r", 0x0420: "r",
    0x0441: "s", 0x0421: "s",
    0x0442: "t", 0x0422: "t",
    0x0443: "u", 0x0423: "u",
    0x0444: "f", 0x0424: "f",
    0x0445: "h", 0x0425: "h",
    0x0446: "ts", 0x0426: "ts",
    0x0447: "ch", 0x0427: "ch",
    0x0448: "sh", 0x0428: "sh",
    0x0449: "sch", 0x0429: "sch",
    0x044a: "", 0x042a: "",
    0x044b: "y", 0x042b: "y",
    0x044c: "", 0x042c: "",
    0x044d: "e", 0x042d: "e",
    0x044e: "yu", 0x042e: "yu",
    0x044f: "ya", 0x042f: "ya",
}

_ALIAS = {
    "yutube": "youtube",
    "yutub": "youtube",
    "vkontakte": "vk",
    "teleaga": "telegram",
    "telegramm": "telegram",
    "diskord": "discord",
    "vatcap": "whatsapp",
    "gugl": "google",
    "yandeks": "yandex",
}


def _transliterate(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if code in _CYR_MAP:
            out.append(_CYR_MAP[code])
        else:
            out.append(ch)
    return "".join(out)


def _apply_aliases(text: str) -> str:
    if not text:
        return ""
    parts = text.split()
    out = []
    for p in parts:
        out.append(_ALIAS.get(p, p))
    return " ".join(out)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    t = unicodedata.normalize("NFKC", t)
    t = _PUNCT_RE.sub(" ", t)
    t = _SPACES_RE.sub(" ", t).strip()
    t = _transliterate(t)
    t = _apply_aliases(t)
    return t
