from __future__ import annotations

import re
from typing import Dict, List

_TOKEN_RE = re.compile(r"\w+|[^\w]+", flags=re.UNICODE)
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")


_RU_UNITS: Dict[str, int] = {
    "ноль": 0,
    "нуль": 0,
    "один": 1,
    "одна": 1,
    "одну": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "четыри": 4,
    "пять": 5,
    "пятерка": 5,
    "пятёрка": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "васем": 8,
    "восьим": 8,
    "девять": 9,
}

_RU_TEENS: Dict[str, int] = {
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "шестнадцать": 16,
    "семнадцать": 17,
    "восемнадцать": 18,
    "девятнадцать": 19,
    "двадцать": 20,
}

_RU_TENS: Dict[str, int] = {
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
    "шестьдесят": 60,
    "семьдесят": 70,
    "восемьдесят": 80,
    "девяносто": 90,
}

_RU_HUNDREDS: Dict[str, int] = {
    "сто": 100,
    "двести": 200,
    "триста": 300,
    "четыреста": 400,
    "пятьсот": 500,
}

_EN_UNITS: Dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
}

_EN_TEENS: Dict[str, int] = {
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}

_EN_TENS: Dict[str, int] = {
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

_EN_HUNDREDS: Dict[str, int] = {
    "hundred": 100,
}


def _parse_ru(tokens: List[str], idx: int) -> tuple[int | None, int]:
    total = 0
    consumed = 0
    found = False
    while idx + consumed < len(tokens):
        tok = tokens[idx + consumed].lower()
        if tok.isdigit():
            total += int(tok)
            found = True
            consumed += 1
            continue
        if tok in _RU_HUNDREDS:
            total += _RU_HUNDREDS[tok]
            found = True
            consumed += 1
            continue
        if tok in _RU_TENS:
            total += _RU_TENS[tok]
            found = True
            consumed += 1
            continue
        if tok in _RU_TEENS:
            total += _RU_TEENS[tok]
            found = True
            consumed += 1
            continue
        if tok in _RU_UNITS:
            total += _RU_UNITS[tok]
            found = True
            consumed += 1
            continue
        break
    if not found:
        return None, 0
    return total, consumed


def _parse_en(tokens: List[str], idx: int) -> tuple[int | None, int]:
    total = 0
    consumed = 0
    found = False
    while idx + consumed < len(tokens):
        tok = tokens[idx + consumed].lower()
        if tok.isdigit():
            total += int(tok)
            found = True
            consumed += 1
            continue
        if tok in _EN_HUNDREDS:
            total = max(total, 1) * 100
            found = True
            consumed += 1
            continue
        if tok in _EN_TENS:
            total += _EN_TENS[tok]
            found = True
            consumed += 1
            continue
        if tok in _EN_TEENS:
            total += _EN_TEENS[tok]
            found = True
            consumed += 1
            continue
        if tok in _EN_UNITS:
            total += _EN_UNITS[tok]
            found = True
            consumed += 1
            continue
        break
    if not found:
        return None, 0
    return total, consumed


def normalize_numbers(text: str, lang: str = "auto") -> str:
    if not text:
        return ""
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return text

    use_lang = lang
    if lang == "auto":
        use_lang = "ru" if _CYRILLIC_RE.search(text) else "en"

    out: List[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if not tok.isalnum():
            out.append(tok)
            i += 1
            continue

        j = i
        words: List[str] = []
        word_indexes: List[int] = []
        while j < len(tokens):
            if tokens[j].isspace():
                j += 1
                continue
            if not tokens[j].isalnum():
                break
            words.append(tokens[j])
            word_indexes.append(j)
            j += 1

        if use_lang == "ru":
            val, consumed = _parse_ru(words, 0)
        else:
            val, consumed = _parse_en(words, 0)
        if val is not None and consumed > 0:
            out.append(str(val))
            last_token_index = word_indexes[consumed - 1]
            i = last_token_index + 1
            continue

        out.append(tok)
        i += 1
    return "".join(out)
