from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

from core.app_context import AppContext
from core.i18n import help_lines
from core.logger import setup_logger
from core.resources import resource_path
from core.router import CommandRouter
from services.scheduler import Scheduler
from alerts.audio_alerts import AudioAlerts


def _make_router() -> CommandRouter:
    ctx = AppContext(
        notify=lambda _: None,
        data_dir=Path("data"),
        scheduler=Scheduler(notify=lambda _: None),
        volume=None,
        llm_client=None,
    )
    return CommandRouter(ctx)


def _check_i18n() -> List[str]:
    issues: List[str] = []
    r = _make_router()
    cmds = [c.name for c in r.registry.all()]
    ru = "\n".join(help_lines("ru", cmds))
    en = "\n".join(help_lines("en", cmds))
    if re.search(r"[A-Za-z]", ru):
        issues.append("RU help contains Latin letters")
    if re.search(r"[А-Яа-яЁё]", en):
        issues.append("EN help contains Cyrillic")
    return issues


def _check_settings_utf8() -> List[str]:
    issues: List[str] = []
    path = Path("config/settings.json")
    try:
        text = path.read_bytes().decode("utf-8")
        json.loads(text)
    except Exception as e:  # noqa: BLE001
        issues.append(f"settings.json invalid UTF-8 or JSON: {e}")
    return issues


def _check_phrases_utf8() -> List[str]:
    issues: List[str] = []
    path = Path("config/phrases_ru.json")
    try:
        text = path.read_bytes().decode("utf-8")
        if re.search(r"[А-Яа-яЁё]", text) is None:
            issues.append("phrases_ru.json has no Cyrillic")
        json.loads(text)
    except Exception as e:  # noqa: BLE001
        issues.append(f"phrases_ru.json invalid UTF-8 or JSON: {e}")
    return issues


def _router_cases() -> List[Tuple[str, str, str | None]]:
    return [
        ("привет", "greet", None),
        ("помощь", "help", None),
        ("который час", "time", None),
        ("какая дата", "date", None),
        ("открой ютуб", "open_url", None),
        ("найди в интернете фильмы", "search_web", None),
        ("открой заметки", "open_path", None),
        ("создай заметку купить молоко", "note_create", None),
        ("поставь таймер на 5 минут", "timer_set", None),
        ("напомни мне позвонить в 18:30", "reminder_set", None),
        ("очисти чат", "clear_chat", None),
        ("открой почту", "open_mail", None),
        ("открой календарь", "open_calendar", None),
        ("погода", "weather", None),
        ("добавь событие встреча на 10.02.2026 14:00", "event_add", None),
        ("покажи события", "event_list", None),
        ("hello", "greet", "en"),
        ("help", "help", "en"),
        ("what time is it", "time", "en"),
        ("what date is it", "date", "en"),
        ("open youtube", "open_url", "en"),
        ("open mail", "open_mail", "en"),
        ("open calendar", "open_calendar", "en"),
        ("bye", "exit", "en"),
    ]


def _check_router() -> List[str]:
    issues: List[str] = []
    r = _make_router()
    for text, expected, lang in _router_cases():
        res = r.route(text, lang=lang) if lang else r.route(text)
        if res is None:
            issues.append(f"No match for: {text}")
            continue
        if res.name != expected:
            issues.append(f"{text} => {res.name}, expected {expected}")
    return issues


def run_self_test() -> int:
    logger = setup_logger()
    issues: List[str] = []

    issues.extend(_check_i18n())
    issues.extend(_check_settings_utf8())
    issues.extend(_check_phrases_utf8())
    issues.extend(_check_router())
    # audio alerts init + file check
    try:
        _ = AudioAlerts()
    except Exception as e:  # noqa: BLE001
        issues.append(f"AudioAlerts init failed: {e}")
    sound_path = resource_path("Music/Kioko - The Phantom Traveler.mp3")
    if not sound_path.exists():
        issues.append("Alert sound missing: Music/Kioko - The Phantom Traveler.mp3")

    if issues:
        logger.error("Self-test FAILED: %d issue(s)", len(issues))
        for item in issues:
            logger.error("Self-test issue: %s", item)
        print("SELF-TEST: FAIL")
        for item in issues:
            print(" -", item)
        return 1

    logger.info("Self-test PASSED")
    print("SELF-TEST: PASS")
    return 0


def main() -> int:
    return run_self_test()


if __name__ == "__main__":
    raise SystemExit(main())
