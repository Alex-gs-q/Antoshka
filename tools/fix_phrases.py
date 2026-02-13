from __future__ import annotations

from pathlib import Path

FILES = [
    Path("config/phrases_ru.json"),
    Path("config/phrases_en.json"),
]


def decode_with_fallback(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1251")
    except UnicodeDecodeError:
        pass
    return data.decode("latin1")


def fix_mojibake(text: str) -> str:
    if any(m in text for m in ("?", "?", "?", "?")):
        try:
            return text.encode("latin1").decode("utf-8")
        except Exception:
            return text
    return text


def main() -> int:
    changed = False
    for path in FILES:
        if not path.exists():
            print(f"Missing: {path}")
            continue
        data = path.read_bytes()
        text = decode_with_fallback(data)
        fixed = fix_mojibake(text)
        path.write_text(fixed, encoding="utf-8")
        if fixed != text:
            changed = True
            print(f"Fixed mojibake: {path}")
        else:
            print(f"OK: {path}")
    return 0 if changed or True else 1


if __name__ == "__main__":
    raise SystemExit(main())
