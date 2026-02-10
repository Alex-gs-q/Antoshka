from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _check_conflicts() -> List[str]:
    issues: List[str] = []
    conflict_markers = ("<<<<<<<", ">>>>>>>", "=======")
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_dir():
            continue
        if ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if any(m in text for m in conflict_markers):
            issues.append(f"Conflict markers in {path}")
    return issues


def _check_env_gitignore() -> List[str]:
    issues: List[str] = []
    gitignore = PROJECT_ROOT / ".gitignore"
    if not gitignore.exists():
        return [".gitignore not found"]
    gi = gitignore.read_text(encoding="utf-8")
    if ".env" not in gi:
        issues.append(".env is not in .gitignore")
    # ensure .env not tracked
    code, _ = _run(["git", "ls-files", ".env"])
    if code == 0:
        issues.append(".env is tracked by git; remove from repo")
    return issues


def _check_utf8_json(path: Path, label: str) -> List[str]:
    issues: List[str] = []
    try:
        text = path.read_bytes().decode("utf-8")
        json.loads(text)
    except Exception as e:  # noqa: BLE001
        issues.append(f"{label} invalid UTF-8/JSON: {e}")
    return issues


def _check_phrases() -> List[str]:
    issues: List[str] = []
    ru = PROJECT_ROOT / "config/phrases_ru.json"
    en = PROJECT_ROOT / "config/phrases_en.json"
    issues.extend(_check_utf8_json(ru, "phrases_ru.json"))
    issues.extend(_check_utf8_json(en, "phrases_en.json"))
    try:
        text = ru.read_text(encoding="utf-8")
        if re.search(r"[А-Яа-яЁё]", text) is None:
            issues.append("phrases_ru.json has no Cyrillic")
    except Exception:
        pass
    return issues


def _check_settings() -> List[str]:
    return _check_utf8_json(PROJECT_ROOT / "config/settings.json", "settings.json")


def _check_icons() -> List[str]:
    issues: List[str] = []
    icon = PROJECT_ROOT / "assets/icons/app_icon_v3.ico"
    if not icon.exists():
        issues.append("Missing icon: assets/icons/app_icon_v3.ico")
    return issues


def _check_spec_datas() -> List[str]:
    issues: List[str] = []
    spec = PROJECT_ROOT / "Antoshka_pyinstaller.spec"
    if not spec.exists():
        return ["Antoshka_pyinstaller.spec not found"]
    text = spec.read_text(encoding="utf-8")
    required = [
        "config",
        "data",
        "assets/icons",
        "Music",
        "services/audio",
        "services/tts",
    ]
    for item in required:
        if item not in text:
            issues.append(f"Spec missing datas for: {item}")
    return issues


def main() -> int:
    issues: List[str] = []

    # ruff
    code, out = _run(["ruff", "check", "."])
    if code != 0:
        issues.append("ruff check failed")
        print(out)

    # pytest
    code, out = _run(["pytest", "-q"])
    if code != 0:
        issues.append("pytest failed")
        print(out)

    issues.extend(_check_conflicts())
    issues.extend(_check_env_gitignore())
    issues.extend(_check_phrases())
    issues.extend(_check_settings())
    issues.extend(_check_icons())
    issues.extend(_check_spec_datas())

    if issues:
        print("PREBUILD: FAIL")
        for item in issues:
            print(" -", item)
        return 1

    print("PREBUILD: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
